import json
import logging

import pytest
from fastapi.testclient import TestClient

from app import main
from app.telemetry import JsonFormatter, setup_telemetry


@pytest.fixture
def client(monkeypatch):
    # Pas d'attente réelle pendant les tests
    monkeypatch.setenv("CHECKOUT_MIN_MS", "0")
    monkeypatch.setenv("CHECKOUT_MAX_MS", "0")
    monkeypatch.setenv("CHECKOUT_SLOW_PROB", "0")
    return TestClient(main.app)


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_list_products(client):
    response = client.get("/products")
    assert response.status_code == 200
    assert len(response.json()) == 4


def test_get_product_found(client):
    assert client.get("/products/1").json()["name"] == "Clavier mécanique"


def test_get_product_not_found(client):
    assert client.get("/products/999").status_code == 404


def test_get_product_bad_id(client):
    assert client.get("/products/abc").status_code == 422


def test_checkout_ok(client):
    response = client.post("/checkout", json={"items": [{"product_id": 1, "quantity": 2}]})
    assert response.status_code == 200
    assert response.json()["total"] == 179.80
    assert response.json()["status"] == "confirmed"


def test_checkout_slow_path(client, monkeypatch):
    monkeypatch.setenv("CHECKOUT_SLOW_PROB", "1")
    monkeypatch.setattr(main.random, "uniform", lambda a, b: 0)
    response = client.post("/checkout", json={"items": [{"product_id": 2, "quantity": 1}]})
    assert response.status_code == 200


def test_checkout_empty_cart(client):
    assert client.post("/checkout", json={"items": []}).status_code == 422


def test_checkout_out_of_stock(client):
    response = client.post("/checkout", json={"items": [{"product_id": 4, "quantity": 1}]})
    assert response.status_code == 422
    assert "Stock insuffisant" in response.json()["detail"]


def test_checkout_unknown_product(client):
    response = client.post("/checkout", json={"items": [{"product_id": 77, "quantity": 1}]})
    assert response.status_code == 404


def test_flaky_success(client, monkeypatch):
    monkeypatch.setenv("FLAKY_ERROR_RATE", "0")
    assert client.get("/flaky").status_code == 200


def test_flaky_error(client, monkeypatch):
    monkeypatch.setenv("FLAKY_ERROR_RATE", "1")
    assert client.get("/flaky").status_code == 500


def test_invalid_env_value_uses_default(monkeypatch):
    monkeypatch.setenv("FLAKY_ERROR_RATE", "pas-un-nombre")
    assert main._env_float("FLAKY_ERROR_RATE", 0.2) == 0.2


def test_metrics_endpoint_exposes_red_metrics(client):
    client.get("/products")
    body = client.get("/metrics").text
    assert "http_requests_total" in body
    assert 'path="/products"' in body
    assert "http_request_duration_seconds_bucket" in body
    assert 'le="0.2"' in body


def test_unknown_route_is_labelled_unmatched(client):
    client.get("/nexiste-pas")
    assert 'path="unmatched"' in client.get("/metrics").text


def test_json_formatter_without_span():
    record = logging.LogRecord("t", logging.INFO, __file__, 1, "bonjour", None, None)
    record.status = 200
    data = json.loads(JsonFormatter().format(record))
    assert data["message"] == "bonjour"
    assert data["trace_id"] is None
    assert data["status"] == 200


def test_json_formatter_with_span():
    from opentelemetry.sdk.trace import TracerProvider

    tracer = TracerProvider().get_tracer("test")
    with tracer.start_as_current_span("span-test"):
        record = logging.LogRecord("t", logging.INFO, __file__, 1, "dans un span", None, None)
        data = json.loads(JsonFormatter().format(record))
    assert len(data["trace_id"]) == 32
    assert len(data["span_id"]) == 16


def test_setup_telemetry_disabled_without_endpoint(monkeypatch):
    from fastapi import FastAPI

    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    assert setup_telemetry(FastAPI()) is False


def test_setup_telemetry_enabled_with_endpoint():
    from fastapi import FastAPI

    # Aucun collecteur n'est contacté pendant le test : l'export est asynchrone
    assert setup_telemetry(FastAPI(), endpoint="http://localhost:4318") is True
