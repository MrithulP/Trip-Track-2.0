"""
analysis.py — TripTrack's Python analysis engine.

This module knows nothing about Flask or Tkinter. It takes the same
`state` dict the web app keeps in localStorage ({budget, expenses,
tripName, currency, days, ...}) and turns it into:

  - descriptive statistics (numpy)
  - a trip-end spend forecast (scikit-learn LinearRegression)
  - flagged unusual expenses (scikit-learn IsolationForest)
  - two matplotlib Figures (category breakdown, spend trend + forecast)

Both app.py (web, renders figures to PNG) and desktop_analysis.py
(Tkinter, embeds figures directly) import this file so the numbers
shown in the browser and in the desktop tool are always identical.
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")  # safe for both a web server and headless embedding
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import IsolationForest

CAT_COLORS = {
    "Food": "#f7c444", "Travel": "#7c6af7", "Stay": "#38d1d1",
    "Activities": "#2dd4a0", "Shopping": "#e96bbf", "Medical": "#f25f5f",
    "Fuel": "#f07a4a", "Other": "#7878a0",
}

# Dark theme to match the web app's CSS variables.
BG = "#13131a"
GRID = "#2a2a38"
TEXT = "#f0f0f8"
MUTED = "#7878a0"
ACCENT = "#7c6af7"
TEAL = "#38d1d1"
AMBER = "#f7c444"
RED = "#f25f5f"
GREEN = "#2dd4a0"


def _style_axes(fig, ax):
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.tick_params(colors=MUTED, labelsize=9)
    for spine in ax.spines.values():
        spine.set_color(GRID)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(True, color=GRID, linewidth=0.6, alpha=0.6)
    ax.set_axisbelow(True)


# ---------------------------------------------------------- statistics --

def compute_stats(state):
    """numpy-based descriptive statistics over expense amounts."""
    expenses = state.get("expenses", [])
    if not expenses:
        return {
            "num_expenses": 0, "total_spent": 0.0, "mean": 0.0, "median": 0.0,
            "std": 0.0, "min": 0.0, "max": 0.0, "remaining": state.get("budget", 0),
        }

    amounts = np.array([e["amount"] for e in expenses], dtype=float)
    budget = float(state.get("budget", 0))
    total = float(amounts.sum())

    return {
        "num_expenses": int(amounts.size),
        "total_spent": total,
        "mean": float(np.mean(amounts)),
        "median": float(np.median(amounts)),
        "std": float(np.std(amounts)),
        "min": float(np.min(amounts)),
        "max": float(np.max(amounts)),
        "remaining": budget - total,
    }


def _daily_totals(state):
    """Returns (day_numbers, per_day_amounts) for every day 1..trip_days."""
    days = max(int(state.get("days", 1)), 1)
    totals = np.zeros(days)
    for e in state.get("expenses", []):
        d = int(e.get("day", 1))
        if 1 <= d <= days:
            totals[d - 1] += float(e["amount"])
    return np.arange(1, days + 1), totals


# ----------------------------------------------------------- forecast ---

def compute_forecast(state):
    """
    Fits scikit-learn LinearRegression on (day, cumulative spend) for the
    days that have passed so far, then extrapolates to the trip's final
    day to estimate the total spend by the end of the trip.
    """
    days_axis, daily = _daily_totals(state)
    cumulative = np.cumsum(daily)
    days_with_spend = np.where(daily > 0)[0]

    if days_with_spend.size < 2:
        # Not enough data points for a meaningful trend line yet.
        return {
            "has_forecast": False, "projected_total": None,
            "daily_burn_rate": None, "over_budget": False,
        }

    last_active_day = days_with_spend.max() + 1  # 1-indexed
    X = days_axis[:last_active_day].reshape(-1, 1)
    y = cumulative[:last_active_day]

    model = LinearRegression()
    model.fit(X, y)

    total_days = days_axis[-1]
    projected_total = float(model.predict([[total_days]])[0])
    projected_total = max(projected_total, float(cumulative[-1]) if cumulative.size else 0.0)
    daily_burn_rate = float(model.coef_[0])
    budget = float(state.get("budget", 0))

    return {
        "has_forecast": True,
        "projected_total": projected_total,
        "daily_burn_rate": daily_burn_rate,
        "over_budget": bool(budget > 0 and projected_total > budget),
        "trend_line": model.predict(days_axis.reshape(-1, 1)).tolist(),
    }


# ----------------------------------------------------------- anomalies --

def detect_anomalies(state):
    """
    Flags unusually large expenses using scikit-learn's IsolationForest.
    Needs at least 5 expenses to have any statistical meaning; with so
    few points we deliberately keep contamination low so it only flags
    genuine standouts, not routine variation.
    """
    expenses = state.get("expenses", [])
    if len(expenses) < 5:
        return []

    amounts = np.array([[e["amount"]] for e in expenses], dtype=float)
    model = IsolationForest(contamination=0.15, random_state=42)
    labels = model.fit_predict(amounts)  # -1 = outlier, 1 = normal

    flagged = [
        {"name": e["name"], "amount": e["amount"], "day": e.get("day", 1), "cat": e.get("cat", "Other")}
        for e, label in zip(expenses, labels) if label == -1
    ]
    # Only surface the genuinely large ones (not unusually *small* expenses).
    if flagged:
        median_amt = float(np.median(amounts))
        flagged = [f for f in flagged if f["amount"] > median_amt]
    return sorted(flagged, key=lambda f: -f["amount"])[:5]


# -------------------------------------------------------------- charts --

def build_category_chart(state):
    """Donut chart of spend by category, colored to match the app's palette."""
    expenses = state.get("expenses", [])
    fig, ax = plt.subplots(figsize=(4.4, 4.4), dpi=130)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)

    if not expenses:
        ax.text(0.5, 0.5, "No expenses yet", color=MUTED, ha="center", va="center", fontsize=11)
        ax.axis("off")
        return fig

    totals = {}
    for e in expenses:
        totals[e["cat"]] = totals.get(e["cat"], 0) + e["amount"]
    labels = list(totals.keys())
    values = list(totals.values())
    colors = [CAT_COLORS.get(c, MUTED) for c in labels]

    wedges, _ = ax.pie(
        values, colors=colors, startangle=90, wedgeprops={"width": 0.42, "edgecolor": BG, "linewidth": 2},
    )
    ax.legend(
        wedges, [f"{l}  {v:,.0f}" for l, v in zip(labels, values)],
        loc="center left", bbox_to_anchor=(1.0, 0.5), frameon=False,
        labelcolor=TEXT, fontsize=9,
    )
    total = sum(values)
    ax.text(0, 0, f"{total:,.0f}", color=TEXT, ha="center", va="center", fontsize=16, fontweight="bold")
    fig.tight_layout()
    return fig


