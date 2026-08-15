from opentelemetry import trace
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor


def setup_otel(
    app,
    service_name: str = "fastapi-app",
    collector_endpoint="http://otel-collector:4318/v1/traces",
):
    """
    Initializes OpenTelemetry tracing and instrumentation for a FastAPI app.
    - service_name: name to appear in OpenSearch traces
    - collector_endpoint: your OTEL collector (HTTP OTLP)
    """

    resource = Resource(attributes={SERVICE_NAME: service_name})
    tracer_provider = TracerProvider(resource=resource)

    otlp_exporter = OTLPSpanExporter(endpoint=collector_endpoint)
    span_processor = BatchSpanProcessor(otlp_exporter)

    tracer_provider.add_span_processor(span_processor)
    trace.set_tracer_provider(tracer_provider)

    # Instrument FastAPI and Requests
    FastAPIInstrumentor.instrument_app(app)
    RequestsInstrumentor().instrument()
