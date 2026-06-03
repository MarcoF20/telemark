import tkinter as tk
import time
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

DEBUG_SAVE_TIMING = False


class MarcadorView(tk.Frame):

    def __init__(self, parent, on_llamada_saved=None, **kwargs):
        super().__init__(parent, bg=WHITE, **kwargs)
        self._on_saved  = on_llamada_saved
        self._llamada_id = None
        self._sesion_id  = None
        self._build()
        self._bind_hotkeys()
        self._init_sesion()

    def _bind_hotkeys(self):
        hotkeys = {
            "<Control-Return>": self._hotkey_save_call,
            "<Control-n>": self._hotkey_next_call,
            "<Control-N>": self._hotkey_next_call,
            "<Control-Key-1>": self._mark_dead_number,
            "<Control-Key-2>": self._mark_no_answer,
            "<Control-Key-3>": self._mark_voicemail,
            "<Control-Key-4>": self._mark_answered,
            "<Control-Key-5>": lambda: self._mark_retention("retained"),
            "<Control-Key-6>": lambda: self._mark_retention("not_retained"),
            "<Control-Key-7>": lambda: self._mark_lead_status("lead"),
            "<Control-Key-8>": lambda: self._mark_lead_status("not_lead"),
            "<Control-l>": self._hotkey_save_lead,
            "<Control-L>": self._hotkey_save_lead,
        }
        for sequence, action in hotkeys.items():
            self.bind_all(sequence, self._run_hotkey(action), add="+")

    def _run_hotkey(self, action):
        def _handler(event):
            action()
            return "break"
        return _handler

    def _save_timer(self):
        return time.perf_counter() if DEBUG_SAVE_TIMING else None

    def _log_save_timing(self, label, start):
        if DEBUG_SAVE_TIMING and start is not None:
            print(f"{label}: {time.perf_counter() - start:.4f}s")

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
        topbar = tk.Frame(self, bg=PRIMARY, padx=PAD, pady=PAD_S)
        topbar.pack(fill="x")
        tk.Label(topbar, text="Marcador", font=FONT_TITLE,
                 fg=WHITE, bg=PRIMARY).pack(side="left")
        self._sesion_lbl = tk.Label(topbar, text="Sin sesión",
                                     font=FONT_SMALL, fg="#93C5FD", bg=PRIMARY)
        self._sesion_lbl.pack(side="left", padx=(12, 0))

        tk.Button(topbar, text="↺  Nueva sesión", font=FONT_SMALL,
                  bg=PRIMARY_DARK, fg=WHITE, relief="flat", bd=0,
                  padx=10, pady=4, cursor="hand2",
                  activebackground=PRIMARY_MID, activeforeground=WHITE,
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
        tk.Label(r1, text="Número", font=FONT_BODY, fg=TEXT_SEC,
                 bg=WHITE, width=16, anchor="w").pack(side="left")
        self._line_status = RadioGroup(r1, [
            {"label": "Inactivo", "value": "dead", "style": "negative"},
            {"label": "Vivo",       "value": "alive", "style": "positive"},
        ], callback=self._on_line_status, bg=WHITE)
        self._line_status.pack(side="left")

        self._answer_row = tk.Frame(c, bg=WHITE)
        self._answer_row.pack_forget()
        tk.Label(self._answer_row, text="Respuesta", font=FONT_BODY, fg=TEXT_SEC,
                 bg=WHITE, width=16, anchor="w").pack(side="left")
        self._answer_status = RadioGroup(self._answer_row, [
            {"label": "No contestó", "value": "not_answered", "style": "negative"},
            {"label": "Buzón",       "value": "voicemail",    "style": "neutral"},
            {"label": "Contestó",    "value": "answered",     "style": "positive"},
        ], callback=self._on_answer_status, bg=WHITE)
        self._answer_status.pack(side="left")

        self._retention_row = tk.Frame(c, bg=WHITE)
        self._retention_row.pack_forget()
        tk.Label(self._retention_row, text="¿Retuvo?", font=FONT_BODY, fg=TEXT_SEC,
                 bg=WHITE, width=16, anchor="w").pack(side="left")
        self._retention = RadioGroup(self._retention_row, [
            {"label": "Retenido",    "value": "retained",     "style": "positive"},
            {"label": "No retenido", "value": "not_retained", "style": "negative"},
        ], callback=self._on_retention, bg=WHITE)
        self._retention.pack(side="left")

        self._lead_status_row = tk.Frame(c, bg=WHITE)
        self._lead_status_row.pack_forget()
        tk.Label(self._lead_status_row, text="Lead", font=FONT_BODY, fg=TEXT_SEC,
                 bg=WHITE, width=16, anchor="w").pack(side="left")
        self._lead_status = RadioGroup(self._lead_status_row, [
            {"label": "Lead",    "value": "lead",     "style": "positive"},
            {"label": "No lead", "value": "not_lead", "style": "negative"},
        ], callback=self._on_lead_status, bg=WHITE)
        self._lead_status.pack(side="left")

        self._callback_row = tk.Frame(c, bg=WHITE)
        self._callback_row.pack_forget()
        tk.Label(self._callback_row, text="Callback", font=FONT_BODY, fg=TEXT_SEC,
                 bg=WHITE, width=16, anchor="w").pack(side="left")
        self._callback_tag = RadioGroup(self._callback_row, [
            {"label": "No llamar", "value": "none", "style": "default"},
            {"label": "Llamar luego", "value": "call_later", "style": "info"},
        ], bg=WHITE)
        self._callback_tag.pack(side="left")

        self._notas_row = tk.Frame(c, bg=WHITE)
        self._notas_row.pack(fill="x", pady=(PAD_S, 0))
        tk.Label(self._notas_row, text="Notas", font=FONT_BODY, fg=TEXT_SEC,
                 bg=WHITE, width=16, anchor="nw").pack(side="left", pady=(3, 0))
        self._notas_estado = tk.Text(self._notas_row, font=FONT_BODY, height=2, width=42,
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

        self._build_hotkey_guide(c)

    def _build_hotkey_guide(self, parent):
        guide = tk.Frame(parent, bg=WHITE)
        guide.pack(fill="x", pady=(PAD_S, 0))

        items = [
            "Ctrl+1: Inactivo",
            "Ctrl+2: No contestó",
            "Ctrl+3: Buzón",
            "Ctrl+4: Contestó",
            "Ctrl+5: Retenido",
            "Ctrl+6: No retenido",
            "Ctrl+7: Lead",
            "Ctrl+8: No lead",
            "Ctrl+Enter: Guardar llamada",
            "Ctrl+N: Siguiente número",
        ]

        for text in items:
            tk.Label(
                guide,
                text=text,
                font=FONT_SMALL,
                fg=GRAY_DARK,
                bg=WHITE,
                anchor="w",
            ).pack(anchor="w")

    def _on_line_status(self, value):
        self._answer_status.reset()
        self._retention.reset()
        self._lead_status.reset()
        self._callback_tag.reset()
        self._retention_row.pack_forget()
        self._lead_status_row.pack_forget()
        self._callback_row.pack_forget()
        self._sec_lead_outer.pack_forget()

        if value == "alive":
            self._steps.set_step(1)
            self._answer_row.pack(fill="x", pady=3, before=self._notas_row)
        else:
            self._steps.set_step(1)
            self._answer_row.pack_forget()

    def _on_answer_status(self, value):
        self._retention.reset()
        self._lead_status.reset()
        self._callback_tag.reset()
        self._retention_row.pack_forget()
        self._lead_status_row.pack_forget()
        self._callback_row.pack_forget()
        self._sec_lead_outer.pack_forget()

        if value == "answered":
            self._steps.set_step(2)
            self._retention_row.pack(fill="x", pady=3, before=self._notas_row)
        elif value == "voicemail":
            self._steps.set_step(1)
            self._callback_tag.set("voicemail_retry")
            self._callback_row.pack(fill="x", pady=3, before=self._notas_row)
        else:
            self._steps.set_step(1)

    def _on_retention(self, value):
        self._lead_status.reset()
        self._sec_lead_outer.pack_forget()
        if value == "retained":
            self._steps.set_step(3)
            self._lead_status_row.pack(fill="x", pady=3, before=self._notas_row)
        else:
            self._steps.set_step(2)
            self._lead_status_row.pack_forget()

    def _on_lead_status(self, value):
        if value == "lead":
            self._steps.set_step(3)
            self._sec_lead_outer.pack(fill="x", padx=PAD, pady=(0, PAD_S))
        else:
            self._steps.set_step(3)
            self._sec_lead_outer.pack_forget()

    def _mark_no_answer(self):
        self._line_status.set("alive")
        self._answer_status.set("not_answered")

    def _mark_voicemail(self):
        self._line_status.set("alive")
        self._answer_status.set("voicemail")

    def _mark_dead_number(self):
        self._line_status.set("dead")

    def _mark_answered(self):
        self._line_status.set("alive")
        self._answer_status.set("answered")

    def _mark_retention(self, value):
        self._mark_answered()
        self._retention.set(value)

    def _mark_lead_status(self, value):
        self._mark_retention("retained")
        self._lead_status.set(value)

    def _hotkey_save_call(self):
        self._guardar_sin_lead(silent_invalid=True)

    def _hotkey_next_call(self):
        if self._num_display.get_number():
            self._num_display._increment()
            self._reset(keep_number=True)

    def _hotkey_save_lead(self):
        self._guardar_lead_rapido()

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
                  font=FONT_BODY, bg=PRIMARY_LIGHT, fg=PRIMARY,
                  relief="flat", bd=0, padx=12, pady=6, cursor="hand2",
                  highlightbackground=PRIMARY_MID, highlightthickness=1,
                  command=self._abrir_perfilacion).pack(side="left")

    def _abrir_perfilacion(self):
        numero = self._num_display.get_number()
        if not numero:
            messagebox.showwarning("Sin número", "Confirma el número primero.")
            return
        if not self._can_save_lead():
            return
        # First save the llamada if not saved yet
        if not self._llamada_id:
            self._llamada_id = guardar_llamada(self._call_data(lead_status="lead"),
                                                self._sesion_id)
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
                  bg=PRIMARY, fg=WHITE, relief="flat", bd=0,
                  padx=14, pady=6, cursor="hand2",
                  activebackground=PRIMARY_MID, activeforeground=WHITE,
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

    def _guardar_sin_lead(self, silent_invalid=False):
        step_start = self._save_timer()
        numero = self._num_display.get_number()
        if not numero:
            if not silent_invalid:
                messagebox.showwarning("Sin número", "Confirma el número primero.")
            return
        if not self._call_state_is_valid(silent=silent_invalid):
            return
        self._log_save_timing("Validate call", step_start)

        step_start = self._save_timer()
        lead_status = self._lead_status.get()
        lid = guardar_llamada(self._call_data(), self._sesion_id)
        if lead_status == "lead":
            guardar_lead(self._lead_data(numero), lid, self._sesion_id)
        self._log_save_timing("DB save call", step_start)

        step_start = self._save_timer()
        if self._on_saved:
            self._on_saved()
        self._log_save_timing("Visible refresh", step_start)

        step_start = self._save_timer()
        self._num_display._increment()
        self._reset(keep_number=True)
        self._log_save_timing("Prepare next", step_start)

    def _guardar_lead_rapido(self, silent_invalid=False):
        step_start = self._save_timer()
        numero = self._num_display.get_number()
        if not numero:
            if not silent_invalid:
                messagebox.showwarning("Sin número", "Confirma el número primero.")
            return
        if not self._can_save_lead(silent=silent_invalid):
            return
        self._lead_status.set("lead")
        self._log_save_timing("Validate lead", step_start)

        step_start = self._save_timer()
        lid = guardar_llamada(self._call_data(lead_status="lead"), self._sesion_id)
        guardar_lead(self._lead_data(numero), lid, self._sesion_id)
        self._log_save_timing("DB save lead", step_start)

        messagebox.showinfo("Lead guardado", f"Lead de {numero} guardado.")
        step_start = self._save_timer()
        if self._on_saved:
            self._on_saved()
        self._log_save_timing("Visible refresh", step_start)

        step_start = self._save_timer()
        self._num_display._increment()
        self._reset(keep_number=True)
        self._log_save_timing("Prepare next", step_start)

    def _can_save_lead(self, silent=False):
        if self._line_status.get() != "alive" or self._answer_status.get() != "answered":
            if not silent:
                messagebox.showwarning("Sin contacto",
                                       "Registra que contestaron antes de guardar el lead.")
            return False
        retention = self._retention.get()
        if retention != "retained":
            if silent:
                return False
            messagebox.showwarning("Falta retención",
                                   "Marca Retenida antes de guardar lead.")
            return False
        return True

    def _call_state_is_valid(self, silent=False):
        line_status = self._line_status.get()
        answer_status = self._answer_status.get()
        retention = self._retention.get()
        lead_status = self._lead_status.get()

        if not line_status:
            if not silent:
                messagebox.showwarning("Estado inválido",
                                       "Marca si el número está vivo o muerto.")
            return False

        if line_status == "dead":
            return True

        if not answer_status:
            if not silent:
                messagebox.showwarning("Estado inválido",
                                       "Marca si contestaron, no contestaron o fue buzón.")
            return False

        if answer_status != "answered":
            return True

        if retention not in ("retained", "not_retained"):
            if not silent:
                messagebox.showwarning("Estado inválido",
                                       "Marca si la persona fue retenida o no retenida.")
            return False

        if retention == "retained" and lead_status not in ("lead", "not_lead"):
            if not silent:
                messagebox.showwarning("Estado inválido",
                                       "Marca si la llamada retenida se convirtió en lead.")
            return False

        return True

    def _call_data(self, lead_status=None):
        return {
            "numero": self._num_display.get_number(),
            "line_status": self._line_status.get() or "dead",
            "answer_status": self._answer_status.get(),
            "retention_status": self._retention.get(),
            "lead_status": lead_status or self._lead_status.get(),
            "callback_tag": self._callback_tag.get() or "none",
            "notas": self._notas_estado.get("1.0", "end").strip(),
        }

    def _lead_data(self, numero):
        return {
            "numero": numero,
            "nombre": self._nombre_lead.get(),
            "empresa": self._empresa_lead.get(),
            "interes": self._interes_lead.get() or "medio",
            "perfilado": False,
        }

    def _reset(self, keep_number=False):
        self._llamada_id = None
        if not keep_number:
            pass  # keep number display intact
        self._line_status.reset()
        self._answer_status.reset()
        self._retention.reset()
        self._lead_status.reset()
        self._callback_tag.reset()
        self._notas_estado.delete("1.0", "end")
        self._nombre_lead.clear()
        self._empresa_lead.clear()
        self._interes_lead.reset()
        self._sec_estado_outer.pack_forget()
        self._answer_row.pack_forget()
        self._retention_row.pack_forget()
        self._lead_status_row.pack_forget()
        self._callback_row.pack_forget()
        self._sec_lead_outer.pack_forget()
        self._steps.set_step(0)
        if not keep_number:
            self._steps.set_step(0)
        else:
            self._steps.set_step(1)
            self._sec_estado_outer.pack(fill="x", padx=PAD, pady=(0, PAD_S))
