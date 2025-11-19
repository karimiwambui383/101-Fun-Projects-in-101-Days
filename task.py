"""
Rewritten: todozen_local_dark_rewritten.py
A cleaned, refactored, and bug-fixed single-file ToDo app using customtkinter.
Storage: local MongoDB (optional) or JSON fallback.
Fix: avoids shadowing tkinter internals (no _register defined), clearer structure, safer threading,
and small improvements (better date handling, explicit persistent save on close).

Dependencies:
  pip install customtkinter tkcalendar plyer pymongo

Run with: python todozen_local_dark_rewritten.py
"""

import os
import json
import threading
import time
import traceback
from datetime import datetime, timedelta, date
from uuid import uuid4
from functools import partial
from typing import List, Dict, Any, Optional

# UI & extras
try:
    import customtkinter as ctk
    from tkcalendar import DateEntry
    from plyer import notification
except Exception:
    print("Missing libraries. Run: python -m pip install customtkinter tkcalendar plyer pymongo")
    raise

# Optional pymongo
try:
    from pymongo import MongoClient
except Exception:
    MongoClient = None

# -----------------------
# Configuration
# -----------------------
FILE_NAME = "tasks.json"
NOTIFY_CHECK_INTERVAL = 8   # seconds between notification checks
NOTIFY_LOOKAHEAD_MIN = 0    # minutes ahead to trigger (0 = at due time)
SNOOZE_OPTIONS = [5, 10, 15, 30, 60]
DEFAULT_LOCAL_MONGO_URI = "mongodb://localhost:27017/todozen"

# -----------------------
# Utilities
# -----------------------

def now_local() -> datetime:
    return datetime.now()


