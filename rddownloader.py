#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RDDownloader — Download torrents and magnets through Real-Debrid without
opening the website.

Paste a magnet link or open a .torrent file. The app sends it to Real-Debrid
(which downloads it on their servers), fetches the direct links and downloads
the files to the folder you choose, with progress bar, speed and ETA.

Multi-language UI (Português / English / Español). See translations.py.

Requirements: PyQt5, requests   ->   pip install -r requirements.txt
"""

import os
import sys
import json
import time
import threading
import subprocess
import traceback
import tempfile
import shutil
import re
from collections import deque
from urllib.parse import urlsplit, parse_qs

import requests
from PyQt5.QtCore import (
    Qt, QObject, QRunnable, QThreadPool, pyqtSignal, pyqtSlot, QLocale,
    QTimer, QPointF, QRectF, QSize
)
from PyQt5.QtGui import (
    QIcon, QPixmap, QPainter, QColor, QLinearGradient, QPen, QPalette, QFont,
    QKeySequence
)
from PyQt5.QtWidgets import (
    QApplication, QWidget, QMainWindow, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QFileDialog, QTableWidget, QTableWidgetItem,
    QProgressBar, QFrame, QHeaderView, QMessageBox, QAbstractItemView,
    QComboBox, QSpinBox, QSystemTrayIcon, QMenu, QStackedWidget, QShortcut,
    QSizePolicy
)

import translations as i18n
from translations import tr


APP_NAME = "RDDownloader"
APP_VERSION = "1.1.0"
APITOKEN_URL = "https://real-debrid.com/apitoken"


# --------------------------------------------------------------------------
# Persistent configuration (API key + folder + language + concurrency)
# --------------------------------------------------------------------------
CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".config", "rddownloader")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")


def load_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            if not isinstance(cfg, dict):
                return {}
            # Keep persisted values within the same bounds as the UI. A
            # malformed config must not prevent the application from starting.
            try:
                value = int(cfg.get("max_concurrent", 3))
            except (TypeError, ValueError):
                value = 3
            cfg["max_concurrent"] = max(1, min(value, 10))
            for key in ("api_key", "download_folder", "language"):
                if key in cfg and not isinstance(cfg[key], str):
                    cfg.pop(key)
            return cfg
    except Exception:
        return {}


def save_config(cfg):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        # The file holds the API key: create it readable by the owner only.
        fd = os.open(CONFIG_PATH, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception:
        pass


# --------------------------------------------------------------------------
# Real-Debrid API client
# --------------------------------------------------------------------------
class RealDebridError(Exception):
    pass


class RealDebrid:
    BASE = "https://api.real-debrid.com/rest/1.0"

    def __init__(self, token):
        self.token = (token or "").strip()
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "%s/%s" % (APP_NAME, APP_VERSION)

    def _headers(self):
        return {"Authorization": "Bearer " + self.token}

    def _check(self, r):
        if r.status_code == 401:
            raise RealDebridError(tr("err_invalid_key"))
        if r.status_code == 403:
            raise RealDebridError(tr("err_forbidden"))
        if not r.ok:
            try:
                msg = r.json().get("error", r.text)
            except Exception:
                msg = r.text
            raise RealDebridError(tr("err_status", code=r.status_code, msg=msg))
        return r

    def user(self):
        r = self._check(self.session.get(self.BASE + "/user",
                                         headers=self._headers(), timeout=30))
        return r.json()

    def add_magnet(self, magnet):
        r = self._check(self.session.post(
            self.BASE + "/torrents/addMagnet",
            headers=self._headers(), data={"magnet": magnet}, timeout=60))
        return r.json()["id"]

    def add_torrent_file(self, filepath):
        with open(filepath, "rb") as f:
            data = f.read()
        r = self._check(self.session.put(
            self.BASE + "/torrents/addTorrent",
            headers=self._headers(), data=data, timeout=120))
        return r.json()["id"]

    def select_files(self, torrent_id, files="all"):
        self._check(self.session.post(
            self.BASE + "/torrents/selectFiles/" + torrent_id,
            headers=self._headers(), data={"files": files}, timeout=60))

    def info(self, torrent_id):
        r = self._check(self.session.get(
            self.BASE + "/torrents/info/" + torrent_id,
            headers=self._headers(), timeout=30))
        return r.json()

    def unrestrict(self, link):
        r = self._check(self.session.post(
            self.BASE + "/unrestrict/link",
            headers=self._headers(), data={"link": link}, timeout=60))
        return r.json()

    def delete(self, torrent_id):
        try:
            self.session.delete(self.BASE + "/torrents/" + torrent_id,
                                headers=self._headers(), timeout=30)
        except Exception:
            pass


class VerifySignals(QObject):
    succeeded = pyqtSignal(object)
    failed = pyqtSignal(str)


class VerifyAccountJob(QRunnable):
    """Run account verification away from the GUI thread."""

    def __init__(self, token):
        super().__init__()
        self.token = token
        self.signals = VerifySignals()

    @pyqtSlot()
    def run(self):
        try:
            self.signals.succeeded.emit(RealDebrid(self.token).user())
        except Exception as e:
            self.signals.failed.emit(str(e))


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
ERROR_STATES = {"magnet_error", "error", "virus", "dead"}
MAX_RETRIES = 3
RETRY_DELAY = 30
SPEED_WINDOW = 4.0  # seconds of history used for the instantaneous speed


class _Paused(Exception):
    pass


class _Canceled(Exception):
    pass


def human_size(n):
    if not n:
        return "-"
    units = ["B", "KB", "MB", "GB", "TB"]
    f = float(n)
    for u in units:
        if f < 1024 or u == units[-1]:
            return "%.1f %s" % (f, u)
        f /= 1024


def human_duration(secs):
    secs = max(int(secs), 0)
    if secs < 60:
        return "%ds" % secs
    m, s = divmod(secs, 60)
    if m < 60:
        return "%dm %02ds" % (m, s)
    h, m = divmod(m, 60)
    return "%dh %02dm" % (h, m)


def magnet_display_name(magnet):
    """Readable name for a magnet: its 'dn' field, else a short info-hash."""
    try:
        query = parse_qs(urlsplit(magnet).query)
        name = (query.get("dn") or [""])[0].strip()
        if name:
            return name
        info_hash = (query.get("xt") or [""])[0].rsplit(":", 1)[-1]
        if info_hash:
            return "magnet:%s…" % info_hash[:16]
    except Exception:
        pass
    return magnet[:60] + "…"


# --------------------------------------------------------------------------
# Worker that processes one item (magnet/torrent) from start to finish
# --------------------------------------------------------------------------
class JobSignals(QObject):
    name = pyqtSignal(str, str)        # job_id, name
    size = pyqtSignal(str, str)        # job_id, human size
    status = pyqtSignal(str, str)      # job_id, status text
    progress = pyqtSignal(str, int)    # job_id, 0-100
    speed = pyqtSignal(str, str)       # job_id, speed (+ ETA)
    download_url = pyqtSignal(str, str)  # job_id, current file's direct URL
    done = pyqtSignal(str, str)        # job_id, final name (for notification)
    failed = pyqtSignal(str, str)      # job_id, message


class DownloadJob(QRunnable):
    def __init__(self, job_id, token, source_kind, source, dest_folder):
        super().__init__()
        self.job_id = job_id
        self.api = RealDebrid(token)
        self.source_kind = source_kind   # "magnet" or "torrent"
        self.source = source
        self.dest_folder = dest_folder
        self.signals = JobSignals()
        self._cancel = False
        self._pause_event = threading.Event()
        self._pause_event.set()  # start unpaused
        self.torrent_id = None
        self.display_name = ""
        self._partial_path = None
        self._samples = deque()  # (timestamp, bytes downloaded) for speed

    def cancel(self):
        self._cancel = True
        self._pause_event.set()  # unblock any waiting

    def pause(self):
        self._pause_event.clear()

    def resume(self):
        self._pause_event.set()

    @property
    def is_paused(self):
        return not self._pause_event.is_set()

    def _wait_if_paused(self):
        if not self._pause_event.is_set():
            self.signals.status.emit(self.job_id, tr("st_paused"))
            self.signals.speed.emit(self.job_id, "")
            while not self._cancel:
                if self._pause_event.wait(timeout=0.5):
                    break
            # Time spent paused must not drag the speed average down.
            self._samples.clear()

    def _sleep(self, seconds):
        """Sleep in small steps so cancellation and pause are responsive."""
        end = time.time() + seconds
        while time.time() < end:
            if self._cancel:
                return
            self._wait_if_paused()
            if self._cancel:
                return
            time.sleep(0.2)

    def _discard_partial(self):
        if self._partial_path:
            try:
                os.unlink(self._partial_path)
            except OSError:
                pass
            self._partial_path = None

    def _rd_status_text(self, st, pct):
        if st in ("downloading", "queued") and pct:
            return tr("st_rd_downloading", pct=pct)
        if st == "magnet_conversion":
            return tr("st_rd_converting")
        if st == "queued":
            return tr("st_rd_queued")
        if st in ("compressing", "uploading"):
            return tr("st_rd_processing", pct=pct)
        if st == "downloading":
            return tr("st_rd_downloading", pct=pct)
        return tr("st_rd_generic", status=st)

    @pyqtSlot()
    def run(self):
        jid = self.job_id
        finished = False
        try:
            self._wait_if_paused()
            if self._cancel:
                raise _Canceled()
            self.signals.status.emit(jid, tr("st_sending"))
            if self.source_kind == "magnet":
                self.torrent_id = self.api.add_magnet(self.source)
            else:
                self.torrent_id = self.api.add_torrent_file(self.source)

            # Wait for conversion and select files
            selected = False
            info = {}
            while not self._cancel:
                self._wait_if_paused()
                if self._cancel:
                    break
                try:
                    info = self.api.info(self.torrent_id)
                except requests.RequestException:
                    self._sleep(10)
                    continue
                st = info.get("status", "")
                fname = info.get("filename") or info.get("original_filename")
                if fname:
                    self.display_name = fname
                    self.signals.name.emit(jid, fname)
                if info.get("bytes"):
                    self.signals.size.emit(jid, human_size(info["bytes"]))

                if st in ERROR_STATES:
                    raise RealDebridError(tr("err_rd_status", status=st))
                if st == "downloaded":
                    break
                if st == "waiting_files_selection" and not selected:
                    self.signals.status.emit(jid, tr("st_selecting"))
                    self.api.select_files(self.torrent_id, "all")
                    selected = True
                    self._sleep(1)
                    continue

                rd_prog = info.get("progress", 0) or 0
                self.signals.status.emit(jid, self._rd_status_text(st, rd_prog))
                self.signals.progress.emit(jid, int(rd_prog) // 2)
                speed = info.get("speed")
                self.signals.speed.emit(
                    jid, "RD " + human_size(speed) + "/s" if speed else "")
                self._sleep(2)

            if self._cancel:
                raise _Canceled()

            # Unrestrict links
            self.signals.speed.emit(jid, "")
            self.signals.status.emit(jid, tr("st_getting_links"))
            links = info.get("links", [])
            if not links:
                raise RealDebridError(tr("err_no_links"))

            unrestricted = []
            for ln in links:
                if self._cancel:
                    raise _Canceled()
                unrestricted.append(self.api.unrestrict(ln))

            total = sum(u.get("filesize", 0) for u in unrestricted)
            if total:
                self.signals.size.emit(jid, human_size(total))

            # Download files
            os.makedirs(self.dest_folder, exist_ok=True)
            downloaded_total = 0
            start = time.time()
            filename = ""
            for u in unrestricted:
                if self._cancel:
                    raise _Canceled()
                filename = u.get("filename", "download.bin")
                url = u.get("download")
                self.signals.download_url.emit(jid, url or "")
                attempt = 0
                while True:
                    if self._cancel:
                        raise _Canceled()
                    self._wait_if_paused()
                    if self._cancel:
                        raise _Canceled()
                    try:
                        self.signals.status.emit(
                            jid, tr("st_downloading_file", name=filename))
                        downloaded_total = self._download_file(
                            jid, url, filename, downloaded_total, total, start)
                        break
                    except _Paused:
                        self._wait_if_paused()
                        continue
                    except (requests.RequestException, OSError):
                        if self._cancel:
                            raise _Canceled()
                        attempt += 1
                        if attempt >= MAX_RETRIES:
                            raise
                        self.signals.speed.emit(jid, "")
                        for secs_left in range(RETRY_DELAY, 0, -1):
                            if self._cancel:
                                raise _Canceled()
                            self._wait_if_paused()
                            self.signals.status.emit(
                                jid, tr("st_retry", secs=secs_left,
                                        n=attempt, max=MAX_RETRIES))
                            time.sleep(1)
                        self._samples.clear()

            if self._cancel:
                raise _Canceled()
            elapsed = max(time.time() - start, 0.001)
            finished = True
            self.signals.progress.emit(jid, 100)
            self.signals.speed.emit(jid, "")
            self.signals.status.emit(jid, tr(
                "st_done", size=human_size(downloaded_total),
                elapsed=human_duration(elapsed)))
            self.signals.done.emit(jid, self.display_name or filename)

        except _Canceled:
            self.signals.status.emit(jid, tr("st_canceled"))
        except RealDebridError as e:
            self.signals.failed.emit(jid, str(e))
        except requests.RequestException as e:
            self.signals.failed.emit(jid, tr("err_network", err=e))
        except Exception as e:
            traceback.print_exc()
            self.signals.failed.emit(jid, tr("err_generic", err=e))
        finally:
            # Never leave hidden .part files behind in the user's folder.
            if not finished:
                self._discard_partial()

    def _publish_file(self, filename):
        # Exclusive creation also protects against downloads in other processes.
        filename = os.path.basename(filename.replace("\\", "/"))
        if filename in ("", ".", ".."):
            filename = "download.bin"
        stem, ext = os.path.splitext(filename)
        suffix = 0
        while True:
            name = filename if suffix == 0 else "%s (%d)%s" % (stem, suffix, ext)
            dest = os.path.join(self.dest_folder, name)
            try:
                os.link(self._partial_path, dest)
            except FileExistsError:
                suffix += 1
                continue
            except OSError:
                # Filesystems without hard links still get overwrite protection.
                try:
                    output = open(dest, "xb")
                except FileExistsError:
                    suffix += 1
                    continue
                try:
                    with output, open(self._partial_path, "rb") as source:
                        shutil.copyfileobj(source, output)
                except BaseException:
                    os.unlink(dest)
                    raise
            os.unlink(self._partial_path)
            self._partial_path = None
            return

    def _speed_text(self, now, current_total, total):
        """Instantaneous speed over the last few seconds, plus ETA."""
        samples = self._samples
        samples.append((now, current_total))
        while len(samples) > 2 and now - samples[0][0] > SPEED_WINDOW:
            samples.popleft()
        t0, b0 = samples[0]
        if now - t0 < 0.05:
            return ""
        rate = max(current_total - b0, 0) / (now - t0)
        text = human_size(rate) + "/s" if rate else "0 B/s"
        if total and rate > 0 and current_total < total:
            text += " · " + human_duration((total - current_total) / rate)
        return text

    def _download_file(self, jid, url, filename, downloaded_total, total, start):
        if self._cancel:
            raise _Canceled()
        if self._partial_path is None:
            fd, self._partial_path = tempfile.mkstemp(
                prefix=".rddownloader-", suffix=".part", dir=self.dest_folder)
            os.close(fd)
        offset = os.path.getsize(self._partial_path)
        headers = {"Accept-Encoding": "identity"}
        if offset:
            headers["Range"] = "bytes=%d-" % offset
        with self.api.session.get(url, headers=headers, stream=True, timeout=60) as r:
            if self._cancel:
                raise _Canceled()
            if r.status_code == 416 and offset:
                if r.headers.get("Content-Range") == "bytes */%d" % offset:
                    self._publish_file(filename)
                    return downloaded_total + offset
            r.raise_for_status()
            file_total = int(r.headers.get("Content-Length", 0))
            if r.status_code == 206:
                match = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+)",
                                     r.headers.get("Content-Range", ""))
                if not match or int(match[1]) != offset:
                    raise requests.RequestException(tr("err_download_range"))
                file_total = int(match[3])
                if int(match[2]) != file_total - 1:
                    raise requests.RequestException(tr("err_download_range"))
            else:
                # A server that ignores Range must restart, never append.
                offset = 0
            file_bytes = offset
            last_emit = 0
            if not self._samples:
                self._samples.append((time.time(), downloaded_total + offset))
            with open(self._partial_path, "ab" if offset else "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 256):
                    if self._cancel:
                        raise _Canceled()
                    if not self._pause_event.is_set():
                        raise _Paused()
                    if not chunk:
                        continue
                    f.write(chunk)
                    file_bytes += len(chunk)
                    current_total = downloaded_total + file_bytes
                    now = time.time()
                    if now - last_emit >= 0.4:
                        last_emit = now
                        if total:
                            pct = 50 + int((current_total / total) * 50)
                            self.signals.progress.emit(jid, min(pct, 99))
                        elif file_total:
                            self.signals.progress.emit(
                                jid, min(int(file_bytes / file_total * 100), 99))
                        self.signals.speed.emit(
                            jid, self._speed_text(now, current_total, total))
            if file_total and file_bytes != file_total:
                raise requests.RequestException(tr("err_download_incomplete"))
        if self._cancel:
            raise _Canceled()
        self._publish_file(filename)
        return downloaded_total + file_bytes


# --------------------------------------------------------------------------
# Look & feel
# --------------------------------------------------------------------------
COLORS = {
    "bg": "#0E1016",
    "surface": "#161922",
    "raised": "#1E2230",
    "raised_hi": "#262B3C",
    "input": "#11141B",
    "border": "#272C3B",
    "border_hi": "#373D51",
    "text": "#E8EAF1",
    "muted": "#9096AB",
    "faint": "#5F657A",
    "accent": "#7C6CFF",
    "accent_hi": "#9488FF",
    "accent_lo": "#6152F2",
    "ok": "#34D399",
    "warn": "#FBBF24",
    "err": "#F87171",
    "select": "#25223F",
}

STYLESHEET = """
QWidget { color: %(text)s; }
QMainWindow, QWidget#central { background: %(bg)s; }
QFrame#card { background: %(surface)s; border: 1px solid %(border)s;
    border-radius: 14px; }
