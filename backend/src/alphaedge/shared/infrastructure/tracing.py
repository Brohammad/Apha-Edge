"""OpenTelemetry distributed tracing setup."""

from __future__ import annotations

import structlog

from alphaedge.config import settings

logger = structlog.get_logger(__name__)


def setup_tracing(app) -> None:
    if not settings.otel_enabled:
        return
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

        resource = Resource.create({"service.name": settings.otel_service_name})
        provider = TracerProvider(resource=resource)

        if settings.otel_exporter_otlp_endpoint:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

            exporter = OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint)
            logger.info(
                "otel_otlp_exporter_configured",
                endpoint=settings.otel_exporter_otlp_endpoint,
            )
        else:
            exporter = ConsoleSpanExporter()
            logger.info("otel_console_exporter_configured")

        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)

        try:
            from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

            FastAPIInstrumentor.instrument_app(app)
        except ImportError:
            logger.warning("otel_fastapi_instrumentation_missing")
    except ImportError:
        logger.warning(
            "otel_packages_missing",
            hint="pip install -e '.[otel]' to enable OpenTelemetry",
        )
