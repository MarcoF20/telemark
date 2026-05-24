import tkinter as tk
from tkinter import ttk, messagebox
from components.theme import *
from components.widgets import (
    RadioGroup, SectionHeader, StepIndicator,
    LabeledEntry, NumberDisplay
)
from views.perfilacion import PerfilacionDialog
from data.database import (
    guardar_llamada, guardar_lead,
    get_config, set_config,
    iniciar_sesion, get_sesion_activa, cerrar_sesion,
    get_stats_sesion,
)


class MarcadorView(tk.Frame):

    def __init__(self, parent, on_llamada_saved=None, **kwargs):
        super().__init__(parent, bg=WHITE, **kwargs)
        self._on_saved  = on_llamada_saved
        self._llamada_id = None
        self._sesion_id  = None
        self._build()
        self._init_sesion()

    # ── Session ────────────────────────────────────────────────────────────────

    def _init_sesion(self):
        sid = get_sesion_activa()
        if sid:
            self._sesion_id = sid
            self._update_sesion_label()
        else:
            self._nueva_sesion()

        # Restore last number
        last = get_config("ultimo_numero")
        if last:
            self._num_display.set_number(last)

    def _nueva_sesion(self):
        if self._sesion_id:
            cerrar_sesion(self._sesion_id)
        self._sesion_id = iniciar_sesion()
        self._num_display.reset_count()
        self._update_sesion_label()
        if self._on_saved:
            self._on_saved()

    def _update_sesion_label(self):
        from datetime import datetime
        self._sesion_lbl.config(
            text=f"Sesión activa · {datetime.now().strftime('%H:%M')}")

    # ── Build ──────────────────────────────────────────────────────────────────

    def _build(self):
        # Top bar
        topbar = tk.Frame(self, bg=PURPLE, padx=PAD, pady=PAD_S)
        topbar.pack(fill="x")
        tk.Label(topbar, text="Marcador", font=FONT_TITLE,
                 fg=WHITE, bg=PURPLE).pack(side="left")
        self._sesion_lbl = tk.Label(topbar, text="Sin sesión",
                                     font=FONT_SMALL, fg="#C5C1F0", bg=PURPLE)
        self._sesion_lbl.pack(side="left", padx=(12, 0))

        tk.Button(topbar, text="↺  Nueva sesión", font=FONT_SMALL,
                  bg=PURPLE_DARK, fg=WHITE, relief="flat", bd=0,
                  padx=10, pady=4, cursor="hand2",
                  activebackground=PURPLE_MID, activeforeground=WHITE,
                  command=self._confirm_nueva_sesion).pack(side="right")

        # Step indicator
        step_bar = tk.Frame(self, bg=WHITE, padx=PAD, pady=PAD_S)
        step_bar.pack(fill="x")
        self._steps = StepIndicator(step_bar, bg=WHITE)
        self._steps.pack(side="left")

        ttk.Separator(self, orient="horizontal").pack(fill="x")

        # Scrollable content
        outer = tk.Frame(self, bg=WHITE)
        outer.pack(fill="both", expand=True)
        self._canvas = tk.Canvas(outer, bg=WHITE, highlightthickness=0)
        vsb = ttk.Scrollbar(outer, orient="vertical", command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=vsb.set)
        self._content = tk.Frame(self._canvas, bg=WHITE)
        win = self._canvas.create_window((0, 0), window=self._content, anchor="nw")

        def _resize(e):
            self._canvas.itemconfig(win, width=e.width)
        self._canvas.bind("<Configure>", _resize)
        self._content.bind("<Configure>",
                           lambda e: self._canvas.configure(
                               scrollregion=self._canvas.bbox("all")))
        self._canvas.bind_all("<MouseWheel>",
                              lambda e: self._canvas.yview_scroll(
                                  -1*(e.delta//120), "units"), add="+")
        self._canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self._build_numero_section()
        self._build_estado_section()
        self._build_lead_section()
        self._build_actions()

    def _card(self, parent=None, title=""):
        p = parent or self._content
        outer = tk.Frame(p, bg=WHITE, padx=PAD, pady=PAD_S)
        outer.pack(fill="x", padx=PAD, pady=(0, PAD_S))
        inner = tk.Frame(outer, bg=WHITE, padx=PAD, pady=PAD_S,
                         highlightbackground=BORDER, highlightthickness=1)
        inner.pack(fill="x")
        if title:
            SectionHeader(inner, title, bg=WHITE).pack(fill="x", pady=(0, PAD_S))
        return inner

    # ── Número ─────────────────────────────────────────────────────────────────

    def _build_numero_section(self):
        c = self._card(title="Número a marcar")
        self._num_display = NumberDisplay(c, on_change=self._on_number_change, bg=WHITE)
        self._num_display.pack(fill="x")

    def _on_number_change(self, number, confirmed=False):
        if confirmed:
            set_config("ultimo_numero", number)
            self._steps.set_step(1)
            self._sec_estado_outer.pack(fill="x", padx=PAD, pady=(0, PAD_S))

    # ── Estado ─────────────────────────────────────────────────────────────────

    def _build_estado_section(self):
        self._sec_estado_outer = tk.Frame(self._content, bg=WHITE)
        self._sec_estado_outer.pack_forget()

        c = tk.Frame(self._sec_estado_outer, bg=WHITE, padx=PAD, pady=PAD_S,
                     highlightbackground=BORDER, highlightthickness=1)
        c.pack(fill="x")
        SectionHeader(c, "Estado de la llamada", bg=WHITE).pack(
            fill="x", pady=(0, PAD_S))

        r1 = tk.Frame(c, bg=WHITE)
        r1.pack(fill="x", pady=3)
        tk.Label(r1, text="¿Hubo tono?", font=FONT_BODY, fg=TEXT_SEC,
                 bg=WHITE, width=16, anchor="w").pack(side="left")
        self._tono = RadioGroup(r1, [
            {"label": "Sí", "value": "si", "style": "positive"},
            {"label": "No", "value": "no", "style": "negative"},
        ], bg=WHITE)
        self._tono.pack(side="left")

        r2 = tk.Frame(c, bg=WHITE)
        r2.pack(fill="x", pady=3)
        tk.Label(r2, text="¿Línea activa?", font=FONT_BODY, fg=TEXT_SEC,
                 bg=WHITE, width=16, anchor="w").pack(side="left")
        self._activo = RadioGroup(r2, [
            {"label": "Activo",           "value": "activo",        "style": "positive"},
            {"label": "Apagado",          "value": "apagado",       "style": "negative"},
            {"label": "Fuera de servicio","value": "fuera_servicio","style": "negative"},
            {"label": "No aplica",        "value": "na",            "style": "neutral"},
        ], bg=WHITE)
        self._activo.pack(side="left")

        r3 = tk.Frame(c, bg=WHITE)
        r3.pack(fill="x", pady=3)
        tk.Label(r3, text="¿Contestaron?", font=FONT_BODY, fg=TEXT_SEC,
                 bg=WHITE, width=16, anchor="w").pack(side="left")
        self._contesto = RadioGroup(r3, [
            {"label": "Sí",          "value": "si",    "style": "positive"},
            {"label": "Buzón",       "value": "buzon", "style": "neutral"},
            {"label": "No contestó", "value": "no",    "style": "negative"},
        ], callback=self._on_contesto, bg=WHITE)
        self._contesto.pack(side="left")

        rn = tk.Frame(c, bg=WHITE)
        rn.pack(fill="x", pady=(PAD_S, 0))
        tk.Label(rn, text="Notas", font=FONT_BODY, fg=TEXT_SEC,
                 bg=WHITE, width=16, anchor="nw").pack(side="left", pady=(3, 0))
        self._notas_estado = tk.Text(rn, font=FONT_BODY, height=2, width=42,
                                      bg=GRAY_BG, fg=TEXT_PRI, relief="flat",
                                      padx=8, pady=6,
                                      highlightbackground=BORDER, highlightthickness=1)
        self._notas_estado.pack(side="left")

        tk.Button(c, text="Guardar sin lead →", font=FONT_SMALL,
                  bg=GRAY_BG, fg=TEXT_SEC, relief="flat", bd=0,
                  padx=10, pady=4, cursor="hand2",
                  highlightbackground=BORDER, highlightthickness=1,
                  command=self._guardar_sin_lead).pack(
                      anchor="w", pady=(PAD_S, 0))

    def _on_contesto(self, value):
        if value == "si":
            self._steps.set_step(2)
            self._sec_lead_outer.pack(fill="x", padx=PAD, pady=(0, PAD_S))
        else:
            self._steps.set_step(1)
            self._sec_lead_outer.pack_forget()

    # ── Lead rápido ────────────────────────────────────────────────────────────

    def _build_lead_section(self):
        self._sec_lead_outer = tk.Frame(self._content, bg=WHITE)
        self._sec_lead_outer.pack_forget()

        c = tk.Frame(self._sec_lead_outer, bg=WHITE, padx=PAD, pady=PAD_S,
                     highlightbackground=BORDER, highlightthickness=1)
        c.pack(fill="x")
        SectionHeader(c, "Lead — captura rápida", bg=WHITE).pack(
            fill="x", pady=(0, PAD_S))

        self._nombre_lead  = LabeledEntry(c, "Nombre",  "Nombre del contacto", bg=WHITE)
        self._empresa_lead = LabeledEntry(c, "Empresa", "Empresa u organización", bg=WHITE)
        for w in (self._nombre_lead, self._empresa_lead):
            w.pack(fill="x", pady=2)

        ri = tk.Frame(c, bg=WHITE)
        ri.pack(fill="x", pady=3)
        tk.Label(ri, text="Interés", font=FONT_BODY, fg=TEXT_SEC,
                 bg=WHITE, width=14, anchor="w").pack(side="left")
        self._interes_lead = RadioGroup(ri, [
            {"label": "Alto",  "value": "alto",  "style": "positive"},
            {"label": "Medio", "value": "medio", "style": "neutral"},
            {"label": "Bajo",  "value": "bajo",  "style": "negative"},
        ], bg=WHITE)
        self._interes_lead.pack(side="left")

        # Button to open full profiling
        btn_row = tk.Frame(c, bg=WHITE)
        btn_row.pack(fill="x", pady=(PAD_S, 0))
        tk.Button(btn_row, text="  Abrir perfilación completa ↗  ",
                  font=FONT_BODY, bg=PURPLE_LIGHT, fg=PURPLE,
                  relief="flat", bd=0, padx=12, pady=6, cursor="hand2",
                  highlightbackground=PURPLE_MID, highlightthickness=1,
                  command=self._abrir_perfilacion).pack(side="left")

    def _abrir_perfilacion(self):
        numero = self._num_display.get_number()
        if not numero:
            messagebox.showwarning("Sin número", "Confirma el número primero.")
            return
        # First save the llamada if not saved yet
        if not self._llamada_id:
            self._llamada_id = guardar_llamada({
                "numero":       numero,
                "tuvo_tono":    self._tono.get() == "si",
                "esta_activo":  self._activo.get() or "activo",
                "contesto":     "si",
                "resultado":    "lead_capturado",
                "notas":        self._notas_estado.get("1.0", "end").strip(),
            }, self._sesion_id)
        PerfilacionDialog(
            self, lead_id=None,
            numero=numero,
            llamada_id=self._llamada_id,
            sesion_id=self._sesion_id,
            on_saved=self._on_perfilacion_saved,
        )

    def _on_perfilacion_saved(self):
        if self._on_saved:
            self._on_saved()
        self._reset()

    # ── Actions ────────────────────────────────────────────────────────────────

    def _build_actions(self):
        ttk.Separator(self, orient="horizontal").pack(fill="x", side="bottom")
        bar = tk.Frame(self, bg=WHITE, padx=PAD, pady=PAD_S)
        bar.pack(fill="x", side="bottom")

        tk.Button(bar, text="  Guardar lead rápido  ", font=FONT_BODY,
                  bg=PURPLE, fg=WHITE, relief="flat", bd=0,
                  padx=14, pady=6, cursor="hand2",
                  activebackground=PURPLE_MID, activeforeground=WHITE,
                  command=self._guardar_lead_rapido).pack(side="left", padx=(0, 8))

        tk.Button(bar, text="Nueva llamada", font=FONT_BODY,
                  bg=GRAY_BG, fg=TEXT_PRI, relief="flat", bd=0,
                  padx=12, pady=6, cursor="hand2",
                  highlightbackground=BORDER, highlightthickness=1,
                  command=self._reset).pack(side="left", padx=(0, 8))

        tk.Button(bar, text="Descartar", font=FONT_BODY,
                  bg=RED_LIGHT, fg=RED, relief="flat", bd=0,
                  padx=12, pady=6, cursor="hand2",
                  command=self._reset).pack(side="left")

    def _confirm_nueva_sesion(self):
        if messagebox.askyesno("Nueva sesión",
                               "¿Resetear los contadores de la sesión actual?\n"
                               "Los datos guardados no se borran."):
            self._nueva_sesion()
            messagebox.showinfo("Sesión reiniciada", "Contadores reseteados.")

    def _guardar_sin_lead(self):
        numero = self._num_display.get_number()
        if not numero:
            messagebox.showwarning("Sin número", "Confirma el número primero.")
            return
        guardar_llamada({
            "numero":      numero,
            "tuvo_tono":   self._tono.get() == "si",
            "esta_activo": self._activo.get() or "na",
            "contesto":    self._contesto.get() or "no",
            "resultado":   "sin_contacto",
            "notas":       self._notas_estado.get("1.0", "end").strip(),
        }, self._sesion_id)
        if self._on_saved:
            self._on_saved()
        self._num_display._increment()
        self._reset(keep_number=True)

    def _guardar_lead_rapido(self):
        numero = self._num_display.get_number()
        if not numero:
            messagebox.showwarning("Sin número", "Confirma el número primero.")
            return
        if self._contesto.get() != "si":
            messagebox.showwarning("Sin contacto",
                                   "Registra que contestaron antes de guardar el lead.")
            return
        lid = guardar_llamada({
            "numero":      numero,
            "tuvo_tono":   self._tono.get() == "si",
            "esta_activo": self._activo.get() or "activo",
            "contesto":    "si",
            "resultado":   "lead_capturado",
            "notas":       self._notas_estado.get("1.0", "end").strip(),
        }, self._sesion_id)

        guardar_lead({
            "numero":   numero,
            "nombre":   self._nombre_lead.get(),
            "empresa":  self._empresa_lead.get(),
            "interes":  self._interes_lead.get() or "medio",
            "perfilado": False,
        }, lid, self._sesion_id)

        messagebox.showinfo("Lead guardado", f"Lead de {numero} guardado.")
        if self._on_saved:
            self._on_saved()
        self._num_display._increment()
        self._reset(keep_number=True)

    def _reset(self, keep_number=False):
        self._llamada_id = None
        if not keep_number:
            pass  # keep number display intact
        self._tono.reset()
        self._activo.reset()
        self._contesto.reset()
        self._notas_estado.delete("1.0", "end")
        self._nombre_lead.clear()
        self._empresa_lead.clear()
        self._interes_lead.reset()
        self._sec_estado_outer.pack_forget()
        self._sec_lead_outer.pack_forget()
        self._steps.set_step(0)
        if not keep_number:
            self._steps.set_step(0)
        else:
            self._steps.set_step(1)
            self._sec_estado_outer.pack(fill="x", padx=PAD, pady=(0, PAD_S))
