"""File prompt tests. Vision and spec generation use a fake provider, never Groq."""

from __future__ import annotations

import asyncio
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.errors import ExtractionError
from app.main import create_app
from app.services.extraction import extract_pdf_text, sniff_kind
from app.services.llm.base import ImageInput
from app.services.llm.groq import GroqProvider
from tests.conftest import FakeLLM, bell_json, make_settings
from tests.pdf_fixtures import blank_pdf, text_pdf

ENDPOINT = "/api/circuits/generate-from-file"
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
BELL_QUESTION = "Generate a Bell State using two qubits and measure both."


def _client(tmp_path, provider=None, **overrides) -> TestClient:
    application = create_app(make_settings(tmp_path, **overrides))
    if provider is not None:
        application.state.llm = provider
    return TestClient(application)


def test_sniff_kind_reads_magic_bytes():
    assert sniff_kind(PNG_BYTES) == "png"
    assert sniff_kind(b"\xff\xd8\xff\xe0rest") == "jpeg"
    assert sniff_kind(b"RIFF\x00\x00\x00\x00WEBPVP8 ") == "webp"
    assert sniff_kind(text_pdf(["hi"])) == "pdf"
    assert sniff_kind(b"hello world") is None


def test_extract_pdf_text_from_generated_fixture():
    result = extract_pdf_text(text_pdf([BELL_QUESTION]), max_pages=10)
    assert "Bell State" in result.text
    assert result.pages_read == 1
    assert result.total_pages == 1


def test_extract_pdf_text_respects_page_cap():
    pages = [f"Question page {index}" for index in range(1, 13)]
    result = extract_pdf_text(text_pdf(pages), max_pages=10)
    assert result.pages_read == 10
    assert result.total_pages == 12
    assert "Question page 10" in result.text
    assert "Question page 11" not in result.text


def test_extract_pdf_text_rejects_damaged_pdf():
    with pytest.raises(ExtractionError) as caught:
        extract_pdf_text(b"%PDF-1.4\nthis is not a real pdf", max_pages=10)
    assert caught.value.status_code == 422


def test_pdf_text_endpoint_generates_and_simulates(tmp_path):
    fake = FakeLLM([bell_json()])
    with _client(tmp_path, fake) as client:
        response = client.post(
            ENDPOINT,
            files={"file": ("question.pdf", text_pdf([BELL_QUESTION]), "application/pdf")},
            data={"prompt": "Use 500 shots worth of detail.", "shots": "500"},
        )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["extraction"]["method"] == "pdf_text"
    assert body["extraction"]["filename"] == "question.pdf"
    assert "Bell State" in body["extraction"]["text"]
    assert body["extraction"]["pages_read"] == 1
    assert body["spec"]["circuit_name"] == "Bell State"
    assert body["validation"]["valid"] is True
    assert sum(body["counts"].values()) == 500
    assert body["visualization"]["svg"].startswith("<svg")
    assert body["prompt"] == "Use 500 shots worth of detail."
    assert fake.vision_calls == []
    user_message = fake.messages[0][-1]["content"]
    assert "Bell State" in user_message
    assert "Use 500 shots worth of detail." in user_message


def test_pdf_text_is_capped_before_the_model(tmp_path):
    fake = FakeLLM([bell_json()])
    long_page = "Bell state " * 100
    with _client(tmp_path, fake, max_extracted_chars=200) as client:
        response = client.post(
            ENDPOINT,
            files={"file": ("long.pdf", text_pdf([long_page]), "application/pdf")},
        )
    assert response.status_code == 200, response.text
    extraction = response.json()["extraction"]
    assert extraction["truncated"] is True
    assert len(extraction["text"]) <= 200
    assert response.json()["prompt"] == "Uploaded file: long.pdf"


def test_image_routes_to_vision_method(tmp_path):
    fake = FakeLLM([bell_json()], transcriptions=[BELL_QUESTION])
    image = PNG_BYTES + b"\x01" * 200_000
    with _client(tmp_path, fake) as client:
        response = client.post(
            ENDPOINT,
            files={"file": ("circuit.png", image, "image/png")},
            data={"prompt": "Label it as a Bell pair."},
        )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["extraction"]["method"] == "image_vision"
    assert body["extraction"]["text"] == BELL_QUESTION
    images, instructions = fake.vision_calls[0]
    assert [item.media_type for item in images] == ["image/png"]
    assert images[0].data == image
    assert instructions == "Label it as a Bell pair."
    assert BELL_QUESTION in fake.messages[0][-1]["content"]


def test_scanned_pdf_renders_pages_for_vision(tmp_path):
    fake = FakeLLM([bell_json()], transcriptions=[BELL_QUESTION])
    with _client(tmp_path, fake) as client:
        response = client.post(
            ENDPOINT,
            files={"file": ("scan.pdf", blank_pdf(5), "application/pdf")},
        )
    assert response.status_code == 200, response.text
    extraction = response.json()["extraction"]
    assert extraction["method"] == "pdf_vision"
    assert extraction["pages_read"] == 3
    assert extraction["total_pages"] == 5
    images, _ = fake.vision_calls[0]
    assert len(images) == 3
    assert all(item.media_type == "image/jpeg" for item in images)
    assert all(item.data.startswith(b"\xff\xd8\xff") for item in images)


