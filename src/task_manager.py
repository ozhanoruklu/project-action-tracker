"""
LYBIP Action Tracker - V9 Final
tasks.json is always read/written from the same folder as the .exe or .py
Requires:
  pip install customtkinter
  pip install tkcalendar
"""

import json
import os
import sys
import customtkinter as ctk
from datetime import datetime, date
from tkinter import messagebox

try:
    from tkcalendar import DateEntry
    CALENDAR_AVAILABLE = True
except ImportError:
    CALENDAR_AVAILABLE = False

# ---------- DATA FILE ----------
# sys.executable = path to the .exe (when packaged) or python.exe (when running as .py)
# We use the folder that contains the .exe or the .py — whichever is running.
if getattr(sys, 'frozen', False):
    # Running as a PyInstaller .exe
    _BASE = os.path.dirname(sys.executable)
else:
    # Running as a normal .py script
    _BASE = os.path.dirname(os.path.abspath(__file__))

DATA_FILE = os.path.join(_BASE, "tasks.json")

# ── Timestamp helpers ─────────────────────────────────────
def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M")

def ensure_timestamps(task):
    now = now_str()
    task.setdefault("created_at",    task.get("created", now))
    task.setdefault("updated_at",    task.get("created", now))
    task.setdefault("waiting_since", "")
    task.setdefault("completed_at",  "")
    task.setdefault("history",       [])
    if task.get("timing") == "This week":
        task["timing"] = "No deadline"
    return task

def stamp(task, new_status):
    now        = now_str()
    old_status = task.get("status", "")
    task["updated_at"] = now
    if new_status == "Waiting":
        task["waiting_since"] = now
        task["completed_at"]  = ""
    elif new_status == "Done":
        task["completed_at"]  = now
        task["waiting_since"] = ""
    elif new_status == "Open":
        task["waiting_since"] = ""
        task["completed_at"]  = ""
    if old_status != new_status:
        task["history"].append(f"{now}  —  Status changed to {new_status}")
    task["status"] = new_status
    return task

# ── Data I/O ──────────────────────────────────────────────
def load_tasks():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                tasks = json.load(f)
            return [ensure_timestamps(t) for t in tasks]
        except Exception:
            return []
    return []

def save_tasks(tasks):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(tasks, f, indent=2, ensure_ascii=False)
    except Exception as e:
        messagebox.showerror("Save Error",
                             f"Could not save tasks.\n\n{e}\n\nPath: {DATA_FILE}")

# ── Sort helpers ──────────────────────────────────────────
PRIORITY_RANK  = {"High": 0, "Medium": 1, "Low": 2}
TIMING_OPTIONS = ["No deadline", "Today", "Specific date"]

def _date_rank(task):
    timing   = task.get("timing", "")
    date_str = task.get("date", "").strip()
    if timing == "Today":
        return (0, datetime.min)
    if timing == "Specific date" and date_str:
        try:
            return (1, datetime.strptime(date_str, "%d/%m/%Y"))
        except ValueError:
            pass
    return (9, datetime.max)

def sort_key_date_priority(task):
    tier, dt = _date_rank(task)
    prio     = PRIORITY_RANK.get(task.get("priority", "Medium"), 1)
    return (tier, dt, prio)

def sort_key_priority_date(task):
    tier, dt = _date_rank(task)
    prio     = PRIORITY_RANK.get(task.get("priority", "Medium"), 1)
    return (prio, tier, dt)

# ---------- THEME ----------
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

PRIORITY_COLORS = {"High": "#e74c3c", "Medium": "#e67e22", "Low": "#27ae60"}
STATUS_COLORS   = {"Open": "#2980b9", "Waiting": "#8e44ad", "Done": "#95a5a6"}
STATUS_ICONS    = {"Open": "🔵", "Waiting": "🟣", "Done": "✅"}


# ═══════════════════════════════════════════════════════════
#  TOOLTIP
# ═══════════════════════════════════════════════════════════
class Tooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text   = text
        self.tw     = None
        widget.bind("<Enter>", self._show)
        widget.bind("<Leave>", self._hide)

    def _show(self, _=None):
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self.tw = ctk.CTkToplevel(self.widget)
        self.tw.wm_overrideredirect(True)
        self.tw.wm_geometry(f"+{x}+{y}")
        ctk.CTkLabel(self.tw, text=self.text,
                     fg_color="#2c3e50", text_color="white",
                     corner_radius=4, font=ctk.CTkFont(size=11),
                     padx=8, pady=4).pack()

    def _hide(self, _=None):
        if self.tw:
            self.tw.destroy()
            self.tw = None


