"""HTTP API tests. The Groq provider is never contacted."""

from __future__ import annotations

import asyncio
import json
import logging

import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.errors import LLMMalformedJSONError, LLMRateLimitError, LLMSchemaUnsupportedError
from app.main import create_app
from app.quantum.examples import BELL_SPEC, BIT_FLIP_SPEC, GHZ_SPEC, SUPERPOSITION_SPEC
from app.services.generation import request_circuit_spec
from app.services.llm.groq import GroqProvider
from app.utils.redact import RedactFilter, install_redaction
from tests.conftest import FakeLLM, bell_json, make_settings


def test_health_reports_subsystems(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["api"]["status"] == "ok"
    assert body["service"]["status"] == "ok"
    assert body["quantum_simulator"]["available"] is True
    assert isinstance(body["pytorch"]["available"], bool)
    if body["pytorch"]["available"]:
        assert isinstance(body["pytorch"]["version"], str) and body["pytorch"]["version"]
    else:
        assert body["pytorch"]["version"] is None
    assert body["llm"]["configured"] is False
    assert "groq_api_key" not in response.text


def test_health_does_not_echo_api_key(tmp_path):
    settings = make_settings(tmp_path, groq_api_key="super-secret-key")
    with TestClient(create_app(settings)) as client:
        text = client.get("/api/health").text
    assert "super-secret-key" not in text
    assert "configured" in text


def test_examples_include_ghz_reference(client):
    body = client.get("/api/circuits/examples").json()
    by_id = {item["id"]: item for item in body["examples"]}
    ghz = by_id["ghz"]
    assert ghz["runnable_without_llm"] is True
    assert ghz["source"] == "reference"
    assert "GHZ" in ghz["prompt"]
    assert ghz["spec"]["num_qubits"] == 3
    assert [gate["qubits"] for gate in ghz["spec"]["gates"]] == [[0], [0, 1], [0, 2]]
    assert by_id["x-h-cnot"]["spec"] is None
    assert by_id["x-h-cnot"]["runnable_without_llm"] is False


@pytest.mark.parametrize(
    "spec, dominant",
    [
        (BELL_SPEC, ("00", "11")),
        (SUPERPOSITION_SPEC, ("0", "1")),
        (BIT_FLIP_SPEC, ("1",)),
        (GHZ_SPEC, ("000", "111")),
    ],
)
def test_simulate_canonical_examples(client, spec, dominant):
    response = client.post("/api/circuits/simulate", json={"spec": spec, "shots": 2000})
    assert response.status_code == 200
    body = response.json()
    assert body["validation"]["valid"] is True
    assert body["visualization"]["svg"].startswith("<svg")
    assert sum(body["counts"].values()) == 2000
    for bitstring in dominant:
        assert body["probabilities"][bitstring] == pytest.approx(0.5 if len(dominant) == 2 else 1.0, abs=0.08)
    assert "groq" not in body["metadata"]["simulator"]


def test_simulate_works_without_groq_key(client):
    response = client.post("/api/circuits/simulate", json={"spec": BIT_FLIP_SPEC, "shots": 100})
    assert response.status_code == 200
    assert response.json()["counts"] == {"1": 100}


def test_simulate_rejects_unsupported_gate(client):
    spec = {
        **SUPERPOSITION_SPEC,
        "gates": [{"gate": "toffoli", "qubits": [0]}],
    }
    response = client.post("/api/circuits/simulate", json={"spec": spec})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_validate_reports_errors_without_failing_the_request(client):
    response = client.post(
        "/api/circuits/validate",
        json={"gate": "h", "qubits": [0]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["valid"] is False
    assert body["errors"]
    assert body["spec"] is None


def test_validate_accepts_wrapped_spec(client):
    response = client.post("/api/circuits/validate", json={"spec": BELL_SPEC})
    assert response.status_code == 200
    assert response.json()["valid"] is True
    assert response.json()["spec"]["circuit_name"] == "Bell State"


def test_generate_missing_key_is_configuration_error_not_a_template(client):
    response = client.post(
        "/api/circuits/generate",
        json={"prompt": "Generate a Bell State using two qubits."},
    )
    assert response.status_code == 503
    body = response.json()
    assert body["error"]["code"] == "configuration_error"
    assert "GROQ_API_KEY" in body["error"]["message"]
    assert "spec" not in body
    assert "counts" not in body


def test_generate_and_simulate_missing_key(client):
    response = client.post(
        "/api/circuits/generate-and-simulate",
        json={"prompt": "Create a quantum superposition using a Hadamard gate.", "shots": 100},
    )
    assert response.status_code == 503
    assert "spec" not in response.json()


def test_shots_above_cap(client):
    response = client.post(
        "/api/circuits/simulate",
        json={"spec": SUPERPOSITION_SPEC, "shots": 10001},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_shots"


def test_malformed_json_body(client):
    response = client.post(
        "/api/circuits/simulate",
        content="{",
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_request_size_limit(tmp_path):
    settings = make_settings(tmp_path, max_request_bytes=1024)
    with TestClient(create_app(settings)) as client:
        response = client.post(
            "/api/circuits/generate",
            json={"prompt": "x" * 2000},
        )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "payload_too_large"


def test_generate_returns_provider_spec_not_a_built_in(tmp_path):
    settings = make_settings(tmp_path, groq_api_key="", llm_max_retries=1)
    application = create_app(settings)
    custom = {
        **SUPERPOSITION_SPEC,
        "circuit_name": "Provider superposition",
        "description": "Returned by the fake provider.",
    }
    application.state.llm = FakeLLM([json.dumps(custom)])
    with TestClient(application) as client:
        response = client.post(
            "/api/circuits/generate-and-simulate",
            json={"prompt": "make a superposition", "shots": 200},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "llm"
    assert body["spec"]["circuit_name"] == "Provider superposition"
    assert body["metadata"]["provider"] == "fake"
    assert body["visualization"]["svg"].startswith("<svg")
    assert sum(body["counts"].values()) == 200


def test_history_does_not_block_simulation_when_unwritable(tmp_path):
    settings = make_settings(
        tmp_path,
        history_enabled=True,
        history_database_path="/proc/does-not-exist/history.db",
    )
    with TestClient(create_app(settings)) as client:
        response = client.post("/api/circuits/simulate", json={"spec": BIT_FLIP_SPEC, "shots": 10})
    assert response.status_code == 200


def test_history_records_successful_simulation(client):
    response = client.post("/api/circuits/simulate", json={"spec": BELL_SPEC, "shots": 10})
    assert response.status_code == 200
    recent = client.app.state.history.recent()
    assert recent
    assert recent[0]["kind"] == "simulate"
    assert recent[0]["valid"] is True
    assert recent[0]["circuit_name"] == "Bell State"


def test_retries_malformed_json_then_accepts_spec(tmp_path, monkeypatch):
    async def no_sleep(_seconds: float) -> None:
        return None

    monkeypatch.setattr("app.services.generation.asyncio.sleep", no_sleep)
    settings = make_settings(tmp_path, llm_max_retries=3)
    provider = FakeLLM(["not-json", bell_json()])
    generated = asyncio.run(request_circuit_spec(provider, "bell", settings))
    assert generated.spec.circuit_name == "Bell State"
    assert generated.attempts == 2
    assert provider.calls == [True, True]


def test_rate_limit_is_retried(tmp_path, monkeypatch):
    async def no_sleep(_seconds: float) -> None:
        return None

    monkeypatch.setattr("app.services.generation.asyncio.sleep", no_sleep)
    settings = make_settings(tmp_path, llm_max_retries=2)
    provider = FakeLLM([LLMRateLimitError(), bell_json()])
    generated = asyncio.run(request_circuit_spec(provider, "bell", settings))
    assert generated.attempts == 2


def test_exhausted_malformed_json_raises(tmp_path, monkeypatch):
    async def no_sleep(_seconds: float) -> None:
        return None

    monkeypatch.setattr("app.services.generation.asyncio.sleep", no_sleep)
    settings = make_settings(tmp_path, llm_max_retries=2)
    provider = FakeLLM(["{", "{"])
    with pytest.raises(LLMMalformedJSONError):
        asyncio.run(request_circuit_spec(provider, "bell", settings))


def test_groq_structured_output_and_redaction(tmp_path, caplog):
    caplog.set_level(logging.WARNING)
    settings = make_settings(tmp_path, groq_api_key="super-secret-key")
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["authorization"] = request.headers.get("authorization")
        captured["body"] = json.loads(request.content.decode())
        return httpx.Response(500, text="boom super-secret-key")

    provider = GroqProvider(settings, transport=httpx.MockTransport(handler))

    async def invoke() -> None:
        await provider.complete([{"role": "user", "content": "bell"}], strict=True)

    with pytest.raises(Exception):
        asyncio.run(invoke())

    assert captured["authorization"] == "Bearer super-secret-key"
    response_format = captured["body"]["response_format"]
    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["strict"] is True
    assert "groq request failed" in caplog.text
    assert "super-secret-key" not in caplog.text


def test_groq_schema_rejection_is_typed(tmp_path):
    settings = make_settings(tmp_path, groq_api_key="super-secret-key")

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, text='{"error": "json_schema is not supported"}')

    provider = GroqProvider(settings, transport=httpx.MockTransport(handler))

    async def invoke() -> None:
        await provider.complete([{"role": "user", "content": "bell"}], strict=True)

    with pytest.raises(LLMSchemaUnsupportedError):
        asyncio.run(invoke())


def test_redact_filter_strips_secret():
    install_redaction("super-secret-key")
    record = logging.LogRecord(
        "app",
        20,
        __file__,
        1,
        "authorization super-secret-key",
        (),
        None,
    )
    assert RedactFilter().filter(record) is True
    assert "super-secret-key" not in record.getMessage()
    assert "[REDACTED]" in record.getMessage()
