#!/bin/sh
# Install the scorer's ML runtime exactly as the container does, from the pinned constraints.
# PyTorch comes from its CPU-only index (no CUDA download on x86), everything else from PyPI:
# the CPU index does not mirror current versions of torch's own dependencies.
set -eu
cd "$(dirname "$0")/.."
torch_version=$(sed -n 's/^torch==//p' constraints.txt)
pip install --no-deps "torch==${torch_version}" --index-url https://download.pytorch.org/whl/cpu
pip install -c constraints.txt ".[scorer]"
python -c "import torch, transformers; print('torch', torch.__version__, '| transformers', transformers.__version__)"
