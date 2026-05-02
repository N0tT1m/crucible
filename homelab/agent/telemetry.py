"""OTel SDK init for redlab-agent.

No-op when OTEL_EXPORTER_OTLP_ENDPOINT isn't set.

Span tree per /chat:
    agent.chat        (root, FastAPI auto-span)
        agent.llm.call    (one per Ollama round-trip)
        tool.<name>       (one per tool invocation)
"""
from __future__ import annotations

import logging
import os
from contextlib import nullcontext

log = logging.getLogger(__name__)

_provider = None
_log_provider = None


def init_otel(app, service_name: str = "redlab-agent") -> bool:
    """Wire OTel into the FastAPI app. Returns True when active."""
    global _provider, _log_provider
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        return False
    try:
        import logging as _logging

        from opentelemetry import _logs as _otel_logs
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
        from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError:
        log.warning("OTEL_EXPORTER_OTLP_ENDPOINT set but opentelemetry not installed")
        return False

    res = Resource.create({"service.name": service_name})

    tp = TracerProvider(resource=res)
    tp.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint, insecure=True)))
    trace.set_tracer_provider(tp)

    lp = LoggerProvider(resource=res)
    lp.add_log_record_processor(BatchLogRecordProcessor(OTLPLogExporter(endpoint=endpoint, insecure=True)))
    _otel_logs.set_logger_provider(lp)
    _logging.getLogger().addHandler(LoggingHandler(logger_provider=lp))

    FastAPIInstrumentor().instrument_app(app)

    _provider = tp
    _log_provider = lp
    return True


def shutdown_otel() -> None:
    global _provider, _log_provider
    for p in (_provider, _log_provider):
        if p is None:
            continue
        try:
            p.shutdown()
        except Exception as e:
            log.warning("otel shutdown failed: %s", e)
    _provider = _log_provider = None


def tracer(name: str = "redlab-agent"):
    try:
        from opentelemetry import trace
        return trace.get_tracer(name)
    except ImportError:
        class _NoopTracer:
            def start_as_current_span(self, *a, **kw):
                return nullcontext()
        return _NoopTracer()
