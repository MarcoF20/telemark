import tkinter as tk
from tkinter import ttk
import calendar
from datetime import date, datetime
from components.theme import *


# ── RadioGroup ─────────────────────────────────────────────────────────────────

class RadioGroup(tk.Frame):
    STYLES = {
        "positive": (GREEN_LIGHT,  GREEN,  GREEN_MID),
        "negative": (RED_LIGHT,    RED,    RED_MID),
        "neutral":  (AMBER_LIGHT,  AMBER,  AMBER_MID),
        "info":     (BLUE_LIGHT,   BLUE,   BLUE_MID),
        "teal":     (TEAL_LIGHT,   TEAL,   TEAL_MID),
        "default":  (PRIMARY_LIGHT, PRIMARY, PRIMARY_MID),
    }

    def __init__(self, parent, options: list, callback=None, bg=WHITE, **kwargs):
        super().__init__(parent, bg=bg, **kwargs)
        self._value = tk.StringVar(value="")
        self._buttons = {}
        self._callback = callback
        self._bg = bg

        for opt in options:
            if isinstance(opt, str):
                label, value, style = opt, opt, "default"
            else:
                label = opt.get("label", opt.get("value", ""))
                value = opt.get("value", label)
                style = opt.get("style", "default")
            btn = tk.Button(
                self, text=label, font=FONT_BODY,
                bg=bg, fg=TEXT_SEC, relief="flat", bd=0,
                padx=12, pady=5, cursor="hand2",
                highlightbackground=BORDER, highlightthickness=1,
                highlightcolor=BORDER,
                activebackground=GRAY_BG,
                command=lambda v=value, s=style: self._select(v, s),
            )
            btn.pack(side="left", padx=(0, 5))
            self._buttons[value] = (btn, style)

    def _select(self, value, style):
        self._value.set(value)
        for v, (btn, s) in self._buttons.items():
            if v == value:
                bg, fg, hi = self.STYLES.get(style, self.STYLES["default"])
                btn.config(bg=bg, fg=fg,
                           highlightbackground=hi, highlightcolor=hi)
            else:
                btn.config(bg=self._bg, fg=TEXT_SEC,
                           highlightbackground=BORDER, highlightcolor=BORDER)
        if self._callback:
            self._callback(value)

    def get(self):
        return self._value.get()

    def set(self, value):
        entry = self._buttons.get(value)
        if entry:
            _, style = entry
            self._select(value, style)

    def reset(self):
        self._value.set("")
        for v, (btn, _) in self._buttons.items():
            btn.config(bg=self._bg, fg=TEXT_SEC,
                       highlightbackground=BORDER, highlightcolor=BORDER)


# ── LabeledEntry ───────────────────────────────────────────────────────────────

class LabeledEntry(tk.Frame):
    def __init__(self, parent, label: str, placeholder: str = "",
                 bg=WHITE, width=26, label_width=14, **kwargs):
        super().__init__(parent, bg=bg, **kwargs)
        tk.Label(self, text=label, font=FONT_BODY, fg=TEXT_SEC,
                 bg=bg, width=label_width, anchor="w").pack(side="left")
        self._var = tk.StringVar()
        self._ph = placeholder
        self._entry = ttk.Entry(self, textvariable=self._var,
                                font=FONT_BODY, width=width)
        self._entry.pack(side="left", fill="x", expand=True, ipady=3)
        if placeholder:
            self._entry.insert(0, placeholder)
            self._entry.config(foreground=TEXT_HINT)
            self._entry.bind("<FocusIn>",  lambda e: self._clear())
            self._entry.bind("<FocusOut>", lambda e: self._restore())

    def _clear(self):
        if self._entry.get() == self._ph:
            self._entry.delete(0, "end")
            self._entry.config(foreground=TEXT_PRI)

    def _restore(self):
        if not self._entry.get():
            self._entry.insert(0, self._ph)
            self._entry.config(foreground=TEXT_HINT)

    def get(self):
        v = self._var.get()
        return "" if v == self._ph else v

    def set(self, value):
        self._entry.config(foreground=TEXT_PRI)
        self._var.set(value or "")

    def clear(self):
        self._entry.delete(0, "end")
        self._restore()

    def focus(self):
        self._entry.focus_set()


# ── LabeledCombo ───────────────────────────────────────────────────────────────

