import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import csv
from datetime import datetime
from components.theme import *
from components.widgets import SectionHeader, bind_tree_mousewheel
from data.database import get_all_leads, delete_lead, get_lead_by_id


COLUMNS = [
    ("id",               "ID",         40),
    ("nombre",           "Nombre",     150),
    ("numero",           "Teléfono",   110),
    ("interes",          "Interés",    70),
    ("producto_interes", "Producto",   160),
    ("perfilado",        "Perfilado",  70),
    ("fecha_seguimiento","Seguimiento",100),
    ("hora_seguimiento", "Hora",       60),
    ("fecha",            "Capturado",  90),
    ("notas",            "Notas",      200),
]

INTERES_TAGS = {
    "alto":  {"background": GREEN_LIGHT,  "foreground": GREEN},
    "medio": {"background": AMBER_LIGHT,  "foreground": AMBER},
    "bajo":  {"background": RED_LIGHT,    "foreground": RED},
}


class LeadsView(tk.Frame):

    def __init__(self, parent, on_refresh=None, **kwargs):
        super().__init__(parent, bg=WHITE, **kwargs)
        self._on_refresh = on_refresh
        self._all_leads  = []
        self._build()
        self.refresh()

    # ── Build ──────────────────────────────────────────────────────────────────

    def _build(self):
        # Toolbar
        bar = tk.Frame(self, bg=WHITE, padx=PAD, pady=PAD_S)
        bar.pack(fill="x")
        tk.Label(bar, text="Prospectos", font=FONT_TITLE,
                 fg=TEXT_PRI, bg=WHITE).pack(side="left")

        for label, cmd, bg_, fg_ in [
            ("↻ Actualizar",        self.refresh,      GRAY_BG,      TEXT_SEC),
            ("⬇ Exportar CSV",      self._export_csv,  PRIMARY_LIGHT, PRIMARY),
            ("+ Nuevo prospecto",   self._nuevo_lead,  PRIMARY,       ON_PRIMARY),
        ]:
            tk.Button(bar, text=label, font=FONT_SMALL,
                      bg=bg_, fg=fg_, relief="flat", bd=0,
                      padx=10, pady=4, cursor="hand2",
                      highlightbackground=BORDER, highlightthickness=1,
                      command=cmd).pack(side="right", padx=(4, 0))

        # Filters
        fbar = tk.Frame(self, bg=GRAY_BG, padx=PAD, pady=PAD_XS)
        fbar.pack(fill="x")

        tk.Label(fbar, text="Buscar:", font=FONT_SMALL,
                 fg=TEXT_SEC, bg=GRAY_BG).pack(side="left")
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *a: self._filter())
        ttk.Entry(fbar, textvariable=self._search_var,
                  font=FONT_BODY, width=22).pack(side="left", padx=(4, 12), ipady=2)

        tk.Label(fbar, text="Interés:", font=FONT_SMALL,
                 fg=TEXT_SEC, bg=GRAY_BG).pack(side="left")
        self._filter_int = tk.StringVar(value="todos")
        for val, lbl in [("todos","Todos"),("alto","Alto"),
                         ("medio","Medio"),("bajo","Bajo")]:
            ttk.Radiobutton(fbar, text=lbl, variable=self._filter_int,
                            value=val, style="Gray.TRadiobutton",
                            command=self._filter).pack(side="left", padx=3)

        tk.Label(fbar, text="  Seguimiento:", font=FONT_SMALL,
                 fg=TEXT_SEC, bg=GRAY_BG).pack(side="left")
        self._filter_seg = tk.StringVar(value="todos")
        for val, lbl in [("todos","Todos"),("pendiente","Con cita"),("sin","Sin cita")]:
            ttk.Radiobutton(fbar, text=lbl, variable=self._filter_seg,
                            value=val, style="Gray.TRadiobutton",
                            command=self._filter).pack(side="left", padx=3)

        tk.Label(fbar, text="  Desde:", font=FONT_SMALL,
                 fg=TEXT_SEC, bg=GRAY_BG).pack(side="left")
        self._desde_var = tk.StringVar()
        self._desde_var.trace_add("write", lambda *a: self._filter())
        ttk.Entry(fbar, textvariable=self._desde_var,
                  font=FONT_SMALL, width=10).pack(side="left", padx=(4, 2), ipady=2)
        tk.Label(fbar, text="Hasta:", font=FONT_SMALL,
                 fg=TEXT_SEC, bg=GRAY_BG).pack(side="left")
        self._hasta_var = tk.StringVar()
        self._hasta_var.trace_add("write", lambda *a: self._filter())
        ttk.Entry(fbar, textvariable=self._hasta_var,
                  font=FONT_SMALL, width=10).pack(side="left", padx=(4, 0), ipady=2)
        tk.Label(fbar, text="(AAAA-MM-DD)", font=("Segoe UI", 8),
                 fg=TEXT_HINT, bg=GRAY_BG).pack(side="left", padx=(4, 0))

        ttk.Separator(self, orient="horizontal").pack(fill="x")

        # Treeview
        tree_frame = tk.Frame(self, bg=WHITE)
        tree_frame.pack(fill="both", expand=True, padx=PAD, pady=PAD_S)

        cols = [c[0] for c in COLUMNS]
        self._tree = ttk.Treeview(tree_frame, columns=cols,
                                   show="headings", selectmode="browse")
        for col_id, col_lbl, col_w in COLUMNS:
            self._tree.heading(col_id, text=col_lbl,
                               command=lambda c=col_id: self._sort(c))
            self._tree.column(col_id, width=col_w, minwidth=40, anchor="w")

        for tag, opts in INTERES_TAGS.items():
            self._tree.tag_configure(tag, **opts)
        self._tree.tag_configure("proximos", background=BLUE_LIGHT,
                                  foreground=BLUE)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical",
                             command=self._tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal",
                             command=self._tree.xview)
        self._tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        bind_tree_mousewheel(self._tree)
        self._tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        self._tree.bind("<Double-1>", lambda e: self._edit_selected())

        # Bottom bar
        bot = tk.Frame(self, bg=WHITE, padx=PAD, pady=PAD_XS)
        bot.pack(fill="x")
        self._count_var = tk.StringVar()
        tk.Label(bot, textvariable=self._count_var, font=FONT_SMALL,
                 fg=TEXT_SEC, bg=WHITE).pack(side="left")

        tk.Button(bot, text="✏ Editar seleccionado", font=FONT_SMALL,
                  bg=BLUE_LIGHT, fg=BLUE, relief="flat", bd=0,
                  padx=10, pady=3, cursor="hand2",
                  command=self._edit_selected).pack(side="right", padx=(4, 0))
        tk.Button(bot, text="🗑 Eliminar seleccionado", font=FONT_SMALL,
                  bg=RED_LIGHT, fg=RED, relief="flat", bd=0,
                  padx=10, pady=3, cursor="hand2",
                  command=self._delete_selected).pack(side="right", padx=(4, 0))

    # ── Data ───────────────────────────────────────────────────────────────────

    def refresh(self):
        self._all_leads = get_all_leads()
        self._filter()

    def _filter(self):
        query   = self._search_var.get().lower()
        interes = self._filter_int.get()
        seg     = self._filter_seg.get()
        desde   = self._desde_var.get().strip()
        hasta   = self._hasta_var.get().strip()
        today   = datetime.now().strftime("%Y-%m-%d")

        filtered = []
        for lead in self._all_leads:
            if interes != "todos" and lead.get("interes") != interes:
                continue
            if seg == "pendiente" and not lead.get("fecha_seguimiento"):
                continue
            if seg == "sin" and lead.get("fecha_seguimiento"):
                continue
            fs = lead.get("fecha_seguimiento") or ""
            if desde and fs and fs < desde:
                continue
            if hasta and fs and fs > hasta:
                continue
            if query:
                text = " ".join(str(v) for v in lead.values()).lower()
                if query not in text:
                    continue
            filtered.append(lead)

        self._tree.delete(*self._tree.get_children())
        for lead in filtered:
            vals = []
            for col_id, _, _ in COLUMNS:
                v = lead.get(col_id)
                if col_id == "perfilado":
                    v = "✓ sí" if v else "—"
                elif v is None:
                    v = ""
                vals.append(v)
            # Tag: próximos 3 días
            fs = lead.get("fecha_seguimiento") or ""
            tag = lead.get("interes", "medio")
            if fs and fs >= today:
                tag = "proximos"
            self._tree.insert("", "end", values=vals,
                              iid=str(lead["id"]),
                              tags=(tag,))

        total = len(self._all_leads)
        shown = len(filtered)
        self._count_var.set(f"{shown} de {total} prospectos")

    def _sort(self, col):
        items = [(self._tree.set(k, col), k) for k in self._tree.get_children("")]
        items.sort(key=lambda x: x[0].lower())
        for i, (_, k) in enumerate(items):
            self._tree.move(k, "", i)

    def _get_selected_id(self):
        sel = self._tree.selection()
        if not sel:
            messagebox.showinfo("Sin selección", "Selecciona un prospecto primero.")
            return None
        return int(sel[0])

    def _nuevo_lead(self):
        from views.perfilacion import PerfilacionDialog
        PerfilacionDialog(self, on_saved=self.refresh)

    def _edit_selected(self):
        lead_id = self._get_selected_id()
        if lead_id is None:
            return
        if not self._lead_exists(lead_id):
            return
        from views.perfilacion import PerfilacionDialog
        PerfilacionDialog(self, lead_id=lead_id, on_saved=self.refresh)

    def _delete_selected(self):
        lead_id = self._get_selected_id()
        if lead_id is None:
            return
        lead = get_lead_by_id(lead_id)
        if not lead:
            messagebox.showinfo(
                "Prospecto no disponible",
                "Ese prospecto ya no existe. La lista se va a actualizar."
            )
            self.refresh()
            if self._on_refresh:
                self._on_refresh()
            return
        nombre = lead.get("nombre") or lead.get("numero") or f"ID {lead_id}"
        if messagebox.askyesno("Eliminar prospecto",
                               f"¿Eliminar el prospecto de {nombre}?\nEsta acción no se puede deshacer."):
            delete_lead(lead_id)
            self.refresh()
            if self._on_refresh:
                self._on_refresh()

    def _lead_exists(self, lead_id: int) -> bool:
        if get_lead_by_id(lead_id):
            return True
        messagebox.showinfo(
            "Prospecto no disponible",
            "Ese prospecto ya no existe. La lista se va a actualizar."
        )
        self.refresh()
        if self._on_refresh:
            self._on_refresh()
        return False

    def _export_csv(self):
        data = get_all_leads()
        if not data:
            messagebox.showinfo("Sin datos", "No hay prospectos para exportar.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialfile=f"prospectos_{datetime.now().strftime('%Y%m%d')}.csv",
        )
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
        messagebox.showinfo("Exportado", f"CSV guardado:\n{path}")
