"""Instrumentation OpenTelemetry : traces, logs JSON corrélés (trace_id) et métriques."""

import json
import logging
import os
import sys

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "catalog-api")


class JsonFormatter(logging.Formatter):
    """Formate chaque log en une ligne JSON contenant trace_id et span_id."""

    def format(self, record: logging.LogRecord) -> str:
        span_context = trace.get_current_span().get_span_context()
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": SERVICE_NAME,
            "trace_id": format(span_context.trace_id, "032x") if span_context.is_valid else None,
            "span_id": format(span_context.span_id, "016x") if span_context.is_valid else None,
        }
        for key in ("path", "method", "status", "duration_ms"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        return json.dumps(payload, ensure_ascii=False)


def setup_logging() -> logging.Logger:
    logger = logging.getLogger(SERVICE_NAME)
    logger.setLevel(logging.INFO)
    if not any(getattr(h, "_json_stdout", False) for h in logger.handlers):
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        handler._json_stdout = True  # marqueur pour éviter les doublons
        logger.addHandler(handler)
    return logger


def setup_telemetry(app, endpoint: str | None = None) -> bool:
    """Active l'export OTLP (traces + logs) si un endpoint est configuré.

    Retourne True si l'export est activé. Sans endpoint (tests, poste local),
    seuls les logs JSON sur stdout sont produits.
    """
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

    endpoint = endpoint or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    logger = setup_logging()
    if not endpoint:
        return False

    from opentelemetry._logs import set_logger_provider
    from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
    from opentelemetry.sdk._logs.export import BatchLogRecordProcessor

    resource = Resource.create({"service.name": SERVICE_NAME})
    base = endpoint.rstrip("/")

    # Traces -> Collector -> Tempo
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{base}/v1/traces"))
    )
    trace.set_tracer_provider(tracer_provider)

    # Logs -> Collector -> Loki (le trace_id est attaché automatiquement)
    logger_provider = LoggerProvider(resource=resource)
    logger_provider.add_log_record_processor(
        BatchLogRecordProcessor(OTLPLogExporter(endpoint=f"{base}/v1/logs"))
    )
    set_logger_provider(logger_provider)
    logger.addHandler(LoggingHandler(level=logging.INFO, logger_provider=logger_provider))

    FastAPIInstrumentor.instrument_app(app, excluded_urls="metrics,health")
    return True