class LabeledCombo(tk.Frame):
    def __init__(self, parent, label: str, values: list,
                 bg=WHITE, width=22, label_width=14, **kwargs):
        super().__init__(parent, bg=bg, **kwargs)
        tk.Label(self, text=label, font=FONT_BODY, fg=TEXT_SEC,
                 bg=bg, width=label_width, anchor="w").pack(side="left")
        self._var = tk.StringVar()
        self._combo = ttk.Combobox(self, textvariable=self._var,
                                    values=values, state="readonly",
                                    font=FONT_BODY, width=width)
        self._combo.pack(side="left")

    def get(self):
        return self._var.get()

    def set(self, value):
        self._var.set(value or "")

    def reset(self):
        self._var.set("")


# ── DatePickerEntry ────────────────────────────────────────────────────────────

class DatePickerEntry(tk.Frame):
    """Mouse-friendly date picker that stores dates as YYYY-MM-DD."""

    def __init__(self, parent, bg=WHITE, width=14, **kwargs):
        super().__init__(parent, bg=bg, **kwargs)
        self._var = tk.StringVar()
        self._selected = date.today()
        self._shown_year = self._selected.year
        self._shown_month = self._selected.month
        self._popup = None
        self._days_frame = None
        self._title_var = tk.StringVar()
        self._month_names = (
            "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
            "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre",
            "Diciembre",
        )

        self._entry = ttk.Entry(self, textvariable=self._var,
                                font=FONT_BODY, width=width, state="readonly")
        self._entry.pack(side="left", ipady=3)
        self._entry.bind("<Button-1>", lambda e: self._open_picker())

        self._button = tk.Button(
            self, text="📅", font=FONT_BODY,
            bg=GRAY_BG, fg=TEXT_PRI, relief="flat", bd=0,
            padx=8, pady=4, cursor="hand2",
            activebackground=PRIMARY_LIGHT,
            command=self._open_picker,
        )
        self._button.pack(side="left", padx=(6, 0))

    def _parse_date(self, value):
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except (TypeError, ValueError):
            return None

    def _open_picker(self):
        if self._popup and self._popup.winfo_exists():
            self._popup.lift()
            return

        current = self._parse_date(self._var.get()) or date.today()
        self._selected = current
        self._shown_year = current.year
        self._shown_month = current.month

        self._popup = tk.Toplevel(self)
        self._popup.title("Seleccionar fecha")
        self._popup.configure(bg=WHITE)
        self._popup.resizable(False, False)
        self._popup.transient(self.winfo_toplevel())
        self._popup.bind("<Escape>", lambda e: self._close_picker())
        self._popup.protocol("WM_DELETE_WINDOW", self._close_picker)

        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height() + 4
        self._popup.geometry(f"+{x}+{y}")

        shell = tk.Frame(self._popup, bg=WHITE, padx=10, pady=10,
                         highlightbackground=BORDER, highlightthickness=1)
        shell.pack(fill="both", expand=True)

        header = tk.Frame(shell, bg=WHITE)
        header.pack(fill="x")
        self._nav_button(header, "‹", self._previous_month).pack(side="left")
        tk.Label(header, textvariable=self._title_var, font=FONT_H2,
                 fg=TEXT_PRI, bg=WHITE, width=18).pack(side="left", expand=True)
        self._nav_button(header, "›", self._next_month).pack(side="right")

        weekdays = tk.Frame(shell, bg=WHITE)
        weekdays.pack(fill="x", pady=(8, 2))
        for day_name in ("Lu", "Ma", "Mi", "Ju", "Vi", "Sa", "Do"):
            tk.Label(weekdays, text=day_name, font=FONT_SMALL,
                     fg=TEXT_SEC, bg=WHITE, width=4).pack(side="left")

        self._days_frame = tk.Frame(shell, bg=WHITE)
        self._days_frame.pack()

        footer = tk.Frame(shell, bg=WHITE)
        footer.pack(fill="x", pady=(8, 0))
        tk.Button(footer, text="Hoy", font=FONT_SMALL,
                  bg=GRAY_BG, fg=TEXT_PRI, relief="flat", bd=0,
                  padx=10, pady=4, cursor="hand2",
                  activebackground=PRIMARY_LIGHT,
                  command=lambda: self._select_date(date.today())).pack(side="left")
        tk.Button(footer, text="Limpiar", font=FONT_SMALL,
                  bg=WHITE, fg=TEXT_SEC, relief="flat", bd=0,
                  padx=10, pady=4, cursor="hand2",
                  activebackground=GRAY_BG,
                  command=self.clear).pack(side="right")

        self._render_calendar()
        self._popup.grab_set()
        self._popup.focus_set()

    def _nav_button(self, parent, text, command):
        return tk.Button(parent, text=text, font=("Segoe UI", 13, "bold"),
                         bg=WHITE, fg=PRIMARY, relief="flat", bd=0,
                         width=3, cursor="hand2",
                         activebackground=PRIMARY_LIGHT,
                         activeforeground=PRIMARY_DARK,
                         command=command)

    def _previous_month(self):
        if self._shown_month == 1:
            self._shown_month = 12
            self._shown_year -= 1
        else:
            self._shown_month -= 1
        self._render_calendar()

    def _next_month(self):
        if self._shown_month == 12:
            self._shown_month = 1
            self._shown_year += 1
        else:
            self._shown_month += 1
        self._render_calendar()

    def _render_calendar(self):
        if not self._days_frame:
            return

        for child in self._days_frame.winfo_children():
            child.destroy()

        month_name = self._month_names[self._shown_month]
        self._title_var.set(f"{month_name} {self._shown_year}")

        month = calendar.Calendar(firstweekday=0).monthdatescalendar(
            self._shown_year, self._shown_month
        )
        today = date.today()

        for week in month:
            row = tk.Frame(self._days_frame, bg=WHITE)
            row.pack(fill="x")
            for day in week:
                in_month = day.month == self._shown_month
                is_selected = day == self._selected
                is_today = day == today
                bg = PRIMARY if is_selected else (PRIMARY_LIGHT if is_today else WHITE)
                fg = WHITE if is_selected else (TEXT_PRI if in_month else TEXT_HINT)

                btn = tk.Button(
                    row, text=str(day.day), font=FONT_BODY,
                    width=4, height=1, relief="flat", bd=0,
                    bg=bg, fg=fg, cursor="hand2",
                    activebackground=PRIMARY_MID,
                    activeforeground=WHITE,
                    command=lambda d=day: self._select_date(d),
                )
                btn.pack(side="left", padx=1, pady=1)

    def _select_date(self, selected):
        self.set(selected.strftime("%Y-%m-%d"))
        self._close_picker()

    def _close_picker(self):
        if self._popup and self._popup.winfo_exists():
            self._popup.grab_release()
            self._popup.destroy()
            parent = self.winfo_toplevel()
            if parent and parent.winfo_exists():
                try:
                    parent.grab_set()
                except tk.TclError:
                    pass
        self._popup = None

    def get(self):
        return self._var.get()

    def set(self, value):
        parsed = self._parse_date(value)
        if parsed:
            self._selected = parsed
            self._shown_year = parsed.year
            self._shown_month = parsed.month
            self._var.set(parsed.strftime("%Y-%m-%d"))
        else:
            self._var.set("")

    def clear(self):
        self._var.set("")
        self._close_picker()


