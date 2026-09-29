# syntax=docker/dockerfile:1.7
# One image family for the three services, built for linux/arm64 (Oracle Ampere) and amd64:
#   target "app"    -> api and ingest (no ML runtime, small)
#   target "scorer" -> adds CPU-only PyTorch and the pinned model weights, baked in at build time

FROM python:3.12-slim-bookworm AS app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
RUN useradd --system --uid 10001 --create-home app
WORKDIR /app
COPY pyproject.toml constraints.txt ./
COPY sentiment ./sentiment
RUN pip install -c constraints.txt .
USER app
ENTRYPOINT ["sentiment"]

FROM app AS scorer
USER root
RUN pip install -c constraints.txt torch --index-url https://download.pytorch.org/whl/cpu \
 && pip install -c constraints.txt ".[scorer]"
ARG SCORER_MODEL=kumo24/bert-sentiment-nuclear
ARG SCORER_REVISION=883de0dd5f6a1a4a4a5f9e5af9b54863ca44cd57
ENV HF_HOME=/opt/hf
RUN python -c "from huggingface_hub import snapshot_download; \
snapshot_download('${SCORER_MODEL}', revision='${SCORER_REVISION}', allow_patterns=['*.json', '*.txt', '*.safetensors'])" \
 && chmod -R a+rX /opt/hf
# The weights are in the image; never reach out to the Hub at runtime.
ENV HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    SCORER_MODEL=${SCORER_MODEL} \
    SCORER_REVISION=${SCORER_REVISION}
USER app