QFrame#dropCard { background: %(surface)s; border: 2px dashed %(border_hi)s;
    border-radius: 14px; }
QFrame#dropCard[dragging="true"] { border-color: %(accent)s;
    background: #1A1930; }
QLabel { background: transparent; }
QLabel#title { font-size: 17pt; font-weight: 700; }
QLabel#subtitle, QLabel#muted { color: %(muted)s; }
QLabel#hint { color: %(faint)s; }
QLabel#version { color: %(faint)s; font-size: 8pt; }
QLabel#sectionTitle { font-size: 11.5pt; font-weight: 700; }
QLabel#fieldLabel { color: %(muted)s; font-weight: 600; }
QLabel#counter { color: %(muted)s; background: %(raised)s; border-radius: 9px;
    padding: 2px 9px; font-weight: 700; }
QLabel#emptyTitle { font-size: 13pt; font-weight: 700; }
QLabel#emptyBody { color: %(muted)s; }
QLabel a { color: %(accent_hi)s; }

QLabel#pill { border-radius: 13px; padding: 5px 12px; font-weight: 600;
    background: %(raised)s; color: %(muted)s; border: 1px solid %(border)s; }
QLabel#pill[state="ok"] { color: %(ok)s; background: rgba(52,211,153,0.10);
    border-color: rgba(52,211,153,0.40); }
