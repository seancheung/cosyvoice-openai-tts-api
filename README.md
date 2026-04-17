# CosyVoice OpenAI-TTS API

**English** · [中文](./README.zh.md)

An [OpenAI TTS](https://platform.openai.com/docs/api-reference/audio/createSpeech)-compatible HTTP service wrapping [CosyVoice 2 / CosyVoice 3](https://github.com/FunAudioLLM/CosyVoice), with zero-shot voice cloning driven by files dropped into a mounted directory.

## Features

- **OpenAI TTS compatible** — `POST /v1/audio/speech` with the same request shape as the OpenAI SDK
- **Voice cloning** — each voice is a `xxx.wav` + `xxx.txt` pair in a mounted directory; the filename is the voice id
- **Both versions in one image** — CosyVoice 2 or 3 is selected at runtime via `COSYVOICE_VERSION` (v3's instruction prefix is added automatically)
- **2 images** — `cuda` (GPU) and CPU; each supports both v2 and v3
- **Models & voices mounted at runtime** — nothing heavy baked into the image
- **Multiple output formats** — `mp3`, `opus`, `aac`, `flac`, `wav`, `pcm`

## Available images

| Image | Device |
|---|---|
| `ghcr.io/seancheung/cosyvoice-openai-tts-api:cuda-latest` | CUDA 12.4 |
| `ghcr.io/seancheung/cosyvoice-openai-tts-api:latest`      | CPU |

Pick the CosyVoice version at runtime with `-e COSYVOICE_VERSION=2` or `-e COSYVOICE_VERSION=3` (default `3`), and mount the matching model directory.

Images are built for `linux/amd64` only (`pynini` on conda-forge has no ARM build).

## Quick start

### 1. Download a model

Models are kept on the host and mounted into `/models` at runtime.

CosyVoice 2:

```bash
pip install modelscope
modelscope download --model iic/CosyVoice2-0.5B \
  --local_dir ./models/CosyVoice2-0.5B
```

CosyVoice 3:

```bash
modelscope download --model FunAudioLLM/Fun-CosyVoice3-0.5B-2512 \
  --local_dir ./models/Fun-CosyVoice3-0.5B
```

HuggingFace also works:

```bash
pip install huggingface_hub
huggingface-cli download FunAudioLLM/CosyVoice2-0.5B \
  --local-dir ./models/CosyVoice2-0.5B
```

The mounted directory must contain the config file that matches the image version:
- v2 requires `cosyvoice2.yaml`
- v3 requires `cosyvoice3.yaml`

### 2. Prepare the voices directory

```
voices/
├── alice.wav     # reference audio, 16kHz+, <=30s
├── alice.txt     # UTF-8 text: the exact transcript of alice.wav
├── bob.wav
└── bob.txt
```

**Rules**: a voice is valid only when both files with the same stem exist; the stem is the voice id; unpaired or extra files are ignored.

### 3. Run the container

GPU (recommended):

```bash
docker run --rm -p 8000:8000 --gpus all \
  -v $PWD/models/Fun-CosyVoice3-0.5B:/models:ro \
  -v $PWD/voices:/voices:ro \
  ghcr.io/seancheung/cosyvoice-openai-tts-api:cuda-latest
```

CPU:

```bash
docker run --rm -p 8000:8000 \
  -v $PWD/models/Fun-CosyVoice3-0.5B:/models:ro \
  -v $PWD/voices:/voices:ro \
  ghcr.io/seancheung/cosyvoice-openai-tts-api:latest
```

For CosyVoice 2, set `-e COSYVOICE_VERSION=2` and mount the matching v2 model directory.

> **GPU prerequisites**: NVIDIA driver + [nvidia-container-toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) on Linux. On Windows use Docker Desktop + WSL2 + NVIDIA Windows driver (R470+); no host CUDA toolkit required.

### 4. docker-compose

See [`docker/docker-compose.example.yml`](./docker/docker-compose.example.yml).

## API usage

The service listens on port `8000` by default.

### GET `/v1/audio/voices`

List all usable voices.

```bash
curl -s http://localhost:8000/v1/audio/voices | jq
```

Response:

```json
{
  "object": "list",
  "data": [
    {
      "id": "alice",
      "preview_url": "http://localhost:8000/v1/audio/voices/preview?id=alice",
      "prompt_text": "希望你以后能够做的比我还好呦。"
    }
  ]
}
```

### GET `/v1/audio/voices/preview?id={id}`

Returns the raw reference wav (`audio/wav`), suitable for a browser `<audio>` element.

### POST `/v1/audio/speech`

OpenAI TTS-compatible endpoint.

```bash
curl -s http://localhost:8000/v1/audio/speech \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "cosyvoice",
    "input": "Hello world, this is a test.",
    "voice": "alice",
    "response_format": "mp3",
    "speed": 1.0
  }' \
  -o out.mp3
```

Request fields:

| Field | Type | Description |
|---|---|---|
| `model` | string | Accepted but ignored (for OpenAI SDK compatibility) |
| `input` | string | Text to synthesize, up to 8000 characters |
| `voice` | string | Voice id — must match an entry from `/v1/audio/voices` |
| `response_format` | string | `mp3` (default) / `opus` / `aac` / `flac` / `wav` / `pcm` |
| `speed` | float | Playback speed, `0.25 - 4.0`, default `1.0` |

Output audio is mono 24 kHz; `pcm` is raw s16le, matching OpenAI's default `pcm` format.

### Using the OpenAI Python SDK

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8000/v1", api_key="sk-noop")

with client.audio.speech.with_streaming_response.create(
    model="cosyvoice",
    voice="alice",
    input="Hello world",
    response_format="mp3",
) as resp:
    resp.stream_to_file("out.mp3")
```

### GET `/healthz`

Returns model version, sample rate, and status for health checks.

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `COSYVOICE_VERSION` | `3` | `2` or `3`; selects the CosyVoice version at runtime |
| `COSYVOICE_MODEL_DIR` | `/models` | Model directory or modelscope id |
| `COSYVOICE_VOICES_DIR` | `/voices` | Voices directory |
| `COSYVOICE_FP16` | `false` | Half-precision inference (GPU only) |
| `COSYVOICE_LOAD_JIT` | `false` | JIT-compile flow encoder (v2 only) |
| `COSYVOICE_LOAD_TRT` | `false` | TensorRT acceleration (CUDA only) |
| `COSYVOICE_LOAD_VLLM` | `false` | vLLM LLM backend |
| `COSYVOICE_TRT_CONCURRENT` | `1` | TensorRT concurrency |
| `MAX_INPUT_CHARS` | `8000` | Upper bound for the `input` field |
| `HOST` | `0.0.0.0` | |
| `PORT` | `8000` | |
| `LOG_LEVEL` | `info` | |

## Building images locally

Initialize the submodule first (the workflow does this automatically).

```bash
git submodule update --init --recursive

# CUDA image
docker buildx build -f docker/Dockerfile.cuda \
  -t cosyvoice-openai-tts-api:cuda .

# CPU image
docker buildx build -f docker/Dockerfile.cpu \
  -t cosyvoice-openai-tts-api:cpu .
```

## Caveats

- **v3 prompt prefix** — CosyVoice 3 expects `prompt_text` to begin with `"You are a helpful assistant.<|endofprompt|>"`. The service prepends it automatically; keep `voices/*.txt` as plain transcripts.
- **Concurrency** — a single CosyVoice instance is not thread-safe; the service serializes inference with an asyncio Lock. Scale out by running more containers behind a load balancer.
- **Long text** — requests whose `input` exceeds `MAX_INPUT_CHARS` (default 8000) return 413; CosyVoice itself handles sentence splitting internally.
- **amd64 only** — `pynini` has no ARM conda-forge build.
- **Version matching** — on startup the service checks the mounted model for `cosyvoice{2,3}.yaml` that matches `COSYVOICE_VERSION`; a mismatch fails fast.

## Project layout

```
.
├── CosyVoice/                 # read-only submodule, never modified
├── app/                       # FastAPI application
│   ├── server.py
│   ├── engine.py              # v2/v3 dispatch and inference
│   ├── voices.py              # voices directory scanner
│   ├── audio.py               # multi-format encoder
│   ├── config.py
│   └── schemas.py
├── docker/
│   ├── Dockerfile.cuda
│   ├── Dockerfile.cpu
│   ├── requirements.cpu.txt   # trimmed deps for CPU image
│   ├── requirements.api.txt
│   ├── entrypoint.sh
│   └── docker-compose.example.yml
├── .github/workflows/
│   └── build-images.yml       # cuda + cpu matrix build
└── README.md
```

## Acknowledgements

Built on top of [FunAudioLLM/CosyVoice](https://github.com/FunAudioLLM/CosyVoice) (Apache 2.0).
