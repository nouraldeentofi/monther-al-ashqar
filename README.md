# Monther Al-Ashqar — website

Bilingual (English / Arabic) portfolio for Monther Al-Ashqar, Senior Project Manager and Owner's Representative.

- English pages at the root, Arabic under `/ar/`, one page per project.
- `llms.txt`, `llms-full.txt`, `robots.txt` and `sitemap.xml` for search engines and AI assistants.
- `source/monther-portfolio.html` is the editable source; `source/build.py` rebuilds every page:

```
pip install playwright && python3 -m playwright install chromium
cd source && python3 build.py   # writes ./site — copy its contents to the repo root
```

Set `SITE_URL` in `build.py` when the site moves to its own domain.