QLabel#pill[state="warn"] { color: %(warn)s; background: rgba(251,191,36,0.10);
    border-color: rgba(251,191,36,0.40); }
QLabel#pill[state="error"] { color: %(err)s; background: rgba(248,113,113,0.10);
    border-color: rgba(248,113,113,0.40); }

QLineEdit, QSpinBox, QComboBox { background: %(input)s;
    border: 1px solid %(border)s; border-radius: 9px; padding: 7px 10px;
    selection-background-color: %(accent)s; selection-color: white; }
QLineEdit:hover, QSpinBox:hover, QComboBox:hover { border-color: %(border_hi)s; }
QLineEdit:focus, QSpinBox:focus, QComboBox:focus { border-color: %(accent)s; }
QLineEdit#magnetEdit { padding: 11px 14px; font-size: 10.5pt; }
QComboBox { padding-right: 28px; }
QComboBox::drop-down { border: none; width: 26px; }
QComboBox::down-arrow { image: url("%(arrow_down)s"); width: 10px; height: 6px; }
QSpinBox { padding-right: 24px; }
QSpinBox::up-button, QSpinBox::down-button { width: 22px; border: none;
    background: transparent; }
QSpinBox::up-arrow { image: url("%(arrow_up)s"); width: 10px; height: 6px; }
QSpinBox::down-arrow { image: url("%(arrow_down)s"); width: 10px; height: 6px; }
QComboBox QAbstractItemView { background: %(raised)s; color: %(text)s;
    border: 1px solid %(border_hi)s; outline: 0; padding: 4px;
    selection-background-color: %(accent)s; selection-color: white; }

QPushButton { background: %(raised)s; border: 1px solid %(border)s;
    border-radius: 9px; padding: 8px 16px; font-weight: 600; }
QPushButton:hover { background: %(raised_hi)s; border-color: %(border_hi)s; }
QPushButton:pressed { background: %(surface)s; }
QPushButton:disabled { color: %(faint)s; background: %(surface)s;
    border-color: %(border)s; }
