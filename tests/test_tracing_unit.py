from app.observability.tracing import setup_tracing, instrument_fastapi
from fastapi import FastAPI


def test_tracing_no_endpoint():
    # Should return quickly without raising
    setup_tracing()
    app = FastAPI()
    instrument_fastapi(app)


def test_tracing_with_dummy_endpoint(monkeypatch):
    # Patch settings to simulate enabled tracing
    from app.observability import tracing as tr

    class S:
        OTEL_EXPORTER_OTLP_ENDPOINT = "http://localhost:4318/v1/traces"
        OTEL_SERVICE_NAME = "test-svc"

    monkeypatch.setattr(tr, "settings", S)
    # Should not raise even if exporter cannot reach endpoint (we don't send spans here)
    setup_tracing()
    app = FastAPI()
    instrument_fastapi(app)
