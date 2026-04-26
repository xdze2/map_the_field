# LLM Validation Setup

Local LLM inference for `llm_validate.py` using llama.cpp via Docker.

## Hardware context

- GPU: Quadro K2200 — 4GB VRAM, ~2.2GB free at runtime
- Ollama 0.18.x has a runner bug causing segfaults on 3b+ models on this machine
- llama.cpp (Docker) works correctly — confirmed 2026-04-26

## Prerequisites

- Docker Engine + NVIDIA Container Toolkit installed
- Model file downloaded to `/media/data/llm_models/`

### Install Docker (Ubuntu)

```bash
sudo apt-get remove docker docker-engine docker.io containerd runc
sudo apt-get update && sudo apt-get install ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker $USER && newgrp docker
```

### Install NVIDIA Container Toolkit

```bash
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

Verify GPU passthrough:

```bash
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
```

## Download a model

```bash
pip install huggingface-hub
huggingface-cli download \
  Qwen/Qwen2.5-3B-Instruct-GGUF \
  qwen2.5-3b-instruct-q4_k_m.gguf \
  --local-dir /media/data/llm_models
```

## Start the llama.cpp server

```bash
docker run -d --gpus all \
  -v /media/data/llm_models:/models \
  -p 8083:8080 \
  ghcr.io/ggml-org/llama.cpp:server-cuda \
  -m /models/qwen2.5-3b-instruct-q4_k_m.gguf \
  --n-gpu-layers 15 \
  --ctx-size 2048
```

- Host port 8083 → container port 8080 (llama.cpp default)
- `--n-gpu-layers 15` — tune down if you get OOM errors
- `--ctx-size 2048` — keeps KV cache within available VRAM

Check it's running:

```bash
docker ps
curl http://localhost:8083/health
```

Stop it:

```bash
docker stop <container_id>
```

## Run llm_validate.py

```bash
source tools/venv/bin/activate
pip install openai  # one-time

# validate all DDG files
python tools/llm_validate.py --provider llamacpp

# validate specific SIRENs
python tools/llm_validate.py --provider llamacpp 123456789 987654321

# dry-run (print prompts only)
python tools/llm_validate.py --provider llamacpp --dry-run

# custom server URL or model
python tools/llm_validate.py --provider llamacpp --llamacpp-url http://localhost:8083/v1 --model qwen2.5-3b-instruct-q4_k_m.gguf
```

Use `--provider ollama` to fall back to Ollama (if the bug is fixed in a future version).
