# CosyVoice OpenAI-TTS API

[English](./README.md) · **中文**

一个 [OpenAI TTS](https://platform.openai.com/docs/api-reference/audio/createSpeech) 兼容的 HTTP 服务，对 [CosyVoice 2 / CosyVoice 3](https://github.com/FunAudioLLM/CosyVoice) 进行封装，支持从挂载目录零样本克隆音色。

## 特性

- **OpenAI TTS 兼容**：`POST /v1/audio/speech`，请求体格式与 OpenAI SDK 一致
- **音色克隆**：挂载 `voices/` 目录下的 `xxx.wav` + `xxx.txt` 对，文件名即音色 id
- **单镜像双版本**：同一镜像通过运行时环境变量 `COSYVOICE_VERSION` 选择 CosyVoice 2 或 3（v3 自动拼接指令前缀）
- **2 个镜像**：`cuda`（GPU）和 CPU，各自同时支持 v2 与 v3
- **模型/音色运行时挂载**：不打包进镜像
- **多种输出格式**：`mp3`、`opus`、`aac`、`flac`、`wav`、`pcm`

## 可用镜像

| 镜像 | 设备 |
|---|---|
| `ghcr.io/seancheung/cosyvoice-openai-tts-api:cuda-latest` | CUDA 12.4 |
| `ghcr.io/seancheung/cosyvoice-openai-tts-api:latest`      | CPU |

通过运行时环境变量 `-e COSYVOICE_VERSION=2` 或 `-e COSYVOICE_VERSION=3` 选择 CosyVoice 版本（默认 `3`），并挂载对应的模型目录。

镜像仅构建 `linux/amd64`（`pynini` 在 conda-forge 只有 x86 版本）。

## 快速开始

### 1. 下载模型

模型需要预先下载到本机目录，容器启动时挂载到 `/models`。

CosyVoice 2：

```bash
pip install modelscope
modelscope download --model iic/CosyVoice2-0.5B \
  --local_dir ./models/CosyVoice2-0.5B
```

CosyVoice 3：

```bash
modelscope download --model FunAudioLLM/Fun-CosyVoice3-0.5B-2512 \
  --local_dir ./models/Fun-CosyVoice3-0.5B
```

也可以用 HuggingFace：

```bash
pip install huggingface_hub
huggingface-cli download FunAudioLLM/CosyVoice2-0.5B \
  --local-dir ./models/CosyVoice2-0.5B
```

挂载的目录必须包含对应版本的配置文件：
- v2 需要 `cosyvoice2.yaml`
- v3 需要 `cosyvoice3.yaml`

### 2. 准备音色目录

```
voices/
├── alice.wav     # 参考音频，16kHz 以上，<=30s
├── alice.txt     # UTF-8 纯文本，内容为 alice.wav 中说出的原文
├── bob.wav
└── bob.txt
```

**规则**：必须同时存在同名的 `.wav` 和 `.txt` 才会被识别为有效音色；文件名（不含后缀）即音色 id；多余或缺对的文件会被忽略。

### 3. 运行容器

GPU 版本（推荐）：

```bash
docker run --rm -p 8000:8000 --gpus all \
  -v $PWD/models/Fun-CosyVoice3-0.5B:/models:ro \
  -v $PWD/voices:/voices:ro \
  ghcr.io/seancheung/cosyvoice-openai-tts-api:cuda-latest
```

CPU 版本：

```bash
docker run --rm -p 8000:8000 \
  -v $PWD/models/Fun-CosyVoice3-0.5B:/models:ro \
  -v $PWD/voices:/voices:ro \
  ghcr.io/seancheung/cosyvoice-openai-tts-api:latest
```

切到 CosyVoice 2 只需设置 `-e COSYVOICE_VERSION=2`，并挂载对应的 v2 模型目录。

> **GPU 要求**：宿主机需安装 NVIDIA 驱动与 [nvidia-container-toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)。Windows 需 Docker Desktop + WSL2 + NVIDIA Windows 驱动。

### 4. docker-compose

参考 [`docker/docker-compose.example.yml`](./docker/docker-compose.example.yml)。

## API 用法

服务默认监听 `8000` 端口。

### GET `/v1/audio/voices`

列出所有可用音色。

```bash
curl -s http://localhost:8000/v1/audio/voices | jq
```

返回：

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

返回参考音频本体（`audio/wav`），可用于浏览器 `<audio>` 试听。

### POST `/v1/audio/speech`

OpenAI TTS 兼容接口。

```bash
curl -s http://localhost:8000/v1/audio/speech \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "cosyvoice",
    "input": "你好世界，这是一段测试语音。",
    "voice": "alice",
    "response_format": "mp3",
    "speed": 1.0
  }' \
  -o out.mp3
```

请求字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `model` | string | 接受但忽略（为了与 OpenAI SDK 兼容） |
| `input` | string | 要合成的文本，最长 8000 字符 |
| `voice` | string | 音色 id，必须匹配 `/v1/audio/voices` 中的某一项 |
| `response_format` | string | `mp3`（默认） / `opus` / `aac` / `flac` / `wav` / `pcm` |
| `speed` | float | 语速，范围 `0.25 - 4.0`，默认 `1.0` |

输出音频为单声道 24 kHz；`pcm` 为裸的 s16le 数据，与 OpenAI 默认 `pcm` 格式一致。

### 使用 OpenAI Python SDK

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8000/v1", api_key="sk-noop")

with client.audio.speech.with_streaming_response.create(
    model="cosyvoice",
    voice="alice",
    input="你好世界",
    response_format="mp3",
) as resp:
    resp.stream_to_file("out.mp3")
```

### GET `/healthz`

返回模型版本、采样率与状态，用于健康检查。

## 环境变量

| 变量 | 默认值 | 说明 |
|---|---|---|
| `COSYVOICE_VERSION` | `3` | `2` 或 `3`；运行时选择 CosyVoice 版本 |
| `COSYVOICE_MODEL_DIR` | `/models` | 模型目录或 modelscope ID |
| `COSYVOICE_VOICES_DIR` | `/voices` | 音色目录 |
| `COSYVOICE_FP16` | `false` | 半精度推理（仅 GPU 有意义） |
| `COSYVOICE_LOAD_JIT` | `false` | JIT 编译 flow encoder（仅 v2） |
| `COSYVOICE_LOAD_TRT` | `false` | TensorRT 加速（仅 CUDA） |
| `COSYVOICE_LOAD_VLLM` | `false` | 使用 vLLM 加速 LLM |
| `COSYVOICE_TRT_CONCURRENT` | `1` | TensorRT 并发 |
| `MAX_INPUT_CHARS` | `8000` | `input` 字段上限 |
| `HOST` | `0.0.0.0` | |
| `PORT` | `8000` | |
| `LOG_LEVEL` | `info` | |

## 本地构建镜像

构建前需先初始化 submodule（workflow 已处理）。

```bash
git submodule update --init --recursive

# CUDA 镜像
docker buildx build -f docker/Dockerfile.cuda \
  -t cosyvoice-openai-tts-api:cuda .

# CPU 镜像
docker buildx build -f docker/Dockerfile.cpu \
  -t cosyvoice-openai-tts-api:cpu .
```

## 局限 / 注意事项

- **v3 提示前缀**：CosyVoice 3 要求 `prompt_text` 带 `"You are a helpful assistant.<|endofprompt|>"` 前缀，服务会自动拼接；`voices/*.txt` 中只需放纯原文。
- **并发**：CosyVoice 模型在单实例下非线程安全，服务内部用 asyncio Lock 串行化。并发请求依赖横向扩容（多容器 + 负载均衡）。
- **长文本**：超过 `MAX_INPUT_CHARS`（默认 8000）返回 413；CosyVoice 内部已自动切句。
- **仅 amd64**：`pynini` 仅有 x86 的 conda-forge 构建，ARM 不支持。
- **模型版本匹配**：启动时会校验挂载的模型目录内是否存在 `cosyvoice{2,3}.yaml`，不匹配直接失败。

## 目录结构

```
.
├── CosyVoice/                 # 只读 submodule，不修改
├── app/                       # FastAPI 应用
│   ├── server.py
│   ├── engine.py              # v2/v3 调度与推理
│   ├── voices.py              # 音色扫描
│   ├── audio.py               # 多格式编码
│   ├── config.py
│   └── schemas.py
├── docker/
│   ├── Dockerfile.cuda
│   ├── Dockerfile.cpu
│   ├── requirements.cpu.txt   # CPU 镜像精简版依赖
│   ├── requirements.api.txt
│   ├── entrypoint.sh
│   └── docker-compose.example.yml
├── .github/workflows/
│   └── build-images.yml       # cuda + cpu 矩阵构建
└── README.md
```

## 致谢

基于 [FunAudioLLM/CosyVoice](https://github.com/FunAudioLLM/CosyVoice)（Apache 2.0）。
