<p align="center">
  <img src="assets/icon.png" alt="RDDownloader logo" width="88">
</p>

<h1 align="center">RDDownloader</h1>

<p align="center">
  <b>A fast, free Real-Debrid desktop client.</b><br>
  Paste a magnet link or drop a .torrent file and get the files on your PC, no browser needed.
</p>

<p align="center">
  <a href="https://github.com/GabrielCatarini/RDDownloader/releases/latest"><img alt="Latest release" src="https://img.shields.io/github/v/release/GabrielCatarini/RDDownloader?color=7c6cff"></a>
  <a href="https://github.com/GabrielCatarini/RDDownloader/releases"><img alt="Downloads" src="https://img.shields.io/github/downloads/GabrielCatarini/RDDownloader/total?color=34d399"></a>
  <img alt="Platforms" src="https://img.shields.io/badge/platform-Windows%20%7C%20Linux-informational">
  <a href="LICENSE"><img alt="MIT License" src="https://img.shields.io/github/license/GabrielCatarini/RDDownloader"></a>
</p>

<p align="center">
  <img src="assets/screenshot.png" alt="RDDownloader: Real-Debrid downloader window showing magnet and torrent downloads with progress, speed and ETA" width="860">
</p>

## Download

| Platform | File |
|---|---|
| **Windows 10/11** | [RDDownloader-windows.exe](https://github.com/GabrielCatarini/RDDownloader/releases/latest/download/RDDownloader-windows.exe) |
| **Linux** (x86_64) | [RDDownloader-linux](https://github.com/GabrielCatarini/RDDownloader/releases/latest/download/RDDownloader-linux) |

These are single portable files, so you don't need to install Python or anything else. On Linux, make the file executable first (`chmod +x RDDownloader-linux`).

> Windows SmartScreen may warn about a new, unsigned app. Click **More info → Run anyway**. The executables are built by [GitHub Actions](.github/workflows/build.yml) from this repository.

## Quick start

1. Copy your API key from [real-debrid.com/apitoken](https://real-debrid.com/apitoken).
2. Paste it into RDDownloader and click **Save & verify**.
3. Paste a magnet link (or drop a `.torrent` file) and click **Download**.

## Features

- Magnet links and `.torrent` files, with drag & drop
- Real-time speed, ETA and progress per download
- Pause and resume, with downloads continuing from the last byte received
- Automatic retry when the network drops
- Parallel downloads
- Shows your account status and premium expiry date
- Desktop notifications
- English, Português and Español

## Run from source

```bash
git clone https://github.com/GabrielCatarini/RDDownloader.git
cd RDDownloader
./run.sh          # Windows: double-click run.bat
```

The launcher creates a local `.venv` and installs the dependencies (Python 3.8+, PyQt5, requests). On Windows it also installs Python through `winget` if Python is missing.

## Privacy

Your API key is stored only on your computer (`~/.config/rddownloader/config.json`), and only your user account can read it. The app talks only to the official Real-Debrid API and has no telemetry.

## Contributing

Bug reports, translations and pull requests are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE). RDDownloader is not affiliated with Real-Debrid. Only download content you have the right to access.
