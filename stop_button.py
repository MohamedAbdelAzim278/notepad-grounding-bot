import threading
import tkinter as tk

_stop_event = threading.Event()


def is_stopped() -> bool:
    return _stop_event.is_set()


def _on_stop(root: tk.Tk):
    _stop_event.set()
    root.destroy()


def run_stop_button():
    """Show an always-on-top Stop button. Blocks until the window is closed."""
    root = tk.Tk()
    root.title("Bot Control")
    root.attributes("-topmost", True)
    root.resizable(False, False)
    root.overrideredirect(True)  # borderless

    screen_w = root.winfo_screenwidth()
    root.geometry(f"110x40+{screen_w - 120}+10")

    btn = tk.Button(
        root,
        text="⏹  Stop Bot",
        command=lambda: _on_stop(root),
        bg="#e53935",
        fg="white",
        font=("Segoe UI", 10, "bold"),
        relief="flat",
        cursor="hand2",
        activebackground="#b71c1c",
        activeforeground="white",
        bd=0,
    )
    btn.pack(fill="both", expand=True)

    root.protocol("WM_DELETE_WINDOW", lambda: _on_stop(root))
    root.mainloop()
