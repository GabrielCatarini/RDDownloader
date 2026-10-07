#!/usr/bin/env python3
"""
Regenerate assets/icon.png, assets/icon.ico and assets/screenshot.png.

    QT_QPA_PLATFORM=offscreen python3 tools/make_assets.py

The screenshot uses demo data only: no real account, key or folder.
"""
import os
import sys
from unittest.mock import patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication  # noqa: E402

import rddownloader as rd  # noqa: E402

ASSETS = os.path.join(ROOT, "assets")

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


def make_screenshot(lang="pt"):
    cfg = {"api_key": "demo", "download_folder": "~/Downloads/RealDebrid",
           "language": lang, "max_concurrent": 3}
    with patch.object(rd, "load_config", return_value=cfg), \
            patch.object(rd, "save_config"), \
            patch.object(rd.MainWindow, "AUTO_VERIFY", False):
        win = rd.MainWindow()
        win.resize(1240, 720)
        win._last_user = {"username": "usuario", "type": "premium",
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


def main():
    app = QApplication(sys.argv)
    rd.apply_theme(app)
    os.makedirs(ASSETS, exist_ok=True)
    make_icons()
    make_screenshot()
    print("assets updated in", ASSETS)


if __name__ == "__main__":
    main()
