from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False, extra="ignore")

    cosyvoice_version: Literal["2", "3"] = Field(default="2")
    cosyvoice_model_dir: str = Field(default="/models")
    cosyvoice_voices_dir: str = Field(default="/voices")

    cosyvoice_fp16: bool = Field(default=False)
    cosyvoice_load_jit: bool = Field(default=False)
    cosyvoice_load_trt: bool = Field(default=False)
    cosyvoice_load_vllm: bool = Field(default=False)
    cosyvoice_trt_concurrent: int = Field(default=1)

    max_input_chars: int = Field(default=8000)
    default_response_format: Literal["mp3", "opus", "aac", "flac", "wav", "pcm"] = Field(default="mp3")

    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    log_level: str = Field(default="info")

    @field_validator("cosyvoice_version", mode="before")
    @classmethod
    def _coerce_version(cls, v):
        if v is None:
            return "2"
        return str(v).strip()

    @property
    def voices_path(self) -> Path:
        return Path(self.cosyvoice_voices_dir)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
