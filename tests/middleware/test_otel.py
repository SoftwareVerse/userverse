from unittest.mock import MagicMock

from app.middleware.otel import setup_otel


def test_setup_otel_instruments_app(monkeypatch):
    resource_instance = MagicMock(name="resource")
    tracer_provider = MagicMock(name="tracer_provider")
    exporter = MagicMock(name="exporter")
    span_processor = MagicMock(name="span_processor")
    requests_instrumentor = MagicMock()
    fastapi_instrumentor = MagicMock()
    resource_factory = MagicMock(return_value=resource_instance)
    tracer_provider_factory = MagicMock(return_value=tracer_provider)
    exporter_factory = MagicMock(return_value=exporter)
    span_processor_factory = MagicMock(return_value=span_processor)
    set_tracer_provider = MagicMock()

    monkeypatch.setattr("app.middleware.otel.Resource", resource_factory)
    monkeypatch.setattr("app.middleware.otel.TracerProvider", tracer_provider_factory)
    monkeypatch.setattr("app.middleware.otel.OTLPSpanExporter", exporter_factory)
    monkeypatch.setattr(
        "app.middleware.otel.BatchSpanProcessor", span_processor_factory
    )
    monkeypatch.setattr(
        "app.middleware.otel.trace.set_tracer_provider", set_tracer_provider
    )
    monkeypatch.setattr("app.middleware.otel.FastAPIInstrumentor", fastapi_instrumentor)
    monkeypatch.setattr(
        "app.middleware.otel.RequestsInstrumentor",
        MagicMock(return_value=requests_instrumentor),
    )

    app = object()
    setup_otel(app, service_name="userverse-api", collector_endpoint="http://collector")

    resource_factory.assert_called_once()
    tracer_provider_factory.assert_called_once_with(resource=resource_instance)
    exporter_factory.assert_called_once_with(endpoint="http://collector")
    span_processor_factory.assert_called_once_with(exporter)
    tracer_provider.add_span_processor.assert_called_once_with(span_processor)
    set_tracer_provider.assert_called_once_with(tracer_provider)
    fastapi_instrumentor.instrument_app.assert_called_once_with(app)
    requests_instrumentor.instrument.assert_called_once_with()