# ── LabeledSpinbox ─────────────────────────────────────────────────────────────

class LabeledSpinbox(tk.Frame):
    def __init__(self, parent, label: str, from_=1, to=20,
                 bg=WHITE, label_width=14, **kwargs):
        super().__init__(parent, bg=bg, **kwargs)
        tk.Label(self, text=label, font=FONT_BODY, fg=TEXT_SEC,
                 bg=bg, width=label_width, anchor="w").pack(side="left")
        self._var = tk.StringVar(value="")
        self._spin = tk.Spinbox(self, from_=from_, to=to,
                                textvariable=self._var,
                                font=FONT_BODY, width=6,
                                bg=GRAY_BG, fg=TEXT_PRI,
                                relief="flat",
                                highlightbackground=BORDER,
                                highlightthickness=1)
        self._spin.pack(side="left")

    def get(self):
        v = self._var.get()
        try:
            return int(v)
        except (ValueError, TypeError):
            return None

    def set(self, value):
        self._var.set(str(value) if value is not None else "")

    def reset(self):
        self._var.set("")


# ── StatCard ───────────────────────────────────────────────────────────────────

class StatCard(tk.Frame):
    def __init__(self, parent, label: str, value="0",
                 color=TEXT_PRI, bg=WHITE, **kwargs):
        super().__init__(parent, bg=bg, padx=14, pady=12,
                         highlightbackground=BORDER, highlightthickness=1,
                         **kwargs)
        self._num_var = tk.StringVar(value=str(value))
        tk.Label(self, textvariable=self._num_var, font=FONT_BIG,
                 fg=color, bg=bg).pack()
        tk.Label(self, text=label, font=FONT_SMALL,
                 fg=TEXT_SEC, bg=bg).pack()

    def update_value(self, value):
        self._num_var.set(str(value))


