"""OpenTelemetry setup centralizzato per tutti i servizi CCI/AVCS.

Ogni servizio chiama `setup_telemetry(service_name, version)` all'avvio.
"""
from __future__ import annotations

import logging
import os

import structlog
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter


def setup_telemetry(service_name: str, version: str = "0.1.0") -> trace.Tracer:
    """Inizializza OpenTelemetry tracing + structlog JSON.

    Esportatore: OTLP gRPC se OTEL_EXPORTER_OTLP_ENDPOINT è impostata,
    altrimenti console (utile in test).
    """
    resource = Resource.create(
        {
            "service.name": service_name,
            "service.version": version,
        }
    )
    provider = TracerProvider(resource=resource)

    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if otlp_endpoint:
        exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
    else:
        exporter = ConsoleSpanExporter()  # type: ignore[assignment]

    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    _setup_structlog(service_name, version)

    return trace.get_tracer(service_name)


def _setup_structlog(service_name: str, version: str) -> None:
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level, logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )

    # Bind campi fissi a ogni log record
    structlog.contextvars.bind_contextvars(
        service=service_name,
        version=version,
        environment=os.getenv("ENVIRONMENT", "development"),
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """Ritorna un logger strutturato per il modulo specificato."""
    return structlog.get_logger(name)
