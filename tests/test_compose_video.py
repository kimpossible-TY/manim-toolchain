"""Tests for hardware-accelerated video composition."""

import sys
import unittest
from pathlib import Path

from scripts.compose_video import (
    get_available_encoders,
    get_optimal_encoder_args,
)


class TestComposeVideo(unittest.TestCase):
    def test_get_available_encoders(self) -> None:
        encoders = get_available_encoders()
        self.assertIsInstance(encoders, set)
        self.assertTrue(len(encoders) > 0)

    def test_optimal_encoder_on_darwin(self) -> None:
        encoders = get_available_encoders()
        h264_args = get_optimal_encoder_args("h264", bitrate="10M")
        self.assertIn("-pix_fmt", h264_args)
        self.assertIn("yuv420p", h264_args)

        if sys.platform == "darwin" and "h264_videotoolbox" in encoders:
            self.assertIn("h264_videotoolbox", h264_args)
            self.assertIn("10M", h264_args)

    def test_hevc_encoder_selection(self) -> None:
        encoders = get_available_encoders()
        hevc_args = get_optimal_encoder_args("hevc")
        if sys.platform == "darwin" and "hevc_videotoolbox" in encoders:
            self.assertIn("hevc_videotoolbox", hevc_args)
            self.assertIn("-tag:v", hevc_args)
            self.assertIn("hvc1", hevc_args)


if __name__ == "__main__":
    unittest.main()