# ── FunnelBar ──────────────────────────────────────────────────────────────────

class FunnelBar(tk.Frame):
    def __init__(self, parent, label: str, value: int, total: int,
                 color=PRIMARY, bg=WHITE, **kwargs):
        super().__init__(parent, bg=bg, **kwargs)
        self._color = color
        self._total = max(total, 1)
        self._value = value

        hdr = tk.Frame(self, bg=bg)
        hdr.pack(fill="x")
        tk.Label(hdr, text=label, font=FONT_SMALL, fg=TEXT_SEC, bg=bg).pack(side="left")
        self._val_lbl = tk.Label(hdr, text=str(value), font=("Segoe UI", 9, "bold"),
                                  fg=TEXT_PRI, bg=bg)
        self._val_lbl.pack(side="right")

        self._canvas = tk.Canvas(self, height=10, bg=GRAY_CARD,
                                  highlightthickness=0, bd=0)
        self._canvas.pack(fill="x", pady=(3, 0))
        self._canvas.bind("<Configure>", lambda e: self._draw())

    def _draw(self):
        w = self._canvas.winfo_width()
        h = 10
        r = 5
        self._canvas.delete("all")
        # bg track
        self._canvas.create_oval(0, 0, 2*r, h, fill=GRAY_CARD, outline="")
        self._canvas.create_oval(w-2*r, 0, w, h, fill=GRAY_CARD, outline="")
        self._canvas.create_rectangle(r, 0, w-r, h, fill=GRAY_CARD, outline="")
        # fill
        fw = max(int(w * self._value / self._total), 0)
        if fw > 0:
            fr = min(r, fw)
            self._canvas.create_oval(0, 0, 2*fr, h, fill=self._color, outline="")
            if fw > fr:
                self._canvas.create_oval(fw-2*fr, 0, fw, h, fill=self._color, outline="")
                self._canvas.create_rectangle(fr, 0, fw-fr, h, fill=self._color, outline="")

    def update(self, value, total):
        self._value = value
        self._total = max(total, 1)
        self._val_lbl.config(text=str(value))
        self._draw()


# ── StepIndicator ──────────────────────────────────────────────────────────────

class StepIndicator(tk.Frame):
    STEPS = ["número", "estado", "retención", "prospecto"]

    def __init__(self, parent, bg=WHITE, **kwargs):
        super().__init__(parent, bg=bg, **kwargs)
        self._labels = []
        self._bg = bg
        for i, step in enumerate(self.STEPS):
            lbl = tk.Label(self, text=f"  {step}  ", font=FONT_SMALL,
                           padx=8, pady=4, bg=GRAY_BG, fg=TEXT_SEC,
                           highlightbackground=BORDER, highlightthickness=1)
            lbl.pack(side="left")
            self._labels.append(lbl)
            if i < len(self.STEPS) - 1:
                tk.Label(self, text=" › ", fg=GRAY_MID, bg=bg,
                         font=FONT_BODY).pack(side="left")
        self.set_step(0)

    def set_step(self, index: int):
        for i, lbl in enumerate(self._labels):
            if i < index:
                lbl.config(bg=GREEN_LIGHT, fg=GREEN,
                            highlightbackground=GREEN_MID)
            elif i == index:
                lbl.config(bg=PRIMARY, fg=WHITE,
                            highlightbackground=PRIMARY_DARK)
            else:
                lbl.config(bg=GRAY_BG, fg=TEXT_SEC,
                            highlightbackground=BORDER)


# ── SectionHeader ──────────────────────────────────────────────────────────────

class SectionHeader(tk.Frame):
    def __init__(self, parent, text: str, bg=WHITE, **kwargs):
        super().__init__(parent, bg=bg, **kwargs)
        tk.Label(self, text=text.upper(),
                 font=("Segoe UI", 8, "bold"),
                 fg=TEXT_HINT, bg=bg,).pack(side="left")
        tk.Frame(self, bg=BORDER, height=1).pack(
            side="left", fill="x", expand=True, padx=(8, 0), pady=7)


# ── NumberDisplay ──────────────────────────────────────────────────────────────

