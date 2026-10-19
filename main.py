import datetime
import json
import queue
import sys
import threading
import tkinter as tk
import ctypes
from pathlib import Path

import psutil
import pystray
from PIL import Image, ImageDraw

BASE = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent
CONFIG_PATH = BASE / "config.json"

DEFAULT_SKIP_WEEKDAYS = [4, 5, 6]

pending = []
pending_lock = threading.Lock()


def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)

# --------- Single instance ----------
def ensure_single_instance():
    handle = ctypes.windll.kernel32.CreateMutexW(None, False, "TADuluBosQ_single_instance")
    if ctypes.windll.kernel32.GetLastError() == 183: 
        sys.exit(0)
    return handle


# ---------- Kontrol proses ----------
def suspend_procs(procs):
    ok = []
    for p in procs:
        try:
            p.suspend()
            ok.append(p)
            with pending_lock:
                pending.append(p)
        except psutil.Error as e:
            print(f"Failed to suspend PID {p.pid}: {e}")
    return ok


def _forget(procs):
    with pending_lock:
        for p in procs:
            if p in pending:
                pending.remove(p)


def resume_procs(procs):
    for p in procs:
        try:
            p.resume()
        except psutil.Error as e:
            print(f"Failed to resume PID {p.pid}: {e}")
    _forget(procs)


def kill_procs(procs):
    for p in procs:
        try:
            victims = p.children(recursive=True) + [p]
        except psutil.Error:
            victims = [p]
        for v in victims:
            try:
                v.kill()
            except psutil.Error as e:
                print(f"Failed to kill PID {v.pid}: {e}")
    _forget(procs)


def resume_all_pending():
    with pending_lock:
        left = list(pending)
    resume_procs(left)


# ---------- Pendeteksi proses (jalan di thread terpisah) ----------
def monitor(config, events, stop):
    targets = {k.lower(): v for k, v in config["targets"].items()}
    interval = config.get("poll_interval", 0.5)
    skip_days = set(config.get("skip_weekdays", DEFAULT_SKIP_WEEKDAYS))
    active = set()      
    first_scan = True    

    while not stop.is_set():
        found = {}
        for p in psutil.process_iter(["name"]):
            try:
                name = p.info["name"]
                if name and name.lower() in targets:
                    found.setdefault(name.lower(), []).append(p)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        for name, info in targets.items():
            if name in found and name not in active:
                active.add(name)
                if first_scan:
                    continue
                if datetime.date.today().weekday() in skip_days:
                    continue 
                procs = suspend_procs(found[name])  
                events.put((info, procs))          
            elif name not in found:
                active.discard(name)  
                
        first_scan = False
        stop.wait(interval)


# ---------- Popup ----------
def show_popup(root, info, procs):
    colors = {
        "background": "#0b2f5b",
        "card": "#1557a6",
        "heading": "#ffffff",
        "text": "#e5f0ff",
        "muted": "#a9c8ed",
        "border": "#3475c2",
        "primary": "#0b2f5b",
        "primary_hover": "#082445",
        "secondary": "#3475c2",
        "secondary_hover": "#4385d2",
    }

    win = tk.Toplevel(root)
    win.title("TADuluBosQ")
    win.configure(bg=colors["background"])
    win.attributes("-topmost", True)
    win.resizable(False, False)

    def on_cancel():
        kill_procs(procs)
        win.destroy()

    def on_play():
        resume_procs(procs)
        win.destroy()

    win.protocol("WM_DELETE_WINDOW", on_cancel)

    w, h = 440, 270
    x = (win.winfo_screenwidth() - w) // 2
    y = (win.winfo_screenheight() - h) // 2
    win.geometry(f"{w}x{h}+{x}+{y}")

    card = tk.Frame(
        win,
        bg=colors["card"],
        highlightbackground=colors["border"],
        highlightthickness=1,
    )
    card.pack(fill="both", expand=True, padx=16, pady=16)

    tk.Frame(card, bg=colors["card"], height=4).pack(fill="x")
    content = tk.Frame(card, bg=colors["card"])
    content.pack(fill="both", expand=True)
    body = tk.Frame(content, bg=colors["card"])
    body.place(relx=0.5, rely=0.5, anchor="center")

    tk.Label(
        body,
        text=info.get("title", "TA Dulu Bosss!"),
        font=("Segoe UI", 16, "bold"),
        fg=colors["heading"],
        bg=colors["card"],
    ).pack(pady=(24, 8))
    tk.Label(
        body,
        text=info.get("message", ""),
        font=("Segoe UI", 10),
        fg=colors["text"],
        bg=colors["card"],
        wraplength=360,
        justify="center",
    ).pack(pady=(0, 12))

    frame = tk.Frame(body, bg=colors["card"])
    frame.pack(pady=(0, 24))

    cancel_btn = tk.Button(
        frame,
        text="Cancel",
        font=("Segoe UI", 10, "bold"),
        width=12,
        fg=colors["heading"],
        bg=colors["secondary"],
        activeforeground=colors["heading"],
        activebackground=colors["secondary_hover"],
        relief="flat",
        bd=0,
        cursor="hand2",
        command=on_cancel,
    )
    cancel_btn.pack(side="left", padx=6, ipady=5)

    play_btn = tk.Button(
        frame,
        text="",
        font=("Segoe UI", 10, "bold"),
        width=16,
        fg="#ffffff",
        bg=colors["primary"],
        activeforeground="#ffffff",
        activebackground=colors["primary_hover"],
        disabledforeground=colors["muted"],
        relief="flat",
        bd=0,
        cursor="hand2",
        state="disabled",
        command=on_play,
    )
    play_btn.pack(side="left", padx=6, ipady=5)

    def tick(n):
        if not win.winfo_exists():
            return
        if n > 0:
            play_btn.config(text=f"Play Anyway ({n})")
            win.after(1000, tick, n - 1)
        else:
            play_btn.config(text="Play Anyway", state="normal")

    tick(info.get("countdown", 5))
    win.lift()
    win.focus_force()


# ---------- Tray icon ----------
def make_icon_image():
    img = Image.new("RGB", (64, 64), "#1e1e2e")
    ImageDraw.Draw(img).ellipse((12, 12, 52, 52), fill="#f9e2af")
    return img


def main():
    _mutex_handle = ensure_single_instance() 
    config = load_config()
    events = queue.Queue()
    stop = threading.Event()

    root = tk.Tk()
    root.withdraw() 

    threading.Thread(target=monitor, args=(config, events, stop), daemon=True).start()

    def on_quit(icon, item):
        icon.stop()
        stop.set() 

    icon = pystray.Icon(
        "TADuluBosQ", make_icon_image(), "TADuluBosQ",
        menu=pystray.Menu(pystray.MenuItem("Exit", on_quit)),
    )
    icon.run_detached()

    def poll():
        if stop.is_set():
            root.quit()
            return
        try:
            while True:
                info, procs = events.get_nowait()
                show_popup(root, info, procs)
        except queue.Empty:
            pass
        root.after(200, poll)

    poll()
    try:
        root.mainloop()
    finally:
        resume_all_pending() 
        

if __name__ == "__main__":
    main()