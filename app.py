"""
app.py — tiny Flask server for TripTrack.

It serves the same index.html / manifest / service worker as before
(the app still works offline from localStorage) and adds ONE endpoint,
/api/analyze, which runs the Python analysis engine on the trip data
the browser sends and returns stats + matplotlib charts as base64 PNGs.

Run:  python app.py   ->  http://127.0.0.1:5000
"""

import base64
import io

from flask import Flask, jsonify, request, send_from_directory
import matplotlib.pyplot as plt

import analysis

app = Flask(__name__, static_folder=None)


def fig_to_base64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)  # free memory — important on a long-running server
    return base64.b64encode(buf.getvalue()).decode("ascii")


@app.route("/")
def index():
    return send_from_directory(".", "index.html")


STATIC_FILES = {"index.html", "style.css", "script.js", "service-worker.js", "manifest.json"}


@app.route("/<path:filename>")
def assets(filename):
    if filename in STATIC_FILES or filename.endswith((".png", ".ico")):
        return send_from_directory(".", filename)
    return ("Not found", 404)


@app.route("/api/analyze", methods=["POST"])
def analyze():
    state = request.get_json(silent=True)
    if not isinstance(state, dict) or not isinstance(state.get("expenses"), list):
        return jsonify({"error": "Invalid trip data."}), 400

    # Light sanitising: keep only well-formed expenses.
    clean = []
    for e in state["expenses"]:
        try:
            clean.append({
                "name": str(e.get("name", "")), "amount": float(e["amount"]),
                "cat": str(e.get("cat", "Other")), "day": int(e.get("day", 1) or 1),
            })
        except (KeyError, TypeError, ValueError):
            continue
    state["expenses"] = clean

    result = analysis.analyze(state)
    return jsonify({
        "stats": result["stats"],
        "forecast": {k: v for k, v in result["forecast"].items() if k != "trend_line"},
        "anomalies": result["anomalies"],
        "insights": result["insights"],
        "charts": {
            "category": fig_to_base64(result["category_fig"]),
            "trend": fig_to_base64(result["trend_fig"]),
        },
    })


if __name__ == "__main__":
    app.run(debug=True)
