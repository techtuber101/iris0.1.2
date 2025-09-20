import logging
import os
import sys
from time import monotonic

class RateLimitedFilter(logging.Filter):
    """Allow up to N records per key every window seconds."""
    def __init__(self, max_per_window=50, window_sec=1.0):
        super().__init__()
        self.max = max_per_window
        self.window = window_sec
        self._bucket = {}
    
    def filter(self, record):
        key = (record.name, record.levelno)
        now = monotonic()
        win_start, count = self._bucket.get(key, (now, 0))
        if now - win_start > self.window:
            self._bucket[key] = (now, 1)
            return True
        if count < self.max:
            self._bucket[key] = (win_start, count + 1)
            return True
        return False

def configure_logging():
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(RateLimitedFilter(
        max_per_window=int(os.getenv("LOG_MAX_PER_WINDOW", "200")),
        window_sec=float(os.getenv("LOG_WINDOW_SEC", "1.0")),
    ))
    fmt = "%(asctime)s %(levelname)s %(name)s: %(message)s"
    handler.setFormatter(logging.Formatter(fmt))
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
