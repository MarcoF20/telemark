import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from components.theme import *
from components.widgets import SectionHeader, bind_canvas_mousewheel
from data.database import get_leads_con_seguimiento, get_lead_by_id


class SeguimientoView(tk.Frame):
    """Shows all leads with scheduled follow-up calls, sorted by date."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=WHITE, **kwargs)
        self._build()
        self.refresh()

    def _build(self):
        hdr = tk.Frame(self, bg=PRIMARY, padx=PAD, pady=PAD_S)
        hdr.pack(fill="x")
        tk.Label(hdr, text="📅  Seguimientos agendados",
                 font=FONT_TITLE, fg=WHITE, bg=PRIMARY).pack(side="left")
        tk.Button(hdr, text="↻  Actualizar", font=FONT_SMALL,
                  bg=PRIMARY_DARK, fg=WHITE, relief="flat", bd=0,
                  padx=10, pady=4, cursor="hand2",
                  command=self.refresh).pack(side="right")

        ttk.Separator(self, orient="horizontal").pack(fill="x")

        # Scrollable list
        outer = tk.Frame(self, bg=GRAY_BG)
        outer.pack(fill="both", expand=True)
        canvas = tk.Canvas(outer, bg=GRAY_BG, highlightthickness=0)
        vsb = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        self._body = tk.Frame(canvas, bg=GRAY_BG, padx=PAD, pady=PAD)
        win = canvas.create_window((0, 0), window=self._body, anchor="nw")

        def _resize(e):
            canvas.itemconfig(win, width=e.width)
        canvas.bind("<Configure>", _resize)
        self._body.bind("<Configure>",
                        lambda e: canvas.configure(
                            scrollregion=canvas.bbox("all")))
        bind_canvas_mousewheel(canvas)
        canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self._count_lbl = tk.Label(self, text="",
                                    font=FONT_SMALL, fg=TEXT_SEC, bg=WHITE,
                                    padx=PAD, pady=4, anchor="w")
        self._count_lbl.pack(fill="x")

    def refresh(self):
        for w in self._body.winfo_children():
            w.destroy()

        leads = get_leads_con_seguimiento()
        today = datetime.now().strftime("%Y-%m-%d")
        now_time = datetime.now().strftime("%H:%M")

        if not leads:
            tk.Label(self._body, text="No hay seguimientos agendados.",
                     font=FONT_BODY, fg=TEXT_SEC, bg=GRAY_BG).pack(pady=PAD*2)
            self._count_lbl.config(text="0 seguimientos")
            return

        # Group by date
        grupos: dict[str, list] = {}
        for lead in leads:
            d = lead.get("fecha_seguimiento") or "Sin fecha"
            grupos.setdefault(d, []).append(lead)

        for fecha, grupo in grupos.items():
            # Date header
            if fecha == today:
                label_text = f"Hoy — {fecha}"
                label_bg, label_fg = PRIMARY_LIGHT, PRIMARY
            elif fecha < today:
                label_text = f"Vencido — {fecha}"
                label_bg, label_fg = RED_LIGHT, RED
            else:
                label_text = fecha
                label_bg, label_fg = BLUE_LIGHT, BLUE

            date_hdr = tk.Frame(self._body, bg=GRAY_BG)
            date_hdr.pack(fill="x", pady=(PAD_S, PAD_XS))
            tk.Label(date_hdr, text=f"  {label_text}  ",
                     font=("Segoe UI", 9, "bold"),
                     bg=label_bg, fg=label_fg,
                     padx=8, pady=4).pack(side="left")
            tk.Frame(date_hdr, bg=BORDER, height=1).pack(
                side="left", fill="x", expand=True, padx=(8, 0), pady=6)

            for lead in grupo:
                self._build_card(lead, today, now_time)

        self._count_lbl.config(text=f"{len(leads)} seguimientos agendados")

    def _build_card(self, lead, today, now_time):
        fecha = lead.get("fecha_seguimiento") or ""
        hora  = lead.get("hora_seguimiento") or ""
        is_past = (fecha < today) or (fecha == today and hora and hora < now_time)

        card = tk.Frame(self._body, bg=WHITE, padx=PAD, pady=PAD_S,
                        highlightbackground=RED_MID if is_past else BORDER,
                        highlightthickness=1 if is_past else 1)
        card.pack(fill="x", pady=(0, PAD_S))

        # Left info
        left = tk.Frame(card, bg=WHITE)
        left.pack(side="left", fill="x", expand=True)

        nombre = lead.get("nombre") or lead.get("numero") or "—"
        tk.Label(left, text=nombre, font=("Segoe UI", 11, "bold"),
                 fg=TEXT_PRI, bg=WHITE).pack(anchor="w")

        tel = lead.get("numero") or ""
        hora_str = hora[:5] if hora else "—"
        tk.Label(left, text=f"📞 {tel}  ·  ⏰ {hora_str}",
                 font=FONT_SMALL, fg=TEXT_SEC, bg=WHITE).pack(anchor="w")

        notas = (lead.get("seguimiento_notas") or "").strip()
        if notas:
            tk.Label(left, text=notas, font=FONT_SMALL,
                     fg=TEXT_HINT, bg=WHITE, wraplength=400,
                     justify="left").pack(anchor="w")

        # Right: badges + edit
        right = tk.Frame(card, bg=WHITE)
        right.pack(side="right", fill="y")

        interes = lead.get("interes", "medio")
        ibg = {
            "alto": (GREEN_LIGHT, GREEN),
            "medio": (AMBER_LIGHT, AMBER),
            "bajo": (RED_LIGHT, RED),
        }.get(interes, (GRAY_BG, TEXT_SEC))
        tk.Label(right, text=f" {interes} ", font=FONT_SMALL,
                 bg=ibg[0], fg=ibg[1]).pack(anchor="e", pady=(0, 4))

        if lead.get("perfilado"):
            tk.Label(right, text=" ✓ perfilado ", font=FONT_SMALL,
                     bg=PRIMARY_LIGHT, fg=PRIMARY).pack(anchor="e", pady=(0, 4))

        if is_past:
            tk.Label(right, text=" ⚠ vencido ", font=FONT_SMALL,
                     bg=RED_LIGHT, fg=RED).pack(anchor="e", pady=(0, 4))

        tk.Button(right, text="Abrir lead", font=FONT_SMALL,
                  bg=BLUE_LIGHT, fg=BLUE, relief="flat", bd=0,
                  padx=8, pady=3, cursor="hand2",
                  command=lambda lid=lead["id"]: self._open_lead(lid)
                  ).pack(anchor="e")

    def _open_lead(self, lead_id: int):
        if not get_lead_by_id(lead_id):
            messagebox.showinfo(
                "Lead no disponible",
                "Ese lead ya no existe. La lista se va a actualizar."
            )
            self.refresh()
            return
        from views.perfilacion import PerfilacionDialog
        PerfilacionDialog(self, lead_id=lead_id, on_saved=self.refresh)