QPushButton[variant="primary"] { background: %(accent)s; color: white;
    border: 1px solid %(accent)s; }
QPushButton[variant="primary"]:hover { background: %(accent_hi)s;
    border-color: %(accent_hi)s; }
QPushButton[variant="primary"]:pressed { background: %(accent_lo)s; }
QPushButton[variant="primary"]:disabled { background: %(raised)s;
    color: %(faint)s; border-color: %(border)s; }
QPushButton[variant="ghost"] { background: transparent;
    border-color: transparent; color: %(muted)s; }
QPushButton[variant="ghost"]:hover { color: %(text)s; background: %(raised)s; }
QPushButton[variant="ghost"]:checked { color: %(text)s; background: %(raised)s;
    border-color: %(border)s; }
QPushButton[variant="danger"]:hover { color: %(err)s;
    border-color: rgba(248,113,113,0.55); }

QTableWidget { background: transparent; border: none; outline: 0;
    gridline-color: transparent; selection-background-color: %(select)s;
    selection-color: %(text)s; }
QTableWidget::item { border-bottom: 1px solid %(border)s; padding: 0 10px; }
QTableWidget::item:selected { background: %(select)s; color: %(text)s; }
QWidget#progressCell { background: transparent; }
QLabel#pct { color: %(muted)s; font-size: 8.5pt; font-weight: 700; }
QHeaderView { background: transparent; }
QHeaderView::section { background: transparent; color: %(faint)s;
    border: none; border-bottom: 1px solid %(border)s; padding: 6px 10px;
    font-size: 8.5pt; font-weight: 700; }

QProgressBar { background: %(raised_hi)s; border: none; border-radius: 4px;
    min-height: 8px; max-height: 8px; }
QProgressBar::chunk { border-radius: 4px; background: qlineargradient(
    x1:0, y1:0, x2:1, y2:0, stop:0 %(accent_lo)s, stop:1 %(accent_hi)s); }
QProgressBar[state="done"]::chunk { background: %(ok)s; }
QProgressBar[state="paused"]::chunk { background: %(warn)s; }
QProgressBar[state="error"]::chunk { background: %(err)s; }

QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: %(border_hi)s; border-radius: 3px;
    min-height: 30px; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; width: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }

QMenu { background: %(raised)s; border: 1px solid %(border_hi)s;
    border-radius: 10px; padding: 6px; }
QMenu::item { padding: 7px 20px; border-radius: 6px; }
QMenu::item:selected { background: %(accent)s; color: white; }
QMenu::item:disabled { color: %(faint)s; }
QMenu::separator { height: 1px; background: %(border)s; margin: 5px 8px; }
QToolTip { background: %(raised)s; color: %(text)s;
    border: 1px solid %(border_hi)s; padding: 6px; }
QMessageBox { background: %(surface)s; }
"""


def _arrow_images():
    """Small chevrons for combo/spin boxes (QSS needs image files)."""
    folder = os.path.join(CONFIG_DIR, "theme")
    paths = {}
    try:
        os.makedirs(folder, exist_ok=True)
        for name, up in (("arrow_down", False), ("arrow_up", True)):
            for scale, suffix in ((1, ""), (2, "@2x")):
                pm = QPixmap(10 * scale, 6 * scale)
                pm.fill(Qt.transparent)
                p = QPainter(pm)
                p.setRenderHint(QPainter.Antialiasing)
                p.setPen(QPen(QColor(COLORS["muted"]), 1.6 * scale,
                              Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                y0, y1 = (5 * scale, 1 * scale) if up else (1 * scale, 5 * scale)
                p.drawPolyline(QPointF(1 * scale, y0), QPointF(5 * scale, y1),
                               QPointF(9 * scale, y0))
                p.end()
                pm.save(os.path.join(folder, name + suffix + ".png"))
            paths[name] = os.path.join(folder, name + ".png").replace("\\", "/")
    except Exception:
        paths = {"arrow_down": "", "arrow_up": ""}
    return paths


def apply_theme(app):
    app.setStyle("Fusion")
    pal = QPalette()
    c = {k: QColor(v) for k, v in COLORS.items()}
    pal.setColor(QPalette.Window, c["surface"])
    pal.setColor(QPalette.WindowText, c["text"])
    pal.setColor(QPalette.Base, c["input"])
    pal.setColor(QPalette.AlternateBase, c["raised"])
    pal.setColor(QPalette.Text, c["text"])
    pal.setColor(QPalette.Button, c["raised"])
    pal.setColor(QPalette.ButtonText, c["text"])
    pal.setColor(QPalette.Highlight, c["accent"])
    pal.setColor(QPalette.HighlightedText, QColor("white"))
    pal.setColor(QPalette.ToolTipBase, c["raised"])
    pal.setColor(QPalette.ToolTipText, c["text"])
    pal.setColor(QPalette.PlaceholderText, c["faint"])
    pal.setColor(QPalette.Link, c["accent_hi"])
    for role in (QPalette.Text, QPalette.WindowText, QPalette.ButtonText):
        pal.setColor(QPalette.Disabled, role, c["faint"])
    app.setPalette(pal)
    font = app.font()
    font.setPointSizeF(max(font.pointSizeF(), 10.0))
    app.setFont(font)
    app.setStyleSheet(STYLESHEET % dict(COLORS, **_arrow_images()))


def app_icon_pixmap(size):
    """The app icon (violet tile with a download arrow), drawn in code."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    s = float(size)
    tile = QRectF(s * 0.04, s * 0.04, s * 0.92, s * 0.92)
    grad = QLinearGradient(tile.topLeft(), tile.bottomRight())
    grad.setColorAt(0, QColor("#9A8CFF"))
    grad.setColorAt(1, QColor("#4F46E5"))
    p.setPen(Qt.NoPen)
    p.setBrush(grad)
    p.drawRoundedRect(tile, s * 0.24, s * 0.24)
    p.setPen(QPen(QColor("white"), s * 0.085, Qt.SolidLine, Qt.RoundCap,
                  Qt.RoundJoin))
    p.setBrush(Qt.NoBrush)
    p.drawLine(QPointF(s * 0.5, s * 0.23), QPointF(s * 0.5, s * 0.60))
    p.drawPolyline(QPointF(s * 0.33, s * 0.45), QPointF(s * 0.5, s * 0.62),
                   QPointF(s * 0.67, s * 0.45))
    p.drawLine(QPointF(s * 0.30, s * 0.76), QPointF(s * 0.70, s * 0.76))
    p.end()
    return pm


def app_icon():
    icon = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        icon.addPixmap(app_icon_pixmap(size))
    return icon


def repolish(widget):
    widget.style().unpolish(widget)
    widget.style().polish(widget)


def make_button(variant=None):
    btn = QPushButton()
    btn.setCursor(Qt.PointingHandCursor)
    if variant:
        btn.setProperty("variant", variant)
    return btn


def make_card(name="card"):
    card = QFrame()
    card.setObjectName(name)
    return card


def make_label(name=None):
    lbl = QLabel()
    if name:
        lbl.setObjectName(name)
    return lbl


# --------------------------------------------------------------------------
# Main window
# --------------------------------------------------------------------------
COL_NAME, COL_SIZE, COL_PROGRESS, COL_SPEED, COL_STATUS = range(5)
STATUS_COLORS = {"done": "ok", "error": "err", "paused": "warn"}


