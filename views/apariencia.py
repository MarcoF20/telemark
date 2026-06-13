import tkinter as tk
from tkinter import messagebox

from components.theme import *
from data.database import get_config, set_config


COLOR_CONFIG_KEY = "tema_color_principal"


class AparienciaView(tk.Frame):
    PALETTE = [
        ["#B91C1C", "#C2410C", "#B45309", "#A16207",
         "#15803D", "#0F766E", "#1D4ED8", "#6D28D9"],
        ["#DC2626", "#EA580C", "#D97706", "#CA8A04",
         "#16A34A", "#0D9488", "#2563EB", "#7C3AED"],
        ["#EF4444", "#F97316", "#F59E0B", "#EAB308",
         "#22C55E", "#14B8A6", "#3B82F6", "#8B5CF6"],
        ["#F87171", "#FB923C", "#FBBF24", "#FACC15",
         "#4ADE80", "#2DD4BF", "#60A5FA", "#A78BFA"],
    ]

    def __init__(self, parent, on_theme_saved=None):
        super().__init__(parent, bg=WHITE)
        self._on_theme_saved = on_theme_saved
        self._saved_color = get_config(COLOR_CONFIG_KEY, DEFAULT_PRIMARY)
        if not is_valid_hex_color(self._saved_color):
            self._saved_color = DEFAULT_PRIMARY
        self._selected_color = self._saved_color.upper()
        self._swatches = []
        self._build()

    def _build(self):
        outer = tk.Frame(self, bg=WHITE)
        outer.pack(fill="both", expand=True)

        content = tk.Frame(outer, bg=WHITE, padx=PAD, pady=PAD)
        content.place(relx=0.5, rely=0.46, anchor="center")

        tk.Label(
            content,
            text="Apariencia",
            font=("Segoe UI", 18, "bold"),
            fg=TEXT_PRI,
            bg=WHITE,
        ).pack(pady=(0, 12))

        tk.Label(
            content,
            text="Tu color principal actual",
            font=FONT_H2,
            fg=TEXT_PRI,
            bg=WHITE,
        ).pack(pady=(0, 10))

        self._color_preview = tk.Frame(
            content,
            bg=self._selected_color,
            width=128,
            height=128,
            highlightbackground=BORDER_MED,
            highlightthickness=1,
        )
        self._color_preview.pack(pady=(0, 10))
        self._color_preview.pack_propagate(False)

        self._color_lbl = tk.Label(
            content,
            text="Color seleccionado",
            font=FONT_MED,
            fg=TEXT_PRI,
            bg=WHITE,
        )
        self._color_lbl.pack(pady=(0, 14))

        tk.Label(
            content,
            text="Elige un color con un clic y luego guarda el cambio.",
            font=FONT_BODY,
            fg=TEXT_SEC,
            bg=WHITE,
        ).pack(pady=(0, 12))

        palette = tk.Frame(content, bg=WHITE)
        palette.pack(pady=(0, 20))
        for row in self.PALETTE:
            row_frame = tk.Frame(palette, bg=WHITE)
            row_frame.pack()
            for color in row:
                self._add_swatch(row_frame, color)
        self._refresh_swatches()

        actions = tk.Frame(content, bg=WHITE)
        actions.pack()

        tk.Button(
            actions,
            text="Guardar color",
            font=("Segoe UI", 11, "bold"),
            bg=PRIMARY,
            fg=ON_PRIMARY,
            relief="flat",
            bd=0,
            padx=22,
            pady=10,
            cursor="hand2",
            activebackground=PRIMARY_MID,
            activeforeground=ON_PRIMARY,
            command=self._save,
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            actions,
            text="Usar color original",
            font=("Segoe UI", 11),
            bg=PRIMARY_LIGHT,
            fg=PRIMARY_DARK,
            relief="flat",
            bd=0,
            padx=18,
            pady=10,
            cursor="hand2",
            activebackground=GRAY_BG,
            activeforeground=PRIMARY_DARK,
            highlightbackground=PRIMARY_MID,
            highlightthickness=1,
            command=self._reset_default,
        ).pack(side="left")

    def _add_swatch(self, parent, color: str):
        shell = tk.Frame(parent, bg=BORDER_MED, padx=3, pady=3)
        shell.pack(side="left", padx=4, pady=4)
        btn = tk.Button(
            shell,
            text="",
            font=("Segoe UI", 14, "bold"),
            bg=color,
            fg=self._text_on_color(color),
            width=4,
            height=2,
            relief="flat",
            bd=0,
            cursor="hand2",
            activebackground=color,
            activeforeground=self._text_on_color(color),
            command=lambda c=color: self._set_selected_color(c),
        )
        btn.pack()
        self._swatches.append((shell, btn, color.upper()))

    def _set_selected_color(self, color: str):
        self._selected_color = color.upper()
        self._color_preview.config(bg=self._selected_color)
        self._refresh_swatches()

    def _refresh_swatches(self):
        for shell, btn, color in self._swatches:
            selected = color == self._selected_color
            shell.config(bg=TEXT_PRI if selected else BORDER_MED)
            btn.config(text="✓" if selected else "")

    def _text_on_color(self, color: str):
        color = color.lstrip("#")
        red, green, blue = (int(color[i:i + 2], 16) for i in (0, 2, 4))
        luminance = (red * 0.299 + green * 0.587 + blue * 0.114) / 255
        return TEXT_PRI if luminance > 0.62 else WHITE

    def _reset_default(self):
        self._set_selected_color(DEFAULT_PRIMARY)

    def _save(self):
        set_config(COLOR_CONFIG_KEY, self._selected_color)
        self._saved_color = self._selected_color
        if self._on_theme_saved:
            self._on_theme_saved(self._selected_color)
        else:
            messagebox.showinfo(
                "Color guardado",
                "El color principal se guardó correctamente.",
                parent=self,
            )
