import datetime
import json
import queue
import sys
import threading
import tkinter as tk
from pathlib import Path

import psutil
import pystray
from PIL import Image, ImageDraw

# Folder tempat config.json berada (di samping .py atau .exe)
BASE = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent
CONFIG_PATH = BASE / "config.json"

# Python: Senin=0 ... Jumat=4, Sabtu=5, Minggu=6
DEFAULT_SKIP_WEEKDAYS = [4, 5, 6]

# Proses yang sedang dibekukan menunggu keputusan user
pending = []
pending_lock = threading.Lock()


def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


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
            print(f"Gagal suspend PID {p.pid}: {e}")
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
            print(f"Gagal resume PID {p.pid}: {e}")
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
                print(f"Gagal kill PID {v.pid}: {e}")
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
    active = set()       # target yang sedang berjalan, supaya popup tidak berulang
    first_scan = True    # proses yang sudah jalan sebelum program mulai tidak di-suspend

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
                    continue  # hari bebas popup, biarkan aplikasi jalan normal
                procs = suspend_procs(found[name])  # bekukan secepat mungkin
                events.put((info, procs))           # kirim ke thread UI
            elif name not in found:
                active.discard(name)  # reset, popup muncul lagi di peluncuran berikutnya

        first_scan = False
        stop.wait(interval)


# ---------- Popup ----------
def show_popup(root, info, procs):
    win = tk.Toplevel(root)
    win.title("TADuluBosQ")
    win.configure(bg="#1e1e2e")
    win.attributes("-topmost", True)
    win.resizable(False, False)

    def on_cancel():
        kill_procs(procs)
        win.destroy()

    def on_play():
        resume_procs(procs)
        win.destroy()

    # Tombol X dianggap Cancel, supaya aplikasi tidak tertinggal membeku selamanya
    win.protocol("WM_DELETE_WINDOW", on_cancel)

    w, h = 440, 240
    x = (win.winfo_screenwidth() - w) // 2
    y = (win.winfo_screenheight() - h) // 2
    win.geometry(f"{w}x{h}+{x}+{y}")

    tk.Label(win, text=info.get("title", "TADuluBosQ"), font=("Segoe UI", 16, "bold"),
             fg="#f9e2af", bg="#1e1e2e").pack(pady=(25, 10))
    tk.Label(win, text=info.get("message", ""), font=("Segoe UI", 11),
             fg="#cdd6f4", bg="#1e1e2e", wraplength=380, justify="center").pack(pady=5)

    frame = tk.Frame(win, bg="#1e1e2e")
    frame.pack(pady=25)

    tk.Button(frame, text="Cancel", font=("Segoe UI", 11), width=14,
              command=on_cancel).pack(side="left", padx=8)

    play_btn = tk.Button(frame, text="", font=("Segoe UI", 11), width=16,
                         state="disabled", command=on_play)
    play_btn.pack(side="left", padx=8)

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
    config = load_config()
    events = queue.Queue()
    stop = threading.Event()

    root = tk.Tk()
    root.withdraw()  # window utama disembunyikan, hanya dipakai sebagai induk popup

    threading.Thread(target=monitor, args=(config, events, stop), daemon=True).start()

    def on_quit(icon, item):
        icon.stop()
        stop.set()  # poll() di bawah yang akan menutup tkinter

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
        resume_all_pending()  # jangan sampai ada aplikasi tertinggal membeku saat program keluar


if __name__ == "__main__":
    main()