class NumberDisplay(tk.Frame):
    """Shows the current number with +/- controls and counter."""

    def __init__(self, parent, on_change=None, bg=WHITE, **kwargs):
        super().__init__(parent, bg=bg, **kwargs)
        self._on_change = on_change
        self._bg = bg
        self._number = tk.StringVar(value="")
        self._count  = tk.IntVar(value=0)
        self._locked = False
        self._build()

    def _build(self):
        # Number entry row
        top = tk.Frame(self, bg=self._bg)
        top.pack(fill="x")

        tk.Label(top, text="Número base", font=FONT_SMALL,
                 fg=TEXT_SEC, bg=self._bg).pack(side="left")
        self._count_lbl = tk.Label(top, text="0 marcadas",
                                    font=FONT_SMALL, fg=TEXT_HINT, bg=self._bg)
        self._count_lbl.pack(side="right")

        mid = tk.Frame(self, bg=self._bg)
        mid.pack(fill="x", pady=(6, 0))

        validate_digits = (self.register(self._is_digits_or_empty), "%P")
        self._entry = ttk.Entry(mid, textvariable=self._number,
                                font=("Segoe UI", 16), width=18,
                                validate="key",
                                validatecommand=validate_digits)
        self._entry.pack(side="left", ipady=6)
        self._entry.bind("<Return>", lambda e: self._confirm())

        self._confirm_btn = tk.Button(mid, text="✓", font=FONT_H2,
                  bg=PRIMARY, fg=WHITE, relief="flat", bd=0,
                  padx=12, pady=6, cursor="hand2",
                  activebackground=PRIMARY_MID, activeforeground=WHITE,
                  command=self._confirm)
        self._confirm_btn.pack(side="left", padx=(6, 0))

        self._change_btn = tk.Button(mid, text="Cambiar numero base", font=FONT_BODY,
                  bg=GRAY_BG, fg=TEXT_PRI, relief="flat", bd=0,
                  padx=10, pady=6, cursor="hand2",
                  highlightbackground=BORDER, highlightthickness=1,
                  command=self.unlock)

        tk.Button(mid, text="+1", font=FONT_BODY,
                  bg=GRAY_BG, fg=TEXT_PRI, relief="flat", bd=0,
                  padx=10, pady=6, cursor="hand2",
                  highlightbackground=BORDER, highlightthickness=1,
                  command=self._increment).pack(side="left", padx=(4, 0))

        self._confirmed_lbl = tk.Label(self, text="",
                                        font=("Segoe UI", 11, "bold"),
                                        fg=PRIMARY, bg=self._bg)
        self._confirmed_lbl.pack(anchor="w", pady=(4, 0))

    def _confirm(self):
        num = self._digits_only(self._number.get())
        self._number.set(num)
        if num:
            self._confirmed_lbl.config(text=f"✓  {num}")
            self.lock()
            if self._on_change:
                self._on_change(num, confirmed=True)

    def _increment(self):
        raw = self._digits_only(self._number.get())
        if not raw:
            return
        new_val = str(int(raw) + 1).zfill(len(raw))
        self._number.set(new_val)
        self._confirmed_lbl.config(text=f"✓  {new_val}")
        self.lock()
        self._count.set(self._count.get() + 1)
        self._count_lbl.config(text=f"{self._count.get()} marcadas")
        if self._on_change:
            self._on_change(new_val, confirmed=True)

    def get_number(self) -> str:
        return self._confirmed_lbl.cget("text").replace("✓", "").strip()

    def get_raw(self) -> str:
        return self._digits_only(self._number.get())

    def set_number(self, value: str):
        value = self._digits_only(value)
        self._number.set(value)
        if value:
            self._confirmed_lbl.config(text=f"✓  {value}")
            self.lock()

    def _is_digits_or_empty(self, value: str) -> bool:
        return value == "" or value.isdigit()

    def _digits_only(self, value: str) -> str:
        return "".join(ch for ch in str(value or "") if ch.isdigit())

    def lock(self):
        self._locked = True
        self._entry.configure(state="disabled")
        self._confirm_btn.configure(state="disabled", cursor="")
        if not self._change_btn.winfo_ismapped():
            self._change_btn.pack(side="left", padx=(4, 0))

    def unlock(self):
        self._locked = False
        self._entry.configure(state="normal")
        self._confirm_btn.configure(state="normal", cursor="hand2")
        self._change_btn.pack_forget()
        self._entry.focus_set()
        self._entry.selection_range(0, "end")

    def reset_count(self):
        self._count.set(0)
        self._count_lbl.config(text="0 marcadas")

    def get_count(self) -> int:
        return self._count.get()
