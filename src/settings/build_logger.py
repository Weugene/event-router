import logging
import sys

from src.middleware.tracer import get_trace_id
from src.settings.configuration_singleton import get_config


class TraceIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "trace_id"):
            record.trace_id = get_trace_id()
        return True


def build_logger(name: str = "event-router") -> logging.Logger:
    config = get_config()
    logger = logging.getLogger(name)
    logger.setLevel(config.log_level.upper())

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt="%(asctime)s %(levelname)s [%(name)s] [trace_id=%(trace_id)s] %(message)s"
        )
        handler.setFormatter(formatter)
        handler.addFilter(TraceIdFilter())
        logger.addHandler(handler)

    return logger