def parse_iso(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None


def combine_date_time(d: date, hour: int, minute: int) -> Optional[datetime]:
    try:
        return datetime(d.year, d.month, d.day, hour, minute, 0)
    except Exception:
        return None


# -----------------------
# Storage
# -----------------------
class Storage:
    def __init__(self, uri: Optional[str] = None) -> None:
        self.use_mongo = False
        self.client = None
        self.collection = None

        env_uri = os.getenv("MONGO_URI")
        uri_to_try = env_uri or uri or DEFAULT_LOCAL_MONGO_URI

        if uri_to_try and MongoClient is not None:
            try:
                self.client = MongoClient(uri_to_try, serverSelectionTimeoutMS=3000)
                self.client.server_info()
                db = self.client.get_database() if self.client is not None else self.client["todozen"]
                self.collection = db["todozen_tasks"]
                self.use_mongo = True
                print("Storage: using MongoDB at:", uri_to_try)
            except Exception as e:
                print("MongoDB connection failed (using local JSON). Error:", e)
                self.use_mongo = False

        if not self.use_mongo:
            # ensure local file exists
            if not os.path.exists(FILE_NAME):
                with open(FILE_NAME, "w", encoding="utf-8") as f:
                    json.dump([], f)

    def load(self) -> List[Dict[str, Any]]:
        if self.use_mongo and self.collection is not None:
            docs = list(self.collection.find({}))
            tasks = []
            for d in docs:
                t = dict(d)
                _id = t.pop("_id", None)
                t["id"] = str(_id) if _id else t.get("id", str(uuid4()))
                tasks.append(t)
            return tasks
        else:
            try:
                with open(FILE_NAME, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return []

    def save(self, tasks: List[Dict[str, Any]]) -> None:
        if self.use_mongo and self.collection is not None:
            for t in tasks:
                cond = {"id": t.get("id")}
                t_clean = dict(t)
                t_clean.pop("_id", None)
                self.collection.replace_one(cond, t_clean, upsert=True)
            # sync deletion
            try:
                remote = list(self.collection.find({}, {"id": 1}))
                remote_ids = {str(r.get("id")) for r in remote if r.get("id")}
                local_ids = {t.get("id") for t in tasks if t.get("id")}
                to_delete = list(remote_ids - local_ids)
                if to_delete:
                    self.collection.delete_many({"id": {"$in": to_delete}})
            except Exception:
                pass
        else:
            with open(FILE_NAME, "w", encoding="utf-8") as f:
                json.dump(tasks, f, indent=2, ensure_ascii=False)


# -----------------------
# App
# -----------------------
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


class ToDoZen(ctk.CTk):
    def __init__(self, storage: Storage):
        super().__init__()
        self.storage = storage
        self.tasks = self.storage.load()
        self.title("🪷 ToDoZen — Local Dark Mode")
        self.geometry("920x660")
        self.minsize(760, 520)

        # moods
        self.moods = {
            "Calm": {"bg": "#0f1720", "accent": "#60a5a5", "text": "#e6eef9"},
            "Forest": {"bg": "#07120a", "accent": "#2f8f6f", "text": "#dff3e7"},
            "Sunset": {"bg": "#1a0b07", "accent": "#ff8a65", "text": "#ffece6"},
            "Dark": {"bg": "#0b0b0d", "accent": "#2b9cff", "text": "#e6eef9"},
        }
        self.current_mood = "Dark"

        # lifecycle controls
        self._stop_event = threading.Event()
        self._notifier_thread: Optional[threading.Thread] = None

        # build UI
        self._build_ui()
        self._apply_mood(self.current_mood)
        self.render_tasks()

        # start notifier
        self._start_notifier()

        # pulse animation
        self.after(700, self._pulse_add_button)

    # ---------------- UI ----------------
    def _build_ui(self) -> None:
        header = ctk.CTkFrame(self, corner_radius=10)
        header.pack(fill="x", padx=12, pady=10)

        self.title_label = ctk.CTkLabel(header, text="🪷 ToDoZen", font=("Helvetica", 22, "bold"))
        self.title_label.pack(side="left", padx=(12, 6))
        self.count_label = ctk.CTkLabel(header, text="", font=("Helvetica", 11))
        self.count_label.pack(side="left")

        self.mood_var = ctk.StringVar(value=self.current_mood)
        mood_menu = ctk.CTkOptionMenu(header, values=list(self.moods.keys()), variable=self.mood_var, command=self._on_mood_change, width=120)
        mood_menu.pack(side="right", padx=8)

        storage_text = "MongoDB (local)" if self.storage.use_mongo else "Local JSON"
        self.storage_label = ctk.CTkLabel(header, text=f"Storage: {storage_text}", font=("Helvetica", 10))
        self.storage_label.pack(side="right", padx=(8, 12))

        add_frame = ctk.CTkFrame(self, corner_radius=10)
        add_frame.pack(fill="x", padx=12, pady=(0, 12))

        self.task_entry = ctk.CTkEntry(add_frame, placeholder_text="What needs doing?", width=420)
        self.task_entry.grid(row=0, column=0, padx=8, pady=12)

        self.category_var = ctk.StringVar(value="General")
        cats = ["Work", "Personal", "Study", "Fitness", "Errands", "General"]
        cat_menu = ctk.CTkOptionMenu(add_frame, values=cats, variable=self.category_var, width=120)
        cat_menu.grid(row=0, column=1, padx=6)

        self.date_entry = DateEntry(add_frame, width=12)
        self.date_entry.grid(row=0, column=2, padx=6)

        hours = [f"{h:02d}" for h in range(24)]
        mins = [f"{m:02d}" for m in range(0, 60, 5)]

        self.hour_var = ctk.StringVar(value=f"{now_local().hour:02d}")
        self.hour_menu = ctk.CTkOptionMenu(add_frame, values=hours, variable=self.hour_var, width=70)
        self.hour_menu.grid(row=0, column=3, padx=4)

        self.min_var = ctk.StringVar(value=f"{now_local().minute:02d}")
        if int(self.min_var.get()) % 5 != 0:
            self.min_var.set(f"{(int(self.min_var.get()) // 5) * 5:02d}")
        self.min_menu = ctk.CTkOptionMenu(add_frame, values=mins, variable=self.min_var, width=70)
        self.min_menu.grid(row=0, column=4, padx=4)

        self.recur_var = ctk.StringVar(value="None")
        recur_menu = ctk.CTkOptionMenu(add_frame, values=["None", "Daily", "Weekly", "Monthly"], variable=self.recur_var, width=110)
        recur_menu.grid(row=0, column=5, padx=6)

        self.add_button = ctk.CTkButton(add_frame, text="➕ Add", width=110, command=self.add_task)
        self.add_button.grid(row=0, column=6, padx=8)

        self.tasks_frame = ctk.CTkScrollableFrame(self, label_text="Your Tasks", width=880, height=420, corner_radius=10)
        self.tasks_frame.pack(padx=12, pady=6)

        footer = ctk.CTkFrame(self, corner_radius=10)
        footer.pack(fill="x", padx=12, pady=(6, 12))
        ctk.CTkLabel(footer, text="Built with focus ✨", anchor="w").pack(side="left", padx=12)
        ctk.CTkButton(footer, text="Save", width=100, command=self._persist).pack(side="right", padx=12)

    # ---------------- Data ops ----------------
    def add_task(self) -> None:
        text = self.task_entry.get().strip()
        if not text:
            from tkinter import messagebox
            messagebox.showwarning("No task", "Please enter a task.")
            return

        d = self.date_entry.get_date()
        try:
            hour = int(self.hour_var.get())
            minute = int(self.min_var.get())
        except Exception:
            hour, minute = now_local().hour, 0

        due_dt = combine_date_time(d, hour, minute)
        if not due_dt:
            return

        task = {
            "id": str(uuid4()),
            "task": text,
            "category": self.category_var.get(),
            "due": due_dt.isoformat(),
            "done": False,
            "created": datetime.utcnow().isoformat(),
            "recurrence": self.recur_var.get().lower(),
            "notified": False,
        }
        self.tasks.append(task)
        self._persist()
        self.task_entry.delete(0, "end")
        self.render_tasks()
        self._toast(f"Added: {text}")

    def toggle_done(self, task_id: str) -> None:
        for t in self.tasks:
            if t.get("id") == task_id:
                t["done"] = not t.get("done", False)
                if t["done"] and t.get("recurrence", "none") != "none":
                    self._schedule_next_for_recurring(t)
                if not t["done"]:
                    t["notified"] = False
                break
        self._persist()
        self.render_tasks()

    def delete_task(self, task_id: str) -> None:
        self.tasks = [t for t in self.tasks if t.get("id") != task_id]
        self._persist()
        self.render_tasks()

    def snooze_task(self, task_id: str, minutes: int) -> None:
        for t in self.tasks:
            if t.get("id") == task_id:
                due = parse_iso(t.get("due"))
                if due:
                    new_due = due + timedelta(minutes=minutes)
                    t["due"] = new_due.isoformat()
                    t["notified"] = False
                    self._persist()
                    self.render_tasks()
                    self._toast(f"Snoozed {t['task']} by {minutes} min")
                break

    def edit_task_due(self, task_id: str, new_dt: datetime) -> None:
        for t in self.tasks:
            if t.get("id") == task_id:
                t["due"] = new_dt.isoformat()
                t["notified"] = False
                self._persist()
                self.render_tasks()
                break

    def _schedule_next_for_recurring(self, task: Dict[str, Any]) -> None:
        rec = task.get("recurrence", "none")
        if rec == "none":
            return
        due = parse_iso(task.get("due"))
        if not due:
            return
        if rec == "daily":
            next_due = due + timedelta(days=1)
        elif rec == "weekly":
            next_due = due + timedelta(weeks=1)
        elif rec == "monthly":
            next_due = due + timedelta(days=30)  # naive
        else:
            return
        new_task = dict(task)
        new_task["id"] = str(uuid4())
        new_task["due"] = next_due.isoformat()
        new_task["done"] = False
        new_task["notified"] = False
        self.tasks.append(new_task)

    def _persist(self) -> None:
        try:
            self.storage.save(self.tasks)
        except Exception as e:
            print("Persist error:", e)
            traceback.print_exc()

    # ---------------- UI Rendering ----------------
    def render_tasks(self) -> None:
        for w in self.tasks_frame.winfo_children():
            w.destroy()

        def due_key(t: Dict[str, Any]):
            d = parse_iso(t.get("due"))
            return d or datetime.max

        self.tasks.sort(key=due_key)

        if not self.tasks:
            ctk.CTkLabel(self.tasks_frame, text="No tasks yet. Create your rhythm ✨").pack(pady=12)
        else:
            for t in self.tasks:
                self._render_task_card(t)

        pending = sum(1 for t in self.tasks if not t.get("done", False))
        self.count_label.configure(text=f" • {pending} pending")

    def _render_task_card(self, t: Dict[str, Any]) -> None:
        frame = ctk.CTkFrame(self.tasks_frame, corner_radius=10)
        frame.pack(fill="x", padx=8, pady=6)

        left = ctk.CTkFrame(frame, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True, padx=6, pady=6)

        title = t.get("task", "")
        if t.get("done"):
            title = "✅ " + title
        ctk.CTkLabel(left, text=title, anchor="w", font=("Helvetica", 13, "bold")).pack(fill="x")
        due_dt = parse_iso(t.get("due"))
        due_str = due_dt.strftime("%Y-%m-%d %H:%M") if due_dt else "No due"
        meta = f"{t.get('category','General')} • Due: {due_str} • {t.get('recurrence','none').capitalize()}"
        ctk.CTkLabel(left, text=meta, anchor="w", font=("Helvetica", 10)).pack(fill="x", pady=(2, 0))

        right = ctk.CTkFrame(frame, fg_color="transparent")
        right.pack(side="right", padx=6, pady=6)

        done_txt = "↩ Undo" if t.get("done") else "✅ Done"
        ctk.CTkButton(right, text=done_txt, width=90, command=partial(self.toggle_done, t.get("id"))).pack(side="right", padx=4)
        ctk.CTkButton(right, text="✎", width=42, command=partial(self._open_edit_dialog, t.get("id"))).pack(side="right", padx=4)
        ctk.CTkButton(right, text="🗑", width=42, fg_color="#ff6b6b", hover_color="#ff8080", command=partial(self.delete_task, t.get("id"))).pack(side="right", padx=4)

        snooze_menu = ctk.CTkOptionMenu(right, values=[f"{m}m" for m in SNOOZE_OPTIONS], width=80, command=lambda val, id=t.get("id"): self._on_snooze_choice(id, val))
        snooze_menu.set("Snooze")
        snooze_menu.pack(side="right", padx=6)

        self._animate_widget_in(frame)

    def _open_edit_dialog(self, task_id: str) -> None:
        task = next((x for x in self.tasks if x.get("id") == task_id), None)
        if not task:
            return
        dlg = ctk.CTkToplevel(self)
        dlg.title("Edit Task")
        dlg.geometry("420x220")

        ctk.CTkLabel(dlg, text=task.get("task", ""), font=("Helvetica", 12, "bold")).pack(pady=8)
        de = DateEntry(dlg)
        due_dt = parse_iso(task.get("due"))
        if due_dt:
            de.set_date(due_dt.date())
        de.pack(pady=6)

        hours = [f"{h:02d}" for h in range(24)]
        mins = [f"{m:02d}" for m in range(0, 60, 5)]
        hvar = ctk.StringVar(value=f"{due_dt.hour:02d}" if due_dt else f"{now_local().hour:02d}")
        mvar = ctk.StringVar(value=f"{(due_dt.minute // 5) * 5:02d}" if due_dt else f"{now_local().minute:02d}")

        hmenu = ctk.CTkOptionMenu(dlg, values=hours, variable=hvar, width=80)
        hmenu.pack(side="left", padx=12, pady=8)
        mmenu = ctk.CTkOptionMenu(dlg, values=mins, variable=mvar, width=80)
        mmenu.pack(side="left", padx=12, pady=8)

        def save_and_close() -> None:
            try:
                new_dt = combine_date_time(de.get_date(), int(hvar.get()), int(mvar.get()))
                if new_dt:
                    self.edit_task_due(task_id, new_dt)
            except Exception:
                pass
            dlg.destroy()

        ctk.CTkButton(dlg, text="Save", command=save_and_close).pack(pady=10)

    def _on_snooze_choice(self, task_id: str, val: str) -> None:
        if not val or val == "Snooze":
            return
        try:
            m = int(val.replace("m", "").strip())
            self.snooze_task(task_id, m)
        except Exception:
            pass

    # ---------------- Animations ----------------
    def _animate_widget_in(self, widget, steps: int = 6, delay: int = 10) -> None:
        def step(i: int) -> None:
            pad = int(30 * (1 - (i / steps)))
            try:
                widget.pack_configure(padx=pad)
                if i < steps:
                    widget.after(delay, lambda: step(i + 1))
            except Exception:
                pass

        step(0)

    def _pulse_add_button(self) -> None:
        try:
            cur = self.add_button.winfo_width()
            def grow() -> None:
                try:
                    self.add_button.configure(width=cur + 8)
                    self.after(200, shrink)
                except Exception:
                    pass
            def shrink() -> None:
                try:
                    self.add_button.configure(width=cur)
                    self.after(1800, grow)
                except Exception:
                    pass
            grow()
        except Exception:
            pass

    # ---------------- Mood ----------------
    def _on_mood_change(self, mood: str) -> None:
        self._apply_mood(mood)

    def _apply_mood(self, mood: str) -> None:
        if mood not in self.moods:
            return
        self.current_mood = mood
        m = self.moods[mood]
        try:
            self.configure(fg_color=m["bg"])
        except Exception:
            pass
        try:
            self.title_label.configure(text_color=m["text"])
            self.count_label.configure(text_color=m["text"])
            self.storage_label.configure(text_color=m["text"])
            self.add_button.configure(fg_color=m["accent"])
        except Exception:
            pass

    # ---------------- Toast / Notifications ----------------
    def _toast(self, message: str) -> None:
        try:
            t = ctk.CTkToplevel(self)
            t.overrideredirect(True)
            x = self.winfo_rootx() + 80
            y = self.winfo_rooty() + 80
            t.geometry(f"300x60+{x}+{y}")
            ctk.CTkLabel(t, text=message).pack(fill="both", expand=True, padx=12, pady=12)
            t.after(1400, lambda: t.destroy())
        except Exception:
            pass

    def _start_notifier(self) -> None:
        if self._notifier_thread and self._notifier_thread.is_alive():
            return
        self._stop_event.clear()
        self._notifier_thread = threading.Thread(target=self._notifier_loop, daemon=True)
        self._notifier_thread.start()

    def _notifier_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                now = now_local()
                for t in list(self.tasks):
                    try:
                        if t.get("done"):
                            continue
                        if t.get("notified"):
                            continue
                        due = parse_iso(t.get("due"))
                        if not due:
                            continue
                        window_start = now - timedelta(minutes=1)
                        window_end = now + timedelta(minutes=NOTIFY_LOOKAHEAD_MIN)
                        if window_start <= due <= window_end:
                            title = f"Reminder: {t.get('task')}"
                            body = f"{t.get('category','General')} • Due {due.strftime('%Y-%m-%d %H:%M')}"
                            try:
                                notification.notify(title=title, message=body, timeout=8)
                            except Exception:
                                pass
                            t["notified"] = True
                            self._persist()
                            self._show_inapp_notification(t)
                    except Exception:
                        traceback.print_exc()
                time.sleep(NOTIFY_CHECK_INTERVAL)
            except Exception:
                traceback.print_exc()
                time.sleep(2)

    def _show_inapp_notification(self, task: Dict[str, Any]) -> None:
        try:
            top = ctk.CTkToplevel(self)
            top.title("Task Due")
            top.geometry("360x130")
            ctk.CTkLabel(top, text=f"⏰ {task.get('task')}", font=("Helvetica", 12, "bold")).pack(pady=(8, 4))
            due = parse_iso(task.get("due"))
            ctk.CTkLabel(top, text=f"Due: {due.strftime('%Y-%m-%d %H:%M') if due else '—'}", font=("Helvetica", 10)).pack()
            btn_frame = ctk.CTkFrame(top, fg_color="transparent")
            btn_frame.pack(pady=8)
            ctk.CTkButton(btn_frame, text="Snooze 10m", command=lambda: [self.snooze_task(task.get("id"), 10), top.destroy()]).pack(side="left", padx=6)
            ctk.CTkButton(btn_frame, text="Snooze 30m", command=lambda: [self.snooze_task(task.get("id"), 30), top.destroy()]).pack(side="left", padx=6)
            ctk.CTkButton(btn_frame, text="Mark Done", command=lambda: [self.toggle_done(task.get("id")), top.destroy()]).pack(side="left", padx=6)
            top.after(18000, lambda: top.destroy())
        except Exception:
            pass

    # ---------------- Lifecycle ----------------
    def on_close(self) -> None:
        try:
            self._stop_event.set()
            # give notifier thread a moment
            if self._notifier_thread and self._notifier_thread.is_alive():
                self._notifier_thread.join(timeout=1.0)
        except Exception:
            pass
        finally:
            self._persist()
            self.destroy()


# -----------------------
# Run
# -----------------------

def main() -> None:
    storage = Storage()
    app = ToDoZen(storage)
    # safe protocol hook
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()


if __name__ == "__main__":
    main()
