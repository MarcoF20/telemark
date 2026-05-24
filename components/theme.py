import tkinter as tk
from tkinter import ttk

# ── Palette ────────────────────────────────────────────────────────────────────
PURPLE       = "#534AB7"
PURPLE_LIGHT = "#EEEDFE"
PURPLE_MID   = "#7F77DD"
PURPLE_DARK  = "#3C3489"
GREEN        = "#3B6D11"
GREEN_LIGHT  = "#EAF3DE"
GREEN_MID    = "#639922"
RED          = "#A32D2D"
RED_LIGHT    = "#FCEBEB"
RED_MID      = "#E24B4A"
AMBER        = "#854F0B"
AMBER_LIGHT  = "#FAEEDA"
AMBER_MID    = "#BA7517"
BLUE         = "#185FA5"
BLUE_LIGHT   = "#E6F1FB"
BLUE_MID     = "#378ADD"
TEAL         = "#0F6E56"
TEAL_LIGHT   = "#E1F5EE"
TEAL_MID     = "#1D9E75"
GRAY_BG      = "#F4F3F0"
GRAY_CARD    = "#EFEFEB"
GRAY_MID     = "#C4C3BC"
GRAY_DARK    = "#5F5E5A"
WHITE        = "#FFFFFF"
BORDER       = "#E2E1DC"
BORDER_MED   = "#CECDC7"
TEXT_PRI     = "#1A1A18"
TEXT_SEC     = "#6B6B67"
TEXT_HINT    = "#A5A49F"

# ── Radius ─────────────────────────────────────────────────────────────────────
R_SM  = 6
R_MD  = 10
R_LG  = 14
R_XL  = 18

# ── Fonts ──────────────────────────────────────────────────────────────────────
FONT_TITLE  = ("Segoe UI", 14, "bold")
FONT_H2     = ("Segoe UI", 11, "bold")
FONT_BODY   = ("Segoe UI", 10)
FONT_SMALL  = ("Segoe UI", 9)
FONT_MONO   = ("Consolas", 11)
FONT_BIG    = ("Segoe UI", 22, "bold")
FONT_MED    = ("Segoe UI", 16, "bold")

# ── Spacing ────────────────────────────────────────────────────────────────────
PAD    = 16
PAD_S  = 8
PAD_XS = 4


