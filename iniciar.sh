#!/usr/bin/env bash
# RDDownloader - lancador para Linux/macOS (rodar a partir do codigo-fonte).
# Na primeira vez cria um ambiente isolado em .venv e instala as dependencias.
set -e
cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
    echo "Python 3 nao encontrado. Instale-o pelo gerenciador de pacotes"
    echo "(ex.: sudo apt install python3 python3-venv) ou use o binario pronto:"
    echo "  https://github.com/GabrielCatarini/RDDownloader/releases/latest"
    exit 1
fi

if [ ! -x .venv/bin/python ]; then
    echo "Preparando o RDDownloader (somente na primeira vez)..."
    if ! python3 -m venv .venv; then
        rm -rf .venv
        echo "Falta o modulo venv. No Ubuntu/Debian: sudo apt install python3-venv"
        exit 1
    fi
fi

if ! .venv/bin/python -c "import PyQt5, requests" >/dev/null 2>&1; then
    echo "Instalando dependencias..."
    .venv/bin/python -m pip install --disable-pip-version-check -q -r requirements.txt
fi

exec .venv/bin/python rddownloader.py "$@"
