import logging
import os
import sys

PY_ENV = os.environ.get("PY_ENV", "production")

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG if PY_ENV == "development" else logging.WARNING)

formatter = logging.Formatter("[%(levelname)s] [%(asctime)s] %(message)s")
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)
