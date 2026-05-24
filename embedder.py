"""
AsyncEmbedder — Async OpenAI embeddings with rate-limit handling.
Falls back to mock embeddings if no API key is provided (demo mode).
"""

import asyncio
import logging
import os
import time
from typing import Optional

import numpy as np

logger = logging.getLogger("pipeline.embedder")


class AsyncEmbedder:
    def __init__(self, config):
        self.config = config
        self.model = config.embedding_model
        self._client = None
        self._demo_mode = not bool(config.openai_api_key)

        if self._demo_mode:
            logger.warning(
                "OPENAI_API_KEY not set — running in DEMO MODE (random embeddings)."
            )
        else:
            self._init_client()

    def _init_client(self):
        try:
            import openai
            self._client = openai.AsyncOpenAI(api_key=self.config.openai_api_key)
            logger.info(f"OpenAI client initialized (model: {self.model})")
        except ImportError:
            logger.error("openai package not found. Install with: pip install openai")
            self._demo_mode = True

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts. Uses mock in demo mode."""
        if self._demo_mode:
            return await self._mock_embed(texts)
        return await self._openai_embed(texts)

    async def _openai_embed(self, texts: list[str]) -> list[list[float]]:
        """Call OpenAI Embeddings API."""
        # Truncate texts to avoid token limits (approx 8192 tokens max)
        texts = [t[:8000] for t in texts]
        response = await self._client.embeddings.create(
            model=self.model,
            input=texts,
        )
        return [item.embedding for item in response.data]

    async def _mock_embed(self, texts: list[str]) -> list[list[float]]:
        """Generate deterministic random embeddings for demo/testing."""
        await asyncio.sleep(0.05)  # Simulate network latency
        dim = 1536  # text-embedding-3-small dimension
        result = []
        for text in texts:
            rng = np.random.default_rng(abs(hash(text)) % (2**31))
            vec = rng.standard_normal(dim).astype(np.float32)
            vec /= np.linalg.norm(vec)  # normalize to unit sphere
            result.append(vec.tolist())
        return result
