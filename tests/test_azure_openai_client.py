"""Unit tests for the Azure OpenAI client using a mocked OpenAI SDK."""

import sys
from types import ModuleType, SimpleNamespace

from ai.llm_client import AzureOpenAIClient


class FakeResponses:
    def __init__(self):
        self.calls = []
        self.next_response = SimpleNamespace(output_text="PONG", status="completed")

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.next_response


class FakeOpenAI:
    instances = []

    def __init__(self, *, api_key, base_url, timeout, max_retries):
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.responses = FakeResponses()
        self.instances.append(self)


def install_fake_sdk(monkeypatch):
    FakeOpenAI.instances.clear()
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "gpt-5-mini")
    fake_module = ModuleType("openai")
    fake_module.OpenAI = FakeOpenAI
    monkeypatch.setitem(sys.modules, "openai", fake_module)


def test_configure_uses_azure_v1_endpoint_deployment_and_safe_test_budget(monkeypatch):
    install_fake_sdk(monkeypatch)
    client = AzureOpenAIClient(api_key="", endpoint="", deployment="gpt-5-mini")

    ok, message = client.configure(
        endpoint="https://example-resource.openai.azure.com/openai/v1/",
        api_key="fake-key",
        deployment="gpt-5-mini",
        test_connection=True,
    )

    assert ok is True
    assert "gpt-5-mini" in message
    sdk_client = FakeOpenAI.instances[-1]
    assert sdk_client.base_url == "https://example-resource.openai.azure.com/openai/v1/"
    assert sdk_client.api_key == "fake-key"
    request = sdk_client.responses.calls[0]
    assert request["model"] == "gpt-5-mini"
    assert request["max_output_tokens"] >= 4096
    assert request["reasoning"] == {"effort": "minimal"}
    assert request["text"]["format"]["type"] == "text"
    assert client.is_available() is True


def test_configure_reports_incomplete_response(monkeypatch):
    install_fake_sdk(monkeypatch)
    client = AzureOpenAIClient(api_key="", endpoint="", deployment="gpt-5-mini")
    FakeOpenAI.instances.clear()

    original_init = FakeOpenAI.__init__

    def init_with_incomplete(self, **kwargs):
        original_init(self, **kwargs)
        self.responses.next_response = SimpleNamespace(
            output_text="",
            status="incomplete",
            incomplete_details=SimpleNamespace(reason="max_output_tokens"),
            output=[],
        )

    FakeOpenAI.__init__ = init_with_incomplete
    try:
        ok, message = client.configure(
            endpoint="https://example-resource.openai.azure.com",
            api_key="fake-key",
            deployment="gpt-5-mini",
            test_connection=True,
        )
    finally:
        FakeOpenAI.__init__ = original_init

    assert ok is False
    assert "output-token budget" in message


def test_generate_sends_strict_json_schema_with_reasoning_budget(monkeypatch):
    install_fake_sdk(monkeypatch)
    client = AzureOpenAIClient(api_key="", endpoint="", deployment="gpt-5-mini")
    ok, _ = client.configure(
        endpoint="https://example-resource.openai.azure.com",
        api_key="fake-key",
        deployment="gpt-5-mini",
        test_connection=False,
    )
    assert ok is True

    output = client.generate("system instructions", "translate this question")
    request = FakeOpenAI.instances[-1].responses.calls[-1]

    assert output == "PONG"
    assert request["model"] == "gpt-5-mini"
    assert request["instructions"] == "system instructions"
    assert request["input"] == "translate this question"
    assert request["max_output_tokens"] >= 8192
    assert request["reasoning"] == {"effort": "minimal"}
    assert request["text"]["format"]["type"] == "json_schema"
    assert request["text"]["format"]["strict"] is True


def test_extracts_message_text_when_output_text_helper_is_empty(monkeypatch):
    install_fake_sdk(monkeypatch)
    response = SimpleNamespace(
        output_text="",
        output=[
            SimpleNamespace(
                type="message",
                content=[SimpleNamespace(type="output_text", text="PONG")],
            )
        ],
    )
    assert AzureOpenAIClient._extract_output_text(response) == "PONG"


def test_invalid_endpoint_is_rejected_without_sdk_call(monkeypatch):
    install_fake_sdk(monkeypatch)
    client = AzureOpenAIClient(api_key="", endpoint="", deployment="gpt-5-mini")

    ok, message = client.configure(
        endpoint="http://not-https.example",
        api_key="fake-key",
        deployment="gpt-5-mini",
        test_connection=False,
    )

    assert ok is False
    assert "HTTPS" in message
    assert FakeOpenAI.instances == []
