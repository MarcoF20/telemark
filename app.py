import tkinter as tk
from tkinter import ttk, messagebox
import sys
import components.theme as theme
from components.theme import *
from components.theme import apply_theme, set_primary_color
from data.database import get_config
from views.marcador    import MarcadorView
from views.dashboard   import DashboardView
from views.leads       import LeadsView
from views.seguimiento import SeguimientoView
from views.historial   import HistorialView
from views.apariencia  import AparienciaView, COLOR_CONFIG_KEY


NAV_ITEMS = [
    ("marcador",     "📞  Marcador",      MarcadorView),
    ("dashboard",    "📊  Métricas",     DashboardView),
    ("leads",        "👤  Prospectos",         LeadsView),
    ("seguimiento",  "📅  Seguimientos",  SeguimientoView),
    ("historial",    "📋  Historial",     HistorialView),
    ("apariencia",   "🎨  Apariencia",    AparienciaView),
]


class App(tk.Tk):

    def __init__(self):
        super().__init__()
        self._load_saved_theme()
        self.title("TeleMark")
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

    def _load_saved_theme(self):
        color = get_config(COLOR_CONFIG_KEY, DEFAULT_PRIMARY)
        set_primary_color(color)
        self._sync_theme_globals()

    def _sync_theme_globals(self):
        color_names = (
            "DEFAULT_PRIMARY",
            "PRIMARY",
            "PRIMARY_LIGHT",
            "PRIMARY_MID",
            "PRIMARY_DARK",
            "ON_PRIMARY",
        )
        modules = [
            module for name, module in sys.modules.items()
            if name == __name__ or name.startswith("views.") or name.startswith("components.")
        ]
        for module in modules:
            for name in color_names:
                if hasattr(module, name):
                    setattr(module, name, getattr(theme, name))

        widgets = sys.modules.get("components.widgets")
        if widgets and hasattr(widgets, "RadioGroup"):
            widgets.RadioGroup.STYLES["default"] = (
                theme.PRIMARY_LIGHT,
                theme.PRIMARY,
                theme.PRIMARY_MID,
            )

    def _build(self):
        container = tk.Frame(self, bg=WHITE)
        container.pack(fill="both", expand=True)

        # Sidebar
        sidebar = tk.Frame(container, bg=GRAY_BG, width=168)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        # Logo block
        logo = tk.Frame(sidebar, bg=PRIMARY, padx=14, pady=16)
        logo.pack(fill="x")
        tk.Label(logo, text="TeleMark", font=("Segoe UI", 14, "bold"),
                 fg=ON_PRIMARY, bg=PRIMARY).pack(anchor="w")
        tk.Label(logo, text="funeraria · local",
                 font=FONT_SMALL, fg=ON_PRIMARY, bg=PRIMARY).pack(anchor="w")

        # Nav
        nav = tk.Frame(sidebar, bg=GRAY_BG, padx=8, pady=10)
        nav.pack(fill="x")
        for key, label, _ in NAV_ITEMS:
            btn = tk.Button(
                nav, text=label, font=FONT_BODY,
                bg=GRAY_BG, fg=TEXT_SEC,
                relief="flat", bd=0, anchor="w",
                padx=10, pady=8, cursor="hand2",
                activebackground=PRIMARY_LIGHT,
                activeforeground=PRIMARY,
                command=lambda k=key: self._navigate(k),
            )
            btn.pack(fill="x", pady=1)
            self._nav_btns[key] = btn

        # Version
        tk.Label(sidebar, text="v1.1  ·  uso local",
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
            if key == "apariencia":
                kwargs["on_theme_saved"] = self._on_theme_saved
            self._views[key] = ViewClass(self._main, **kwargs)
            self._dirty_views.discard(key)

        self._views[key].pack(fill="both", expand=True)
        if key in self._dirty_views and hasattr(self._views[key], "refresh"):
            self._views[key].refresh()
            self._dirty_views.discard(key)
        self._nav_btns[key].config(
            bg=PRIMARY_LIGHT, fg=PRIMARY,
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

    def _on_theme_saved(self, color: str):
        set_primary_color(color)
        self._sync_theme_globals()
        apply_theme(self)

        active = self._active or "apariencia"
        for child in self.winfo_children():
            child.destroy()

        self._views.clear()
        self._nav_btns.clear()
        self._active = None
        self._dirty_views.clear()
        self.configure(bg=WHITE)
        self._build()
        self._navigate(active)
        messagebox.showinfo(
            "Color guardado",
            "El color principal se guardó correctamente.",
            parent=self,
        )
