import tkinter as tk
from tkinter import ttk, messagebox
from components.theme import *
from components.widgets import (
    RadioGroup, LabeledEntry, LabeledCombo, LabeledSpinbox, SectionHeader
)
from data.database import guardar_lead, update_lead, get_lead_by_id


PRODUCTOS = ["Servicio funerario", "Propiedad de descanso final", "Paquete integral", "No definido"]
CEMENTERIOS = [
    "Monte de los Olivos", "Santa Gema", "Jardin Angeles (el niño)", "Otro / Por definir"
]
HORARIOS = [
    "09:00", "09:30", "10:00", "10:30",
    "11:00", "11:30", "12:00", "12:30", "13:00", "13:30",
    "14:00", "14:30", "15:00", "15:30", "16:00", "16:30",
    "17:00", "17:30", "18:00",
]


class PerfilacionDialog(tk.Toplevel):
    """Full-screen dialog for lead profiling."""

    def __init__(self, parent, lead_id: int | None = None,
                 numero: str = "", llamada_id: int | None = None,
                 sesion_id: int | None = None,
                 on_saved=None):
        super().__init__(parent)
        self._lead_id   = lead_id
        self._numero    = numero
        self._llamada_id = llamada_id
        self._sesion_id = sesion_id
        self._on_saved  = on_saved
        self._existing  = get_lead_by_id(lead_id) if lead_id else None

        self.title("Perfilación de cita" if not lead_id else "Editar lead")
        self.geometry("700x720")
        self.minsize(620, 600)
        self.configure(bg=WHITE)
        self.transient(parent)

        self._build()
        if self._existing:
            self._populate()
        self._make_modal()

    def _make_modal(self):
        self.update_idletasks()
        try:
            self.wait_visibility()
            self.grab_set()
        except tk.TclError:
            self.after_idle(self._retry_grab)
        self.focus_set()

    def _retry_grab(self):
        if not self.winfo_exists():
            return
        try:
            self.grab_set()
            self.focus_set()
        except tk.TclError:
            pass

    # ── Build ──────────────────────────────────────────────────────────────────

    def _build(self):
        # Header bar
        hdr = tk.Frame(self, bg=PURPLE, padx=PAD, pady=PAD_S)
        hdr.pack(fill="x")
        tk.Label(hdr, text="Perfilación de cita",
                 font=FONT_TITLE, fg=WHITE, bg=PURPLE).pack(side="left")
        tk.Button(hdr, text="✕", font=FONT_BODY,
                  bg=PURPLE, fg=WHITE, relief="flat", bd=0,
                  activebackground=PURPLE_DARK, cursor="hand2",
                  command=self.destroy).pack(side="right")

        # Scrollable body
        outer = tk.Frame(self, bg=WHITE)
        outer.pack(fill="both", expand=True)
        canvas = tk.Canvas(outer, bg=WHITE, highlightthickness=0)
        vsb = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        self._body = tk.Frame(canvas, bg=WHITE, padx=PAD, pady=PAD_S)
        win = canvas.create_window((0, 0), window=self._body, anchor="nw")

        def _resize(e):
            canvas.itemconfig(win, width=e.width)
        canvas.bind("<Configure>", _resize)
        self._body.bind("<Configure>",
                        lambda e: canvas.configure(
                            scrollregion=canvas.bbox("all")))
        canvas.bind_all("<MouseWheel>",
                        lambda e: canvas.yview_scroll(-1*(e.delta//120), "units"),
                        add="+")
        canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self._build_contacto()
        self._build_calificacion()
        self._build_funeraria()
        self._build_seguimiento()

        # Action bar
        sep = ttk.Separator(self, orient="horizontal")
        sep.pack(fill="x", side="bottom")
        bar = tk.Frame(self, bg=WHITE, padx=PAD, pady=PAD_S)
        bar.pack(fill="x", side="bottom")
        tk.Button(bar, text="  Guardar perfilación  ", font=FONT_BODY,
                  bg=PURPLE, fg=WHITE, relief="flat", bd=0,
                  padx=16, pady=7, cursor="hand2",
                  activebackground=PURPLE_MID, activeforeground=WHITE,
                  command=self._save).pack(side="left")
        tk.Button(bar, text="Cancelar", font=FONT_BODY,
                  bg=GRAY_BG, fg=TEXT_PRI, relief="flat", bd=0,
                  padx=12, pady=7, cursor="hand2",
                  command=self.destroy).pack(side="left", padx=(8, 0))

    def _section(self, title, icon=""):
        f = tk.Frame(self._body, bg=WHITE, pady=PAD_S)
        f.pack(fill="x")
        lbl_text = f"{icon}  {title}" if icon else title
        SectionHeader(f, lbl_text, bg=WHITE).pack(fill="x", pady=(0, PAD_S))
        return f

    def _build_contacto(self):
        sec = self._section("Datos de contacto", "👤")
        self._nombre  = LabeledEntry(sec, "Nombre completo", "Nombre completo del prospecto", bg=WHITE)
        self._tel     = LabeledEntry(sec, "Teléfono",        "Número de contacto", bg=WHITE)
        self._empresa = LabeledEntry(sec, "Empresa / Ref",   "Empresa u origen del contacto", bg=WHITE)
        self._email   = LabeledEntry(sec, "Email",           "correo@ejemplo.com", bg=WHITE)
        for w in (self._nombre, self._tel, self._empresa, self._email):
            w.pack(fill="x", pady=3)

    def _build_calificacion(self):
        sec = self._section("Calificación", "⭐")

        ri = tk.Frame(sec, bg=WHITE)
        ri.pack(fill="x", pady=3)
        tk.Label(ri, text="Nivel de interés", font=FONT_BODY, fg=TEXT_SEC,
                 bg=WHITE, width=14, anchor="w").pack(side="left")
        self._interes = RadioGroup(ri, [
            {"label": "Alto",  "value": "alto",  "style": "positive"},
            {"label": "Medio", "value": "medio", "style": "neutral"},
            {"label": "Bajo",  "value": "bajo",  "style": "negative"},
        ], bg=WHITE)
        self._interes.pack(side="left")

        rd = tk.Frame(sec, bg=WHITE)
        rd.pack(fill="x", pady=3)
        tk.Label(rd, text="Toma la decisión", font=FONT_BODY, fg=TEXT_SEC,
                 bg=WHITE, width=14, anchor="w").pack(side="left")
        self._decisor = RadioGroup(rd, [
            {"label": "Solo",              "value": "solo",     "style": "positive"},
            {"label": "Con esposa/pareja", "value": "conjunto", "style": "neutral"},
            {"label": "Otro familiar",     "value": "otro",     "style": "info"},
        ], bg=WHITE)
        self._decisor.pack(side="left")

        rp = tk.Frame(sec, bg=WHITE)
        rp.pack(fill="x", pady=3)
        tk.Label(rp, text="Forma de pago", font=FONT_BODY, fg=TEXT_SEC,
                 bg=WHITE, width=14, anchor="w").pack(side="left")
        self._pago = RadioGroup(rp, [
            {"label": "Tarjeta crédito", "value": "credito", "style": "default"},
            {"label": "Tarjeta débito",  "value": "debito",  "style": "teal"},
            {"label": "Efectivo",        "value": "efectivo","style": "neutral"},
            {"label": "No definido",     "value": "nd",      "style": "info"},
        ], bg=WHITE)
        self._pago.pack(side="left")

        rn = tk.Frame(sec, bg=WHITE)
        rn.pack(fill="x", pady=3)
        tk.Label(rn, text="Notas generales", font=FONT_BODY, fg=TEXT_SEC,
                 bg=WHITE, width=14, anchor="nw").pack(side="left", pady=(3, 0))
        self._notas = tk.Text(rn, font=FONT_BODY, height=3, width=44,
                               bg=GRAY_BG, fg=TEXT_PRI, relief="flat",
                               padx=8, pady=6,
                               highlightbackground=BORDER, highlightthickness=1)
        self._notas.pack(side="left")

    def _build_funeraria(self):
        sec = self._section("Perfilación funeraria", "🪦")

        # Familia
        fam = tk.Frame(sec, bg=WHITE)
        fam.pack(fill="x", pady=3)
        self._miembros   = LabeledSpinbox(fam, "Miembros familia", 1, 20, bg=WHITE)
        self._miembros.pack(side="left")
        tk.Label(fam, text="   A proteger:", font=FONT_BODY, fg=TEXT_SEC, bg=WHITE).pack(side="left")
        self._a_proteger = LabeledSpinbox(fam, "", 1, 20, bg=WHITE, label_width=0)
        self._a_proteger.pack(side="left")

        # Producto
        self._producto = LabeledCombo(sec, "Producto de interés", PRODUCTOS, bg=WHITE)
        self._producto.pack(fill="x", pady=3)

        # Cementerio
        self._cementerio = LabeledCombo(sec, "Cementerio / nicho", CEMENTERIOS, bg=WHITE)
        self._cementerio.pack(fill="x", pady=3)

    def _build_seguimiento(self):
        sec = self._section("Seguimiento", "📅")

        # Checkbox agendar
        self._agendar_var = tk.BooleanVar(value=False)
        chk = ttk.Checkbutton(sec, text="Agendar llamada de seguimiento",
                               variable=self._agendar_var,
                               command=self._toggle_seguimiento)
        chk.pack(anchor="w", pady=(0, PAD_S))

        self._seg_frame = tk.Frame(sec, bg=WHITE)
        self._seg_frame.pack(fill="x")
        self._seg_frame.pack_forget()

        # Fecha
        fd = tk.Frame(self._seg_frame, bg=WHITE)
        fd.pack(fill="x", pady=3)
        tk.Label(fd, text="Fecha (AAAA-MM-DD)", font=FONT_BODY, fg=TEXT_SEC,
                 bg=WHITE, width=18, anchor="w").pack(side="left")
        self._fecha_seg = ttk.Entry(fd, font=FONT_BODY, width=14)
        self._fecha_seg.pack(side="left", ipady=3)

        # Hora
        fh = tk.Frame(self._seg_frame, bg=WHITE)
        fh.pack(fill="x", pady=3)
        tk.Label(fh, text="Hora", font=FONT_BODY, fg=TEXT_SEC,
                 bg=WHITE, width=18, anchor="w").pack(side="left")
        self._hora_seg_var = tk.StringVar()
        self._hora_combo = ttk.Combobox(fh, textvariable=self._hora_seg_var,
                                         values=HORARIOS, state="readonly",
                                         font=FONT_BODY, width=10)
        self._hora_combo.pack(side="left")

        # Notas seguimiento
        fn = tk.Frame(self._seg_frame, bg=WHITE)
        fn.pack(fill="x", pady=3)
        tk.Label(fn, text="Notas seguimiento", font=FONT_BODY, fg=TEXT_SEC,
                 bg=WHITE, width=18, anchor="nw").pack(side="left", pady=(3, 0))
        self._seg_notas = tk.Text(fn, font=FONT_BODY, height=2, width=36,
                                   bg=GRAY_BG, fg=TEXT_PRI, relief="flat",
                                   padx=8, pady=6,
                                   highlightbackground=BORDER, highlightthickness=1)
        self._seg_notas.pack(side="left")

    def _toggle_seguimiento(self):
        if self._agendar_var.get():
            self._seg_frame.pack(fill="x")
        else:
            self._seg_frame.pack_forget()

    # ── Populate (edit mode) ───────────────────────────────────────────────────

    def _populate(self):
        d = self._existing
        self._nombre.set(d.get("nombre") or "")
        self._tel.set(d.get("numero") or "")
        self._empresa.set(d.get("empresa") or "")
        self._email.set(d.get("email") or "")
        if d.get("interes"):    self._interes.set(d["interes"])
        if d.get("decide_solo"):self._decisor.set(d["decide_solo"])
        if d.get("forma_pago"): self._pago.set(d["forma_pago"])
        if d.get("notas"):
            self._notas.insert("1.0", d["notas"])
        if d.get("miembros_familia"):
            self._miembros.set(d["miembros_familia"])
        if d.get("a_proteger"):
            self._a_proteger.set(d["a_proteger"])
        if d.get("producto_interes"):
            self._producto.set(d["producto_interes"])
        if d.get("cementerio_nicho"):
            self._cementerio.set(d["cementerio_nicho"])
        if d.get("agendar_llamada"):
            self._agendar_var.set(True)
            self._toggle_seguimiento()
            self._fecha_seg.insert(0, d.get("fecha_seguimiento") or "")
            self._hora_seg_var.set(d.get("hora_seguimiento") or "")
            seg_notas = d.get("seguimiento_notas") or ""
            if seg_notas:
                self._seg_notas.insert("1.0", seg_notas)

    # ── Save ───────────────────────────────────────────────────────────────────

    def _save(self):
        nombre = self._nombre.get()
        tel    = self._tel.get() or self._numero

        if not nombre and not tel:
            messagebox.showwarning("Datos incompletos",
                                   "Al menos ingresa nombre o teléfono.")
            return

        data = {
            "numero":           tel,
            "nombre":           nombre,
            "empresa":          self._empresa.get(),
            "email":            self._email.get(),
            "interes":          self._interes.get() or "medio",
            "decide_solo":      self._decisor.get(),
            "forma_pago":       self._pago.get(),
            "notas":            self._notas.get("1.0", "end").strip(),
            "miembros_familia": self._miembros.get(),
            "a_proteger":       self._a_proteger.get(),
            "producto_interes": self._producto.get(),
            "cementerio_nicho": self._cementerio.get(),
            "agendar_llamada":  self._agendar_var.get(),
            "fecha_seguimiento":self._fecha_seg.get().strip() if self._agendar_var.get() else "",
            "hora_seguimiento": self._hora_seg_var.get() if self._agendar_var.get() else "",
            "seguimiento_notas":self._seg_notas.get("1.0","end").strip() if self._agendar_var.get() else "",
            "perfilado":        True,
        }

        if self._lead_id:
            update_lead(self._lead_id, data)
            msg = "Lead actualizado correctamente."
        else:
            lid = guardar_lead(data, self._llamada_id or 0, self._sesion_id)
            msg = f"Lead #{lid} guardado."

        messagebox.showinfo("Guardado", msg)
        if self._on_saved:
            self._on_saved()
        self.destroy()
