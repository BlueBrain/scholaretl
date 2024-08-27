"""Injectable dependencies for endpoints."""

import logging
from functools import cache

from scholaretl.app.config import Settings

logger = logging.getLogger(__name__)


@cache
def get_settings() -> Settings:
    """Load all parameters.

    Note that this function is cached and environment will be read just once.
    """
    logger.info("Reading the environment and instantiating settings")
    return Settings()