def test_vision_reply_without_a_question_is_422(tmp_path):
    fake = FakeLLM([], transcriptions=["NO_QUANTUM_CONTENT"])
    with _client(tmp_path, fake) as client:
        response = client.post(ENDPOINT, files={"file": ("cat.png", PNG_BYTES, "image/png")})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "extraction_empty"
    assert fake.calls == []


def test_unsupported_declared_type_is_415(tmp_path):
    with _client(tmp_path, FakeLLM([])) as client:
        response = client.post(ENDPOINT, files={"file": ("notes.txt", b"Bell state", "text/plain")})
    assert response.status_code == 415
    assert response.json()["error"]["code"] == "unsupported_media_type"


def test_mismatched_magic_bytes_are_415(tmp_path):
    with _client(tmp_path, FakeLLM([])) as client:
        disguised = client.post(
            ENDPOINT,
            files={"file": ("question.png", text_pdf([BELL_QUESTION]), "image/png")},
        )
        garbage = client.post(
            ENDPOINT,
            files={"file": ("photo.jpg", b"MZ\x90\x00 not an image", "image/jpeg")},
        )
    assert disguised.status_code == 415
    assert "application/pdf" in disguised.json()["error"]["message"]
    assert garbage.status_code == 415


def test_file_over_upload_cap_is_413(tmp_path):
    just_over = PNG_BYTES + b"\x00" * (1024 * 1024)
    far_over = PNG_BYTES + b"\x00" * (2 * 1024 * 1024)
    with _client(tmp_path, FakeLLM([]), max_upload_mb=1) as client:
        checked_in_route = client.post(
            ENDPOINT,
            files={"file": ("big.png", just_over, "image/png")},
        )
        checked_by_header = client.post(
            ENDPOINT,
            files={"file": ("huge.png", far_over, "image/png")},
        )
    assert checked_in_route.status_code == 413
    assert checked_in_route.json()["error"]["code"] == "file_too_large"
    assert checked_by_header.status_code == 413
    assert checked_by_header.json()["error"]["code"] == "file_too_large"


def test_json_endpoints_keep_the_small_body_cap(tmp_path):
    with _client(tmp_path, FakeLLM([]), max_request_bytes=1024) as client:
        response = client.post("/api/circuits/generate", json={"prompt": "x" * 2000})
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "payload_too_large"


def test_missing_file_is_422(tmp_path):
    with _client(tmp_path, FakeLLM([])) as client:
        response = client.post(ENDPOINT, data={"prompt": "Bell state"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_image_without_key_is_configuration_error(tmp_path):
    with _client(tmp_path) as client:
        response = client.post(ENDPOINT, files={"file": ("circuit.png", PNG_BYTES, "image/png")})
    assert response.status_code == 503
    body = response.json()
    assert body["error"]["code"] == "configuration_error"
    assert "spec" not in body
    assert "counts" not in body


def test_pdf_without_key_returns_extracted_text_and_no_circuit(tmp_path):
    with _client(tmp_path) as client:
        response = client.post(
            ENDPOINT,
            files={"file": ("question.pdf", text_pdf([BELL_QUESTION]), "application/pdf")},
        )
    assert response.status_code == 503
    body = response.json()
    assert body["error"]["code"] == "configuration_error"
    assert "Bell State" in body["extraction"]["text"]
    assert body["extraction"]["method"] == "pdf_text"
    assert "spec" not in body
    assert "counts" not in body


def test_scanned_pdf_without_key_is_configuration_error(tmp_path):
    with _client(tmp_path) as client:
        response = client.post(
            ENDPOINT,
            files={"file": ("scan.pdf", blank_pdf(1), "application/pdf")},
        )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "configuration_error"


def test_health_reports_upload_limits(client):
    body = client.get("/api/health").json()
    assert body["uploads"]["max_upload_mb"] == 10
    assert body["uploads"]["max_pdf_pages"] == 10
    assert "application/pdf" in body["uploads"]["media_types"]
    assert body["llm"]["vision_model"]


def test_groq_vision_request_uses_vision_model_and_data_url(tmp_path):
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": "<think>reading</think>Prepare a Bell state."}}
                ]
            },
        )

    settings = make_settings(
        tmp_path,
        groq_api_key="secret",
        groq_vision_model="qwen/qwen3.8-27b",
    )
    provider = GroqProvider(settings, transport=httpx.MockTransport(handler))
    text = asyncio.run(
        provider.transcribe_images(
            [ImageInput(media_type="image/png", data=PNG_BYTES)],
            instructions="two qubits",
        )
    )
    assert text == "Prepare a Bell state."
    payload = seen["payload"]
    assert isinstance(payload, dict)
    assert payload["model"] == "qwen/qwen3.8-27b"
    assert "response_format" not in payload
    content = payload["messages"][0]["content"]
    assert content[0]["type"] == "text"
    assert "two qubits" in content[0]["text"]
    assert content[1]["image_url"]["url"].startswith("data:image/png;base64,")
