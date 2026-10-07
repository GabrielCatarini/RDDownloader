#!/usr/bin/env python3
"""
Regenerate the icon, screenshot and social preview in assets/ and copy the
images used by the website into docs/.

    QT_QPA_PLATFORM=offscreen python3 tools/make_assets.py

The screenshot uses demo data only: no real account, key or folder.
"""
import os
import shutil
import sys
from unittest.mock import patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import QRectF, Qt  # noqa: E402
from PyQt5.QtGui import (  # noqa: E402
    QColor, QFont, QImage, QLinearGradient, QPainter, QPainterPath)
from PyQt5.QtWidgets import QApplication  # noqa: E402

import rddownloader as rd  # noqa: E402

ASSETS = os.path.join(ROOT, "assets")
DOCS = os.path.join(ROOT, "docs")

DEMO = [
    ("ubuntu-24.04.1-desktop-amd64.iso", "5.7 GB", 100, "", "done",
     lambda: rd.tr("st_done", size="5.7 GB", elapsed="4m 12s")),
    ("Big.Buck.Bunny.2008.1080p", "1.3 GB", 73, "38.4 MB/s · 9s", "active",
     lambda: rd.tr("st_downloading_file", name="big_buck_bunny_1080p.mp4")),
    ("Sintel.2010.4K.Open.Movie", "4.1 GB", 31, "RD 112.0 MB/s", "active",
     lambda: rd.tr("st_rd_downloading", pct=62)),
    ("debian-12.7.0-amd64-DVD-1.iso", "3.7 GB", 58, "", "paused",
     lambda: rd.tr("st_paused")),
    ("Tears.of.Steel.2012.mkv", "-", 0, "", "error",
     lambda: rd.tr("err_prefix") + rd.tr("err_rd_status", status="dead")),
]


def make_icons():
    rd.app_icon_pixmap(256).save(os.path.join(ASSETS, "icon.png"))
    try:
        from PIL import Image
    except ImportError:
        print("Pillow not installed: skipping icon.ico")
        return
    Image.open(os.path.join(ASSETS, "icon.png")).save(
        os.path.join(ASSETS, "icon.ico"),
        sizes=[(s, s) for s in (16, 24, 32, 48, 64, 128, 256)])


def make_screenshot(lang="en"):
    cfg = {"api_key": "demo", "download_folder": "~/Downloads/RealDebrid",
           "language": lang, "max_concurrent": 3}
    with patch.object(rd, "load_config", return_value=cfg), \
            patch.object(rd, "save_config"), \
            patch.object(rd.MainWindow, "AUTO_VERIFY", False):
        win = rd.MainWindow()
        win.resize(1240, 720)
        win._last_user = {"username": "user", "type": "premium",
                          "expiration": "2027-03-14T00:00:00Z"}
        win._set_account_state("ok")
        with patch.object(win.pool, "start"):
            for i, (name, size, pct, speed, state, status) in enumerate(DEMO):
                win._start_job("magnet", "magnet:?xt=urn:btih:%d" % i, name)
                jid = "job%d" % (i + 1)
                row = win.rows[jid]
                row["size"].setText(size)
                row["bar"].setValue(pct)
                row["speed"].setText(speed)
                row["status"].setText(status())
                win._paint_state(row, state)
                # Nothing runs: canceled jobs keep their row "active" only.
                win.jobs[jid].cancel()
                if state in ("done", "error"):
                    win.jobs.pop(jid)
        win._refresh_list()
        win.table.selectRow(1)
        win.show()
        for _ in range(5):
            QApplication.processEvents()
        win.grab().save(os.path.join(ASSETS, "screenshot.png"))
        win.close()


def make_social_preview():
    """1280x640 card for GitHub's social preview and Open Graph tags."""
    w, h = 1280, 640
    img = QImage(w, h, QImage.Format_ARGB32)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    bg = QLinearGradient(0, 0, w, h)
    bg.setColorAt(0, QColor("#15132B"))
    bg.setColorAt(1, QColor(rd.COLORS["bg"]))
    p.fillRect(0, 0, w, h, bg)

    p.drawPixmap(80, 150, rd.app_icon_pixmap(96))
    p.setPen(QColor(rd.COLORS["text"]))
    font = QFont()
    font.setPixelSize(56)
    font.setWeight(QFont.Bold)
    p.setFont(font)
    p.drawText(QRectF(80, 270, 560, 80), Qt.AlignLeft | Qt.AlignVCenter,
               rd.APP_NAME)
    font.setPixelSize(30)
    font.setWeight(QFont.Normal)
    p.setFont(font)
    p.setPen(QColor(rd.COLORS["muted"]))
    p.drawText(QRectF(80, 355, 520, 90), Qt.AlignLeft | Qt.TextWordWrap,
               "Real-Debrid desktop downloader for magnets and torrents")
    font.setPixelSize(22)
    font.setWeight(QFont.DemiBold)
    p.setFont(font)
    p.setPen(QColor(rd.COLORS["accent_hi"]))
    p.drawText(QRectF(80, 465, 560, 40), Qt.AlignLeft | Qt.AlignVCenter,
               "Windows  ·  Linux  ·  Free & open source")

    shot = QImage(os.path.join(ASSETS, "screenshot.png"))
    target = QRectF(640, 120, 760, 760 * shot.height() / shot.width())
    clip = QPainterPath()
    clip.addRoundedRect(target, 18, 18)
    p.setClipPath(clip)
    p.drawImage(target, shot)
    p.end()
    img.save(os.path.join(ASSETS, "social-preview.png"))


def copy_to_docs():
    os.makedirs(DOCS, exist_ok=True)
    for name in ("icon.png", "screenshot.png", "social-preview.png"):
        shutil.copy(os.path.join(ASSETS, name), os.path.join(DOCS, name))


def main():
    app = QApplication(sys.argv)
    rd.apply_theme(app)
    os.makedirs(ASSETS, exist_ok=True)
    make_icons()
    make_screenshot()
    make_social_preview()
    copy_to_docs()
    print("assets updated in", ASSETS, "and", DOCS)


if __name__ == "__main__":
    main()
