#!/usr/bin/env python3
"""Small Tkinter front-end for the first Music Replacer MVP."""
from __future__ import annotations
import json
import shutil
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

ROOT = Path(__file__).resolve().parent
PATCHER = ROOT / "patch_stq.py"
BUILD = "0005"

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"DDDA Music Replacer — MVP build {BUILD}")
        self.geometry("720x430")
        self.minsize(680, 390)
        self.configure(bg="#f4f5f7")
        self.archive = tk.StringVar(value="title.arc")
        self.source_key = tk.StringVar(value=r"bgm\wave2\Tittle_DDN")
        self.stq = tk.StringVar()
        self.audio = tk.StringVar()
        self.output = tk.StringVar()
        self.loop = tk.StringVar(value="full")
        self.status = tk.StringVar(value="Выберите STQ, replacement-файл и папку результата.")
        self._style()
        self._build()

    def _style(self):
        s = ttk.Style(self)
        try: s.theme_use("clam")
        except tk.TclError: pass
        s.configure("TFrame", background="#f4f5f7")
        s.configure("Card.TFrame", background="#ffffff")
        s.configure("Title.TLabel", background="#f4f5f7", foreground="#1d2433", font=("Segoe UI", 18, "bold"))
        s.configure("Sub.TLabel", background="#f4f5f7", foreground="#5c6575", font=("Segoe UI", 10))
        s.configure("TLabel", background="#ffffff", foreground="#283142", font=("Segoe UI", 10))
        s.configure("Hint.TLabel", background="#ffffff", foreground="#687386", font=("Segoe UI", 9))
        s.configure("Accent.TButton", font=("Segoe UI", 10, "bold"), padding=(14, 8))
        s.configure("TButton", padding=(10, 6))

    def _build(self):
        outer = ttk.Frame(self, padding=24); outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="DDDA Music Replacer", style="Title.TLabel").pack(anchor="w")
        ttk.Label(outer, text="MVP: подготовка replacement-трека и патчинг STQ", style="Sub.TLabel").pack(anchor="w", pady=(2, 18))
        card = ttk.Frame(outer, style="Card.TFrame", padding=18); card.pack(fill="both", expand=True)
        self._row(card, 0, "Извлечённый STQ", self.stq, "Файл Tittle_bgm.stq")
        self._row(card, 1, "Replacement audio", self.audio, "OGG/Vorbis; на выходе получит .sngw")
        self._row(card, 2, "Папка результата", self.output, "Будет создана готовая структура nativePC")
        ttk.Label(card, text="Loop", style="TLabel").grid(row=3, column=0, sticky="w", pady=(16, 4))
        box = ttk.Combobox(card, textvariable=self.loop, values=("full", "none"), state="readonly", width=16)
        box.grid(row=3, column=1, sticky="w", pady=(16, 4))
        ttk.Label(card, text="full = повтор от начала до конца replacement", style="Hint.TLabel").grid(row=3, column=2, sticky="w", padx=(12, 0), pady=(16, 4))
        ttk.Separator(card).grid(row=4, column=0, columnspan=3, sticky="ew", pady=18)
        ttk.Label(card, text="Текущий MVP работает с титлом: bgm\\wave2\\Tittle_DDN", style="Hint.TLabel").grid(row=5, column=0, columnspan=3, sticky="w")
        ttk.Button(card, text="Собрать replacement", style="Accent.TButton", command=self.build).grid(row=6, column=2, sticky="e", pady=(22, 0))
        ttk.Label(outer, textvariable=self.status, style="Sub.TLabel", wraplength=660).pack(anchor="w", pady=(12, 0))
        card.columnconfigure(1, weight=1)
        card.columnconfigure(2, weight=1)

    def _row(self, parent, row, label, var, hint):
        ttk.Label(parent, text=label, style="TLabel").grid(row=row, column=0, sticky="w", pady=7)
        ttk.Entry(parent, textvariable=var).grid(row=row, column=1, sticky="ew", padx=(16, 8), pady=7)
        ttk.Button(parent, text="Выбрать…", command=lambda r=row: self.pick(r)).grid(row=row, column=2, pady=7)
        ttk.Label(parent, text=hint, style="Hint.TLabel").grid(row=row+0, column=3, sticky="w", padx=(10, 0), pady=7)

    def pick(self, row):
        if row == 0:
            p = filedialog.askopenfilename(title="Выберите извлечённый STQ", filetypes=[("STQ", "*.stq"), ("Все файлы", "*.*")])
            if p: self.stq.set(p)
        elif row == 1:
            p = filedialog.askopenfilename(title="Выберите replacement OGG/Vorbis", filetypes=[("Audio", "*.ogg *.sngw"), ("Все файлы", "*.*")])
            if p: self.audio.set(p)
        else:
            p = filedialog.askdirectory(title="Выберите папку результата")
            if p: self.output.set(p)

    def build(self):
        if not all((self.source_key.get(), self.stq.get(), self.audio.get(), self.output.get())):
            messagebox.showwarning("Не хватает данных", "Укажите ключ трека и выберите STQ, replacement audio и папку результата.")
            return
        out_root = Path(self.output.get())
        out_root.mkdir(parents=True, exist_ok=True)
        archive_dir = "title" if self.archive.get() == "title.arc" else "main"
        stq_name = "Tittle_bgm.stq" if self.archive.get() == "title.arc" else "bgm.stq"
        out_stq = out_root / "patched" / stq_name
        try:
            audio_path = Path(self.audio.get())
            # tittleddn_b.ogg -> DDDA_AI_Overhaul\\music\\title\\tittleddn_b
            # Для bbs_rpg тот же принцип, но каталог replacement = main.
            stem = audio_path.stem
            target_name = "DDDA_AI_Overhaul\\music\\" + archive_dir + "\\" + stem
            cmd = [sys.executable, str(PATCHER), self.stq.get(), self.audio.get(),
                   "--source", self.source_key.get(), "--out", str(out_stq),
                   "--target", target_name, "--loop", self.loop.get()]
            proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
            if proc.returncode:
                raise RuntimeError(proc.stderr.strip() or proc.stdout.strip())
            report = json.loads(proc.stdout)
            # The game resolves STQ names below nativePC/sound/stream and adds .sngw.
            target = out_root / "nativePC" / "sound" / "stream" / "DDDA_AI_Overhaul" / "music" / archive_dir / (stem + ".sngw")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(audio_path, target)
            report["archive"] = self.archive.get()
            report["source_key"] = self.source_key.get()
            report["target_directory"] = archive_dir
            (out_root / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            self.status.set(f"Готово. STQ: {out_stq}\nSNGW: {target}\nТеперь замените STQ внутри {self.archive.get()} вручную.")
            messagebox.showinfo("Готово", f"Replacement подготовлен.\n\nSTQ пока нужно вручную вернуть в {self.archive.get()}.")
        except Exception as e:
            self.status.set("Ошибка: " + str(e))
            messagebox.showerror("Сборка не выполнена", str(e))

if __name__ == "__main__":
    App().mainloop()
