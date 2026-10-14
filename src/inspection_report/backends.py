"""Vision-language model backends.

Both backends expose ``describe(image_path, prompt) -> str``. The local backend
runs a small VLM with ``transformers`` on CPU (imported lazily, install the
``local`` extra). The API backend talks to any OpenAI-compatible
``/chat/completions`` endpoint, for example a local Ollama server.
"""

from __future__ import annotations

import base64
import mimetypes
from pathlib import Path
from typing import Protocol

import httpx

from .config import Settings


class Backend(Protocol):
    def describe(self, image_path: Path, prompt: str) -> str: ...


class BackendError(RuntimeError):
    pass


def image_to_data_url(image_path: Path) -> str:
    mime = mimetypes.guess_type(image_path.name)[0] or "image/jpeg"
    data = base64.b64encode(image_path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{data}"


class ApiBackend:
    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str = "",
        client: httpx.Client | None = None,
        timeout: float = 300.0,
    ) -> None:
        self.url = base_url.rstrip("/") + "/chat/completions"
        self.model = model
        self.headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self.client = client or httpx.Client(timeout=timeout)

    def describe(self, image_path: Path, prompt: str) -> str:
        payload = {
            "model": self.model,
            "temperature": 0,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_to_data_url(image_path)}},
                    ],
                }
            ],
        }
        try:
            resp = self.client.post(self.url, json=payload, headers=self.headers)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
            raise BackendError(f"API backend failed: {exc}") from exc


class LocalBackend:
    """Small VLM (default SmolVLM-256M) on CPU via transformers; loaded on first use."""

    def __init__(self, model_name: str, max_new_tokens: int = 400) -> None:
        self.model_name = model_name
        self.max_new_tokens = max_new_tokens
        self._processor = None
        self._model = None

    def _load(self) -> None:
        try:
            from transformers import AutoModelForVision2Seq, AutoProcessor
        except ImportError as exc:  # pragma: no cover - depends on optional extra
            raise BackendError(
                'Local backend needs the extra: pip install -e ".[local]"'
            ) from exc
        self._processor = AutoProcessor.from_pretrained(self.model_name)
        self._model = AutoModelForVision2Seq.from_pretrained(self.model_name).eval()

    def describe(self, image_path: Path, prompt: str) -> str:  # pragma: no cover - needs model
        from PIL import Image

        if self._model is None:
            self._load()
        messages = [
            {"role": "user", "content": [{"type": "image"}, {"type": "text", "text": prompt}]}
        ]
        text = self._processor.apply_chat_template(messages, add_generation_prompt=True)
        image = Image.open(image_path).convert("RGB")
        inputs = self._processor(text=text, images=[image], return_tensors="pt")
        out = self._model.generate(**inputs, max_new_tokens=self.max_new_tokens, do_sample=False)
        new_tokens = out[:, inputs["input_ids"].shape[1] :]
        return self._processor.batch_decode(new_tokens, skip_special_tokens=True)[0].strip()


def get_backend(settings: Settings) -> Backend:
    if settings.backend == "api":
        return ApiBackend(settings.api_base_url, settings.api_model, settings.api_key)
    return LocalBackend(settings.local_model)
