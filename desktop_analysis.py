"""
desktop_analysis.py — TripTrack Desktop Analyzer (Tkinter).

Open a trip exported from the web app (the ⬇ button -> triptrack_export.json)
and explore it in a native window: statistics, forecast, flagged expenses,
and the same matplotlib charts the browser shows — computed by the very
same analysis.py engine.

Run:  python desktop_analysis.py
"""

import json
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

import analysis

BG, SURFACE, TEXT, MUTED, ACCENT = "#0a0a0f", "#13131a", "#f0f0f8", "#7878a0", "#7c6af7"


class TripAnalyzer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("TripTrack — Desktop Analyzer")
        self.geometry("1100x700")
        self.configure(bg=BG)
        self.state_data = None
        self.canvases = []
        self._build_ui()

    # ------------------------------------------------------------ layout --
    def _build_ui(self):
        top = tk.Frame(self, bg=SURFACE, padx=16, pady=12)
        top.pack(fill="x")
        self.title_lbl = tk.Label(top, text="TripTrack ✈  Desktop Analyzer", bg=SURFACE, fg=TEXT,
                                  font=("Segoe UI", 14, "bold"))
        self.title_lbl.pack(side="left")
        tk.Button(top, text="Open trip file…", command=self.open_file, bg=ACCENT, fg="white",
                  relief="flat", padx=14, pady=6, cursor="hand2").pack(side="right")

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        # left: stats + insights + expense table
        left = tk.Frame(body, bg=BG, width=380)
        left.pack(side="left", fill="y", padx=(0, 12))
        left.pack_propagate(False)

        self.stats_lbl = tk.Label(left, text="Open an exported trip to begin.", bg=SURFACE, fg=TEXT,
                                  justify="left", anchor="nw", padx=12, pady=10, font=("Consolas", 10))
        self.stats_lbl.pack(fill="x")

        self.insight_lbl = tk.Label(left, text="", bg=SURFACE, fg=TEXT, justify="left", anchor="nw",
                                    wraplength=350, padx=12, pady=10, font=("Segoe UI", 10))
        self.insight_lbl.pack(fill="x", pady=(10, 0))

        cols = ("day", "name", "cat", "amount")
        self.table = ttk.Treeview(left, columns=cols, show="headings", height=10)
        for c, w in zip(cols, (40, 150, 90, 80)):
            self.table.heading(c, text=c.title())
            self.table.column(c, width=w, anchor="w")
        self.table.pack(fill="both", expand=True, pady=(10, 0))

        # right: charts
        self.chart_frame = tk.Frame(body, bg=BG)
        self.chart_frame.pack(side="left", fill="both", expand=True)

    # ------------------------------------------------------------ actions --
    def open_file(self):
        path = filedialog.askopenfilename(title="Open TripTrack export",
                                          filetypes=[("TripTrack JSON", "*.json"), ("All files", "*.*")])
        if not path:
            return
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data.get("expenses"), list):
                raise ValueError("No 'expenses' list found.")
        except (OSError, ValueError) as err:
            messagebox.showerror("Couldn't open file", f"That doesn't look like a TripTrack export.\n\n{err}")
            return
        self.state_data = data
        self.refresh()

    def refresh(self):
        data = self.state_data
        result = analysis.analyze(data)
        sym = data.get("currency", {}).get("sym", "")
        s, f = result["stats"], result["forecast"]

        self.title_lbl.config(text=f"TripTrack ✈  {data.get('tripName') or 'Untitled trip'}")
        proj = f"{sym}{f['projected_total']:,.0f}" if f["has_forecast"] else "n/a (need 2+ days of data)"
        self.stats_lbl.config(text=(
            f"Budget        {sym}{data.get('budget', 0):,.0f}\n"
            f"Spent         {sym}{s['total_spent']:,.0f}\n"
            f"Remaining     {sym}{s['remaining']:,.0f}\n"
            f"Avg expense   {sym}{s['mean']:,.0f}\n"
            f"Median        {sym}{s['median']:,.0f}\n"
            f"Std dev       {sym}{s['std']:,.0f}\n"
            f"Projected     {proj}"))
        self.insight_lbl.config(text="\n\n".join("• " + t for t in result["insights"]))

        self.table.delete(*self.table.get_children())
        for e in sorted(data["expenses"], key=lambda e: (e.get("day", 1), e["name"])):
            self.table.insert("", "end", values=(e.get("day", 1), e["name"], e["cat"], f"{sym}{e['amount']:,.0f}"))

        for w in self.chart_frame.winfo_children():
            w.destroy()
        for fig in (result["trend_fig"], result["category_fig"]):
            canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True, pady=(0, 8))

    def on_close(self):
        plt.close("all")
        self.destroy()


if __name__ == "__main__":
    app = TripAnalyzer()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()
