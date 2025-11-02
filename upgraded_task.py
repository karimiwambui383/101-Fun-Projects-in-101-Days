# todozen_full.py
"""
ToDoZen Full — All features except AI assistant (number 14).
Single-file app:
- GUI: customtkinter + tkcalendar
- Local SQLite offline-first (default) + optional Mongo sync (env MONGO_URI or default localhost)
- Notifications: plyer + in-app
- Snooze + recurring tasks (daily/weekly/monthly/custom)
- Accurate monthly recurrence using dateutil.relativedelta
- Voice add (speech_recognition) + TTS (pyttsx3)
- Dashboard/analytics using matplotlib
- Gamification: XP/coins/streaks
- Backup/Restore (JSON export/import)
- Email reminders (SMTP)
- Mood themes, small animations, system tray (pystray)
- Password-protected profiles (bcrypt)
"""
import os
import json
import threading
import time
import traceback
import sqlite3
import math
from datetime import datetime, timedelta, date
from uuid import uuid4
from functools import partial

# Third-party imports with friendly error messages
try:
    import customtkinter as ctk
    from tkcalendar import DateEntry
    from plyer import notification
    from dateutil.relativedelta import relativedelta
    import schedule
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    import pyttsx3
    import speech_recognition as sr
    import bcrypt
except Exception as e:
    print("Missing libraries or environment packages. Run:")
    print(" python -m pip install customtkinter tkcalendar plyer pymongo schedule python-dateutil pystray pillow matplotlib speechrecognition pyttsx3 bcrypt sqlite-utils")
    raise

# Optional libraries
try:
    from pymongo import MongoClient
except Exception:
    MongoClient = None

try:
    import pystray
    from PIL import Image, ImageDraw
except Exception:
    pystray = None

# -------------------------
# CONFIG
# -------------------------
APP_TITLE = "🪷 ToDoZen — Full Suite"
DB_FILE = "todozen_local.db"
JSON_BACKUP = "todozen_backup.json"
DEFAULT_LOCAL_MONGO_URI = "mongodb://localhost:27017/todozen"
NOTIFY_CHECK_INTERVAL = 15  # seconds
DEFAULT_SNOOZE_OPTIONS = [5, 10, 15, 30, 60]
THEMES = {
    "Dark": {"bg": "#0b0b0d", "accent": "#2b9cff", "text": "#e6eef9"},
    "Calm": {"bg": "#0f1720", "accent": "#60a5a5", "text": "#e6eef9"},
    "Forest": {"bg": "#07120a", "accent": "#2f8f6f", "text": "#dff3e7"},
    "Sunset": {"bg": "#1a0b07", "accent": "#ff8a65", "text": "#ffece6"},
}

