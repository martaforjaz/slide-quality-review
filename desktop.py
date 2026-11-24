"""Desktop entry point for private slide folders."""
from pathlib import Path
from queue import Empty, Queue
import hashlib
import os
from threading import Thread
from tkinter import Button, Entry, Label, StringVar, Tk, filedialog
import webbrowser

from review_folder import report

root = Tk()
root.title("Slide Quality Review")
root.columnconfigure(0, weight=1)
folder = StringVar()
status = StringVar(value="Paste a local or network folder path, or browse for it.")
results = Queue()

Label(root, text="Folder containing whole-slide images").grid(row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(12,4))
entry = Entry(root, textvariable=folder, width=75)
entry.grid(row=1, column=0, sticky="ew", padx=12)
entry.focus_set()


def browse():
    selected = filedialog.askdirectory()
    if selected:
        folder.set(selected)


Button(root, text="Browse", command=browse).grid(row=1, column=1, padx=(0,12))


def review():
    value = folder.get().strip().strip('"')
    if not value:
        status.set("Enter a folder path.")
        return
    run["state"] = "disabled"
    status.set("Sampling slides and building PNG previews…")

    def process():
        try:
            source = Path(value).expanduser().resolve()
            key = hashlib.sha256(str(source).encode()).hexdigest()[:16]
            location = Path(os.getenv("LOCALAPPDATA", Path.home())) / "SlideQualityReview" / key
            done, errors = report(source, location)
            results.put((location, f"{done} slides reviewed. {errors} unreadable."))
        except (ValueError, OSError) as exc:
            results.put((None, str(exc)))

    Thread(target=process, daemon=True).start()
    root.after(100, poll)


def poll():
    try:
        location, message = results.get_nowait()
    except Empty:
        root.after(100, poll)
        return
    status.set(message)
    run["state"] = "normal"
    if location:
        webbrowser.open((location / "index.html").as_uri())


run = Button(root, text="Review folder", command=review)
run.grid(row=2, column=0, sticky="w", padx=12, pady=8)
Label(root, textvariable=status, wraplength=550, justify="left").grid(row=3, column=0, columnspan=2, sticky="w", padx=12, pady=(0,12))
root.bind("<Return>", lambda _: review() if run["state"]=="normal" else None)
root.mainloop()
