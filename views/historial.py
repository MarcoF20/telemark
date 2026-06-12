import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import csv
from datetime import datetime
from components.theme import *
from components.widgets import bind_tree_mousewheel
from data.database import get_all_llamadas, delete_llamada

COLUMNS = [
    ("id",          "ID",         40),
    ("numero",      "Número",     120),
    ("fecha",       "Fecha",      90),
    ("hora",        "Hora",       60),
    ("line_status", "Línea",      90),
    ("answer_status", "Respuesta", 120),
    ("retention_status", "Retención", 120),
    ("lead_status", "Lead",       90),
    ("callback_tag", "Callback",  120),
    ("notas",       "Notas",      220),
]

RESULTADO_TAGS = {
    "lead_capturado": {"background": GREEN_LIGHT, "foreground": GREEN},
    "callback":       {"background": BLUE_LIGHT,  "foreground": BLUE},
    "voicemail":      {"background": AMBER_LIGHT, "foreground": AMBER},
    "sin_contacto":   {"background": GRAY_BG,     "foreground": TEXT_SEC},
}

RESULTADO_FILTERS = [
    ("lead", "Prospecto"),
    ("callback", "Callback"),
    ("sin", "Sin prospecto"),
]

ANSWER_FILTERS = [
    ("answered", "Contestó"),
    ("not_answered", "No contestó"),
    ("voicemail", "Buzón"),
    ("dead", "Inactivo"),
]

RETENTION_LABELS = {
    "retained": "Retenida",
    "not_retained": "No retenida",
    "not_applicable": "No aplica",
}

LINE_LABELS = {
    "alive": "Activo",
    "dead": "Inactivo",
}

ANSWER_LABELS = {
    "answered": "Contestó",
    "not_answered": "No contestó",
    "voicemail": "Buzón",
    "not_applicable": "No aplica",
}

LEAD_LABELS = {
    "lead": "Lead",
    "not_lead": "No lead",
    "not_applicable": "No aplica",
}

CALLBACK_LABELS = {
    "none": "",
    "voicemail_retry": "Buzón",
    "call_later": "Llamar luego",
    "follow_up": "Follow-up",
}


