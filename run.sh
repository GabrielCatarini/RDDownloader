#!/usr/bin/env bash
# RDDownloader - Linux/macOS launcher (run from source).
# On first run it creates an isolated .venv and installs the dependencies.
set -e
cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
    echo "Python 3 not found. Install it with your package manager"
    echo "(e.g. sudo apt install python3 python3-venv) or grab the prebuilt binary:"
    echo "  https://github.com/GabrielCatarini/RDDownloader/releases/latest"
    exit 1
fi

if [ ! -x .venv/bin/python ]; then
    echo "Setting up RDDownloader (first run only)..."
    if ! python3 -m venv .venv; then
        rm -rf .venv
        echo "The venv module is missing. On Ubuntu/Debian: sudo apt install python3-venv"
        exit 1
    fi
fi

if ! .venv/bin/python -c "import PyQt5, requests" >/dev/null 2>&1; then
    echo "Installing dependencies..."
    .venv/bin/python -m pip install --disable-pip-version-check -q -r requirements.txt
fi

exec .venv/bin/python rddownloader.py "$@"
