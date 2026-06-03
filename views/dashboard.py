import tkinter as tk
from tkinter import ttk
from datetime import datetime
from components.theme import *
from components.widgets import StatCard, FunnelBar, SectionHeader
from data.database import get_stats_sesion, get_sesion_activa, get_leads_recientes

INTERES_COLORS = {
    "alto":  (GREEN_LIGHT, GREEN),
    "medio": (AMBER_LIGHT, AMBER),
    "bajo":  (RED_LIGHT,   RED),
}


class DashboardView(tk.Frame):

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=GRAY_BG, **kwargs)
        self._stat_cards  = {}
        self._funnel_bars = {}
        self._build()
        self.refresh()

    def _build(self):
        # Header
        hdr = tk.Frame(self, bg=GRAY_BG, padx=PAD, pady=PAD_S)
        hdr.pack(fill="x")
        tk.Label(hdr, text="Dashboard", font=FONT_TITLE,
                 fg=TEXT_PRI, bg=GRAY_BG).pack(side="left")
        self._time_lbl = tk.Label(hdr, text="",
                                   font=FONT_SMALL, fg=TEXT_SEC, bg=GRAY_BG)
        self._time_lbl.pack(side="left", padx=(10, 0))
        tk.Button(hdr, text="↻  Actualizar", font=FONT_SMALL,
                  bg=WHITE, fg=TEXT_SEC, relief="flat", bd=0,
                  padx=10, pady=4, cursor="hand2",
                  highlightbackground=BORDER, highlightthickness=1,
                  command=self.refresh).pack(side="right")

        ttk.Separator(self, orient="horizontal").pack(fill="x")

        body = tk.Frame(self, bg=GRAY_BG, padx=PAD, pady=PAD)
        body.pack(fill="both", expand=True)

        # Stat cards
        cards_grid = tk.Frame(body, bg=GRAY_BG)
        cards_grid.pack(fill="x", pady=(0, PAD))
        metrics = [
            ("marcadas",             "Llamadas",       TEXT_PRI),
            ("alive",                "Activos",        GREEN),
            ("answered",             "Contestaron",    BLUE),
            ("retained",             "Retenidas",      TEAL),
            ("leads",                "Leads",          PRIMARY),
            ("lead_conversion_rate", "Conversión lead", PRIMARY),
        ]
        for i, (key, label, color) in enumerate(metrics):
            card = StatCard(cards_grid, label, "0", color=color, bg=WHITE)
            card.grid(row=0, column=i, sticky="ew",
                      padx=(0, 8), pady=(0, 8), ipadx=4)
            cards_grid.grid_columnconfigure(i, weight=1)
            self._stat_cards[key] = card

        # Two columns
        cols = tk.Frame(body, bg=GRAY_BG)
        cols.pack(fill="both", expand=True)

        # Funnel
        left = tk.Frame(cols, bg=WHITE, padx=PAD, pady=PAD,
                        highlightbackground=BORDER, highlightthickness=1)
        left.pack(side="left", fill="both", expand=True, padx=(0, PAD_S))

        SectionHeader(left, "Embudo de llamadas", bg=WHITE).pack(
            fill="x", pady=(0, PAD_S))
        funnel_defs = [
            ("marcadas", "Llamadas",    GRAY_MID),
            ("alive",    "Activos",     GREEN_MID),
            ("answered", "Contestaron", BLUE_MID),
            ("retained", "Retenidas",   TEAL_MID),
            ("leads",    "Leads",       PRIMARY),
        ]
        for key, label, color in funnel_defs:
            bar = FunnelBar(left, label, 0, 1, color=color, bg=WHITE)
            bar.pack(fill="x", pady=(0, 12))
            self._funnel_bars[key] = bar

        # Recent leads
        right = tk.Frame(cols, bg=WHITE, padx=PAD, pady=PAD,
                         highlightbackground=BORDER, highlightthickness=1)
        right.pack(side="left", fill="both", expand=True)

        SectionHeader(right, "Últimos leads", bg=WHITE).pack(
            fill="x", pady=(0, PAD_S))
        self._leads_frame = tk.Frame(right, bg=WHITE)
        self._leads_frame.pack(fill="both", expand=True)

    def refresh(self):
        sid = get_sesion_activa()
        stats = get_stats_sesion(sid)

        self._time_lbl.config(
            text=f"Sesión · {datetime.now().strftime('%H:%M')}")

        for key in ("marcadas", "alive", "answered", "retained", "leads"):
            self._stat_cards[key].update_value(stats[key])
        self._stat_cards["lead_conversion_rate"].update_value(
            f"{stats['lead_conversion_rate']}%"
        )

        total = max(stats["marcadas"], 1)
        for key in ("marcadas", "alive", "answered", "retained", "leads"):
            self._funnel_bars[key].update(stats[key], total)

        for w in self._leads_frame.winfo_children():
            w.destroy()

        leads = get_leads_recientes(6)
        if not leads:
            tk.Label(self._leads_frame, text="Sin leads en esta sesión",
                     font=FONT_SMALL, fg=TEXT_SEC, bg=WHITE).pack(pady=PAD)
        else:
            for lead in leads:
                self._build_lead_row(lead)

    def _build_lead_row(self, lead):
        row = tk.Frame(self._leads_frame, bg=WHITE, pady=6,
                       highlightbackground=BORDER, highlightthickness=1)
        row.pack(fill="x", pady=(0, 4), padx=2)

        interes = lead.get("interes", "medio")
        badge_bg, badge_fg = INTERES_COLORS.get(interes, (GRAY_BG, TEXT_SEC))
        tk.Label(row, text=f" {interes} ", font=FONT_SMALL,
                 bg=badge_bg, fg=badge_fg).pack(side="right", padx=6)

        if lead.get("perfilado"):
            tk.Label(row, text="✓ perfilado", font=FONT_SMALL,
                     bg=PRIMARY_LIGHT, fg=PRIMARY).pack(side="right", padx=2)

        info = tk.Frame(row, bg=WHITE)
        info.pack(side="left", fill="x", padx=8)
        nombre = lead.get("nombre") or lead.get("numero") or "—"
        hora = (lead.get("hora") or "")[:5]
        tk.Label(info, text=nombre, font=("Segoe UI", 10, "bold"),
                 fg=TEXT_PRI, bg=WHITE).pack(anchor="w")
        tk.Label(info, text=hora, font=FONT_SMALL,
                 fg=TEXT_SEC, bg=WHITE).pack(anchor="w")
