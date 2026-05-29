import tkinter as tk
from tkinter import ttk
from components.theme import *
from components.theme import apply_theme
from views.marcador    import MarcadorView
from views.dashboard   import DashboardView
from views.leads       import LeadsView
from views.seguimiento import SeguimientoView
from views.historial   import HistorialView


NAV_ITEMS = [
    ("marcador",     "📞  Marcador",      MarcadorView),
    ("dashboard",    "📊  Dashboard",     DashboardView),
    ("leads",        "👤  Leads",         LeadsView),
    ("seguimiento",  "📅  Seguimientos",  SeguimientoView),
    ("historial",    "📋  Historial",     HistorialView),
]


class App(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("TeleAssist")
        self.geometry("1120x700")
        self.minsize(900, 580)
        self.configure(bg=WHITE)
        apply_theme(self)

        self._views: dict[str, tk.Frame] = {}
        self._nav_btns: dict[str, tk.Button] = {}
        self._active = None
        self._dirty_views = set()

        self._build()
        self._navigate("marcador")

    def _build(self):
        container = tk.Frame(self, bg=WHITE)
        container.pack(fill="both", expand=True)

        # Sidebar
        sidebar = tk.Frame(container, bg=GRAY_BG, width=168)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        # Logo block
        logo = tk.Frame(sidebar, bg=PURPLE, padx=14, pady=16)
        logo.pack(fill="x")
        tk.Label(logo, text="TeleAssist", font=("Segoe UI", 14, "bold"),
                 fg=WHITE, bg=PURPLE).pack(anchor="w")
        tk.Label(logo, text="funeraria · local",
                 font=FONT_SMALL, fg="#C5C1F0", bg=PURPLE).pack(anchor="w")

        # Nav
        nav = tk.Frame(sidebar, bg=GRAY_BG, padx=8, pady=10)
        nav.pack(fill="x")
        for key, label, _ in NAV_ITEMS:
            btn = tk.Button(
                nav, text=label, font=FONT_BODY,
                bg=GRAY_BG, fg=TEXT_SEC,
                relief="flat", bd=0, anchor="w",
                padx=10, pady=8, cursor="hand2",
                activebackground=PURPLE_LIGHT,
                activeforeground=PURPLE,
                command=lambda k=key: self._navigate(k),
            )
            btn.pack(fill="x", pady=1)
            self._nav_btns[key] = btn

        # Version
        tk.Label(sidebar, text="v2.0  ·  uso local",
                 font=("Segoe UI", 8), fg=GRAY_MID,
                 bg=GRAY_BG, padx=14, pady=8).pack(
                     side="bottom", anchor="w")

        # Divider
        tk.Frame(container, bg=BORDER, width=1).pack(side="left", fill="y")

        # Content
        self._main = tk.Frame(container, bg=WHITE)
        self._main.pack(side="left", fill="both", expand=True)

    def _navigate(self, key: str):
        if self._active == key:
            view = self._views.get(key)
            if view and hasattr(view, "refresh"):
                view.refresh()
            return

        if self._active and self._active in self._views:
            self._views[self._active].pack_forget()
            self._nav_btns[self._active].config(
                bg=GRAY_BG, fg=TEXT_SEC,
                font=FONT_BODY)

        if key not in self._views:
            _, _, ViewClass = next(n for n in NAV_ITEMS if n[0] == key)
            kwargs = {}
            if key == "marcador":
                kwargs["on_llamada_saved"] = self._on_saved
            if key == "leads":
                kwargs["on_refresh"] = self._on_saved
            self._views[key] = ViewClass(self._main, **kwargs)
            self._dirty_views.discard(key)

        self._views[key].pack(fill="both", expand=True)
        if key in self._dirty_views and hasattr(self._views[key], "refresh"):
            self._views[key].refresh()
            self._dirty_views.discard(key)
        self._nav_btns[key].config(
            bg=PURPLE_LIGHT, fg=PURPLE,
            font=("Segoe UI", 10, "bold"))
        self._active = key

    def _on_saved(self):
        refreshable = {"dashboard", "leads", "seguimiento", "historial"}
        self._dirty_views.update(refreshable - {"marcador"})

        if self._active == "marcador":
            return

        view = self._views.get(self._active)
        if view and hasattr(view, "refresh"):
            view.refresh()
            self._dirty_views.discard(self._active)
