"""OTel SDK init for the redbox CLI.

No-op when OTEL_EXPORTER_OTLP_ENDPOINT isn't set, so the CLI stays
runnable in fully-offline mode without the otel extra installed.

Install:
    pip install -e '.[otel]'
Use:
    OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317 redbox bench …
"""
from __future__ import annotations

import logging
import os

log = logging.getLogger(__name__)

_provider = None


def init_otel(service_name: str = "redbox") -> bool:
    """Initialise the global tracer provider. Returns True when active."""
    global _provider
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        return False
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError:
        log.warning("OTEL_EXPORTER_OTLP_ENDPOINT set but opentelemetry not installed; "
                    "run: pip install -e '.[otel]'")
        return False

    res = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=res)
    provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint, insecure=True))
    )
    trace.set_tracer_provider(provider)
    _provider = provider
    return True


def shutdown_otel() -> None:
    """Flush + shutdown the tracer provider. Call on CLI exit."""
    global _provider
    if _provider is None:
        return
    try:
        _provider.shutdown()
    except Exception as e:
        log.warning("otel shutdown failed: %s", e)
    _provider = None


def tracer(name: str = "redbox"):
    """Get a tracer; returns a no-op tracer when otel isn't initialised."""
    try:
        from opentelemetry import trace
        return trace.get_tracer(name)
    except ImportError:
        from contextlib import nullcontext

        class _NoopTracer:
            def start_as_current_span(self, *a, **kw):
                return nullcontext()

        return _NoopTracer()
