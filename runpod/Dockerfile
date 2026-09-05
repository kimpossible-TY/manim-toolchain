# Build for disposable Runpod Linux GPU Pods with:
#   docker build --platform linux/amd64 -f runpod/Dockerfile -t <registry>/manim-blender-worker:5.2.1-pod-slim-py310.20260903 .
# Keep the Blender version pinned so a worker image is reproducible.
FROM nvidia/cuda:12.4.1-base-ubuntu22.04@sha256:8767a245ed2c481eb245d8f6c625accc3788e1fb8612403d6b4cd4645a4f09c7

ARG BLENDER_VERSION=5.2.1
ARG BLENDER_SHA256=a31f524fa99a527d3d52b7f5aaa68c34e1a19d5a1c9473f79c5cc610fd5b10e9

ENV DEBIAN_FRONTEND=noninteractive \
    BLENDER_BIN=/opt/blender/blender \
    RUNPOD_SCRIPTS_DIR=/opt/render/scripts \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        libdbus-1-3 \
        libdrm2 \
        libegl1 \
        libfontconfig1 \
        libgbm1 \
        libgl1 \
        libsm6 \
        libx11-6 \
        libxcursor1 \
        libxfixes3 \
        libxi6 \
        libxinerama1 \
        libxkbcommon0 \
        libxkbcommon-x11-0 \
        libxrandr2 \
        libxrender1 \
        libxxf86vm1 \
        libwayland-client0 \
        python3 \
        python3-pip \
        tar \
        xz-utils \
    && rm -rf /var/lib/apt/lists/* \
    && curl --fail --location --retry 3 \
        "https://download.blender.org/release/Blender5.2/blender-${BLENDER_VERSION}-linux-x64.tar.xz" \
        --output /tmp/blender.tar.xz \
    && echo "${BLENDER_SHA256}  /tmp/blender.tar.xz" | sha256sum --check \
    && tar -xJf /tmp/blender.tar.xz -C /opt \
    && mv "/opt/blender-${BLENDER_VERSION}-linux-x64" /opt/blender \
    && rm /tmp/blender.tar.xz \
    && /opt/blender/blender --background --version

WORKDIR /opt/render
COPY scripts/blender_render.py scripts/blender_cycles.py scripts/verify_frame_sequence.py \
     scripts/runpod_job_utils.py /opt/render/scripts/
COPY runpod/worker/ /opt/render/worker/
RUN chmod 755 /opt/render/worker/pod_start.sh

CMD ["/opt/render/worker/pod_start.sh"]
