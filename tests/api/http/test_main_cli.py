from unittest.mock import MagicMock

from app.main import main


def test_main_reload_mode_forces_single_worker(monkeypatch):
    dict_config = MagicMock()
    uvicorn_run = MagicMock()
    logger_info = MagicMock()
    logger_warning = MagicMock()

    monkeypatch.setattr("app.main.get_uvicorn_log_config", lambda **_: {"log": "cfg"})
    monkeypatch.setattr("app.main.logging.config.dictConfig", dict_config)
    monkeypatch.setattr("app.main.uvicorn.run", uvicorn_run)
    monkeypatch.setattr("app.main.logger.info", logger_info)
    monkeypatch.setattr("app.main.logger.warning", logger_warning)

    main.callback(
        port=9000,
        host="127.0.0.1",
        env="testing",
        reload=True,
        workers=3,
        verbose=True,
    )

    logger_warning.assert_called_once()
    dict_config.assert_called_once_with({"log": "cfg"})
    uvicorn_run.assert_called_once_with(
        "app.main:create_app",
        factory=True,
        host="127.0.0.1",
        port=9000,
        reload=True,
        log_config={"log": "cfg"},
    )


def test_main_non_reload_mode_runs_server(monkeypatch):
    dict_config = MagicMock()
    config_instance = MagicMock(name="config")
    server_instance = MagicMock()
    config_factory = MagicMock(return_value=config_instance)
    server_factory = MagicMock(return_value=server_instance)

    monkeypatch.setattr("app.main.get_uvicorn_log_config", lambda **_: {"log": "cfg"})
    monkeypatch.setattr("app.main.logging.config.dictConfig", dict_config)
    monkeypatch.setattr("app.main.Config", config_factory)
    monkeypatch.setattr("app.main.Server", server_factory)

    main.callback(
        port=8100,
        host="0.0.0.0",
        env="production",
        reload=False,
        workers=2,
        verbose=False,
    )

    dict_config.assert_called_once_with({"log": "cfg"})
    config_factory.assert_called_once_with(
        app="app.main:create_app",
        factory=True,
        host="0.0.0.0",
        port=8100,
        workers=2,
        use_colors=True,
    )
    server_factory.assert_called_once_with(config_instance)
    server_instance.run.assert_called_once_with()