def build_trend_chart(state, forecast):
    """Cumulative spend vs. day, with budget line and a forecast trend."""
    days_axis, daily = _daily_totals(state)
    cumulative = np.cumsum(daily)
    budget = float(state.get("budget", 0))

    fig, ax = plt.subplots(figsize=(7.2, 4.0), dpi=130)
    _style_axes(fig, ax)

    ax.plot(days_axis, cumulative, color=ACCENT, linewidth=2.2, marker="o", markersize=4, label="Actual spend")
    ax.fill_between(days_axis, cumulative, color=ACCENT, alpha=0.08)

    if budget > 0:
        ax.axhline(budget, color=TEAL, linestyle="--", linewidth=1.4, label="Budget")

    if forecast.get("has_forecast"):
        trend = np.array(forecast["trend_line"])
        line_color = RED if forecast["over_budget"] else GREEN
        ax.plot(days_axis, trend, color=line_color, linestyle=":", linewidth=2, label="Forecast trend")

    ax.set_xlabel("Day", color=MUTED, fontsize=10)
    ax.set_ylabel("Cumulative spend", color=MUTED, fontsize=10)
    ax.legend(frameon=False, labelcolor=TEXT, fontsize=9, loc="upper left")
    fig.tight_layout()
    return fig


# ------------------------------------------------------------ insights --

def build_insights(state, stats, forecast, anomalies):
    """Plain-English, rule-based takeaways — same tone as the rest of the app."""
    insights = []
    budget = float(state.get("budget", 0))

    if stats["num_expenses"] == 0:
        return ["Log a few expenses to unlock analysis."]

    if budget > 0:
        pct = stats["total_spent"] / budget * 100
        insights.append(f"You've used {pct:.0f}% of your budget so far.")

    if forecast.get("has_forecast"):
        proj = forecast["projected_total"]
        if forecast["over_budget"]:
            insights.append(
                f"At your current burn rate, you're projected to spend {proj:,.0f} by the end of the "
                f"trip — over budget by {proj - budget:,.0f}."
            )
        else:
            insights.append(f"At your current burn rate, you're on track to finish around {proj:,.0f}.")

    if stats["std"] > 0 and stats["mean"] > 0:
        insights.append(
            f"Your typical expense is {stats['median']:,.0f}, "
            f"but they range from {stats['min']:,.0f} to {stats['max']:,.0f}."
        )

    for a in anomalies[:3]:
        insights.append(f"Unusually large expense flagged: \"{a['name']}\" ({a['amount']:,.0f}) on day {a['day']}.")

    return insights


# ------------------------------------------------------------- bundle ---

def analyze(state):
    """Run the full pipeline and return every figure/number the UI needs."""
    stats = compute_stats(state)
    forecast = compute_forecast(state)
    anomalies = detect_anomalies(state)
    insights = build_insights(state, stats, forecast, anomalies)
    category_fig = build_category_chart(state)
    trend_fig = build_trend_chart(state, forecast)
    return {
        "stats": stats, "forecast": forecast, "anomalies": anomalies,
        "insights": insights, "category_fig": category_fig, "trend_fig": trend_fig,
    }
