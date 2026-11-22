"""
QueryOpt AI — Azure OpenAI LLM Client
=====================================
Uses the official OpenAI Python SDK with an Azure OpenAI v1 endpoint.
The configured Azure deployment name is passed as the request's model value.
"""

from __future__ import annotations

import os
from typing import Optional, Tuple
from urllib.parse import urlparse

from config.settings import get_settings


class AzureOpenAIClient:
    """Generate text with an Azure OpenAI model deployment."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None,
        deployment: Optional[str] = None,
    ):
        settings = get_settings()
        self.api_key = (api_key if api_key is not None else settings.azure_openai_api_key or "").strip()
        self.endpoint = self._normalize_endpoint(
            endpoint if endpoint is not None else settings.azure_openai_endpoint or ""
        )
        self.deployment_name = (
            deployment if deployment is not None else settings.azure_openai_deployment
        ).strip() or "gpt-5-mini"
        # Kept as an alias because the UI's stats endpoint historically used model_name.
        self.model_name = self.deployment_name
        self._client = None

        if self.api_key and self.endpoint:
            self._init_sdk()

    @staticmethod
    def _normalize_endpoint(endpoint: str) -> str:
        """Normalize the Azure resource endpoint, not a deployment-specific URL."""
        clean = (endpoint or "").strip().rstrip("/")
        if clean.endswith("/openai/v1"):
            clean = clean[: -len("/openai/v1")].rstrip("/")
        return clean

    @staticmethod
    def _validate_endpoint(endpoint: str) -> Optional[str]:
        parsed = urlparse(endpoint)
        if parsed.scheme != "https" or not parsed.netloc:
            return "Enter the HTTPS Azure OpenAI resource endpoint, for example https://your-resource.openai.azure.com."
        if parsed.query or parsed.fragment:
            return "The Azure endpoint must not contain a query string or fragment."
        return None

    @staticmethod
    def _build_sdk_client(api_key: str, endpoint: str):
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError(
                "The OpenAI Python SDK is not installed. Run: pip install -r requirements.txt"
            ) from exc

        base_url = f"{endpoint.rstrip('/')}/openai/v1/"
        return OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=45.0,
            max_retries=2,
        )

    def _init_sdk(self) -> bool:
        if not self.api_key or not self.endpoint:
            self._client = None
            return False
        try:
            endpoint_error = self._validate_endpoint(self.endpoint)
            if endpoint_error:
                self._client = None
                return False
            self._client = self._build_sdk_client(self.api_key, self.endpoint)
            return True
        except Exception:
            self._client = None
            return False

    def is_available(self) -> bool:
        """Return True when credentials and an SDK client are configured."""
        return bool(self.api_key and self.endpoint and self._client is not None)

    def clear(self) -> None:
        """Clear Azure credentials from this process."""
        self.api_key = ""
        self.endpoint = ""
        self.deployment_name = "gpt-5-mini"
        self.model_name = self.deployment_name
        self._client = None
        os.environ.pop("AZURE_OPENAI_API_KEY", None)
        os.environ.pop("AZURE_OPENAI_ENDPOINT", None)
        os.environ.pop("AZURE_OPENAI_DEPLOYMENT", None)

    def configure(
        self,
        endpoint: str,
        api_key: str,
        deployment: str = "gpt-5-mini",
        test_connection: bool = True,
    ) -> Tuple[bool, str]:
        """Configure the Azure deployment and optionally verify it with a real call.

        An empty API-key field reuses the key already configured in this process,
        allowing users to change the endpoint or deployment without retyping it.
        """
        clean_endpoint = self._normalize_endpoint(endpoint)
        clean_key = (api_key or self.api_key).strip()
        clean_deployment = (deployment or "gpt-5-mini").strip()

        endpoint_error = self._validate_endpoint(clean_endpoint)
        if endpoint_error:
            return False, endpoint_error
        if not clean_key:
            return False, "Enter an Azure OpenAI API key from your Azure resource."
        if not clean_deployment:
            return False, "Enter the Azure model deployment name."

        try:
            candidate_client = self._build_sdk_client(clean_key, clean_endpoint)
            if test_connection:
                response = candidate_client.responses.create(
                    model=clean_deployment,
                    input="Reply with only the word PONG.",
                    # GPT-5 reasoning tokens count against max_output_tokens. A very
                    # small cap (such as 32) can end the response before visible text.
                    max_output_tokens=4096,
                    reasoning={"effort": "minimal"},
                    text={"format": {"type": "text"}},
                )
                if not self._extract_output_text(response):
                    return False, self._empty_response_message(response)
        except Exception as exc:
            return False, f"Azure OpenAI connection test failed: {self._friendly_error(exc)}"

        # Update the active configuration only after the optional test succeeds.
        self.api_key = clean_key
        self.endpoint = clean_endpoint
        self.deployment_name = clean_deployment
        self.model_name = clean_deployment
        self._client = candidate_client
        os.environ["AZURE_OPENAI_API_KEY"] = clean_key
        os.environ["AZURE_OPENAI_ENDPOINT"] = clean_endpoint
        os.environ["AZURE_OPENAI_DEPLOYMENT"] = clean_deployment
        return True, f"Connected to Azure OpenAI deployment '{clean_deployment}' successfully."

    @staticmethod
    def _extract_output_text(response) -> str:
        """Extract visible text from a Responses API object.

        ``output_text`` is the convenient SDK property, but inspecting message
        content as a fallback makes diagnostics more robust across SDK versions.
        Reasoning items are intentionally not treated as user-facing output.
        """
        text = (getattr(response, "output_text", "") or "").strip()
        if text:
            return text

        for item in getattr(response, "output", None) or []:
            if getattr(item, "type", None) != "message":
                continue
            for content in getattr(item, "content", None) or []:
                content_type = getattr(content, "type", None)
                if content_type in {"output_text", "text"}:
                    value = getattr(content, "text", "") or ""
                    if value.strip():
                        return value.strip()
        return ""

    @staticmethod
    def _empty_response_message(response) -> str:
        """Explain why a successful API request did not contain visible text."""
        status = getattr(response, "status", None)
        details = getattr(response, "incomplete_details", None)
        reason = getattr(details, "reason", None) if details is not None else None
        if status == "incomplete" and reason == "max_output_tokens":
            return (
                "Azure accepted the request, but GPT-5 mini used the output-token "
                "budget for reasoning before producing text. The connection test "
                "now uses a larger token budget; restart the app and try again."
            )
        if status == "incomplete":
            return (
                f"Azure returned an incomplete response"
                f"{f' ({reason})' if reason else ''}. Try again or check the model deployment."
            )
        if status and status not in {"completed", "succeeded"}:
            return f"Azure returned response status '{status}' without visible text. Check the deployment and try again."
        return (
            "Azure completed the request but returned no visible text. "
            "Check the deployment's model/version support and Azure content-filter results."
        )

    @staticmethod
    def _friendly_error(exc: Exception) -> str:
        """Return a useful error without exposing request headers or credentials."""
        message = str(exc).replace("\n", " ").strip()
        if len(message) > 700:
            message = message[:697] + "..."
        status_code = getattr(exc, "status_code", None)
        if status_code == 401:
            return "Authentication failed (HTTP 401). Check the Azure OpenAI key."
        if status_code == 403:
            return "Access denied (HTTP 403). Check resource access and subscription permissions."
        if status_code == 404:
            return "Resource or deployment not found (HTTP 404). Verify the endpoint and deployment name."
        if status_code == 429:
            return "Rate limit or quota exceeded (HTTP 429). Check deployment capacity and quota."
        return message or exc.__class__.__name__

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Call Azure OpenAI Responses API and return generated text."""
        if not self.is_available():
            raise RuntimeError(
                "Azure OpenAI is not configured. Set AZURE_OPENAI_ENDPOINT, "
                "AZURE_OPENAI_API_KEY, and AZURE_OPENAI_DEPLOYMENT in your .env file."
            )

        try:
            response = self._client.responses.create(
                model=self.deployment_name,
                instructions=system_prompt,
                input=user_prompt,
                # The output budget includes hidden GPT-5 reasoning tokens.
                # 4096 leaves room for reasoning plus the structured SQL response.
                max_output_tokens=8192,
                reasoning={"effort": "minimal"},
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "nl_to_sql_result",
                        "strict": True,
                        "schema": {
                            "type": "object",
                            "properties": {
                                "sql": {"type": "string"},
                                "explanation": {"type": "string"},
                                "assumptions": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                            },
                            "required": ["sql", "explanation", "assumptions"],
                            "additionalProperties": False,
                        },
                    }
                },
            )
            output = self._extract_output_text(response)
            if not output:
                raise RuntimeError(self._empty_response_message(response))
            return output
        except Exception as exc:
            raise RuntimeError(f"Azure OpenAI API error: {self._friendly_error(exc)}") from exc