# ═══════════════════════════════════════════════════════════
#  HISTORY WINDOW
# ═══════════════════════════════════════════════════════════
class HistoryWindow(ctk.CTkToplevel):
    def __init__(self, parent, task):
        super().__init__(parent)
        self.title(f"History — {task.get('title','')[:40]}")
        self.geometry("480x380")
        self.resizable(True, True)
        self.grab_set(); self.lift(); self.focus_force()

        hdr = ctk.CTkFrame(self, fg_color="#1a1a2e", corner_radius=0, height=52)
        hdr.pack(fill="x"); hdr.pack_propagate(False)
        ctk.CTkLabel(hdr, text=f"📜  {task.get('title','')[:44]}",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color="white").pack(expand=True, padx=14)

        body = ctk.CTkFrame(self, fg_color="white", corner_radius=0)
        body.pack(fill="both", expand=True)

        ts_frame = ctk.CTkFrame(body, fg_color="#f0f4f8", corner_radius=6)
        ts_frame.pack(fill="x", padx=14, pady=(12, 6))
        for label, value in [
            ("Created",       task.get("created_at",    "—")),
            ("Last updated",  task.get("updated_at",    "—")),
            ("Waiting since", task.get("waiting_since", "—") or "—"),
            ("Completed",     task.get("completed_at",  "—") or "—"),
        ]:
            row = ctk.CTkFrame(ts_frame, fg_color="transparent")
            row.pack(fill="x", padx=10, pady=2)
            ctk.CTkLabel(row, text=f"{label}:",
                         font=ctk.CTkFont(size=11, weight="bold"),
                         text_color="#555", width=110, anchor="w").pack(side="left")
            ctk.CTkLabel(row, text=value,
                         font=ctk.CTkFont(size=11),
                         text_color="#1a1a2e", anchor="w").pack(side="left")

        ctk.CTkLabel(body, text="Status History",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color="#444").pack(anchor="w", padx=14, pady=(4, 2))

        scroll = ctk.CTkScrollableFrame(body, fg_color="#fafafa",
                                         corner_radius=6, height=140)
        scroll.pack(fill="both", expand=True, padx=14, pady=(0, 8))
        history = task.get("history", [])
        if not history:
            ctk.CTkLabel(scroll, text="No history recorded yet.",
                         font=ctk.CTkFont(size=11),
                         text_color="#bbb").pack(pady=20)
        else:
            for entry in reversed(history):
                ctk.CTkLabel(scroll, text=f"• {entry}",
                             font=ctk.CTkFont(size=11),
                             text_color="#444", anchor="w").pack(
                             fill="x", padx=8, pady=2)

        ctk.CTkButton(body, text="Close", command=self.destroy,
                      width=90, height=30,
                      fg_color="#1a1a2e",
                      hover_color="#2c3e50").pack(pady=(0, 12))


# ═══════════════════════════════════════════════════════════
#  ABOUT WINDOW
# ═══════════════════════════════════════════════════════════
class AboutWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("About")
        self.geometry("400x310")
        self.resizable(False, False)
        self.grab_set(); self.lift(); self.focus_force()

        hdr = ctk.CTkFrame(self, fg_color="#1a1a2e", corner_radius=0, height=68)
        hdr.pack(fill="x"); hdr.pack_propagate(False)
        ctk.CTkLabel(hdr, text="📋  LYBIP Action Tracker",
                     font=ctk.CTkFont(size=16, weight="bold"),
                     text_color="white").pack(expand=True)

        body = ctk.CTkFrame(self, fg_color="white", corner_radius=0)
        body.pack(fill="both", expand=True)
        for label, value in [
            ("Version:",      "v0.1-internal"),
            ("Purpose:",      "Technical Office Management Tool"),
            ("Description:",  "A lightweight internal tool for tracking\ntasks and actions within the LYBIP Project."),
            ("Developed by:", "Ozhan Oruklu"),
            ("Release Date:", "20 March 2026"),
        ]:
            row = ctk.CTkFrame(body, fg_color="transparent")
            row.pack(fill="x", padx=24, pady=4)
            ctk.CTkLabel(row, text=label,
                         font=ctk.CTkFont(size=12, weight="bold"),
                         text_color="#555", width=110, anchor="w").pack(side="left")
            ctk.CTkLabel(row, text=value,
                         font=ctk.CTkFont(size=12),
                         text_color="#1a1a2e", anchor="w",
                         justify="left").pack(side="left")

        ctk.CTkButton(body, text="Close", command=self.destroy,
                      width=100, height=32,
                      fg_color="#1a1a2e",
                      hover_color="#2c3e50").pack(pady=14)


