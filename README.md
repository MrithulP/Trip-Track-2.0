# TripTrack v2 — web UI + Python analysis

Same offline-first PWA you built (index.html, localStorage, dark expedition theme),
plus a Python layer for analysis.

## Setup
    pip install -r requirements.txt
    python app.py            # open http://127.0.0.1:5000

Add expenses as usual, then press **Analyze Trip** at the bottom of the page.

## What Python does
| File | Libraries | Role |
|---|---|---|
| analysis.py | numpy, scikit-learn, matplotlib | stats, LinearRegression spend forecast, IsolationForest unusual-expense detection, dark-themed charts |
| app.py | Flask | serves the app + `/api/analyze` |
| desktop_analysis.py | tkinter, matplotlib | native window: open an exported trip and view the same analysis |

## Desktop analyzer
1. In the web app press the **⬇** icon in the header (downloads `triptrack_export.json`).
2. `python desktop_analysis.py` -> "Open trip file…". Try `sample_trip.json` first.

Tkinter ships with the standard Python installer on Windows/macOS.
The web app still works offline without Python; only the Analysis section needs the server.
