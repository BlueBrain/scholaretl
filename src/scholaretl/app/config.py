"""Configuration."""

import os
from typing import Literal

from dotenv import dotenv_values
from pydantic import BaseModel, ConfigDict
from pydantic_settings import BaseSettings, SettingsConfigDict


class SettingsGrobid(BaseModel):
    """Grobid settings."""

    url: str | None = None

    model_config = ConfigDict(frozen=True)


class SettingsLogging(BaseModel):
    """Metadata settings."""

    level: Literal["debug", "info", "warning", "error", "critical"] = "info"
    external_packages: Literal["debug", "info", "warning", "error", "critical"] = (
        "warning"
    )

    model_config = ConfigDict(frozen=True)


class Settings(BaseSettings):
    """All settings."""

    grobid: SettingsGrobid = SettingsGrobid()  # has no required
    logging: SettingsLogging = SettingsLogging()  # has no required

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="SCHOLARETL__",
        env_nested_delimiter="__",
        frozen=True,
    )


# Load the remaining variables into the environment
# Necessary for things like SSL_CERT_FILE
config = dotenv_values()
for k, v in config.items():
    if k.lower().startswith("scholaretl_"):
        continue
    if v is None:
        continue
    os.environ[k] = os.environ.get(k, v)  # environment has precedence
