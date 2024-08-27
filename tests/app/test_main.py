import logging

from fastapi.testclient import TestClient
from scholaretl.app.config import Settings
from scholaretl.app.dependencies import get_settings
from scholaretl.app.main import app


def test_startup(caplog, monkeypatch):
    caplog.set_level(logging.INFO)
    monkeypatch.setenv("SCHOLARETL__GROBID__ULR", "fake-url")
    monkeypatch.setenv("SCHOLARETL__LOGGING__LEVEL", "debug")
    monkeypatch.setenv("SCHOLARETL__LOGGING__EXTERNAL_PACKAGES", "critical")

    # The with statement triggers the startup.
    with TestClient(app) as test_client:
        test_client.get("/healthz")
    assert caplog.record_tuples[0][::2] == (
        "scholaretl.app.dependencies",
        "Reading the environment and instantiating settings",
    )
    assert (
        logging.getLevelName(logging.getLogger("scholaretl").getEffectiveLevel())
        == "DEBUG"
    )
    assert (
        logging.getLevelName(logging.getLogger("httpx").getEffectiveLevel())
        == "CRITICAL"
    )


def test_settings_endpoint(app_client):
    custom_settings = Settings(
        grobid={
            "url": "fake-url",
        }
    )
    app.dependency_overrides[get_settings] = lambda: custom_settings

    response = app_client.get("/settings")
    assert response.json() == custom_settings.model_dump(mode="json")

    response = app_client.get("/")
    assert response.json() == {"status": "ok"}
