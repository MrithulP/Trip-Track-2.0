# TripTrack v3 — simpler front end + Python analysis

Same dark expedition app, same offline-first PWA. The front end is now three small files,
and Python does the analysis.

## Files

| File | What it is |
|---|---|
| `index.html` | Markup only — no styles, no scripts inside |
| `style.css` | All styling (colors live in the `:root` variables at the top) |
| `script.js` | All behavior: trip state, rendering, export, calls the Python server |
| `app.py` | Flask server: serves the files above + `/api/analyze` |
| `analysis.py` | numpy / scikit-learn / matplotlib analysis engine |
| `desktop_analysis.py` | Tkinter desktop analyzer (opens an exported trip) |
| `manifest.json`, `service-worker.js` | PWA files (offline support) |
| `sample_trip.json` | Example trip for the desktop analyzer |

To add or rename an expense category, edit the `CATS` list at the top of `script.js` —
the dropdown, filter tabs and colors all come from it. Currencies are the `CURRENCIES` list.

## Run it

    pip install -r requirements.txt
    python app.py            # then open http://127.0.0.1:5000

Add expenses as usual, then press **Analyze Trip** at the bottom of the page.
The app itself still works offline; only the Analysis section needs `python app.py` running.

## Desktop analyzer

1. In the web app press the **⬇** icon in the header (downloads `triptrack_export.json`).
2. `python desktop_analysis.py` → "Open trip file…" (try `sample_trip.json` first).

## When you edit index.html / style.css / script.js

The service worker caches these files so the app works offline. After editing, either bump
`CACHE_NAME` in `service-worker.js` (e.g. `triptrack-v7`) or hard-refresh (Ctrl+Shift+R),
otherwise the browser may keep showing the old version.
