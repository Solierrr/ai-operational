from pathlib import Path

import yaml
from fastapi.testclient import TestClient

from src.api.app import app, build_openapi
from src.version import VERSION

client = TestClient(app)


def test_contract_follows_the_standard_metadata():
    schema = client.get("/openapi.json").json()

    assert schema["info"]["title"] == "Solaria — ai-operational"
    assert schema["info"]["version"] == VERSION
    assert schema["info"]["license"]["name"] == "CC0-1.0"
    assert schema["servers"][0]["description"] == "QA"
    assert schema["security"] == [{"bearerAuth": []}]
    assert schema["components"]["securitySchemes"]["bearerAuth"] == {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
    }


def test_every_error_response_uses_problem_detail():
    schema = build_openapi(include_internal=True)

    for name, path in schema["paths"].items():
        for operation in path.values():
            assert "500" in operation["responses"]
            for code, response in operation["responses"].items():
                if code.startswith(("4", "5")) and (name, code) != ("/ready", "503"):
                    assert list(response["content"]) == ["application/problem+json"]
    assert "HTTPValidationError" not in schema["components"]["schemas"]
    assert "ProblemDetail" in schema["components"]["schemas"]


def test_health_routes_are_public():
    schema = build_openapi(include_internal=True)

    assert schema["paths"]["/health"]["get"]["security"] == []
    assert schema["paths"]["/ready"]["get"]["security"] == []


def test_exported_contract_matches_the_code():
    exported = yaml.safe_load(
        (Path(__file__).resolve().parents[2] / "openapi.yaml").read_text(
            encoding="utf-8"
        )
    )

    assert exported == build_openapi(include_internal=True)


def test_ready_documents_the_down_status_without_problem_detail():
    schema = build_openapi(include_internal=True)

    down = schema["paths"]["/ready"]["get"]["responses"]["503"]
    assert list(down["content"]) == ["application/json"]


def test_chat_lists_its_error_codes():
    schema = build_openapi(include_internal=True)

    chat = schema["paths"]["/chat"]["post"]
    assert chat["operationId"] == "sendChatMessage"
    assert "UNAUTHENTICATED" in chat["x-error-codes"]


def test_debug_and_a2a_routes_stay_out_of_the_contract():
    schema = build_openapi(include_internal=True)

    assert not [path for path in schema["paths"] if path.startswith("/debug")]
    assert set(schema["paths"]) == {"/chat", "/health", "/ready"}
