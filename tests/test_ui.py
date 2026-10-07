import json
import os
import tempfile
import time
import unittest
from threading import Event
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication

import rddownloader


class UiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def pump_until(self, predicate, timeout=2):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self.app.processEvents()
            if predicate():
                return True
            time.sleep(0.01)
        self.app.processEvents()
        return predicate()

    def test_load_config_normalizes_invalid_concurrency_without_real_config(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json") as config:
            json.dump({"max_concurrent": "not-a-number"}, config)
            config.flush()
            with patch.object(rddownloader, "CONFIG_PATH", config.name):
                self.assertEqual(
                    rddownloader.load_config()["max_concurrent"], 3)

            config.seek(0)
            config.truncate()
            json.dump({"max_concurrent": 99}, config)
            config.flush()
            with patch.object(rddownloader, "CONFIG_PATH", config.name):
                self.assertEqual(
                    rddownloader.load_config()["max_concurrent"], 10)

    def make_window(self):
        config = {
            "api_key": "test-token",
            "download_folder": tempfile.gettempdir(),
            "language": "en",
            "max_concurrent": 1,
        }
        config_patch = patch.object(rddownloader, "load_config", return_value=config)
        save_patch = patch.object(rddownloader, "save_config")
        verify_patch = patch.object(rddownloader.MainWindow, "AUTO_VERIFY", False)
        for p in (config_patch, save_patch, verify_patch):
            p.start()
            self.addCleanup(p.stop)
        window = rddownloader.MainWindow()
        self.addCleanup(window.close)
        return window

    def test_verify_account_is_async_and_handles_success(self):
        entered = Event()
        release = Event()
        user = {
            "username": "tester",
            "type": "premium",
            "expiration": "2030-01-01T00:00:00Z",
        }

        def blocked_user(_api):
            entered.set()
            release.wait(2)
            return user

        window = self.make_window()
        with patch.object(rddownloader.RealDebrid, "user", blocked_user):
            started = time.monotonic()
            window.verify_account()
            elapsed = time.monotonic() - started
            self.assertLess(elapsed, 0.5)
            self.assertFalse(window.check_btn.isEnabled())
            self.assertTrue(entered.wait(1))
            release.set()
            self.assertTrue(self.pump_until(
                lambda: window._verify_job is None and window.check_btn.isEnabled()))
            self.assertEqual(window._last_user, user)

    def test_verify_account_is_async_and_handles_error(self):
        entered = Event()
        release = Event()

        def blocked_user(_api):
            entered.set()
            release.wait(2)
            raise RuntimeError("simulated network failure")

        window = self.make_window()
        with patch.object(rddownloader.RealDebrid, "user", blocked_user), \
                patch.object(rddownloader.QMessageBox, "critical") as critical:
            started = time.monotonic()
            window.verify_account()
            self.assertLess(time.monotonic() - started, 0.5)
            self.assertTrue(entered.wait(1))
            release.set()
            self.assertTrue(self.pump_until(
                lambda: window._verify_job is None and window.check_btn.isEnabled()))
            self.assertIsNone(window._last_user)
            critical.assert_called_once()

    def test_empty_state_and_clear_finished(self):
        window = self.make_window()
        self.assertEqual(window.stack.currentIndex(), 0)
        with patch.object(window.pool, "start"):
            window._start_job("magnet", "magnet:?xt=urn:btih:abc", "a")
            window._start_job("magnet", "magnet:?xt=urn:btih:def", "b")
        self.assertEqual(window.stack.currentIndex(), 1)
        window.on_done("job1", "a")
        window.on_failed("job2", "boom")
        self.assertTrue(window.clear_btn.isEnabled())
        window.clear_finished()
        self.assertEqual(window.table.rowCount(), 0)
        self.assertEqual(window.stack.currentIndex(), 0)

    def test_retry_reuses_failed_row(self):
        window = self.make_window()
        with patch.object(window.pool, "start") as start:
            window._start_job("magnet", "magnet:?xt=urn:btih:abc", "a")
            window.on_failed("job1", "boom")
            window.retry("job1")
            self.assertEqual(start.call_count, 2)
        self.assertEqual(window.table.rowCount(), 1)
        self.assertEqual(window.rows["job1"]["state"], "queued")
        self.assertIn("job1", window.jobs)
        window.jobs["job1"].cancel()  # nothing active: close without asking


if __name__ == "__main__":
    unittest.main()
