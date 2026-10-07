# Contribuindo / Contributing

Obrigado por ajudar o RDDownloader! 🎉
Thanks for helping RDDownloader! 🎉

## 🌍 Adicionar/melhorar uma tradução (a forma mais fácil de contribuir)

Adding/improving a translation is the easiest way to contribute.

1. Abra [`translations.py`](translations.py).
2. Copie o bloco inteiro do idioma `"en"` (do `{` ao `}`).
3. Cole como um novo idioma usando o código [ISO 639-1](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes),
   por exemplo `"fr"` para francês:
   ```python
   "fr": {
       "app_title": "RDDownloader — Real-Debrid",
       "group_config": "Paramètres",
       ...
   },
   ```
4. Traduza **apenas os valores** (lado direito). **Não** altere as chaves nem o
   texto entre `{}` — são variáveis (ex.: `{pct}`, `{name}`, `{size}`).
5. Adicione o nome do idioma em `LANGUAGE_NAMES`:
   ```python
   LANGUAGE_NAMES = {
       "pt": "Português",
       "en": "English",
       "es": "Español",
       "fr": "Français",
   }
   ```
6. Rode o programa — o idioma aparece sozinho no seletor. Abra um Pull Request!

> Translate only the **values** (right side). Do **not** change the keys or the
> text inside `{}` — those are runtime variables.

## 🐛 Reportar bugs / Report bugs

Abra uma *issue* descrevendo o que aconteceu, o que esperava, e (se possível) a
mensagem de erro do terminal.

## 💡 Ideias de funcionalidades / Feature ideas

Abra uma issue com a etiqueta `enhancement`. Sugestões bem-vindas!

## 🧑‍💻 Estilo de código / Code style

- Mantenha o código simples e legível (segue o estilo do arquivo).
- Strings visíveis ao usuário **sempre** passam por `tr("chave")` — nada de
  texto fixo na interface.
- Rode os testes antes do PR:
  `QT_QPA_PLATFORM=offscreen python3 -m unittest discover -s tests -t .`
- Mudou o visual? Regere o ícone e a screenshot com
  `python3 tools/make_assets.py` (usa só dados de demonstração).
