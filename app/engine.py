from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import List

log = logging.getLogger(__name__)

V3_PROMPT_PREFIX = "You are a helpful assistant.<|endofprompt|>"

_DEFAULT_COSYVOICE_PATHS = (
    os.environ.get("COSYVOICE_REPO_DIR", "/opt/CosyVoice"),
)


def _ensure_sys_path() -> None:
    for base in _DEFAULT_COSYVOICE_PATHS:
        if not base:
            continue
        matcha = str(Path(base) / "third_party" / "Matcha-TTS")
        for p in (base, matcha):
            if p not in sys.path and Path(p).exists():
                sys.path.insert(0, p)


_ensure_sys_path()


class TTSEngine:
    def __init__(self, settings):
        from cosyvoice.cli.cosyvoice import CosyVoice2, CosyVoice3

        self.version = settings.cosyvoice_version
        self.model_dir = settings.cosyvoice_model_dir
        self._validate_model_dir()

        common_kwargs = dict(
            load_trt=settings.cosyvoice_load_trt,
            load_vllm=settings.cosyvoice_load_vllm,
            fp16=settings.cosyvoice_fp16,
            trt_concurrent=settings.cosyvoice_trt_concurrent,
        )

        log.info("loading CosyVoice%s from %s (%s)", self.version, self.model_dir, common_kwargs)
        if self.version == "2":
            self.model = CosyVoice2(
                self.model_dir,
                load_jit=settings.cosyvoice_load_jit,
                **common_kwargs,
            )
        else:
            self.model = CosyVoice3(self.model_dir, **common_kwargs)

        self.sample_rate = int(self.model.sample_rate)
        self._lock = asyncio.Lock()
        log.info("engine ready: version=%s sample_rate=%s", self.version, self.sample_rate)

    def _validate_model_dir(self) -> None:
        p = Path(self.model_dir)
        if not p.exists() or not p.is_dir():
            log.warning(
                "model_dir %s not a local directory; CosyVoice will try to download via modelscope",
                self.model_dir,
            )
            return
        expected = f"cosyvoice{self.version}.yaml"
        if not (p / expected).exists():
            candidates = [f.name for f in p.glob("cosyvoice*.yaml")]
            raise RuntimeError(
                f"model_dir {p} does not contain {expected}; found {candidates}. "
                f"Mount the correct model for CosyVoice{self.version}."
            )

    def format_prompt(self, text: str) -> str:
        if self.version != "3":
            return text
        if text.startswith("You are") and "<|endofprompt|>" in text:
            return text
        return V3_PROMPT_PREFIX + text

    async def synthesize(self, tts_text: str, prompt_text: str, prompt_wav: str, speed: float = 1.0):
        prompt_text = self.format_prompt(prompt_text)

        async with self._lock:
            tensor = await asyncio.to_thread(
                self._run_inference, tts_text, prompt_text, prompt_wav, speed
            )
        return tensor

    def _run_inference(self, tts_text: str, prompt_text: str, prompt_wav: str, speed: float):
        import torch

        chunks: List = []
        for out in self.model.inference_zero_shot(
            tts_text,
            prompt_text,
            prompt_wav,
            zero_shot_spk_id="",
            stream=False,
            speed=speed,
            text_frontend=True,
        ):
            chunks.append(out["tts_speech"])
        if not chunks:
            raise RuntimeError("inference produced no audio")
        return torch.cat(chunks, dim=1)
