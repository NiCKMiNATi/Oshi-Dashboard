"""One-shot CLI locking and bounded logs; no scheduling or ingestion policy."""

import errno
import logging
import os
import time
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from logging.handlers import RotatingFileHandler
from pathlib import Path


class FetchBusy(Exception):
    pass


@contextmanager
def fetch_lock(runtime: Path):
    runtime.mkdir(mode=0o700, parents=True, exist_ok=True)
    # Never delete this file: the OS releases the lock even after a crash.
    with (runtime / "ingestion.lock").open("a+b") as stream:
        if os.name == "nt":
            import msvcrt

            if stream.seek(0, 2) == 0:
                stream.write(b"\0")
                stream.flush()
            stream.seek(0)

            def acquire():
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)

            def release():
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            def acquire():
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)

            def release():
                fcntl.flock(stream, fcntl.LOCK_UN)

        try:
            acquire()
        except OSError as error:
            if error.errno in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
                raise FetchBusy("Fetch already running; skipped this invocation.") from None
            raise
        try:
            yield
        finally:
            stream.seek(0)
            release()


class LogStream:
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.pending = ""

    def write(self, value: str) -> int:
        self.pending += value
        while "\n" in self.pending or len(self.pending) >= 4096:
            end = self.pending.find("\n")
            end = min(end, 4096) if end >= 0 else 4096
            line, self.pending = self.pending[:end], self.pending[end:]
            self.pending = self.pending.removeprefix("\n")
            if line:
                self.logger.info("%s", line)
        return len(value)

    def flush(self):
        if self.pending:
            self.logger.info("%s", self.pending)
            self.pending = ""


class FetchLogHandler(RotatingFileHandler):
    def handleError(self, record):
        # Logging's default error handler writes tracebacks to stderr, which is
        # redirected to this same handler. Fail clearly instead of recursing.
        raise OSError("Cannot write background log") from None


@contextmanager
def background_log(runtime: Path):
    # Call only while holding fetch_lock: rotation has a single writer.
    handler = FetchLogHandler(
        runtime / "background-fetch.log", maxBytes=1_048_576, backupCount=3, encoding="utf-8"
    )
    formatter = logging.Formatter("%(asctime)sZ %(message)s", datefmt="%Y-%m-%dT%H:%M:%S")
    formatter.converter = time.gmtime
    handler.setFormatter(formatter)
    logger = logging.Logger("oshi.background", level=logging.INFO)
    logger.addHandler(handler)
    stream = LogStream(logger)
    try:
        with redirect_stdout(stream), redirect_stderr(stream):
            yield
            stream.flush()
    finally:
        try:
            stream.flush()
        finally:
            handler.close()
