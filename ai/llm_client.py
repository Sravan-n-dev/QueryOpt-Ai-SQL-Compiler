"""
QueryOpt AI — Gemini LLM Client
===============================
Wrapper around the official google-genai SDK for natural language to SQL translation.
"""

from __future__ import annotations

import os
from typing import Optional


class GeminiClient:
    """Client for generating SQL queries using Google Gemini."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.model_name = model or os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        self._client = None

        if self.api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except Exception:
                self._client = None

    def is_available(self) -> bool:
        """Return True if an API key is configured and SDK client is initialized."""
        return bool(self.api_key and self._client is not None)

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Call the Gemini API and return raw response text."""
        if not self.is_available():
            raise RuntimeError(
                "Gemini API key is not configured. Please set the GEMINI_API_KEY environment variable in your .env file."
            )

        try:
            from google import genai
            from google.genai import types

            response = self._client.models.generate_content(
                model=self.model_name,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.1,
                ),
            )
            return response.text or ""
        except Exception as exc:
            raise RuntimeError(f"Gemini API generation failed: {str(exc)}") from exc
