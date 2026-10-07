# Contributing

Thanks for helping improve RDDownloader!

## Development setup

```bash
./run.sh                     # creates .venv, installs deps, starts the app
QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest discover -s tests -t .
```

- Keep the code simple and in the style of the surrounding file.
- Every user-visible string goes through `tr("key")`, so there is no hard-coded UI text.
- If you change the UI, regenerate the icon, screenshot and social preview with
  `python3 tools/make_assets.py`. It uses demo data only.

## Adding a translation

1. Open [`translations.py`](translations.py) and copy the whole `"en"` block.
2. Paste it under a new [ISO 639-1](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes) code, e.g. `"fr"`.
3. Translate **only the values**. Don't change the keys or anything inside `{}`, because those are runtime variables (`{pct}`, `{name}`, …).
4. Add the language name to `LANGUAGE_NAMES` (e.g. `"fr": "Français"`).

The new language then shows up automatically in the selector.

## Releasing

Bump `APP_VERSION` in `rddownloader.py`, then push a tag:

```bash
git tag v1.2.0 && git push origin v1.2.0
```

GitHub Actions runs the tests, builds the Windows and Linux executables and publishes the release.

## Bugs and ideas

Open an [issue](https://github.com/GabrielCatarini/RDDownloader/issues). For bugs, include what happened, what you expected and any error message.
