import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import csv
from datetime import datetime
from components.theme import *
from data.database import get_all_llamadas, delete_llamada

COLUMNS = [
    ("id",          "ID",         40),
    ("numero",      "Número",     120),
    ("fecha",       "Fecha",      90),
    ("hora",        "Hora",       60),
    ("tuvo_tono",   "Tono",       50),
    ("esta_activo", "Activo",     110),
    ("contesto",    "Contestó",   80),
    ("retention_status", "Retención", 120),
    ("resultado",   "Resultado",  130),
    ("notas",       "Notas",      220),
]

RESULTADO_TAGS = {
    "lead_capturado": {"background": GREEN_LIGHT, "foreground": GREEN},
    "sin_contacto":   {"background": GRAY_BG,     "foreground": TEXT_SEC},
}

RETENTION_LABELS = {
    "retained": "Retenida",
    "not_retained": "No retenida",
    "not_applicable": "No aplica",
}


class HistorialView(tk.Frame):

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=WHITE, **kwargs)
        self._build()
        self.refresh()

    def _build(self):
        bar = tk.Frame(self, bg=WHITE, padx=PAD, pady=PAD_S)
        bar.pack(fill="x")
        tk.Label(bar, text="Historial de llamadas", font=FONT_TITLE,
                 fg=TEXT_PRI, bg=WHITE).pack(side="left")

        for label, cmd, bg_, fg_ in [
            ("↻ Actualizar",   self.refresh,    GRAY_BG,      TEXT_SEC),
            ("⬇ Exportar CSV", self._export,    PURPLE_LIGHT, PURPLE),
        ]:
            tk.Button(bar, text=label, font=FONT_SMALL,
                      bg=bg_, fg=fg_, relief="flat", bd=0,
                      padx=10, pady=4, cursor="hand2",
                      highlightbackground=BORDER, highlightthickness=1,
                      command=cmd).pack(side="right", padx=(4, 0))

        ttk.Separator(self, orient="horizontal").pack(fill="x")

        tree_frame = tk.Frame(self, bg=WHITE)
        tree_frame.pack(fill="both", expand=True, padx=PAD, pady=PAD_S)

        cols = [c[0] for c in COLUMNS]
        self._tree = ttk.Treeview(tree_frame, columns=cols,
                                   show="headings", selectmode="browse")
        for col_id, col_lbl, col_w in COLUMNS:
            self._tree.heading(col_id, text=col_lbl)
            self._tree.column(col_id, width=col_w, minwidth=40, anchor="w")

        for tag, opts in RESULTADO_TAGS.items():
            self._tree.tag_configure(tag, **opts)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical",
                             command=self._tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal",
                             command=self._tree.xview)
        self._tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self._tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        bot = tk.Frame(self, bg=WHITE, padx=PAD, pady=PAD_XS)
        bot.pack(fill="x")
        self._count_var = tk.StringVar()
        tk.Label(bot, textvariable=self._count_var, font=FONT_SMALL,
                 fg=TEXT_SEC, bg=WHITE).pack(side="left")
        tk.Button(bot, text="🗑 Eliminar seleccionado", font=FONT_SMALL,
                  bg=RED_LIGHT, fg=RED, relief="flat", bd=0,
                  padx=10, pady=3, cursor="hand2",
                  command=self._delete_selected).pack(side="right")

    def refresh(self):
        self._tree.delete(*self._tree.get_children())
        data = get_all_llamadas()
        for row in data:
            vals = []
            for col_id, _, _ in COLUMNS:
                v = row.get(col_id, "") or ""
                if col_id == "tuvo_tono":
                    v = "Sí" if v == 1 else "No"
                elif col_id == "retention_status":
                    v = RETENTION_LABELS.get(v, v)
                vals.append(v)
            tag = row.get("resultado", "sin_contacto")
            self._tree.insert("", "end", values=vals,
                              iid=str(row["id"]),
                              tags=(tag,) if tag in RESULTADO_TAGS else ())
        self._count_var.set(f"{len(data)} llamadas en total")

    def _delete_selected(self):
        sel = self._tree.selection()
        if not sel:
            messagebox.showinfo("Sin selección", "Selecciona una llamada primero.")
            return
        lid = int(sel[0])
        if messagebox.askyesno("Eliminar llamada",
                               f"¿Eliminar la llamada #{lid}?\n"
                               "Si tiene un lead asociado también se eliminará."):
            delete_llamada(lid)
            self.refresh()

    def _export(self):
        data = get_all_llamadas()
        if not data:
            messagebox.showinfo("Sin datos", "No hay llamadas para exportar.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialfile=f"historial_{datetime.now().strftime('%Y%m%d')}.csv",
        )
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
        messagebox.showinfo("Exportado", f"CSV guardado:\n{path}")
