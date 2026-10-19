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


def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


# ---------- Pendeteksi proses (jalan di thread terpisah) ----------
def monitor(config, events, stop):
    targets = {k.lower(): v for k, v in config["targets"].items()}
    interval = config.get("poll_interval", 2)
    active = set()  # target yang sedang berjalan, supaya popup tidak berulang

    while not stop.is_set():
        running = set()
        for p in psutil.process_iter(["name"]):
            try:
                name = p.info["name"]
                if name:
                    running.add(name.lower())
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        for name, info in targets.items():
            if name in running and name not in active:
                active.add(name)
                events.put(info)       # kirim ke thread UI
            elif name not in running:
                active.discard(name)   # reset, popup muncul lagi di peluncuran berikutnya

        stop.wait(interval)


# ---------- Popup ----------
def show_popup(root, info):
    win = tk.Toplevel(root)
    win.title("TADuluBosQ")
    win.configure(bg="#1e1e2e")
    win.attributes("-topmost", True)
    win.resizable(False, False)
    win.protocol("WM_DELETE_WINDOW", lambda: None)  # tidak bisa ditutup lewat X

    w, h = 440, 230
    x = (win.winfo_screenwidth() - w) // 2
    y = (win.winfo_screenheight() - h) // 2
    win.geometry(f"{w}x{h}+{x}+{y}")

    tk.Label(win, text=info.get("title", "TADuluBosQ"), font=("Segoe UI", 16, "bold"),
             fg="#f9e2af", bg="#1e1e2e").pack(pady=(25, 10))
    tk.Label(win, text=info.get("message", ""), font=("Segoe UI", 11),
             fg="#cdd6f4", bg="#1e1e2e", wraplength=380, justify="center").pack(pady=5)

    btn = tk.Button(win, text="", font=("Segoe UI", 11), state="disabled",
                    width=16, command=win.destroy)
    btn.pack(pady=25)

    def tick(n):
        if not win.winfo_exists():
            return
        if n > 0:
            btn.config(text=f"Play Anyway ({n})")
            win.after(1000, tick, n - 1)
        else:
            btn.config(text="Play Anyway", state="normal")

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
                show_popup(root, events.get_nowait())
        except queue.Empty:
            pass
        root.after(300, poll)

    poll()
    root.mainloop()


if __name__ == "__main__":
    main()