# ═══════════════════════════════════════════════════════════
#  MAIN APP
# ═══════════════════════════════════════════════════════════
class TaskApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("LYBIP Action Tracker  —  v0.1-internal")
        self.geometry("1160x700")
        self.minsize(960, 560)

        self.tasks = load_tasks()
        self.selected_task_index = None

        self.filter_dropdown = ctk.StringVar(value="Active")
        self.flt_open        = ctk.BooleanVar(value=False)
        self.flt_waiting     = ctk.BooleanVar(value=False)
        self.flt_high_prio   = ctk.BooleanVar(value=False)
        self.flt_today       = ctk.BooleanVar(value=False)
        self.sort_mode       = ctk.StringVar(value="Date then Priority")

        import tkinter as tk
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._refresh_list())

        self._build_ui()
        self._bind_shortcuts()
        self._refresh_list()

    # ── KEYBOARD SHORTCUTS ─────────────────────────────────
    def _bind_shortcuts(self):
        self.bind("<Control-f>", lambda e: self._focus_search())
        self.bind("<Escape>", self._on_escape)
        for widget in (self.title_entry, self.details_text):
            widget.bind("<Return>", lambda e: self._save_task())

    def _focus_search(self):
        self.search_entry.focus_set()
        self.search_entry.select_range(0, "end")

    def _on_escape(self, _event=None):
        if self.search_var.get():
            self.search_var.set("")
            self.search_entry.focus_set()
        elif self.selected_task_index is not None:
            self._cancel_edit()

    # ── TOP BAR ────────────────────────────────────────────
    def _build_topbar(self):
        bar = ctk.CTkFrame(self, fg_color="#1a1a2e", corner_radius=0, height=52)
        bar.pack(fill="x"); bar.pack_propagate(False)

        ctk.CTkLabel(bar, text="📋  LYBIP Action Tracker",
                     font=ctk.CTkFont(size=16, weight="bold"),
                     text_color="white").pack(side="left", padx=18)

        self.search_entry = ctk.CTkEntry(
            bar,
            textvariable=self.search_var,
            placeholder_text="Search...  (Ctrl+F)",
            width=240, height=30,
            fg_color="#2c3e50",
            border_color="#3d5166",
            text_color="white",
            placeholder_text_color="#7f9ab5",
            font=ctk.CTkFont(size=12),
        )
        self.search_entry.pack(side="right", padx=(8, 10))

        ctk.CTkButton(bar, text="ℹ  About", width=84, height=30,
                      fg_color="#2c3e50", hover_color="#34495e",
                      font=ctk.CTkFont(size=12),
                      command=lambda: AboutWindow(self)).pack(side="right", padx=(0, 4))

    # ── FILTER BAR ─────────────────────────────────────────
    def _build_filterbar(self, parent):
        bar = ctk.CTkFrame(parent, fg_color="#eef1f5", corner_radius=0, height=46)
        bar.pack(fill="x"); bar.pack_propagate(False)

        ctk.CTkLabel(bar, text="View:",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color="#444").pack(side="left", padx=(12, 4))

        ctk.CTkOptionMenu(
            bar, variable=self.filter_dropdown,
            values=["Active", "All", "Done"],
            width=108, height=28,
            command=lambda _: self._refresh_list()
        ).pack(side="left", padx=4)

        ctk.CTkLabel(bar, text="|", text_color="#bbb",
                     font=ctk.CTkFont(size=16)).pack(side="left", padx=8)

        ctk.CTkCheckBox(bar, text="Open", variable=self.flt_open,
                         font=ctk.CTkFont(size=11),
                         checkbox_width=16, checkbox_height=16,
                         command=self._on_filter_open).pack(side="left", padx=6)

        ctk.CTkCheckBox(bar, text="Waiting", variable=self.flt_waiting,
                         font=ctk.CTkFont(size=11),
                         checkbox_width=16, checkbox_height=16,
                         command=self._on_filter_waiting).pack(side="left", padx=6)

        ctk.CTkCheckBox(bar, text="🔴 High Priority", variable=self.flt_high_prio,
                         font=ctk.CTkFont(size=11),
                         checkbox_width=16, checkbox_height=16,
                         command=self._refresh_list).pack(side="left", padx=6)

        ctk.CTkCheckBox(bar, text="📅 Today", variable=self.flt_today,
                         font=ctk.CTkFont(size=11),
                         checkbox_width=16, checkbox_height=16,
                         command=self._refresh_list).pack(side="left", padx=6)

        clear_btn = ctk.CTkButton(bar, text="Clear Filters",
                                   width=100, height=26,
                                   fg_color="#c0392b", hover_color="#a93226",
                                   font=ctk.CTkFont(size=11),
                                   command=self._clear_filters)
        clear_btn.pack(side="right", padx=10)
        Tooltip(clear_btn, "Reset to Active view")

    def _on_filter_open(self):
        if self.flt_open.get():
            self.flt_waiting.set(False)
        self._refresh_list()

    def _on_filter_waiting(self):
        if self.flt_waiting.get():
            self.flt_open.set(False)
        self._refresh_list()

    # ── SORT + COUNT BAR ───────────────────────────────────
    def _build_sortbar(self, parent):
        bar = ctk.CTkFrame(parent, fg_color="transparent")
        bar.grid(row=1, column=0, sticky="ew", padx=10, pady=(4, 0))
        bar.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(bar, text="Sort by:",
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color="#666").grid(row=0, column=0, padx=(4, 4))

        ctk.CTkOptionMenu(bar, variable=self.sort_mode,
                          values=["Date then Priority", "Priority then Date"],
                          width=180, height=26,
                          font=ctk.CTkFont(size=11),
                          command=lambda _: self._refresh_list()
                          ).grid(row=0, column=1, sticky="w")

        self.count_label = ctk.CTkLabel(bar, text="",
                                         font=ctk.CTkFont(size=11),
                                         text_color="#999")
        self.count_label.grid(row=0, column=2, sticky="e", padx=6)

    # ── MAIN LAYOUT ────────────────────────────────────────
    def _build_ui(self):
        self._build_topbar()

        body = ctk.CTkFrame(self, corner_radius=0, fg_color="#ffffff")
        body.pack(fill="both", expand=True)
        body.grid_columnconfigure(0, weight=0)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(body, width=320, corner_radius=0, fg_color="#f0f4f8")
        left.grid(row=0, column=0, sticky="nsew")
        left.grid_propagate(False)
        self._build_form(left)

        right = ctk.CTkFrame(body, corner_radius=0, fg_color="#ffffff")
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_rowconfigure(2, weight=1)
        right.grid_columnconfigure(0, weight=1)

        fw = ctk.CTkFrame(right, corner_radius=0, fg_color="transparent")
        fw.grid(row=0, column=0, sticky="ew")
        fw.grid_columnconfigure(0, weight=1)
        self._build_filterbar(fw)

        self._build_sortbar(right)

        self.scroll_frame = ctk.CTkScrollableFrame(right, fg_color="#f8f9fa",
                                                    corner_radius=0)
        self.scroll_frame.grid(row=2, column=0, sticky="nsew")
        self.scroll_frame.grid_columnconfigure(0, weight=1)

    # ── FORM ───────────────────────────────────────────────
    def _build_form(self, parent):
        pad = {"padx": 16, "pady": 4}

        ctk.CTkLabel(parent, text="➕  Add / Edit Task",
                     font=ctk.CTkFont(size=15, weight="bold"),
                     text_color="#1a1a2e").pack(anchor="w", padx=16, pady=(14, 6))

        ctk.CTkLabel(parent, text="Title *",
                     font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", **pad)
        self.title_entry = ctk.CTkEntry(parent,
                                         placeholder_text="Short task title…",
                                         height=34)
        self.title_entry.pack(fill="x", **pad)

        ctk.CTkLabel(parent, text="Details",
                     font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", **pad)
        self.details_text = ctk.CTkTextbox(parent, height=80, border_width=1)
        self.details_text.pack(fill="x", **pad)

        ctk.CTkLabel(parent, text="Priority",
                     font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", **pad)
        self.priority_var = ctk.StringVar(value="Medium")
        ctk.CTkOptionMenu(parent, variable=self.priority_var,
                           values=["High", "Medium", "Low"]).pack(fill="x", **pad)

        ctk.CTkLabel(parent, text="Timing",
                     font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", **pad)
        self.timing_var = ctk.StringVar(value="No deadline")
        ctk.CTkOptionMenu(parent, variable=self.timing_var,
                           values=TIMING_OPTIONS,
                           command=self._toggle_date).pack(fill="x", **pad)

        self.date_frame = ctk.CTkFrame(parent, fg_color="#e8ecf0", corner_radius=6)
        ctk.CTkLabel(self.date_frame, text="Select or type date:",
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color="#444").pack(anchor="w", padx=10, pady=(8, 2))

        import tkinter as tk
        self.date_entry_var = tk.StringVar()

        if CALENDAR_AVAILABLE:
            self.date_picker = DateEntry(
                self.date_frame,
                textvariable=self.date_entry_var,
                date_pattern="dd/mm/yyyy",
                width=16,
                background="#2c3e50",
                foreground="white",
                borderwidth=1,
                font=("Segoe UI", 11),
                showweeknumbers=False,
                firstweekday="monday",
            )
            self.date_picker.pack(fill="x", padx=10, pady=(0, 4))
            ctk.CTkLabel(self.date_frame,
                         text="Click the arrow to open calendar",
                         font=ctk.CTkFont(size=10),
                         text_color="#888").pack(anchor="w", padx=10, pady=(0, 6))
        else:
            self.date_picker = ctk.CTkEntry(
                self.date_frame,
                textvariable=self.date_entry_var,
                placeholder_text="e.g. 25/04/2026",
                height=34
            )
            self.date_picker.pack(fill="x", padx=10, pady=(0, 4))
            ctk.CTkLabel(self.date_frame,
                         text="⚠ Install tkcalendar for calendar picker",
                         font=ctk.CTkFont(size=10),
                         text_color="#e67e22").pack(anchor="w", padx=10, pady=(0, 6))

        ctk.CTkLabel(parent, text="Status",
                     font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", **pad)
        self.status_var = ctk.StringVar(value="Open")
        ctk.CTkOptionMenu(parent, variable=self.status_var,
                           values=["Open", "Waiting", "Done"]).pack(fill="x", **pad)

        legend = ctk.CTkFrame(parent, fg_color="#e8ecf0", corner_radius=6)
        legend.pack(fill="x", padx=16, pady=(6, 2))
        for icon, txt in [
            ("🔵", "Open  =  action is with me"),
            ("🟣", "Waiting  =  waiting for others"),
            ("✅", "Done  =  no further follow-up"),
        ]:
            r = ctk.CTkFrame(legend, fg_color="transparent")
            r.pack(fill="x", padx=8, pady=1)
            ctk.CTkLabel(r, text=icon,
                         font=ctk.CTkFont(size=11), width=20).pack(side="left")
            ctk.CTkLabel(r, text=txt,
                         font=ctk.CTkFont(size=10),
                         text_color="#555").pack(side="left")

        bf = ctk.CTkFrame(parent, fg_color="transparent")
        bf.pack(fill="x", padx=16, pady=(10, 2))
        bf.grid_columnconfigure((0, 1), weight=1)

        self.save_btn = ctk.CTkButton(
            bf, text="✅  Save Task",
            command=self._save_task,
            height=38,
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.save_btn.grid(row=0, column=0, sticky="ew", padx=(0, 4))

        self.action_btn = ctk.CTkButton(
            bf, text="🗑  Clear",
            command=self._clear_form,
            height=38,
            fg_color="#95a5a6",
            hover_color="#7f8c8d",
            font=ctk.CTkFont(size=13)
        )
        self.action_btn.grid(row=0, column=1, sticky="ew", padx=(4, 0))

        self.delete_btn = ctk.CTkButton(
            parent, text="🗑  Delete Task",
            command=self._delete_task,
            height=34,
            fg_color="#c0392b",
            hover_color="#a93226",
            font=ctk.CTkFont(size=12)
        )

        self.mode_label = ctk.CTkLabel(
            parent, text="",
            font=ctk.CTkFont(size=11),
            text_color="#e74c3c"
        )
        self.mode_label.pack(pady=2)

    def _toggle_date(self, choice):
        if choice == "Specific date":
            self.date_frame.pack(fill="x", padx=16, pady=(0, 6))
        else:
            self.date_frame.pack_forget()

    def _get_date_value(self):
        return self.date_entry_var.get().strip()

    def _set_date_value(self, date_str):
        if CALENDAR_AVAILABLE and date_str:
            try:
                parsed = datetime.strptime(date_str, "%d/%m/%Y").date()
                self.date_picker.set_date(parsed)
                return
            except (ValueError, AttributeError):
                pass
        self.date_entry_var.set(date_str)

    # ── TASK CARD ──────────────────────────────────────────
    def _make_task_card(self, task, real_index, row):
        is_done = task.get("status") == "Done"
        bg = "#ffffff" if row % 2 == 0 else "#f4f6f9"
        if is_done:
            bg = "#efefef"

        card = ctk.CTkFrame(self.scroll_frame, fg_color=bg,
                             corner_radius=8, border_width=1,
                             border_color="#dde3ec")
        card.grid(row=row, column=0, sticky="ew", padx=8, pady=3)
        card.grid_columnconfigure(1, weight=1)

        pcolor = PRIORITY_COLORS.get(task.get("priority", "Medium"), "#aaa")
        ctk.CTkLabel(card, text="●", text_color=pcolor,
                     font=ctk.CTkFont(size=20), width=26).grid(
                     row=0, column=0, rowspan=2, padx=(10, 4), pady=8)

        tc = "#aaa" if is_done else "#1a1a2e"
        ctk.CTkLabel(card,
                     text=task.get("title", "Untitled"),
                     font=ctk.CTkFont(size=13, weight="bold",
                                       overstrike=is_done),
                     text_color=tc, anchor="w").grid(
                     row=0, column=1, sticky="ew", padx=4, pady=(7, 0))

        timing = task.get("timing", "No deadline")
        if timing == "Specific date" and task.get("date"):
            timing_display = f"Due: {task['date']}"
            timing_color   = "#d35400"
        elif timing == "Today":
            timing_display = "📅 Today"
            timing_color   = "#2980b9"
        else:
            timing_display = "No deadline"
            timing_color   = "#bbb"

        meta_frame = ctk.CTkFrame(card, fg_color="transparent")
        meta_frame.grid(row=1, column=1, sticky="ew", padx=4, pady=(0, 3))
        ctk.CTkLabel(meta_frame, text=timing_display,
                     font=ctk.CTkFont(size=10, weight="bold"),
                     text_color=timing_color).pack(side="left")
        ctk.CTkLabel(meta_frame,
                     text=f"  •  {task.get('priority','')} priority"
                          f"  •  Created: {task.get('created_at', task.get('created', ''))}",
                     font=ctk.CTkFont(size=10),
                     text_color="#999").pack(side="left")

        ts_text  = ""
        ts_color = "#aaa"
        if task.get("status") == "Waiting" and task.get("waiting_since"):
            ts_text  = f"⏳ Waiting since:  {task['waiting_since']}"
            ts_color = "#8e44ad"
        elif is_done and task.get("completed_at"):
            ts_text  = f"✅ Completed:  {task['completed_at']}"
            ts_color = "#27ae60"

        next_row = 2
        if ts_text:
            ctk.CTkLabel(card, text=ts_text,
                         font=ctk.CTkFont(size=10, weight="bold"),
                         text_color=ts_color, anchor="w").grid(
                         row=next_row, column=1, sticky="ew",
                         padx=4, pady=(0, 3))
            next_row += 1

        details = task.get("details", "").strip()
        if details:
            short = (details[:95] + "…") if len(details) > 95 else details
            ctk.CTkLabel(card, text=short,
                         font=ctk.CTkFont(size=11),
                         text_color="#666", anchor="w",
                         wraplength=520).grid(
                         row=next_row, column=0, columnspan=3,
                         sticky="ew", padx=14, pady=(0, 7))

        scolor = STATUS_COLORS.get(task.get("status", "Open"), "#aaa")
        sicon  = STATUS_ICONS.get(task.get("status", "Open"), "")
        ctk.CTkLabel(card,
                     text=f"  {sicon} {task.get('status','')}  ",
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color="white", fg_color=scolor,
                     corner_radius=5).grid(row=0, column=2, rowspan=2,
                                            padx=6, pady=8, sticky="ne")

        btn_col = ctk.CTkFrame(card, fg_color="transparent")
        btn_col.grid(row=0, column=3, rowspan=4, padx=(0, 10), pady=6)
        cur = task.get("status", "Open")

        def _qbtn(text, fg, hv, target):
            disabled = (cur == target)
            ctk.CTkButton(
                btn_col, text=text, width=78, height=23,
                fg_color="#d0d0d0" if disabled else fg,
                hover_color="#d0d0d0" if disabled else hv,
                text_color="#aaaaaa" if disabled else "white",
                font=ctk.CTkFont(size=10),
                state="disabled" if disabled else "normal",
                command=lambda t=target, i=real_index: self._quick_status(i, t)
            ).pack(pady=1)

        _qbtn("🔵 Open",    "#2980b9", "#1f6a9a", "Open")
        _qbtn("🟣 Waiting", "#8e44ad", "#6c3483", "Waiting")
        _qbtn("✅ Done",    "#27ae60", "#1e8449", "Done")

        ctk.CTkButton(btn_col, text="✏ Edit", width=78, height=23,
                       fg_color="#2c3e50", hover_color="#1a252f",
                       font=ctk.CTkFont(size=10),
                       command=lambda i=real_index: self._load_for_edit(i)
                       ).pack(pady=(4, 1))

        ctk.CTkButton(btn_col, text="📜 History", width=78, height=23,
                       fg_color="#7f8c8d", hover_color="#636e72",
                       font=ctk.CTkFont(size=10),
                       command=lambda t=task: HistoryWindow(self, t)
                       ).pack(pady=1)

    # ── FILTER + SEARCH LOGIC ──────────────────────────────
    def _apply_filters(self):
        today_str = date.today().strftime("%d/%m/%Y")
        dropdown  = self.filter_dropdown.get()
        result    = []

        for i, t in enumerate(self.tasks):
            status = t.get("status", "Open")
            if dropdown == "Active":
                if status not in ("Open", "Waiting"):
                    continue
            elif dropdown == "Done":
                if status != "Done":
                    continue
            if self.flt_open.get()      and status != "Open":            continue
            if self.flt_waiting.get()   and status != "Waiting":         continue
            if self.flt_high_prio.get() and t.get("priority") != "High": continue
            if self.flt_today.get():
                if t.get("timing") != "Today" and t.get("date") != today_str:
                    continue
            result.append((i, t))
        return result

    def _apply_search(self, items):
        query = self.search_var.get().strip().lower()
        if not query:
            return items
        return [
            (i, t) for i, t in items
            if query in t.get("title",   "").lower()
            or query in t.get("details", "").lower()
        ]

    def _apply_sort(self, items):
        if self.sort_mode.get() == "Priority then Date":
            return sorted(items, key=lambda x: sort_key_priority_date(x[1]))
        return sorted(items, key=lambda x: sort_key_date_priority(x[1]))

    def _clear_filters(self):
        self.filter_dropdown.set("Active")
        self.flt_open.set(False)
        self.flt_waiting.set(False)
        self.flt_high_prio.set(False)
        self.flt_today.set(False)
        self.search_var.set("")
        self._refresh_list()

    # ── REFRESH ────────────────────────────────────────────
    def _refresh_list(self):
        for w in self.scroll_frame.winfo_children():
            w.destroy()

        filtered = self._apply_filters()
        searched = self._apply_search(filtered)
        sorted_  = self._apply_sort(searched)

        query = self.search_var.get().strip()
        if query:
            self.count_label.configure(
                text=f"{len(sorted_)} result(s) for \"{query}\"")
        else:
            self.count_label.configure(
                text=f"Showing {len(sorted_)} of {len(self.tasks)} tasks")

        if not sorted_:
            msg = (f"No results for \"{query}\"."
                   if query else "No tasks match the current filters.")
            ctk.CTkLabel(self.scroll_frame, text=msg,
                         font=ctk.CTkFont(size=13),
                         text_color="#bbb").grid(row=0, column=0, pady=60)
            return

        for row, (real_i, task) in enumerate(sorted_):
            self._make_task_card(task, real_i, row)

    # ── QUICK STATUS ───────────────────────────────────────
    def _quick_status(self, index, new_status):
        self.tasks[index] = stamp(self.tasks[index], new_status)
        save_tasks(self.tasks)
        self._refresh_list()

    # ── SAVE / UPDATE ──────────────────────────────────────
    def _save_task(self):
        title = self.title_entry.get().strip()
        if not title:
            messagebox.showwarning("Missing Title", "Please enter a task title.")
            return

        timing   = self.timing_var.get()
        date_val = ""
        if timing == "Specific date":
            date_val = self._get_date_value()
            if not date_val:
                messagebox.showwarning("Missing Date",
                                       "Please select or enter a date.")
                return

        new_status = self.status_var.get()
        now        = now_str()

        if self.selected_task_index is not None:
            task       = self.tasks[self.selected_task_index]
            old_status = task.get("status", "")
            task["title"]      = title
            task["details"]    = self.details_text.get("1.0", "end").strip()
            task["priority"]   = self.priority_var.get()
            task["timing"]     = timing
            task["date"]       = date_val
            task["updated_at"] = now
            if old_status != new_status:
                task = stamp(task, new_status)
            else:
                task["status"] = new_status
            self.tasks[self.selected_task_index] = task
            self.selected_task_index = None
        else:
            task = {
                "title":         title,
                "details":       self.details_text.get("1.0", "end").strip(),
                "priority":      self.priority_var.get(),
                "timing":        timing,
                "date":          date_val,
                "status":        new_status,
                "created":       now,
                "created_at":    now,
                "updated_at":    now,
                "waiting_since": now if new_status == "Waiting" else "",
                "completed_at":  now if new_status == "Done"    else "",
                "history":       [f"{now}  —  Task created with status: {new_status}"],
            }
            self.tasks.insert(0, task)

        save_tasks(self.tasks)
        self._clear_form()
        self._refresh_list()

    # ── LOAD FOR EDIT ──────────────────────────────────────
    def _load_for_edit(self, index):
        task = self.tasks[index]
        self.selected_task_index = index

        self.title_entry.delete(0, "end")
        self.title_entry.insert(0, task.get("title", ""))
        self.details_text.delete("1.0", "end")
        self.details_text.insert("1.0", task.get("details", ""))
        self.priority_var.set(task.get("priority", "Medium"))
        self.status_var.set(task.get("status", "Open"))

        timing = task.get("timing", "No deadline")
        if timing not in TIMING_OPTIONS:
            timing = "No deadline"
        self.timing_var.set(timing)
        self._toggle_date(timing)
        if timing == "Specific date":
            self._set_date_value(task.get("date", ""))

        self.save_btn.configure(text="💾  Update Task")
        self.action_btn.configure(
            text="✕  Cancel Edit",
            fg_color="#2980b9",
            hover_color="#1f6a9a",
            command=self._cancel_edit
        )
        self.mode_label.configure(text=f"✏  Editing: {task['title'][:34]}")
        self.delete_btn.pack(fill="x", padx=16, pady=(2, 0))
        self.title_entry.focus()

    # ── CANCEL EDIT ────────────────────────────────────────
    def _cancel_edit(self):
        self._clear_form()

    # ── DELETE ─────────────────────────────────────────────
    def _delete_task(self):
        if self.selected_task_index is None:
            return
        title = self.tasks[self.selected_task_index].get("title", "this task")
        if messagebox.askyesno(
            "Delete Task",
            f"Are you sure you want to delete this task?\n\n\"{title}\""
        ):
            del self.tasks[self.selected_task_index]
            save_tasks(self.tasks)
            self._clear_form()
            self._refresh_list()

    # ── CLEAR FORM ─────────────────────────────────────────
    def _clear_form(self):
        self.title_entry.delete(0, "end")
        self.details_text.delete("1.0", "end")
        self.priority_var.set("Medium")
        self.timing_var.set("No deadline")
        self.status_var.set("Open")
        self.date_frame.pack_forget()
        self.date_entry_var.set("")
        self.selected_task_index = None

        self.save_btn.configure(text="✅  Save Task")
        self.action_btn.configure(
            text="🗑  Clear",
            fg_color="#95a5a6",
            hover_color="#7f8c8d",
            command=self._clear_form
        )
        self.mode_label.configure(text="")
        self.delete_btn.pack_forget()


# ---------- ENTRY POINT ----------
if __name__ == "__main__":
    app = TaskApp()
    app.mainloop()