# -------------------------
# Storage Layer (SQLite + optional Mongo)
# -------------------------
class Storage:
    def __init__(self, db_path=DB_FILE, mongo_uri=None):
        self.db_path = db_path
        self.mongo_uri = os.getenv("MONGO_URI") or mongo_uri or DEFAULT_LOCAL_MONGO_URI
        self.mongo_client = None
        self.mongo_collection = None
        self._ensure_sqlite()
        self._init_mongo_if_available()

    def _ensure_sqlite(self):
        created = not os.path.exists(self.db_path)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        cur = self.conn.cursor()
        # tasks table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            user TEXT,
            title TEXT,
            category TEXT,
            due TEXT,
            created TEXT,
            done INTEGER,
            recurrence TEXT,
            recurrence_extra TEXT,
            notified INTEGER,
            xp INTEGER
        )
        """)
        # users table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash BLOB,
            coins INTEGER DEFAULT 0,
            streak INTEGER DEFAULT 0,
            last_completed TEXT
        )
        """)
        self.conn.commit()

    def _init_mongo_if_available(self):
        if MongoClient is None:
            print("pymongo not installed — Mongo sync disabled")
            return
        try:
            client = MongoClient(self.mongo_uri, serverSelectionTimeoutMS=3000)
            client.server_info()
            self.mongo_client = client
            db = client.get_database()
            self.mongo_collection = db["todozen_tasks"]
            print("Mongo sync enabled:", self.mongo_uri)
        except Exception as e:
            print("Mongo connect failed — continuing with SQLite. Error:", e)
            self.mongo_client = None
            self.mongo_collection = None

    # SQL helpers
    def add_task(self, task):
        cur = self.conn.cursor()
        cur.execute("""
        INSERT OR REPLACE INTO tasks (id,user,title,category,due,created,done,recurrence,recurrence_extra,notified,xp)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (
            task.get("id") or str(uuid4()),
            task.get("user"),
            task.get("title"),
            task.get("category"),
            task.get("due"),
            task.get("created") or datetime.utcnow().isoformat(),
            1 if task.get("done") else 0,
            task.get("recurrence") or "none",
            json.dumps(task.get("recurrence_extra", {})),
            1 if task.get("notified") else 0,
            task.get("xp", 0)
        ))
        self.conn.commit()
        # optionally sync to mongo
        self._sync_task_to_mongo(task)

    def update_task(self, id_, **fields):
        cols = ",".join([f"{k}=?" for k in fields.keys()])
        vals = list(fields.values()) + [id_]
        cur = self.conn.cursor()
        cur.execute(f"UPDATE tasks SET {cols} WHERE id=?", vals)
        self.conn.commit()
        # optionally sync single doc
        doc = self.get_task(id_)
        if doc:
            self._sync_task_to_mongo(dict(doc))

    def delete_task(self, id_):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM tasks WHERE id=?", (id_,))
        self.conn.commit()
        if self.mongo_collection:
            try:
                self.mongo_collection.delete_one({"id": id_})
            except Exception:
                pass

    def get_task(self, id_):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM tasks WHERE id=?", (id_,))
        row = cur.fetchone()
        return dict(row) if row else None

    def list_tasks(self, user=None):
        cur = self.conn.cursor()
        if user:
            cur.execute("SELECT * FROM tasks WHERE user=?", (user,))
        else:
            cur.execute("SELECT * FROM tasks")
        rows = cur.fetchall()
        return [dict(r) for r in rows]

    # user management
    def add_user(self, username, password_hash):
        cur = self.conn.cursor()
        cur.execute("INSERT OR REPLACE INTO users (username,password_hash,coins,streak,last_completed) VALUES (?,?,?,?,?)",
                    (username, password_hash, 0, 0, None))
        self.conn.commit()

    def get_user(self, username):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM users WHERE username=?", (username,))
        row = cur.fetchone()
        return dict(row) if row else None

    def update_user(self, username, **fields):
        cols = ",".join([f"{k}=?" for k in fields.keys()])
        vals = list(fields.values()) + [username]
        cur = self.conn.cursor()
        cur.execute(f"UPDATE users SET {cols} WHERE username=?", vals)
        self.conn.commit()

    # backup/restore
    def export_json(self, path=JSON_BACKUP):
        tasks = self.list_tasks()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(tasks, f, default=str, indent=2)
        return path

    def import_json(self, path):
        with open(path, "r", encoding="utf-8") as f:
            tasks = json.load(f)
        for t in tasks:
            self.add_task(t)

    # mongo sync helper
    def _sync_task_to_mongo(self, task):
        if not self.mongo_collection:
            return
        try:
            doc = task.copy()
            doc["id"] = doc.get("id") or str(uuid4())
            self.mongo_collection.replace_one({"id": doc["id"]}, doc, upsert=True)
        except Exception:
            pass

# -------------------------
# Utilities & Helpers
# -------------------------
def parse_iso(s):
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None

def human_dt(dt):
    try:
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(dt)

def next_month(dt):
    return dt + relativedelta(months=1)

# ......................
# GAMIFICATION: XP logic
# ......................
def award_xp_for_task(task):
    # simple heuristic: base XP by category or length
    base = 10
    cat = (task.get("category") or "").lower()
    if "work" in cat:
        base += 5
    if "urgent" in cat or "important" in cat:
        base += 10
    base += min(20, len(task.get("title","")) // 5)
    return base

# -------------------------
# Notification helper (plyer)
# -------------------------
def send_desktop_notification(title, message):
    try:
        notification.notify(title=title, message=message, timeout=8)
    except Exception:
        pass

# -------------------------
# Voice helpers
# -------------------------
_engine = None
def tts_speak(text):
    global _engine
    try:
        if _engine is None:
            _engine = pyttsx3.init()
        _engine.say(text)
        _engine.runAndWait()
    except Exception:
        pass

def speech_to_text(timeout=5, phrase_time_limit=7):
    r = sr.Recognizer()
    with sr.Microphone() as source:
        r.adjust_for_ambient_noise(source, duration=0.5)
        audio = r.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
    try:
        return r.recognize_google(audio)
    except Exception:
        return ""

# -------------------------
# Main GUI App
# -------------------------
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

class ToDoZenApp(ctk.CTk):
    def __init__(self, storage: Storage):
        super().__init__()
        self.storage = storage
        self.current_user = None
        self.title(APP_TITLE)
        self.geometry("1100x760")
        self.minsize(900, 600)
        self.tasks = []  # cached tasks for current user
        self.snooze_options = DEFAULT_SNOOZE_OPTIONS

        self._stop_thread = threading.Event()
        self._notifier_thread = threading.Thread(target=self._notifier_loop, daemon=True)
        self._notifier_thread.start()

        self._build_login_ui()

    # -------------------------
    # LOGIN / PROFILE UI
    # -------------------------
    def _build_login_ui(self):
        for w in self.winfo_children(): w.destroy()
        frm = ctk.CTkFrame(self, corner_radius=12)
        frm.pack(expand=True, fill="both", padx=30, pady=30)

        ctk.CTkLabel(frm, text="ToDoZen — sign in / register", font=("Helvetica", 22, "bold")).pack(pady=12)
        container = ctk.CTkFrame(frm)
        container.pack(pady=8)

        ctk.CTkLabel(container, text="Username").grid(row=0, column=0, sticky="w")
        self.login_user = ctk.CTkEntry(container, width=260)
        self.login_user.grid(row=1, column=0, padx=6, pady=6)
        ctk.CTkLabel(container, text="Password").grid(row=2, column=0, sticky="w")
        self.login_pass = ctk.CTkEntry(container, width=260, show="*")
        self.login_pass.grid(row=3, column=0, padx=6, pady=6)

        btn_frame = ctk.CTkFrame(frm, fg_color="transparent")
        btn_frame.pack(pady=12)
        ctk.CTkButton(btn_frame, text="Sign in", command=self._signin).pack(side="left", padx=8)
        ctk.CTkButton(btn_frame, text="Register", command=self._register).pack(side="left", padx=8)
        ctk.CTkButton(btn_frame, text="Continue as Guest", command=self._continue_as_guest).pack(side="left", padx=8)

    def _signin(self):
        u = self.login_user.get().strip()
        p = self.login_pass.get().encode("utf-8")
        if not u or not p:
            return
        user = self.storage.get_user(u)
        if not user:
            ctk.messagebox = getattr(ctk, "CTkMessagebox", None)
            from tkinter import messagebox
            messagebox.showerror("No user", "User not found. Register first.")
            return
        if bcrypt.checkpw(p, user["password_hash"]):
            self.current_user = u
            self._build_main_ui()
        else:
            from tkinter import messagebox
            messagebox.showerror("Wrong", "Password incorrect.")

    def register_user(self):
        u = self.login_user.get().strip()
        p = self.login_pass.get().encode("utf-8")
        if not u or not p:
            return
        hashed = bcrypt.hashpw(p, bcrypt.gensalt())
        self.storage.add_user(u, hashed)
        self.current_user = u
        self._build_main_ui()


    def _continue_as_guest(self):
        self.current_user = "guest"
        self._build_main_ui()

    # -------------------------
    # MAIN UI (tabs)
    # -------------------------
    def _build_main_ui(self):
        for w in self.winfo_children(): w.destroy()
        # top frame: title + user + theme select + quick voice add
        top = ctk.CTkFrame(self, corner_radius=8)
        top.pack(fill="x", padx=12, pady=8)
        ctk.CTkLabel(top, text=f"🪷 ToDoZen • {self.current_user}", font=("Helvetica", 18, "bold")).pack(side="left", padx=8)
        # theme
        self.theme_var = ctk.StringVar(value="Dark")
        theme_menu = ctk.CTkOptionMenu(top, values=list(THEMES.keys()), variable=self.theme_var, command=self._on_theme_change, width=140)
        theme_menu.pack(side="right", padx=8)
        # voice quick-add
        ctk.CTkButton(top, text="🎤 Voice Add", command=self._voice_add).pack(side="right", padx=8)

        # Notebook tabs
        self.tabs = ctk.CTkTabview(self, width=1000)
        self.tabs.pack(padx=12, pady=12, fill="both", expand=True)
        self.tabs.add("Tasks")
        self.tabs.add("Dashboard")
        self.tabs.add("Analytics")
        self.tabs.add("Settings")

        self._build_tasks_tab()
        self._build_dashboard_tab()
        self._build_analytics_tab()
        self._build_settings_tab()

        # system tray init (optional)
        self._maybe_init_tray_icon()

        # initial load
        self._load_tasks()
        self.render_task_list()
        self._on_theme_change(self.theme_var.get())

    # -------------------------
    # Tasks tab
    # -------------------------
    def _build_tasks_tab(self):
        tab = self.tabs.tab("Tasks")
        # Add area
        add_frame = ctk.CTkFrame(tab, corner_radius=8)
        add_frame.pack(fill="x", padx=12, pady=8)
        self.entry_title = ctk.CTkEntry(add_frame, placeholder_text="Task title", width=420)
        self.entry_title.grid(row=0, column=0, padx=6, pady=6)
        # category
        self.category_var = ctk.StringVar(value="General")
        cat = ctk.CTkOptionMenu(add_frame, values=["Work","Personal","Study","Fitness","Errands","General"], variable=self.category_var, width=120)
        cat.grid(row=0, column=1, padx=6)
        # date
        self.date_entry = DateEntry(add_frame, width=12)
        self.date_entry.grid(row=0, column=2, padx=6)
        # hour/min dropdowns
        hours = [f"{h:02d}" for h in range(24)]
        mins = [f"{m:02d}" for m in range(0,60,5)]
        self.hour_var = ctk.StringVar(value=f"{datetime.now().hour:02d}")
        self.hour_menu = ctk.CTkOptionMenu(add_frame, values=hours, variable=self.hour_var, width=70)
        self.hour_menu.grid(row=0, column=3, padx=4)
        self.min_var = ctk.StringVar(value=f"{(datetime.now().minute//5)*5:02d}")
        self.min_menu = ctk.CTkOptionMenu(add_frame, values=mins, variable=self.min_var, width=70)
        self.min_menu.grid(row=0, column=4, padx=4)
        # recurrence
        self.recur_var = ctk.StringVar(value="None")
        self.recur_menu = ctk.CTkOptionMenu(add_frame, values=["None","Daily","Weekly","Monthly","Custom"], variable=self.recur_var, width=110)
        self.recur_menu.grid(row=0, column=5, padx=6)
        # custom recurrence extras button
        self.custom_recur_btn = ctk.CTkButton(add_frame, text="Custom", command=self._open_custom_recur_dialog)
        self.custom_recur_btn.grid(row=0, column=6, padx=6)
        # add button
        ctk.CTkButton(add_frame, text="➕ Add Task", command=self._add_task_from_ui).grid(row=0, column=7, padx=6)

        # tasks list area
        self.tasks_list_frame = ctk.CTkScrollableFrame(tab, label_text="Your Tasks", width=980, height=420)
        self.tasks_list_frame.pack(padx=12, pady=12, fill="both", expand=True)

    def _open_custom_recur_dialog(self):
        d = ctk.CTkToplevel(self)
        d.title("Custom Recurrence")
        d.geometry("420x180")
        ctk.CTkLabel(d, text="Custom recurrence: Every X days or specific weekdays").pack(pady=6)
        # every X days
        ctk.CTkLabel(d, text="Every (days):").pack()
        self._cust_days = ctk.CTkEntry(d, placeholder_text="e.g. 3")
        self._cust_days.pack(pady=4)
        # weekdays
        wk_frame = ctk.CTkFrame(d, fg_color="transparent")
        wk_frame.pack(pady=6)
        self._cust_weekdays = {i: ctk.StringVar(value="0") for i in range(7)}
        days = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
        for i,day in enumerate(days):
            cb = ctk.CTkCheckBox(wk_frame, text=day, variable=self._cust_weekdays[i], onvalue="1", offvalue="0")
            cb.grid(row=0, column=i, padx=4)
        ctk.CTkButton(d, text="Save", command=lambda: [d.destroy()]).pack(pady=8)

    def _add_task_from_ui(self):
        title = self.entry_title.get().strip()
        if not title:
            return
        cat = self.category_var.get()
        d = self.date_entry.get_date()
        try:
            h = int(self.hour_var.get())
            m = int(self.min_var.get())
        except Exception:
            h, m = 9, 0
        due = datetime(d.year, d.month, d.day, h, m)
        recur = self.recur_var.get().lower()
        recur_extra = {}
        if recur == "custom":
            # build recurrence_extra from custom fields if provided
            days = self._cust_days.get() if hasattr(self, "_cust_days") else ""
            weekdays = {k:v.get()=="1" for k,v in getattr(self, "_cust_weekdays", {}).items()}
            if days and days.strip().isdigit():
                recur_extra["every_x_days"] = int(days.strip())
            if any(weekdays.values()):
                recur_extra["weekdays"] = [i for i,flag in weekdays.items() if flag]
        task = {
            "id": str(uuid4()),
            "user": self.current_user,
            "title": title,
            "category": cat,
            "due": due.isoformat(),
            "created": datetime.utcnow().isoformat(),
            "done": False,
            "recurrence": recur,
            "recurrence_extra": recur_extra,
            "notified": False,
            "xp": 0
        }
        self.storage.add_task(task)
        self._toast(f"Added: {title}")
        self.entry_title.delete(0, "end")
        self._load_tasks()
        self.render_task_list()

    def _load_tasks(self):
        self.tasks = self.storage.list_tasks(user=self.current_user)
        # convert types
        for t in self.tasks:
            t["notified"] = bool(t.get("notified"))
            t["done"] = bool(t.get("done"))

    def render_task_list(self):
        for w in self.tasks_list_frame.winfo_children():
            w.destroy()
        # sort by due
        def keyf(t):
            dt = parse_iso(t.get("due"))
            return dt or datetime.max
        self.tasks.sort(key=keyf)
        if not self.tasks:
            ctk.CTkLabel(self.tasks_list_frame, text="No tasks yet — add something meaningful ✨").pack(pady=12)
            return
        for t in self.tasks:
            self._render_task_card(t)

    def _render_task_card(self, task):
        f = ctk.CTkFrame(self.tasks_list_frame, corner_radius=8)
        f.pack(fill="x", padx=8, pady=6)
        left = ctk.CTkFrame(f, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True, padx=6, pady=6)
        title = task.get("title")
        if task.get("done"):
            title = "✅ " + title
        ctk.CTkLabel(left, text=title, font=("Helvetica", 13, "bold")).pack(anchor="w")
        due = parse_iso(task.get("due"))
        ctk.CTkLabel(left, text=f"{task.get('category')} • Due: {human_dt(due) if due else '—'} • Rec: {task.get('recurrence')}", font=("Helvetica", 10)).pack(anchor="w")
        right = ctk.CTkFrame(f, fg_color="transparent")
        right.pack(side="right", padx=6, pady=6)
        ctk.CTkButton(right, text="✅/↩", width=70, command=partial(self._toggle_done, task.get("id"))).pack(side="right", padx=4)
        ctk.CTkButton(right, text="✎", width=42, command=partial(self._open_edit_dialog, task.get("id"))).pack(side="right", padx=4)
        ctk.CTkButton(right, text="🗑", width=42, fg_color="#ff6b6b", hover_color="#ff8080", command=partial(self._delete_task, task.get("id"))).pack(side="right", padx=4)
        snooze_menu = ctk.CTkOptionMenu(right, values=[f"{m}m" for m in self.snooze_options], width=80, command=lambda val, id=task.get("id"): self._snooze_choice(id, val))
        snooze_menu.set("Snooze")
        snooze_menu.pack(side="right", padx=6)
        # animation
        self._animate_in(f)

    def _toggle_done(self, id_):
        task = self.storage.get_task(id_)
        if not task:
            return
        new_done = not bool(task.get("done"))
        self.storage.update_task(id_, done=1 if new_done else 0)
        if new_done:
            # award xp and coins
            xp = award_xp_for_task(task)
            user = self.storage.get_user(self.current_user)
            if user:
                new_coins = (user.get("coins") or 0) + math.floor(xp/5)
                new_streak = (user.get("streak") or 0)
                # simple streak logic
                last = parse_iso(user.get("last_completed")) if user.get("last_completed") else None
                today = date.today()
                if last and parse_iso(user.get("last_completed")).date() == today - timedelta(days=1):
                    new_streak += 1
                elif last and parse_iso(user.get("last_completed")).date() == today:
                    # same day completed earlier -> streak unchanged
                    pass
                else:
                    new_streak = 1
                self.storage.update_user(self.current_user, coins=new_coins, streak=new_streak, last_completed=datetime.utcnow().isoformat())
                # set xp on task
                self.storage.update_task(id_, xp=xp)
            # schedule next recurrence if applicable
            if task.get("recurrence") and task.get("recurrence") != "none":
                self._handle_recurrence_after_completion(task)
        self._load_tasks()
        self.render_task_list()

    def _handle_recurrence_after_completion(self, task):
        rec = task.get("recurrence")
        due = parse_iso(task.get("due"))
        if not due:
            return
        next_due = None
        if rec == "daily":
            next_due = due + timedelta(days=1)
        elif rec == "weekly":
            next_due = due + timedelta(weeks=1)
        elif rec == "monthly":
            next_due = due + relativedelta(months=1)
        elif rec == "custom":
            extra = json.loads(task.get("recurrence_extra") or "{}")
            if extra.get("every_x_days"):
                next_due = due + timedelta(days=int(extra["every_x_days"]))
            elif extra.get("weekdays"):
                # find next weekday in list (0=Mon..6=Sun)
                wd = due.weekday()
                days = extra["weekdays"]
                # find next day in days list greater than current wd; else wrap
                days_sorted = sorted(days)
                found = None
                for d in days_sorted:
                    if d > wd:
                        found = d
                        break
                if found is None:
                    found = days_sorted[0]
                    delta_days = (7 - wd) + found
                else:
                    delta_days = found - wd
                next_due = due + timedelta(days=delta_days)
        if next_due:
            new_task = dict(task)
            new_task["id"] = str(uuid4())
            new_task["due"] = next_due.isoformat()
            new_task["done"] = False
            new_task["notified"] = False
            # persist
            self.storage.add_task(new_task)

    def _open_edit_dialog(self, id_):
        task = self.storage.get_task(id_)
        if not task:
            return
        d = ctk.CTkToplevel(self)
        d.title("Edit Task")
        d.geometry("420x220")
        ctk.CTkLabel(d, text=task.get("title"), font=("Helvetica", 12, "bold")).pack(pady=6)
        de = DateEntry(d)
        due = parse_iso(task.get("due"))
        if due:
            de.set_date(due.date())
        de.pack(pady=6)
        hours = [f"{h:02d}" for h in range(24)]
        mins = [f"{m:02d}" for m in range(0,60,5)]
        hv = ctk.StringVar(value=f"{due.hour:02d}" if due else f"{datetime.now().hour:02d}")
        mv = ctk.StringVar(value=f"{(due.minute//5)*5:02d}" if due else f"{datetime.now().minute:02d}")
        hmenu = ctk.CTkOptionMenu(d, values=hours, variable=hv, width=80)
        hmenu.pack(side="left", padx=8, pady=6)
        mmenu = ctk.CTkOptionMenu(d, values=mins, variable=mv, width=80)
        mmenu.pack(side="left", padx=8, pady=6)
        def save_and_close():
            try:
                newdt = datetime(de.get_date().year, de.get_date().month, de.get_date().day, int(hv.get()), int(mv.get()))
                self.storage.update_task(id_, due=newdt.isoformat(), notified=0)
                self._load_tasks()
                self.render_task_list()
            except Exception:
                pass
            d.destroy()
        ctk.CTkButton(d, text="Save", command=save_and_close).pack(pady=10)

    def _delete_task(self, id_):
        self.storage.delete_task(id_)
        self._load_tasks()
        self.render_task_list()

    def _snooze_choice(self, id_, val):
        if not val or val == "Snooze":
            return
        mins = int(val.replace("m",""))
        task = self.storage.get_task(id_)
        if not task:
            return
        due = parse_iso(task.get("due"))
        if not due:
            return
        new_due = due + timedelta(minutes=mins)
        self.storage.update_task(id_, due=new_due.isoformat(), notified=0)
        self._load_tasks()
        self.render_task_list()
        self._toast(f"Snoozed by {mins}m")

    # -------------------------
    # Dashboard & Analytics tabs
    # -------------------------
    def _build_dashboard_tab(self):
        tab = self.tabs.tab("Dashboard")
        # simple calendar and charts
        left = ctk.CTkFrame(tab)
        left.pack(side="left", fill="both", expand=True, padx=12, pady=12)
        right = ctk.CTkFrame(tab, width=360)
        right.pack(side="right", fill="y", padx=12, pady=12)
        # stats
        self.stat_label = ctk.CTkLabel(right, text="Stats", font=("Helvetica", 14, "bold"))
        self.stat_label.pack(pady=6)
        self.stat_text = ctk.CTkLabel(right, text="", anchor="w")
        self.stat_text.pack(pady=6)
        # chart canvas (matplotlib)
        self.fig, self.ax = plt.subplots(figsize=(5,3))
        self.canvas = FigureCanvasTkAgg(self.fig, master=left)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        ctk.CTkButton(right, text="Refresh Stats", command=self._refresh_stats).pack(pady=8)

    def _build_analytics_tab(self):
        tab = self.tabs.tab("Analytics")
        ctk.CTkLabel(tab, text="Analytics & Productivity", font=("Helvetica", 16, "bold")).pack(pady=6)
        self.analytics_text = ctk.CTkLabel(tab, text="", anchor="w")
        self.analytics_text.pack(pady=6)
        ctk.CTkButton(tab, text="Recompute", command=self._recompute_analytics).pack(pady=8)

    def _recompute_analytics(self):
        # simple analytics: completion rate, by-category counts, streaks
        tasks = self.storage.list_tasks(user=self.current_user)
        total = len(tasks)
        done = sum(1 for t in tasks if t.get("done"))
        by_cat = {}
        for t in tasks:
            by_cat[t.get("category","General")] = by_cat.get(t.get("category","General"),0)+1
        user = self.storage.get_user(self.current_user) or {}
        text = f"Total: {total}\nCompleted: {done}\nCompletion rate: { (done/total*100) if total else 0:.1f}%\n\nBy category:\n"
        for k,v in by_cat.items():
            text += f" - {k}: {v}\n"
        text += f"\nCoins: {user.get('coins',0)}  •  Streak: {user.get('streak',0)}"
        self.analytics_text.configure(text=text)

    def _refresh_stats(self):
        tasks = self.storage.list_tasks(user=self.current_user)
        # build category pie
        cats = {}
        for t in tasks:
            cats[t.get("category","General")] = cats.get(t.get("category","General"),0)+1
        self.ax.clear()
        labels = list(cats.keys()) or ["No tasks"]
        sizes = list(cats.values()) or [1]
        self.ax.pie(sizes, labels=labels, autopct="%1.1f%%")
        self.ax.set_title("Tasks by Category")
        self.canvas.draw()
        # stats text
        total = len(tasks)
        pending = sum(1 for t in tasks if not t.get("done"))
        due_today = sum(1 for t in tasks if parse_iso(t.get("due")) and parse_iso(t.get("due")).date()==date.today())
        self.stat_text.configure(text=f"Total: {total}\nPending: {pending}\nDue today: {due_today}")

    # -------------------------
    # Settings tab
    # -------------------------
    def _build_settings_tab(self):
        tab = self.tabs.tab("Settings")
        ctk.CTkLabel(tab, text="Settings", font=("Helvetica", 16, "bold")).pack(pady=8)
        # backup / restore
        ctk.CTkButton(tab, text="Export JSON Backup", command=self._export_backup).pack(pady=6)
        ctk.CTkButton(tab, text="Import JSON Backup", command=self._import_backup).pack(pady=6)
        # email settings
        ctk.CTkLabel(tab, text="Email reminders (SMTP)").pack(pady=4)
        self.smtp_server = ctk.CTkEntry(tab, placeholder_text="smtp.server.com")
        self.smtp_server.pack(pady=4)
        self.smtp_user = ctk.CTkEntry(tab, placeholder_text="user@example.com")
        self.smtp_user.pack(pady=4)
        self.smtp_pass = ctk.CTkEntry(tab, placeholder_text="password", show="*")
        self.smtp_pass.pack(pady=4)
        ctk.CTkButton(tab, text="Send Test Email", command=self._send_test_email).pack(pady=6)
        # sync toggle
        self.sync_var = ctk.BooleanVar(value=bool(self.storage.mongo_collection))
        ctk.CTkCheckBox(tab, text="Sync to MongoDB (if available)", variable=self.sync_var, command=self._toggle_sync).pack(pady=6)
        # tray toggle
        self.tray_var = ctk.BooleanVar(value=True if pystray else False)
        ctk.CTkCheckBox(tab, text="Enable System Tray", variable=self.tray_var).pack(pady=6)

    def _export_backup(self):
        path = self.storage.export_json()
        self._toast(f"Exported to {path}")

    def _import_backup(self):
        # simple: read JSON_BACKUP if exists
        if not os.path.exists(JSON_BACKUP):
            self._toast("No backup file found.")
            return
        self.storage.import_json(JSON_BACKUP)
        self._toast("Imported backup.")
        self._load_tasks()
        self.render_task_list()

    def _send_test_email(self):
        import smtplib
        server = self.smtp_server.get().strip()
        user = self.smtp_user.get().strip()
        pw = self.smtp_pass.get().strip()
        if not server or not user or not pw:
            self._toast("Fill SMTP settings first.")
            return
        try:
            with smtplib.SMTP(server, 587, timeout=10) as s:
                s.starttls()
                s.login(user, pw)
                s.sendmail(user, user, "Subject: ToDoZen Test\n\nThis is a test email from ToDoZen.")
            self._toast("Test email sent.")
        except Exception as e:
            self._toast(f"Email failed: {e}")

    def _toggle_sync(self):
        if self.sync_var.get():
            self.storage._init_mongo_if_available()
            if self.storage.mongo_collection:
                self._toast("Mongo sync enabled.")
            else:
                self._toast("Mongo not available.")
        else:
            self._toast("Mongo sync disabled.")

    # -------------------------
    # Voice quick-add
    # -------------------------
    def _voice_add(self):
        self._toast("Listening...")
        def _do_listen():
            try:
                text = speech_to_text()
                if text:
                    # naive parse: "Title at YYYY-mm-dd HH:MM" or just title
                    title = text
                    # add as task at tomorrow 9am if no datetime found
                    due = datetime.now() + timedelta(days=1)
                    task = {"id": str(uuid4()), "user": self.current_user, "title": title, "category":"Personal",
                            "due": due.isoformat(), "created": datetime.utcnow().isoformat(), "done": False,
                            "recurrence": "none", "recurrence_extra": {}, "notified": False}
                    self.storage.add_task(task)
                    self._load_tasks()
                    self.render_task_list()
                    self._toast(f"Added (voice): {title}")
                    tts_speak("Task added.")
                else:
                    self._toast("Couldn't hear clearly.")
            except Exception:
                self._toast("Voice add failed.")
        threading.Thread(target=_do_listen, daemon=True).start()

    # -------------------------
    # Notifier loop: check due tasks and show notifications
    # -------------------------
    def _notifier_loop(self):
        while not self._stop_thread.is_set():
            try:
                now = datetime.now()
                tasks = self.storage.list_tasks(user=self.current_user)
                for t in tasks:
                    if t.get("done"):
                        continue
                    if t.get("notified"):
                        continue
                    due = parse_iso(t.get("due"))
                    if not due:
                        continue
                    window_start = now - timedelta(minutes=1)
                    window_end = now + timedelta(minutes=0)
                    if window_start <= due <= window_end:
                        send_desktop_notification(f"ToDoZen • {t.get('title')}", f"{t.get('category')} — due {human_dt(due)}")
                        # mark notified and open small in-app action
                        self.storage.update_task(t.get("id"), notified=1)
                        self._show_due_popup(t)
                time.sleep(NOTIFY_CHECK_INTERVAL)
            except Exception:
                traceback.print_exc()
                time.sleep(5)

    def _show_due_popup(self, task):
        try:
            top = ctk.CTkToplevel(self)
            top.title("Task Due")
            top.geometry("360x140")
            ctk.CTkLabel(top, text=f"⏰ {task.get('title')}", font=("Helvetica", 12, "bold")).pack(pady=6)
            due = parse_iso(task.get("due"))
            ctk.CTkLabel(top, text=f"Due: {human_dt(due)}", font=("Helvetica", 10)).pack()
            frame = ctk.CTkFrame(top, fg_color="transparent")
            frame.pack(pady=8)
            ctk.CTkButton(frame, text="Snooze 10m", command=lambda: [self._snooze_choice(task.get("id"), "10m"), top.destroy()]).pack(side="left", padx=4)
            ctk.CTkButton(frame, text="Snooze 30m", command=lambda: [self._snooze_choice(task.get("id"), "30m"), top.destroy()]).pack(side="left", padx=4)
            ctk.CTkButton(frame, text="Mark Done", command=lambda: [self._toggle_done(task.get("id")), top.destroy()]).pack(side="left", padx=4)
            top.after(20000, lambda: top.destroy())
        except Exception:
            pass

    # -------------------------
    # Little utilities & UI niceties
    # -------------------------
    def _toast(self, text):
        t = ctk.CTkToplevel(self)
        t.overrideredirect(True)
        x = self.winfo_rootx() + 80
        y = self.winfo_rooty() + 80
        t.geometry(f"300x60+{x}+{y}")
        ctk.CTkLabel(t, text=text).pack(fill="both", expand=True, padx=12, pady=12)
        t.after(1400, lambda: t.destroy())

    def _animate_in(self, widget, steps=6, delay=10):
        def step(i):
            pad = int(30 * (1 - (i/steps)))
            try:
                widget.pack_configure(padx=pad)
                if i < steps:
                    widget.after(delay, lambda: step(i+1))
            except Exception:
                pass
        step(0)

    # -------------------------
    # System Tray (optional)
    # -------------------------
    def _maybe_init_tray_icon(self):
        if not pystray or not self.tray_var.get():
            return
        # create simple icon
        def create_image():
            img = Image.new('RGB', (64,64), color=(0,0,0))
            d = ImageDraw.Draw(img)
            d.ellipse((8,8,56,56), fill=(43,156,255))
            return img
        image = create_image()
        menu = pystray.Menu(
            pystray.MenuItem('Open', lambda : self.deiconify()),
            pystray.MenuItem('Exit', lambda : self._exit_from_tray())
        )
        icon = pystray.Icon("todozen", image, "ToDoZen", menu)
        def run_icon():
            icon.run()
        threading.Thread(target=run_icon, daemon=True).start()

    def _exit_from_tray(self):
        self.on_close()

    # -------------------------
    # Theme change
    # -------------------------
    def _on_theme_change(self, mood):
        theme = THEMES.get(mood, THEMES["Dark"])
        try:
            self.configure(fg_color=theme["bg"])
        except Exception:
            pass

    # -------------------------
    # Backup helpers
    # -------------------------
    def _export_backup(self):
        path = self.storage.export_json()
        self._toast(f"Exported to {path}")

    # -------------------------
    # Close / lifecycle
    # -------------------------
    def on_close(self):
        self._stop_thread.set()
        try:
            self.storage.conn.close()
        except Exception:
            pass
        self.destroy()

# -------------------------
# Run
# -------------------------
def main():
    storage = Storage()
    app = ToDoZenApp(storage)
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()

if __name__ == "__main__":
    main()
