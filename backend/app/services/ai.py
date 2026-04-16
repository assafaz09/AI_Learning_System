from __future__ import annotations

import logging
from collections.abc import Generator
from pathlib import Path

from openai import OpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)


class AIClient:
    def __init__(self) -> None:
        self.enabled = bool(settings.openai_api_key)
        self.client = OpenAI(api_key=settings.openai_api_key) if self.enabled else None
        self._local_whisper_model = None

    def _require_client(self) -> OpenAI:
        if not self.client:
            raise RuntimeError("OPENAI_API_KEY is missing or empty")
        return self.client

    def _get_local_whisper(self):
        if self._local_whisper_model is None:
            from faster_whisper import WhisperModel
            logger.info("Loading local Whisper model '%s' ...", settings.whisper_local_model)
            self._local_whisper_model = WhisperModel(
                settings.whisper_local_model,
                device="cpu",
                compute_type="int8",
            )
            logger.info("Local Whisper model loaded.")
        return self._local_whisper_model

    def embed(self, text: str) -> list[float]:
        client = self._require_client()
        response = client.embeddings.create(model=settings.openai_embedding_model, input=text)
        return response.data[0].embedding

    def chat(self, system_prompt: str, user_prompt: str) -> str:
        client = self._require_client()
        response = client.chat.completions.create(
            model=settings.openai_chat_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
        )
        return response.choices[0].message.content or ""

    def chat_stream(self, system_prompt: str, user_prompt: str) -> Generator[str, None, None]:
        client = self._require_client()
        stream = client.chat.completions.create(
            model=settings.openai_chat_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                yield delta

    def _transcribe_via_api(self, file_path: Path) -> str:
        client = self._require_client()
        with file_path.open("rb") as audio_file:
            response = client.audio.transcriptions.create(
                model=settings.openai_transcription_model,
                file=audio_file,
            )
        return getattr(response, "text", "") or ""

    def _transcribe_local(self, file_path: Path) -> str:
        model = self._get_local_whisper()
        segments, _info = model.transcribe(str(file_path), beam_size=5)
        return " ".join(segment.text.strip() for segment in segments)

    def transcribe_audio(self, file_path: str | Path) -> str:
        path = Path(file_path)
        if settings.whisper_mode == "api":
            logger.info("Transcribing via OpenAI Whisper API")
            text = self._transcribe_via_api(path)
        else:
            logger.info("Transcribing locally with faster-whisper (%s)", settings.whisper_local_model)
            text = self._transcribe_local(path)

        if not text.strip():
            raise RuntimeError("Transcription returned empty text")
        return text


ai_client = AIClient()
