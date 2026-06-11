#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RDDownloader — Download torrents and magnets through Real-Debrid without
opening the website.

Paste a magnet link or open a .torrent file. The app sends it to Real-Debrid
(which downloads it on their servers), fetches the direct links and downloads
the files to the folder you choose, with progress bar and speed.

Multi-language UI (Português / English / Español). See translations.py.

Requirements: PyQt5, requests   ->   pip install PyQt5 requests
"""

import os
import sys
import json
import time
import subprocess
import traceback

import requests
from PyQt5.QtCore import (
    Qt, QObject, QRunnable, QThreadPool, pyqtSignal, pyqtSlot, QLocale
)
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QApplication, QWidget, QMainWindow, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QFileDialog, QTableWidget, QTableWidgetItem,
    QProgressBar, QGroupBox, QHeaderView, QMessageBox, QAbstractItemView,
    QComboBox, QSpinBox, QStyle, QSystemTrayIcon
)

import translations as i18n
from translations import tr


# --------------------------------------------------------------------------
# Persistent configuration (API key + folder + language + concurrency)
# --------------------------------------------------------------------------
CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".config", "rddownloader")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")


def load_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_config(cfg):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
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


# --------------------------------------------------------------------------
# Worker that processes one item (magnet/torrent) from start to finish
# --------------------------------------------------------------------------
ERROR_STATES = {"magnet_error", "error", "virus", "dead"}


def human_size(n):
    if not n:
        return "-"
    units = ["B", "KB", "MB", "GB", "TB"]
    f = float(n)
    for u in units:
        if f < 1024 or u == units[-1]:
            return "%.1f %s" % (f, u)
        f /= 1024


class JobSignals(QObject):
    name = pyqtSignal(str, str)        # job_id, name
    size = pyqtSignal(str, str)        # job_id, human size
    status = pyqtSignal(str, str)      # job_id, status text
    progress = pyqtSignal(str, int)    # job_id, 0-100
    speed = pyqtSignal(str, str)       # job_id, speed
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
        self.torrent_id = None
        self.display_name = ""

    def cancel(self):
        self._cancel = True

    def _sleep(self, seconds):
        """Sleep in small steps so cancellation is responsive."""
        end = time.time() + seconds
        while time.time() < end:
            if self._cancel:
                return
            time.sleep(0.2)

    @pyqtSlot()
    def run(self):
        jid = self.job_id
        try:
            self.signals.status.emit(jid, tr("st_sending"))
            if self.source_kind == "magnet":
                self.torrent_id = self.api.add_magnet(self.source)
            else:
                self.torrent_id = self.api.add_torrent_file(self.source)

            # Wait for conversion and select files
            selected = False
            info = {}
            while not self._cancel:
                info = self.api.info(self.torrent_id)
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

                rd_prog = info.get("progress", 0)
                if st in ("downloading", "queued"):
                    self.signals.status.emit(
                        jid, tr("st_rd_downloading", pct=rd_prog))
                else:
                    self.signals.status.emit(jid, tr("st_rd_generic", status=st))
                self.signals.progress.emit(jid, int(rd_prog) // 2)
                self._sleep(2)

            if self._cancel:
                self.signals.status.emit(jid, tr("st_canceled"))
                return

            # Unrestrict links
            self.signals.status.emit(jid, tr("st_getting_links"))
            links = info.get("links", [])
            if not links:
                raise RealDebridError(tr("err_no_links"))

            unrestricted = []
            for ln in links:
                if self._cancel:
                    self.signals.status.emit(jid, tr("st_canceled"))
                    return
                unrestricted.append(self.api.unrestrict(ln))

            total = sum(u.get("filesize", 0) for u in unrestricted)
            if total:
                self.signals.size.emit(jid, human_size(total))

            # Download files
            os.makedirs(self.dest_folder, exist_ok=True)
            downloaded_total = 0
            start = time.time()
            for u in unrestricted:
                if self._cancel:
                    self.signals.status.emit(jid, tr("st_canceled"))
                    return
                filename = u.get("filename", "download.bin")
                self.signals.status.emit(
                    jid, tr("st_downloading_file", name=filename))
                downloaded_total = self._download_file(
                    jid, u.get("download"), filename,
                    downloaded_total, total, start)

            elapsed = max(time.time() - start, 0.001)
            self.signals.progress.emit(jid, 100)
            self.signals.speed.emit(jid, "")
            self.signals.status.emit(jid, tr(
                "st_done", size=human_size(downloaded_total), secs=int(elapsed)))
            self.signals.done.emit(jid, self.display_name or filename)

        except RealDebridError as e:
            self.signals.failed.emit(jid, str(e))
        except requests.RequestException as e:
            self.signals.failed.emit(jid, tr("err_network", err=e))
        except Exception as e:
            traceback.print_exc()
            self.signals.failed.emit(jid, tr("err_generic", err=e))

    def _download_file(self, jid, url, filename, downloaded_total, total, start):
        dest = os.path.join(self.dest_folder, filename)
        tmp = dest + ".part"
        r = self.api.session.get(url, stream=True, timeout=60)
        r.raise_for_status()
        file_total = int(r.headers.get("Content-Length", 0))
        last_emit = 0
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 256):
                if self._cancel:
                    r.close()
                    return downloaded_total
                if not chunk:
                    continue
                f.write(chunk)
                downloaded_total += len(chunk)

                now = time.time()
                if now - last_emit >= 0.3:
                    last_emit = now
                    if total:
                        pct = 50 + int((downloaded_total / total) * 50)
                        self.signals.progress.emit(jid, min(pct, 99))
                    elif file_total:
                        self.signals.progress.emit(
                            jid, min(int(downloaded_total / file_total * 100), 99))
                    elapsed = max(now - start, 0.001)
                    self.signals.speed.emit(
                        jid, human_size(downloaded_total / elapsed) + "/s")
        os.replace(tmp, dest)
        return downloaded_total


# --------------------------------------------------------------------------
# Main window
# --------------------------------------------------------------------------
COL_NAME, COL_SIZE, COL_PROGRESS, COL_SPEED, COL_STATUS = range(5)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.cfg = load_config()

        # Language: saved -> system default -> english
        lang = self.cfg.get("language") or i18n.detect_default(
            QLocale.system().name())
        i18n.set_language(lang)

        self.pool = QThreadPool.globalInstance()
        self.pool.setMaxThreadCount(int(self.cfg.get("max_concurrent", 3)))
        self.jobs = {}        # job_id -> DownloadJob
        self.rows = {}        # job_id -> {widgets}
        self._counter = 0
        self._last_user = None

        self.setAcceptDrops(True)
        self._build_ui()
        self._load_into_ui()
        self.retranslate_ui()
        self._init_tray()

    # ---------- UI construction ----------
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        # Settings group
        self.cfg_box = QGroupBox()
        grid = QGridLayout(self.cfg_box)

        self.lbl_key = QLabel()
        grid.addWidget(self.lbl_key, 0, 0)
        self.key_edit = QLineEdit()
        self.key_edit.setEchoMode(QLineEdit.Password)
        grid.addWidget(self.key_edit, 0, 1)
        self.show_key_btn = QPushButton()
        self.show_key_btn.setCheckable(True)
        self.show_key_btn.clicked.connect(self._toggle_key)
        grid.addWidget(self.show_key_btn, 0, 2)
        self.check_btn = QPushButton()
        self.check_btn.clicked.connect(self.verify_account)
        grid.addWidget(self.check_btn, 0, 3)

        self.lbl_folder = QLabel()
        grid.addWidget(self.lbl_folder, 1, 0)
        self.folder_edit = QLineEdit()
        grid.addWidget(self.folder_edit, 1, 1)
        self.folder_btn = QPushButton()
        self.folder_btn.clicked.connect(self.choose_folder)
        grid.addWidget(self.folder_btn, 1, 2)
        self.account_lbl = QLabel()
        grid.addWidget(self.account_lbl, 1, 3)

        # Language + concurrency row
        self.lbl_lang = QLabel()
        grid.addWidget(self.lbl_lang, 2, 0)
        self.lang_combo = QComboBox()
        for code, name in i18n.available_languages():
            self.lang_combo.addItem(name, code)
        self.lang_combo.currentIndexChanged.connect(self._on_language_changed)
        grid.addWidget(self.lang_combo, 2, 1)

        self.lbl_concurrent = QLabel()
        grid.addWidget(self.lbl_concurrent, 2, 2)
        self.concurrent_spin = QSpinBox()
        self.concurrent_spin.setRange(1, 10)
        self.concurrent_spin.valueChanged.connect(self._on_concurrent_changed)
        grid.addWidget(self.concurrent_spin, 2, 3)

        grid.setColumnStretch(1, 1)
        root.addWidget(self.cfg_box)

        # Add download group
        self.in_box = QGroupBox()
        in_layout = QHBoxLayout(self.in_box)
        self.magnet_edit = QLineEdit()
        self.magnet_edit.returnPressed.connect(self.add_magnet)
        in_layout.addWidget(self.magnet_edit, 1)
        self.add_magnet_btn = QPushButton()
        self.add_magnet_btn.clicked.connect(self.add_magnet)
        in_layout.addWidget(self.add_magnet_btn)
        self.add_torrent_btn = QPushButton()
        self.add_torrent_btn.clicked.connect(self.add_torrent)
        in_layout.addWidget(self.add_torrent_btn)
        root.addWidget(self.in_box)

        # Downloads table
        self.table = QTableWidget(0, 5)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(COL_NAME, QHeaderView.Stretch)
        hh.setSectionResizeMode(COL_PROGRESS, QHeaderView.Fixed)
        self.table.setColumnWidth(COL_PROGRESS, 180)
        self.table.setColumnWidth(COL_SIZE, 90)
        self.table.setColumnWidth(COL_SPEED, 100)
        self.table.setColumnWidth(COL_STATUS, 220)
        root.addWidget(self.table, 1)

        # Bottom buttons
        bottom = QHBoxLayout()
        bottom.addStretch(1)
        self.cancel_btn = QPushButton()
        self.cancel_btn.clicked.connect(self.cancel_selected)
        bottom.addWidget(self.cancel_btn)
        self.open_folder_btn = QPushButton()
        self.open_folder_btn.clicked.connect(self.open_folder)
        bottom.addWidget(self.open_folder_btn)
        root.addLayout(bottom)

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

    def retranslate_ui(self):
        """Apply the current language to all static widgets."""
        self.setWindowTitle(tr("app_title"))
        self.cfg_box.setTitle(tr("group_config"))
        self.lbl_key.setText(tr("lbl_api_key"))
        self.key_edit.setPlaceholderText(tr("ph_api_key"))
        self.show_key_btn.setText(
            tr("btn_hide") if self.show_key_btn.isChecked() else tr("btn_show"))
        self.check_btn.setText(tr("btn_verify"))
        self.lbl_folder.setText(tr("lbl_folder"))
        self.folder_btn.setText(tr("btn_choose"))
        self.lbl_lang.setText(tr("lbl_language"))
        self.lbl_concurrent.setText(tr("lbl_concurrent"))
        self.in_box.setTitle(tr("group_add"))
        self.magnet_edit.setPlaceholderText(tr("ph_magnet"))
        self.add_magnet_btn.setText(tr("btn_add_magnet"))
        self.add_torrent_btn.setText(tr("btn_open_torrent"))
        self.table.setHorizontalHeaderLabels([
            tr("col_name"), tr("col_size"), tr("col_progress"),
            tr("col_speed"), tr("col_status")])
        self.cancel_btn.setText(tr("btn_cancel_remove"))
        self.open_folder_btn.setText(tr("btn_open_folder"))
        self._update_account_label()

    def _init_tray(self):
        self.tray = None
        try:
            if QSystemTrayIcon.isSystemTrayAvailable():
                icon = self.style().standardIcon(QStyle.SP_ArrowDown)
                self.tray = QSystemTrayIcon(icon, self)
                self.tray.setToolTip(tr("app_title"))
                self.tray.show()
        except Exception:
            self.tray = None

    def _toggle_key(self):
        if self.show_key_btn.isChecked():
            self.key_edit.setEchoMode(QLineEdit.Normal)
            self.show_key_btn.setText(tr("btn_hide"))
        else:
            self.key_edit.setEchoMode(QLineEdit.Password)
            self.show_key_btn.setText(tr("btn_show"))

    # ---------- Language / concurrency ----------
    def _on_language_changed(self, _index):
        code = self.lang_combo.currentData()
        if not code:
            return
        i18n.set_language(code)
        self.cfg["language"] = code
        save_config(self.cfg)
        self.retranslate_ui()
        if self.tray:
            self.tray.setToolTip(tr("app_title"))

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

    def _update_account_label(self):
        if self._last_user is None:
            self.account_lbl.setText(tr("account_not_verified"))
            return
        u = self._last_user
        self.account_lbl.setText(tr(
            "account_info",
            user=u.get("username", "?"),
            type=u.get("type", ""),
            exp=u.get("expiration", "")[:10]))

    def verify_account(self):
        token = self.key_edit.text().strip()
        if not token:
            QMessageBox.warning(self, tr("title_warning"), tr("msg_need_key"))
            return
        self._persist()
        try:
            self._last_user = RealDebrid(token).user()
        except Exception as e:
            self._last_user = None
            self.account_lbl.setText(tr("account_error"))
            QMessageBox.critical(self, tr("title_error"), str(e))
            return
        self._update_account_label()
        if self._last_user.get("type") != "premium":
            QMessageBox.warning(
                self, tr("title_notice"), tr("msg_not_premium"))

    # ---------- Adding downloads ----------
    def _validate_ready(self):
        if not self.key_edit.text().strip():
            QMessageBox.warning(self, tr("title_warning"), tr("msg_need_key"))
            return False
        if not self.folder_edit.text().strip():
            QMessageBox.warning(self, tr("title_warning"), tr("msg_need_folder"))
            return False
        self._persist()
        return True

    def add_magnet(self):
        magnet = self.magnet_edit.text().strip()
        if not magnet:
            return
        if not magnet.lower().startswith("magnet:"):
            QMessageBox.warning(self, tr("title_warning"), tr("msg_bad_magnet"))
            return
        if not self._validate_ready():
            return
        self.magnet_edit.clear()
        self._start_job("magnet", magnet, magnet[:60] + "...")

    def add_torrent(self):
        if not self._validate_ready():
            return
        path, _ = QFileDialog.getOpenFileName(
            self, tr("dlg_choose_torrent"), "", tr("dlg_torrent_filter"))
        if path:
            self._start_job("torrent", path, os.path.basename(path))

    def _start_job(self, kind, source, display_name):
        self._counter += 1
        jid = "job%d" % self._counter
        self.rows[jid] = self._add_row(jid, display_name)

        job = DownloadJob(jid, self.key_edit.text().strip(),
                          kind, source, self.folder_edit.text().strip())
        job.display_name = display_name
        s = job.signals
        s.name.connect(self.on_name)
        s.size.connect(self.on_size)
        s.status.connect(self.on_status)
        s.progress.connect(self.on_progress)
        s.speed.connect(self.on_speed)
        s.done.connect(self.on_done)
        s.failed.connect(self.on_failed)
        self.jobs[jid] = job
        self.pool.start(job)

    def _add_row(self, jid, name):
        r = self.table.rowCount()
        self.table.insertRow(r)
        name_item = QTableWidgetItem(name)
        name_item.setData(Qt.UserRole, jid)
        self.table.setItem(r, COL_NAME, name_item)
        size_item = QTableWidgetItem("-")
        self.table.setItem(r, COL_SIZE, size_item)
        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(0)
        self.table.setCellWidget(r, COL_PROGRESS, bar)
        speed_item = QTableWidgetItem("")
        self.table.setItem(r, COL_SPEED, speed_item)
        status_item = QTableWidgetItem(tr("st_queued"))
        self.table.setItem(r, COL_STATUS, status_item)
        return {"name": name_item, "size": size_item, "bar": bar,
                "speed": speed_item, "status": status_item}

    # ---------- Drag & drop ----------
    def dragEnterEvent(self, event):
        md = event.mimeData()
        if md.hasUrls() or md.hasText():
            event.acceptProposedAction()

    def dropEvent(self, event):
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

    def on_size(self, jid, size):
        if jid in self.rows:
            self.rows[jid]["size"].setText(size)

    def on_status(self, jid, text):
        if jid in self.rows:
            self.rows[jid]["status"].setText(text)

    def on_progress(self, jid, pct):
        if jid in self.rows:
            self.rows[jid]["bar"].setValue(pct)

    def on_speed(self, jid, text):
        if jid in self.rows:
            self.rows[jid]["speed"].setText(text)

    def on_done(self, jid, name):
        if jid in self.rows:
            self.rows[jid]["speed"].setText("")
        self.jobs.pop(jid, None)
        if self.tray:
            try:
                self.tray.showMessage(
                    tr("notify_done_title"),
                    tr("notify_done_body", name=name),
                    QSystemTrayIcon.Information, 5000)
            except Exception:
                pass

    def on_failed(self, jid, msg):
        if jid in self.rows:
            self.rows[jid]["status"].setText(tr("err_prefix") + msg)
            self.rows[jid]["speed"].setText("")
        self.jobs.pop(jid, None)

    # ---------- Bottom actions ----------
    def cancel_selected(self):
        items = self.table.selectedItems()
        if not items:
            return
        row = items[0].row()
        name_item = self.table.item(row, COL_NAME)
        jid = name_item.data(Qt.UserRole) if name_item else None
        if jid and jid in self.jobs:
            self.jobs[jid].cancel()
        self.rows.pop(jid, None)
        self.jobs.pop(jid, None)
        self.table.removeRow(row)

    def open_folder(self):
        folder = self.folder_edit.text().strip()
        if not (folder and os.path.isdir(folder)):
            return
        try:
            if sys.platform.startswith("win"):
                os.startfile(folder)  # noqa: only exists on Windows
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])
        except Exception:
            pass

    def closeEvent(self, event):
        for job in list(self.jobs.values()):
            job.cancel()
        self._persist()
        event.accept()


def main():
    app = QApplication([])
    app.setStyle("Fusion")
    app.setApplicationName("RDDownloader")
    win = MainWindow()
    win.show()
    app.exec_()


if __name__ == "__main__":
    main()