class HistorialView(tk.Frame):

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=WHITE, **kwargs)
        self._all_calls = []
        self._filtered_calls = []
        self._build()
        self.refresh()

    def _build(self):
        bar = tk.Frame(self, bg=WHITE, padx=PAD, pady=PAD_S)
        bar.pack(fill="x")
        tk.Label(bar, text="Historial de llamadas", font=FONT_TITLE,
                 fg=TEXT_PRI, bg=WHITE).pack(side="left")

        for label, cmd, bg_, fg_ in [
            ("↻ Actualizar",   self.refresh,    GRAY_BG,      TEXT_SEC),
            ("⬇ Exportar CSV", self._export,    PRIMARY_LIGHT, PRIMARY),
        ]:
            tk.Button(bar, text=label, font=FONT_SMALL,
                      bg=bg_, fg=fg_, relief="flat", bd=0,
                      padx=10, pady=4, cursor="hand2",
                      highlightbackground=BORDER, highlightthickness=1,
                      command=cmd).pack(side="right", padx=(4, 0))

        self._build_filters()
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
        bind_tree_mousewheel(self._tree)
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

    def _build_filters(self):
        filters = tk.Frame(self, bg=GRAY_BG, padx=PAD, pady=PAD_XS)
        filters.pack(fill="x")

        top = tk.Frame(filters, bg=GRAY_BG)
        top.pack(fill="x", pady=(0, 3))
        tk.Label(top, text="Buscar:", font=FONT_SMALL,
                 fg=TEXT_SEC, bg=GRAY_BG).pack(side="left")
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *a: self._filter())
        ttk.Entry(top, textvariable=self._search_var,
                  font=FONT_BODY, width=28).pack(side="left", padx=(4, 12), ipady=2)
        tk.Button(top, text="Limpiar filtros", font=FONT_SMALL,
                  bg=GRAY_BG, fg=TEXT_SEC, relief="flat", bd=0,
                  padx=8, pady=3, cursor="hand2",
                  highlightbackground=BORDER, highlightthickness=1,
                  command=self._clear_filters).pack(side="right")

        tk.Label(top, text="Resultado:", font=FONT_SMALL,
                 fg=TEXT_SEC, bg=GRAY_BG).pack(side="left")
        self._result_filter = tk.StringVar(value="")
        for val, lbl in RESULTADO_FILTERS:
            ttk.Radiobutton(top, text=lbl, variable=self._result_filter,
                            value=val, style="Gray.TRadiobutton",
                            command=self._filter).pack(side="left", padx=3)

        mid = tk.Frame(filters, bg=GRAY_BG)
        mid.pack(fill="x", pady=(0, 3))
        tk.Label(mid, text="Respuesta:", font=FONT_SMALL,
                 fg=TEXT_SEC, bg=GRAY_BG).pack(side="left")
        self._answer_filter = tk.StringVar(value="")
        for val, lbl in ANSWER_FILTERS:
            ttk.Radiobutton(mid, text=lbl, variable=self._answer_filter,
                            value=val, style="Gray.TRadiobutton",
                            command=self._filter).pack(side="left", padx=3)

        tk.Label(mid, text="  Notas:", font=FONT_SMALL,
                 fg=TEXT_SEC, bg=GRAY_BG).pack(side="left")
        self._notes_filter = tk.BooleanVar(value=False)
        ttk.Checkbutton(mid, text="Solo con notas",
                        variable=self._notes_filter,
                        style="Gray.TCheckbutton",
                        command=self._filter).pack(side="left", padx=3)

        legend = tk.Frame(filters, bg=GRAY_BG)
        legend.pack(fill="x")
        tk.Label(legend, text="Color:", font=FONT_SMALL,
                 fg=TEXT_SEC, bg=GRAY_BG).pack(side="left")
        for text, tag in [
            ("Prospecto", "lead_capturado"),
            ("Callback", "callback"),
            ("Buzón", "voicemail"),
            ("Sin prospecto", "sin_contacto"),
        ]:
            colors = RESULTADO_TAGS[tag]
            tk.Label(legend, text=f" {text} ", font=FONT_SMALL,
                     bg=colors["background"], fg=colors["foreground"],
                     padx=6, pady=2).pack(side="left", padx=(6, 0))

    def refresh(self):
        self._all_calls = get_all_llamadas()
        self._filter()

    def _filter(self):
        self._tree.delete(*self._tree.get_children())
        query = self._search_var.get().strip().lower()
        result_filter = self._result_filter.get()
        answer_filter = self._answer_filter.get()
        notes_only = self._notes_filter.get()

        data = []
        for row in self._all_calls:
            if result_filter:
                row_group = self._row_group(row)
                if result_filter == "lead" and row_group != "lead_capturado":
                    continue
                if result_filter == "callback" and row_group != "callback":
                    continue
                if result_filter == "sin" and row.get("lead_status") == "lead":
                    continue

            if answer_filter:
                if answer_filter == "dead":
                    if row.get("line_status") != "dead":
                        continue
                elif row.get("answer_status") != answer_filter:
                    continue

            if notes_only:
                if not (row.get("notas") or "").strip():
                    continue

            if query and query not in self._search_text(row):
                continue

            data.append(row)

        self._filtered_calls = data
        for row in data:
            vals = []
            for col_id, _, _ in COLUMNS:
                v = row.get(col_id, "") or ""
                if col_id == "line_status":
                    v = LINE_LABELS.get(v, v)
                elif col_id == "answer_status":
                    v = ANSWER_LABELS.get(v, v)
                elif col_id == "retention_status":
                    v = RETENTION_LABELS.get(v, v)
                elif col_id == "lead_status":
                    v = LEAD_LABELS.get(v, v)
                elif col_id == "callback_tag":
                    v = CALLBACK_LABELS.get(v, v)
                vals.append(v)
            tag = self._row_group(row)
            self._tree.insert("", "end", values=vals,
                              iid=str(row["id"]),
                              tags=(tag,) if tag in RESULTADO_TAGS else ())
        total = len(self._all_calls)
        shown = len(data)
        self._count_var.set(f"{shown} de {total} llamadas")

    def _clear_filters(self):
        self._search_var.set("")
        self._result_filter.set("")
        self._answer_filter.set("")
        self._notes_filter.set(False)
        self._filter()

    def _row_group(self, row):
        if row.get("lead_status") == "lead" or row.get("resultado") == "lead_capturado":
            return "lead_capturado"
        callback_tag = row.get("callback_tag") or "none"
        if callback_tag == "voicemail_retry":
            return "voicemail"
        if callback_tag in ("call_later", "follow_up"):
            return "callback"
        return "sin_contacto"

    def _search_text(self, row):
        parts = []
        for value in row.values():
            parts.append(str(value or ""))
        parts.extend([
            LINE_LABELS.get(row.get("line_status"), ""),
            ANSWER_LABELS.get(row.get("answer_status"), ""),
            RETENTION_LABELS.get(row.get("retention_status"), ""),
            LEAD_LABELS.get(row.get("lead_status"), ""),
            CALLBACK_LABELS.get(row.get("callback_tag"), ""),
        ])
        return " ".join(parts).lower()

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
        data = self._filtered_calls or []
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