def apply_theme(root: tk.Tk):
    style = ttk.Style(root)
    style.theme_use("clam")

    # Frames
    style.configure("TFrame",         background=WHITE)
    style.configure("Card.TFrame",    background=WHITE,    relief="flat")
    style.configure("Gray.TFrame",    background=GRAY_BG)
    style.configure("Sidebar.TFrame", background=GRAY_BG)

    # Labels
    style.configure("TLabel",        background=WHITE,   foreground=TEXT_PRI, font=FONT_BODY)
    style.configure("Sec.TLabel",    background=WHITE,   foreground=TEXT_SEC, font=FONT_SMALL)
    style.configure("Hint.TLabel",   background=WHITE,   foreground=TEXT_HINT,font=FONT_SMALL)
    style.configure("Gray.TLabel",   background=GRAY_BG, foreground=TEXT_PRI, font=FONT_BODY)
    style.configure("GraySec.TLabel",background=GRAY_BG, foreground=TEXT_SEC, font=FONT_SMALL)
    style.configure("Title.TLabel",  background=WHITE,   foreground=TEXT_PRI, font=FONT_TITLE)
    style.configure("H2.TLabel",     background=WHITE,   foreground=TEXT_PRI, font=FONT_H2)
    style.configure("Big.TLabel",    background=WHITE,   foreground=TEXT_PRI, font=FONT_BIG)
    style.configure("GrayBig.TLabel",background=GRAY_BG, foreground=TEXT_PRI, font=FONT_BIG)
    style.configure("GrayMed.TLabel",background=GRAY_BG, foreground=TEXT_PRI, font=FONT_MED)

    # Separator
    style.configure("TSeparator", background=BORDER)

    # Entry
    style.configure("TEntry",
        fieldbackground=GRAY_BG, foreground=TEXT_PRI, font=FONT_BODY,
        bordercolor=BORDER, insertcolor=TEXT_PRI,
        relief="flat", padding=(8, 5))
    style.map("TEntry",
        bordercolor=[("focus", PURPLE)],
        fieldbackground=[("focus", WHITE)])

    # Scrollbar
    style.configure("TScrollbar",
        background=GRAY_BG, troughcolor=GRAY_BG,
        bordercolor=GRAY_BG, arrowcolor=GRAY_MID,
        relief="flat")
    style.map("TScrollbar", background=[("active", GRAY_MID)])

    # Treeview
    style.configure("Treeview",
        background=WHITE, foreground=TEXT_PRI,
        fieldbackground=WHITE, font=FONT_BODY,
        rowheight=30, bordercolor=BORDER, relief="flat")
    style.configure("Treeview.Heading",
        background=GRAY_BG, foreground=TEXT_SEC,
        font=FONT_SMALL, relief="flat", bordercolor=BORDER)
    style.map("Treeview",
        background=[("selected", PURPLE_LIGHT)],
        foreground=[("selected", PURPLE)])

    # Radiobutton
    style.configure("TRadiobutton",
        background=WHITE, foreground=TEXT_PRI, font=FONT_BODY)
    style.configure("Gray.TRadiobutton",
        background=GRAY_BG, foreground=TEXT_PRI, font=FONT_BODY)

    # Checkbutton
    style.configure("TCheckbutton",
        background=WHITE, foreground=TEXT_PRI, font=FONT_BODY)

    # Combobox
    style.configure("TCombobox",
        fieldbackground=GRAY_BG, foreground=TEXT_PRI,
        font=FONT_BODY, selectbackground=PURPLE_LIGHT,
        selectforeground=PURPLE)
    style.map("TCombobox",
        fieldbackground=[("readonly", GRAY_BG)],
        selectbackground=[("readonly", PURPLE_LIGHT)])

    # Notebook (tabs)
    style.configure("TNotebook",
        background=GRAY_BG, bordercolor=BORDER, tabmargins=[0, 0, 0, 0])
    style.configure("TNotebook.Tab",
        background=GRAY_BG, foreground=TEXT_SEC,
        font=FONT_BODY, padding=[14, 7], bordercolor=BORDER)
    style.map("TNotebook.Tab",
        background=[("selected", WHITE)],
        foreground=[("selected", PURPLE)],
        font=[("selected", ("Segoe UI", 10, "bold"))])


# ── Rounded helpers ────────────────────────────────────────────────────────────

def rounded_frame(parent, radius=R_MD, bg=WHITE, bd_color=BORDER, **kwargs):
    """Canvas-backed frame with rounded corners."""
    outer = tk.Canvas(parent, bg=parent.cget("bg"),
                      highlightthickness=0, **kwargs)

    def _draw(event=None):
        w = outer.winfo_width()
        h = outer.winfo_height()
        outer.delete("all")
        r = radius
        outer.create_arc(0, 0, 2*r, 2*r, start=90, extent=90,
                         fill=bg, outline=bd_color)
        outer.create_arc(w-2*r, 0, w, 2*r, start=0, extent=90,
                         fill=bg, outline=bd_color)
        outer.create_arc(0, h-2*r, 2*r, h, start=180, extent=90,
                         fill=bg, outline=bd_color)
        outer.create_arc(w-2*r, h-2*r, w, h, start=270, extent=90,
                         fill=bg, outline=bd_color)
        outer.create_rectangle(r, 0, w-r, h, fill=bg, outline=bg)
        outer.create_rectangle(0, r, w, h-r, fill=bg, outline=bg)
        # border lines
        outer.create_line(r, 0, w-r, 0, fill=bd_color)
        outer.create_line(r, h, w-r, h, fill=bd_color)
        outer.create_line(0, r, 0, h-r, fill=bd_color)
        outer.create_line(w, r, w, h-r, fill=bd_color)

    outer.bind("<Configure>", _draw)
    return outer


def card(parent, bg=WHITE, padx=PAD, pady=PAD_S, **kwargs):
    """Simple card frame with border and rounded look via highlightbackground."""
    f = tk.Frame(parent, bg=bg, padx=padx, pady=pady,
                 highlightbackground=BORDER, highlightthickness=1, **kwargs)
    return f


def pill_label(parent, text, bg, fg, font=None):
    lbl = tk.Label(parent, text=f"  {text}  ",
                   bg=bg, fg=fg,
                   font=font or FONT_SMALL,
                   padx=2, pady=2)
    return lbl
