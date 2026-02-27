from tests import _bootstrap  # noqa: F401

import logging
import queue
import unittest

from gui.main import QueueLogHandler


class IpcEmitterTests(unittest.TestCase):
    def test_queue_log_handler_emit(self) -> None:
        out = queue.Queue()
        handler = QueueLogHandler(out)
        handler.setFormatter(logging.Formatter("%(levelname)s:%(message)s"))

        logger = logging.getLogger("test.queue.handler")
        logger.setLevel(logging.INFO)
        logger.handlers = [handler]
        logger.propagate = False

        logger.info("hello")
        self.assertEqual(out.get(timeout=1), "INFO:hello")


if __name__ == "__main__":
    unittest.main()
