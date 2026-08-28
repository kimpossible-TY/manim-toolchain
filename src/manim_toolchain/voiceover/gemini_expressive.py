"""Gemini TTS service with semantic delivery prompts and cache-safe inputs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from manim_voiceover._typing import JsonValue, VoiceoverData
from manim_voiceover.helper import remove_bookmarks
from manim_voiceover.services.base import PathLike, initialize_speech_service, path_to_string
from manim_voiceover.services.gemini import (
    DEFAULT_GEMINI_TTS_MODEL,
    DEFAULT_GEMINI_VOICE,
    GeminiAuthMode,
    GeminiService,
    _extract_pcm_audio,
    _write_wave_file,
    types,
)

from ..narration import (
    DEFAULT_NARRATION_PROFILE,
    GeminiPromptBuilder,
    GeminiSpeechRenderer,
    NarrationProfile,
    NarrationSegment,
)
from ..narration.renderer import SpeechRequest


class ExpressiveGeminiService(GeminiService):
    """A compatible Gemini service that sends a compact performance direction prompt.

    Plain Manim Voiceover calls remain valid.  When a scene supplies a
    ``NarrationSegment``, its semantic delivery values are resolved before the
    request and included in the cache input.
    """

    supports_narration_segments = True

    def __init__(
        self,
        voice: str = DEFAULT_GEMINI_VOICE,
        model: str = DEFAULT_GEMINI_TTS_MODEL,
        transcription_model: str | None = None,
        auth_mode: GeminiAuthMode | None = None,
        project: str | None = None,
        location: str | None = None,
        *,
        profile: NarrationProfile | None = None,
        scene_context: str | None = None,
        prompt_builder: GeminiPromptBuilder | None = None,
        client: Any | None = None,
        **kwargs: object,
    ) -> None:
        self.profile = profile or DEFAULT_NARRATION_PROFILE
        if not isinstance(self.profile, NarrationProfile):
            raise TypeError("profile must be a NarrationProfile")
        self.scene_context = self._normalise_optional_text(scene_context, "scene_context")
        self.renderer = GeminiSpeechRenderer(prompt_builder)

        if client is None:
            super().__init__(
                voice=voice,
                model=model,
                transcription_model=transcription_model,
                auth_mode=auth_mode,
                project=project,
                location=location,
                **kwargs,
            )
        else:
            # Dependency injection keeps unit tests fully offline while using
            # the same SpeechService cache and timing integration as production.
            self.voice = voice
            self.model = model
            initialize_speech_service(self, kwargs, transcription_model=transcription_model)
            self.client = client

    def set_narration_profile(self, profile: NarrationProfile) -> None:
        if not isinstance(profile, NarrationProfile):
            raise TypeError("profile must be a NarrationProfile")
        self.profile = profile

    def generate_from_text(
        self,
        text: str,
        cache_dir: PathLike | None = None,
        path: PathLike | None = None,
        *,
        narration_segment: NarrationSegment | None = None,
        narration_profile: NarrationProfile | None = None,
        scene_context: str | None = None,
        **kwargs: object,
    ) -> VoiceoverData:
        """Render plain text or a structured segment without leaking directions to captions."""

        del kwargs
        if cache_dir is None:
            cache_dir = self.cache_dir
        cache_path = Path(cache_dir)
        cache_path.mkdir(parents=True, exist_ok=True)

        if narration_segment is None:
            narration_segment = NarrationSegment(text=text)
        if not isinstance(narration_segment, NarrationSegment):
            raise TypeError("narration_segment must be a NarrationSegment")
        profile = narration_profile or self.profile
        if not isinstance(profile, NarrationProfile):
            raise TypeError("narration_profile must be a NarrationProfile")
        request = self.renderer.build_request(
            narration_segment,
            profile,
            scene_context=self._normalise_optional_text(scene_context, "scene_context") or self.scene_context,
        )
        input_text = remove_bookmarks(request.transcript)
        input_data = self._input_data_for_request(input_text, request)

        cached_result = self.get_cached_result(input_data, cache_path)
        if cached_result is not None:
            return cached_result

        audio_path = self.get_audio_basename(input_data) + ".wav" if path is None else path_to_string(path)
        response = self.client.models.generate_content(
            model=self.model,
            contents=request.prompt,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=self.voice)
                    )
                ),
            ),
        )
        _write_wave_file(cache_path / audio_path, _extract_pcm_audio(response))
        return {
            "input_text": request.transcript,
            "input_data": input_data,
            "original_audio": audio_path,
        }

    def _input_data_for_request(self, input_text: str, request: SpeechRequest) -> dict[str, JsonValue]:
        return {
            "input_text": input_text,
            "service": "gemini-expressive",
            "config": {
                "voice": self.voice,
                "model": self.model,
                "profile": request.resolved.profile.cache_dict(),
                "delivery": request.resolved.cache_dict(),
                "prompt_version": self.renderer.prompt_builder.prompt_version,
            },
        }

    @staticmethod
    def _normalise_optional_text(value: str | None, field_name: str) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise TypeError(f"{field_name} must be a string or None")
        normalised = " ".join(value.split())
        if not normalised:
            raise ValueError(f"{field_name} must not be empty when provided")
        return normalised