class MainWindow(QMainWindow):
    # Check the saved key in the background when the window opens.
    AUTO_VERIFY = True

    def __init__(self):
        super().__init__()
        self.cfg = load_config()

        # Language: saved -> system default -> english
        lang = self.cfg.get("language") or i18n.detect_default(
            QLocale.system().name())
        i18n.set_language(lang)

        self.pool = QThreadPool.globalInstance()
        self.pool.setMaxThreadCount(int(self.cfg.get("max_concurrent", 3)))
        self.account_pool = QThreadPool(self)
        self.account_pool.setMaxThreadCount(1)
        self.jobs = {}        # job_id -> DownloadJob
        self.rows = {}        # job_id -> {widgets + state}
        self._counter = 0
        self._last_user = None
        self._account_state = "none"
        self._verify_job = None
        self._verify_silent = False
        self._last_clipboard = ""

        self.setAcceptDrops(True)
        self.setWindowIcon(app_icon())
        self.resize(1080, 700)
        self.setMinimumSize(820, 560)
        self._build_ui()
        self._load_into_ui()
        self.retranslate_ui()
        self._init_tray()

        app = QApplication.instance()
        if app is not None:
            app.applicationStateChanged.connect(self._on_app_state)
        if self.AUTO_VERIFY and self.key_edit.text().strip():
            QTimer.singleShot(250, lambda: self.verify_account(silent=True))

    # ---------- UI construction ----------
    def _build_ui(self):
        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(22, 18, 22, 18)
        root.setSpacing(14)

        root.addLayout(self._build_header())
        self.settings_card = self._build_settings()
        root.addWidget(self.settings_card)
        self.drop_card = self._build_add()
        root.addWidget(self.drop_card)
        root.addWidget(self._build_downloads(), 1)

        delete = QShortcut(QKeySequence.Delete, self.table,
                           activated=self.cancel_selected)
        delete.setContext(Qt.WidgetWithChildrenShortcut)

    def _build_header(self):
        header = QHBoxLayout()
        header.setSpacing(12)
        logo = QLabel()
        logo.setPixmap(app_icon_pixmap(44))
        logo.setFixedSize(QSize(44, 44))
        header.addWidget(logo)

        titles = QVBoxLayout()
        titles.setSpacing(0)
        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        title = make_label("title")
        title.setText(APP_NAME)
        title_row.addWidget(title)
        version = make_label("version")
        version.setText("v" + APP_VERSION)
        title_row.addWidget(version, 0, Qt.AlignBottom)
        title_row.addStretch(1)
        titles.addLayout(title_row)
        self.subtitle = make_label("subtitle")
        self.subtitle.setMinimumWidth(1)  # may be clipped on narrow windows
        titles.addWidget(self.subtitle)
        header.addLayout(titles, 1)

        self.account_lbl = make_label("pill")
        self.account_lbl.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        header.addWidget(self.account_lbl, 0, Qt.AlignVCenter)

        self.lang_combo = QComboBox()
        self.lang_combo.setCursor(Qt.PointingHandCursor)
        for code, name in i18n.available_languages():
            self.lang_combo.addItem(name, code)
        self.lang_combo.currentIndexChanged.connect(self._on_language_changed)
        header.addWidget(self.lang_combo, 0, Qt.AlignVCenter)

        self.settings_btn = make_button("ghost")
        self.settings_btn.setCheckable(True)
        self.settings_btn.toggled.connect(self._toggle_settings)
        header.addWidget(self.settings_btn, 0, Qt.AlignVCenter)
        return header

    def _build_settings(self):
        card = make_card()
        grid = QGridLayout(card)
        grid.setContentsMargins(18, 16, 18, 16)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(10)

        self.settings_title = make_label("sectionTitle")
        grid.addWidget(self.settings_title, 0, 0, 1, 4)

        self.lbl_key = make_label("fieldLabel")
        grid.addWidget(self.lbl_key, 1, 0)
        self.key_edit = QLineEdit()
        self.key_edit.setEchoMode(QLineEdit.Password)
        self.key_edit.returnPressed.connect(self.verify_account)
        grid.addWidget(self.key_edit, 1, 1)
        self.show_key_btn = make_button("ghost")
        self.show_key_btn.setCheckable(True)
        self.show_key_btn.clicked.connect(self._toggle_key)
        grid.addWidget(self.show_key_btn, 1, 2)
        self.check_btn = make_button("primary")
        self.check_btn.clicked.connect(lambda: self.verify_account())
        grid.addWidget(self.check_btn, 1, 3)

        self.key_help = make_label("hint")
        self.key_help.setOpenExternalLinks(True)
        self.key_help.setTextFormat(Qt.RichText)
        grid.addWidget(self.key_help, 2, 1, 1, 3)

        self.lbl_folder = make_label("fieldLabel")
        grid.addWidget(self.lbl_folder, 3, 0)
        self.folder_edit = QLineEdit()
        self.folder_edit.editingFinished.connect(self._persist)
        grid.addWidget(self.folder_edit, 3, 1)
        self.folder_btn = make_button()
        self.folder_btn.clicked.connect(self.choose_folder)
        grid.addWidget(self.folder_btn, 3, 2, 1, 2)

        self.lbl_concurrent = make_label("fieldLabel")
        grid.addWidget(self.lbl_concurrent, 4, 0)
        self.concurrent_spin = QSpinBox()
        self.concurrent_spin.setRange(1, 10)
        self.concurrent_spin.setFixedWidth(90)
        self.concurrent_spin.valueChanged.connect(self._on_concurrent_changed)
        grid.addWidget(self.concurrent_spin, 4, 1, Qt.AlignLeft)

        grid.setColumnStretch(1, 1)
        return card

    def _build_add(self):
        card = make_card("dropCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 14)
        layout.setSpacing(10)
        self.add_title = make_label("sectionTitle")
        layout.addWidget(self.add_title)
        row = QHBoxLayout()
        row.setSpacing(10)
        self.magnet_edit = QLineEdit()
        self.magnet_edit.setObjectName("magnetEdit")
        self.magnet_edit.setClearButtonEnabled(True)
        self.magnet_edit.returnPressed.connect(self.add_magnet)
        row.addWidget(self.magnet_edit, 1)
        self.add_magnet_btn = make_button("primary")
        self.add_magnet_btn.setMinimumHeight(42)
        self.add_magnet_btn.clicked.connect(self.add_magnet)
        row.addWidget(self.add_magnet_btn)
        self.add_torrent_btn = make_button()
        self.add_torrent_btn.setMinimumHeight(42)
        self.add_torrent_btn.clicked.connect(self.add_torrent)
        row.addWidget(self.add_torrent_btn)
        layout.addLayout(row)
        self.drop_hint = make_label("hint")
        layout.addWidget(self.drop_hint)
        return card

    def _build_downloads(self):
        card = make_card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(10)

        top = QHBoxLayout()
        top.setSpacing(8)
        self.downloads_title = make_label("sectionTitle")
        top.addWidget(self.downloads_title)
        self.counter_lbl = make_label("counter")
        top.addWidget(self.counter_lbl)
        top.addStretch(1)
        self.pause_btn = make_button()
        self.pause_btn.setEnabled(False)
        self.pause_btn.clicked.connect(self.pause_resume_selected)
        top.addWidget(self.pause_btn)
        self.cancel_btn = make_button("danger")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.cancel_selected)
        top.addWidget(self.cancel_btn)
        self.clear_btn = make_button()
        self.clear_btn.setEnabled(False)
        self.clear_btn.clicked.connect(self.clear_finished)
        top.addWidget(self.clear_btn)
        self.open_folder_btn = make_button()
        self.open_folder_btn.clicked.connect(self.open_folder)
        top.addWidget(self.open_folder_btn)
        layout.addLayout(top)

        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_empty_state())

        self.table = QTableWidget(0, 5)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setFocusPolicy(Qt.StrongFocus)
        self.table.setShowGrid(False)
        self.table.setWordWrap(False)
        self.table.setTextElideMode(Qt.ElideRight)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(48)
        self.table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_download_menu)
        self.table.itemSelectionChanged.connect(self._update_actions)
        self.table.itemDoubleClicked.connect(self._on_row_double_clicked)
        hh = self.table.horizontalHeader()
        hh.setHighlightSections(False)
        hh.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        hh.setSectionResizeMode(COL_NAME, QHeaderView.Stretch)
        hh.setSectionResizeMode(COL_PROGRESS, QHeaderView.Fixed)
        self.table.setColumnWidth(COL_SIZE, 90)
        self.table.setColumnWidth(COL_PROGRESS, 170)
        self.table.setColumnWidth(COL_SPEED, 165)
        self.table.setColumnWidth(COL_STATUS, 290)
        self.stack.addWidget(self.table)
        layout.addWidget(self.stack, 1)
        return card

    def _build_empty_state(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addStretch(1)
        icon = QLabel()
        pm = app_icon_pixmap(72)
        faded = QPixmap(pm.size())
        faded.fill(Qt.transparent)
        p = QPainter(faded)
        p.setOpacity(0.35)
        p.drawPixmap(0, 0, pm)
        p.end()
        icon.setPixmap(faded)
        icon.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon)
        layout.addSpacing(6)
        self.empty_title = make_label("emptyTitle")
        self.empty_title.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.empty_title)
        self.empty_body = make_label("emptyBody")
        self.empty_body.setAlignment(Qt.AlignCenter)
        self.empty_body.setWordWrap(True)
        layout.addWidget(self.empty_body)
        layout.addStretch(1)
        return page

    def _load_into_ui(self):
        self.key_edit.setText(self.cfg.get("api_key", ""))
        default_folder = self.cfg.get(
            "download_folder",
            os.path.join(os.path.expanduser("~"), "Downloads", "RealDebrid"))
        self.folder_edit.setText(default_folder)
        self.concurrent_spin.setValue(int(self.cfg.get("max_concurrent", 3)))
        # Select current language in the combo
        idx = self.lang_combo.findData(i18n.current_language())
        if idx >= 0:
            self.lang_combo.blockSignals(True)
            self.lang_combo.setCurrentIndex(idx)
            self.lang_combo.blockSignals(False)
        # First run: open the settings so the user sees where the key goes.
        needs_setup = not self.key_edit.text().strip()
        self.settings_btn.setChecked(needs_setup)
        self.settings_card.setVisible(needs_setup)
        (self.key_edit if needs_setup else self.magnet_edit).setFocus()
        self._refresh_list()

    def retranslate_ui(self):
        """Apply the current language to all static widgets."""
        self.setWindowTitle(tr("app_title"))
        self.subtitle.setText(tr("app_subtitle"))
        self.settings_btn.setText(tr("btn_settings"))
        self.lang_combo.setToolTip(tr("lbl_language"))
        self.settings_title.setText(tr("group_config"))
        self.lbl_key.setText(tr("lbl_api_key"))
        self.key_edit.setPlaceholderText(tr("ph_api_key"))
        self.show_key_btn.setText(
            tr("btn_hide") if self.show_key_btn.isChecked() else tr("btn_show"))
        self.check_btn.setText(tr("btn_verify"))
        self.key_help.setText(tr(
            "key_help", link='<a href="%s">real-debrid.com/apitoken</a>'
            % APITOKEN_URL))
        self.lbl_folder.setText(tr("lbl_folder"))
        self.folder_btn.setText(tr("btn_choose"))
        self.lbl_concurrent.setText(tr("lbl_concurrent"))
        self.add_title.setText(tr("group_add"))
        self.magnet_edit.setPlaceholderText(tr("ph_magnet"))
        self.add_magnet_btn.setText(tr("btn_add_magnet"))
        self.add_torrent_btn.setText(tr("btn_open_torrent"))
        self.drop_hint.setText(tr("hint_drop"))
        self.downloads_title.setText(tr("group_downloads"))
        self.empty_title.setText(tr("empty_title"))
        self.empty_body.setText(tr("empty_body"))
        self.table.setHorizontalHeaderLabels([
            tr(k).upper() for k in
            ("col_name", "col_size", "col_progress", "col_speed", "col_status")])
        self.cancel_btn.setText(tr("btn_remove"))
        self.clear_btn.setText(tr("btn_clear_done"))
        self.open_folder_btn.setText(tr("btn_open_folder"))
        if getattr(self, "tray", None):
            self.tray.setToolTip(tr("app_title"))
        self._update_account_label()
        self._update_actions()

    def _init_tray(self):
        self.tray = None
        try:
            if QSystemTrayIcon.isSystemTrayAvailable():
                self.tray = QSystemTrayIcon(app_icon(), self)
                self.tray.setToolTip(tr("app_title"))
                self.tray.activated.connect(self._on_tray_activated)
                self.tray.show()
        except Exception:
            self.tray = None

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self.showNormal()
            self.raise_()
            self.activateWindow()

    def _toggle_key(self):
        if self.show_key_btn.isChecked():
            self.key_edit.setEchoMode(QLineEdit.Normal)
            self.show_key_btn.setText(tr("btn_hide"))
        else:
            self.key_edit.setEchoMode(QLineEdit.Password)
            self.show_key_btn.setText(tr("btn_show"))

    def _toggle_settings(self, visible):
        self.settings_card.setVisible(visible)

    def _open_settings(self, focus=None):
        self.settings_btn.setChecked(True)
        if focus is not None:
            focus.setFocus()

    def _on_app_state(self, state):
        # Coming back to the window with a magnet copied: offer it ready to add.
        if state != Qt.ApplicationActive or self.magnet_edit.text():
            return
        text = QApplication.clipboard().text().strip()
        if text.lower().startswith("magnet:") and text != self._last_clipboard:
            self._last_clipboard = text
            self.magnet_edit.setText(text)
            self.magnet_edit.selectAll()
            self.magnet_edit.setFocus()

    # ---------- Language / concurrency ----------
    def _on_language_changed(self, _index):
        code = self.lang_combo.currentData()
        if not code:
            return
        i18n.set_language(code)
        self.cfg["language"] = code
        save_config(self.cfg)
        self.retranslate_ui()

    def _on_concurrent_changed(self, value):
        self.pool.setMaxThreadCount(int(value))
        self.cfg["max_concurrent"] = int(value)
        save_config(self.cfg)

    # ---------- Configuration ----------
    def _persist(self):
        self.cfg["api_key"] = self.key_edit.text().strip()
        self.cfg["download_folder"] = self.folder_edit.text().strip()
        self.cfg["language"] = i18n.current_language()
        self.cfg["max_concurrent"] = self.concurrent_spin.value()
        save_config(self.cfg)

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, tr("dlg_choose_folder"), self.folder_edit.text())
        if folder:
            self.folder_edit.setText(folder)
            self._persist()

    def _set_account_state(self, state):
        self._account_state = state
        self._update_account_label()

    def _update_account_label(self):
        state = self._account_state
        if state in ("ok", "warn") and self._last_user is not None:
            u = self._last_user
            text = tr("account_info", user=u.get("username", "?"),
                      type=u.get("type", ""),
                      exp=(u.get("expiration") or "")[:10])
        elif state == "checking":
            text = tr("account_checking")
        elif state == "error":
            text = tr("account_error")
        elif not self.key_edit.text().strip():
            text = tr("account_no_key")
        else:
            text = tr("account_not_verified")
        self.account_lbl.setText("●  " + text)
        self.account_lbl.setProperty("state", state)
        repolish(self.account_lbl)

    def verify_account(self, silent=False):
        if self._verify_job is not None:
            return
        token = self.key_edit.text().strip()
        if not token:
            if not silent:
                QMessageBox.warning(self, tr("title_warning"), tr("msg_need_key"))
                self._open_settings(self.key_edit)
            return
        self._persist()
        self._verify_silent = silent
        self.check_btn.setEnabled(False)
        self._set_account_state("checking")
        job = VerifyAccountJob(token)
        self._verify_job = job
        job.signals.succeeded.connect(self._on_account_verified)
        job.signals.failed.connect(self._on_account_verification_failed)
        self.account_pool.start(job)

    def _on_account_verified(self, user):
        self._verify_job = None
        self.check_btn.setEnabled(True)
        self._last_user = user
        premium = user.get("type") == "premium"
        self._set_account_state("ok" if premium else "warn")
        if not premium:
            self._open_settings()
            if not self._verify_silent:
                QMessageBox.warning(
                    self, tr("title_notice"), tr("msg_not_premium"))
        elif not self._verify_silent:
            # Key is good: get the settings out of the way.
            self.settings_btn.setChecked(False)

    def _on_account_verification_failed(self, message):
        self._verify_job = None
        self.check_btn.setEnabled(True)
        self._last_user = None
        self._set_account_state("error")
        self.account_lbl.setToolTip(message)
        self._open_settings()
        if not self._verify_silent:
            QMessageBox.critical(self, tr("title_error"), message)

    # ---------- Adding downloads ----------
    def _validate_ready(self):
        if not self.key_edit.text().strip():
            QMessageBox.warning(self, tr("title_warning"), tr("msg_need_key"))
            self._open_settings(self.key_edit)
            return False
        if not self.folder_edit.text().strip():
            QMessageBox.warning(self, tr("title_warning"), tr("msg_need_folder"))
            self._open_settings(self.folder_edit)
            return False
        self._persist()
        return True

    def add_magnet(self):
        magnet = self.magnet_edit.text().strip()
        if not magnet:
            self.magnet_edit.setFocus()
            return
        if not magnet.lower().startswith("magnet:"):
            QMessageBox.warning(self, tr("title_warning"), tr("msg_bad_magnet"))
            return
        if not self._validate_ready():
            return
        self.magnet_edit.clear()
        self._last_clipboard = magnet
        self._start_job("magnet", magnet, magnet_display_name(magnet))

    def add_torrent(self):
        if not self._validate_ready():
            return
        paths, _ = QFileDialog.getOpenFileNames(
            self, tr("dlg_choose_torrent"), "", tr("dlg_torrent_filter"))
        for path in paths:
            self._start_job("torrent", path, os.path.basename(path))

    def _start_job(self, kind, source, display_name, jid=None):
        if jid is None:
            self._counter += 1
            jid = "job%d" % self._counter
            self.rows[jid] = self._add_row(jid, display_name)
        row = self.rows[jid]
        row.update(kind=kind, source=source, state="queued", download_url="")

        job = DownloadJob(jid, self.key_edit.text().strip(),
                          kind, source, self.folder_edit.text().strip())
        job.display_name = display_name
        s = job.signals
        s.name.connect(self.on_name)
        s.size.connect(self.on_size)
        s.status.connect(self.on_status)
        s.progress.connect(self.on_progress)
        s.speed.connect(self.on_speed)
        s.download_url.connect(self.on_download_url)
        s.done.connect(self.on_done)
        s.failed.connect(self.on_failed)
        self.jobs[jid] = job
        self.pool.start(job)
        self._refresh_list()

    def _add_row(self, jid, name):
        r = self.table.rowCount()
        self.table.insertRow(r)
        name_item = QTableWidgetItem(name)
        name_item.setData(Qt.UserRole, jid)
        name_item.setToolTip(name)
        font = name_item.font()
        font.setWeight(QFont.DemiBold)
        name_item.setFont(font)
        self.table.setItem(r, COL_NAME, name_item)
        size_item = QTableWidgetItem("-")
        self.table.setItem(r, COL_SIZE, size_item)
        cell = QWidget()
        cell.setObjectName("progressCell")
        cell_layout = QHBoxLayout(cell)
        cell_layout.setContentsMargins(10, 0, 12, 0)
        cell_layout.setSpacing(8)
        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(0)
        bar.setTextVisible(False)
        bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        cell_layout.addWidget(bar)
        pct = make_label("pct")
        pct.setText("0%")
        pct.setMinimumWidth(36)
        pct.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        cell_layout.addWidget(pct)
        bar.valueChanged.connect(lambda v, lbl=pct: lbl.setText("%d%%" % v))
        self.table.setCellWidget(r, COL_PROGRESS, cell)
        speed_item = QTableWidgetItem("")
        self.table.setItem(r, COL_SPEED, speed_item)
        status_item = QTableWidgetItem(tr("st_queued"))
        self.table.setItem(r, COL_STATUS, status_item)
        row = {"name": name_item, "size": size_item, "bar": bar,
               "speed": speed_item, "status": status_item, "download_url": ""}
        self._paint_state(row, "queued")
        return row

    def _paint_state(self, row, state):
        row["state"] = state
        row["bar"].setProperty("state", state)
        repolish(row["bar"])
        color = COLORS[STATUS_COLORS.get(state, "muted")]
        row["status"].setForeground(QColor(color))

    def _row_of(self, jid):
        for r in range(self.table.rowCount()):
            item = self.table.item(r, COL_NAME)
            if item is not None and item.data(Qt.UserRole) == jid:
                return r
        return -1

    def _selected_jids(self):
        jids = []
        for index in self.table.selectionModel().selectedRows(COL_NAME):
            item = self.table.item(index.row(), COL_NAME)
            if item is not None:
                jids.append(item.data(Qt.UserRole))
        return jids

    def _remove_rows(self, jids):
        for jid in jids:
            job = self.jobs.pop(jid, None)
            if job is not None:
                job.cancel()
            self.rows.pop(jid, None)
            r = self._row_of(jid)
            if r >= 0:
                self.table.removeRow(r)
        self._refresh_list()

    def _refresh_list(self):
        total = self.table.rowCount()
        self.stack.setCurrentIndex(1 if total else 0)
        active = sum(1 for row in self.rows.values()
                     if row.get("state") in ("queued", "active", "paused"))
        self.counter_lbl.setVisible(bool(total))
        self.counter_lbl.setText(tr("counter", total=total, active=active))
        self._update_actions()

    def _show_download_menu(self, pos):
        row = self.table.rowAt(pos.y())
        if row < 0:
            return
        name_item = self.table.item(row, COL_NAME)
        if name_item is None:
            return
        jid = name_item.data(Qt.UserRole)
        info = self.rows.get(jid, {})
        url = info.get("download_url", "")
        if jid not in self._selected_jids():
            self.table.selectRow(row)
        menu = QMenu(self)
        retry_action = None
        if info.get("state") == "error":
            retry_action = menu.addAction(tr("menu_retry"))
        copy_action = menu.addAction(tr("menu_copy_download_url"))
        copy_action.setEnabled(bool(url))
        if not url:
            copy_action.setToolTip(tr("menu_url_unavailable"))
            menu.setToolTipsVisible(True)
        folder_action = menu.addAction(tr("btn_open_folder"))
        menu.addSeparator()
        remove_action = menu.addAction(tr("btn_remove"))
        chosen = menu.exec_(self.table.viewport().mapToGlobal(pos))
        if chosen is None:
            return
        if chosen == copy_action:
            QApplication.clipboard().setText(url)
        elif chosen == retry_action:
            self.retry(jid)
        elif chosen == folder_action:
            self.open_folder()
        elif chosen == remove_action:
            self.cancel_selected()

    def _on_row_double_clicked(self, item):
        jid = self.table.item(item.row(), COL_NAME).data(Qt.UserRole)
        state = self.rows.get(jid, {}).get("state")
        if state == "done":
            self.open_folder()
        elif state == "error":
            self.retry(jid)

    def retry(self, jid):
        row = self.rows.get(jid)
        if not row or row.get("state") != "error" or not self._validate_ready():
            return
        row["bar"].setValue(0)
        row["speed"].setText("")
        row["status"].setText(tr("st_queued"))
        self._paint_state(row, "queued")
        self._start_job(row["kind"], row["source"], row["name"].text(), jid)

    # ---------- Drag & drop ----------
    def _set_dragging(self, on):
        self.drop_card.setProperty("dragging", "true" if on else "false")
        self.drop_hint.setText(tr("hint_drop_now") if on else tr("hint_drop"))
        repolish(self.drop_card)

    def dragEnterEvent(self, event):
        md = event.mimeData()
        if md.hasUrls() or md.hasText():
            event.acceptProposedAction()
            self._set_dragging(True)

    def dragLeaveEvent(self, event):
        self._set_dragging(False)

    def dropEvent(self, event):
        self._set_dragging(False)
        md = event.mimeData()
        if md.hasUrls():
            for url in md.urls():
                path = url.toLocalFile()
                if path.lower().endswith(".torrent") and os.path.isfile(path):
                    if self._validate_ready():
                        self._start_job("torrent", path, os.path.basename(path))
                elif url.toString().lower().startswith("magnet:"):
                    self.magnet_edit.setText(url.toString())
                    self.add_magnet()
        elif md.hasText() and md.text().strip().lower().startswith("magnet:"):
            self.magnet_edit.setText(md.text().strip())
            self.add_magnet()
        event.acceptProposedAction()

    # ---------- Signal slots ----------
    def on_name(self, jid, name):
        if jid in self.rows:
            self.rows[jid]["name"].setText(name)
            self.rows[jid]["name"].setToolTip(name)

    def on_size(self, jid, size):
        if jid in self.rows:
            self.rows[jid]["size"].setText(size)

    def on_status(self, jid, text):
        row = self.rows.get(jid)
        if row is None:
            return
        row["status"].setText(text)
        row["status"].setToolTip(text)
        job = self.jobs.get(jid)
        if row["state"] == "queued" and job is not None and not job.is_paused:
            self._paint_state(row, "active")
            self._refresh_list()

    def on_progress(self, jid, pct):
        if jid in self.rows:
            self.rows[jid]["bar"].setValue(pct)

    def on_speed(self, jid, text):
        if jid in self.rows:
            self.rows[jid]["speed"].setText(text)

    def on_download_url(self, jid, url):
        if jid in self.rows:
            self.rows[jid]["download_url"] = url

    def on_done(self, jid, name):
        row = self.rows.get(jid)
        if row is not None:
            row["speed"].setText("")
            self._paint_state(row, "done")
        self.jobs.pop(jid, None)
        self._refresh_list()
        if self.tray:
            try:
                self.tray.showMessage(
                    tr("notify_done_title"),
                    tr("notify_done_body", name=name),
                    QSystemTrayIcon.Information, 5000)
            except Exception:
                pass

    def on_failed(self, jid, msg):
        row = self.rows.get(jid)
        if row is not None:
            row["status"].setText(tr("err_prefix") + msg)
            row["status"].setToolTip(msg + "\n\n" + tr("hint_retry"))
            row["speed"].setText("")
            self._paint_state(row, "error")
        self.jobs.pop(jid, None)
        self._refresh_list()

    # ---------- Download actions ----------
    def _update_actions(self):
        jids = self._selected_jids()
        running = [self.jobs[j] for j in jids if j in self.jobs]
        self.cancel_btn.setEnabled(bool(jids))
        self.pause_btn.setEnabled(bool(running))
        if running and all(job.is_paused for job in running):
            self.pause_btn.setText(tr("btn_resume"))
        else:
            self.pause_btn.setText(tr("btn_pause"))
        self.clear_btn.setEnabled(any(
            row.get("state") in ("done", "error") for row in self.rows.values()))

    def pause_resume_selected(self):
        jids = [j for j in self._selected_jids() if j in self.jobs]
        if not jids:
            return
        resume = all(self.jobs[j].is_paused for j in jids)
        for jid in jids:
            job = self.jobs[jid]
            row = self.rows.get(jid)
            if resume:
                job.resume()
                if row is not None:
                    self._paint_state(row, "active")
            else:
                job.pause()
                if row is not None:
                    self._paint_state(row, "paused")
                    row["status"].setText(tr("st_paused"))
                    row["speed"].setText("")
        self._refresh_list()

    def cancel_selected(self):
        self._remove_rows(self._selected_jids())

    def clear_finished(self):
        self._remove_rows([jid for jid, row in self.rows.items()
                           if row.get("state") in ("done", "error")])

    def open_folder(self):
        folder = self.folder_edit.text().strip()
        if not folder:
            return
        try:
            os.makedirs(folder, exist_ok=True)
            if sys.platform.startswith("win"):
                os.startfile(folder)  # noqa: only exists on Windows
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])
        except Exception:
            pass

    def closeEvent(self, event):
        active = [j for j in self.jobs.values() if not j._cancel]
        if active:
            answer = QMessageBox.question(
                self, tr("title_quit"), tr("msg_quit_active", n=len(active)),
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if answer != QMessageBox.Yes:
                event.ignore()
                return
        for job in list(self.jobs.values()):
            job.cancel()
        self._persist()
        # Let canceled jobs remove their partial files before exiting.
        self.pool.waitForDone(3000)
        if self.tray:
            self.tray.hide()
        event.accept()


def main():
    if sys.platform.startswith("win"):
        try:
            # Own taskbar entry/icon instead of the generic Python one.
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                APP_NAME)
        except Exception:
            pass
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setWindowIcon(app_icon())
    apply_theme(app)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
