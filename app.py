#!/usr/bin/env python3
"""DDDA Music Replacer — build 0006: simple STQ slot browser."""
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
ROLES_FILE = ROOT / "catalog" / "known_roles.json"
BUILD = "0006"

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"DDDA Music Replacer — build {BUILD}")
        self.geometry("1050x690")
        self.minsize(880, 560)
        self.configure(bg="#f4f5f7")
        self.archive = tk.StringVar(value="title.arc")
        self.stq = tk.StringVar()
        self.audio = tk.StringVar()
        self.output = tk.StringVar()
        self.search = tk.StringVar()
        self.loop_policy = tk.StringVar(value="auto")
        self.status = tk.StringVar(value="Выберите STQ и нажмите «Загрузить слоты».")
        self.detail = tk.StringVar(value="Слот не выбран.")
        self.description = tk.StringVar()
        self.rows = []
        self.visible_rows = []
        self.roles = self._load_roles()
        self._style()
        self._build()
        self.search.trace_add("write", lambda *_: self._refresh_tree())

    def _load_roles(self):
        try:
            return json.loads(ROLES_FILE.read_text(encoding="utf-8")).get("roles", {})
        except (OSError, ValueError):
            return {}

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
        s.configure("Treeview", rowheight=27, font=("Segoe UI", 9))
        s.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))

    def _build(self):
        outer = ttk.Frame(self, padding=22); outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="DDDA Music Replacer", style="Title.TLabel").pack(anchor="w")
        ttk.Label(outer, text=f"Slot browser · build {BUILD}", style="Sub.TLabel").pack(anchor="w", pady=(2, 14))
        top = ttk.Frame(outer, style="Card.TFrame", padding=14); top.pack(fill="x")
        ttk.Label(top, text="Архив", style="TLabel").grid(row=0, column=0, sticky="w")
        ttk.Combobox(top, textvariable=self.archive, values=("title.arc", "bbs_rpg.arc"), state="readonly", width=16).grid(row=0, column=1, padx=(12, 10), sticky="w")
        ttk.Label(top, text="STQ", style="TLabel").grid(row=0, column=2, sticky="w")
        ttk.Entry(top, textvariable=self.stq).grid(row=0, column=3, padx=(10, 8), sticky="ew")
        ttk.Button(top, text="Выбрать…", command=self.pick_stq).grid(row=0, column=4, padx=(0, 8))
        ttk.Button(top, text="Загрузить слоты", style="Accent.TButton", command=self.load_stq).grid(row=0, column=5)
        top.columnconfigure(3, weight=1)

        filters = ttk.Frame(outer, style="Card.TFrame", padding=(14, 10)); filters.pack(fill="x", pady=(10, 0))
        ttk.Label(filters, text="Поиск", style="TLabel").pack(side="left")
        ttk.Entry(filters, textvariable=self.search, width=34).pack(side="left", padx=(10, 18))
        ttk.Label(filters, text="Можно искать по label, описанию или роли", style="Hint.TLabel").pack(side="left")

        card = ttk.Frame(outer, style="Card.TFrame", padding=12); card.pack(fill="both", expand=True, pady=(10, 0))
        self.tree = ttk.Treeview(card, columns=("slot", "label", "description", "duration", "channels", "loop"), show="headings", selectmode="browse")
        headings = {"slot": "Slot", "label": "Original label", "description": "Описание", "duration": "Длительность", "channels": "Ch", "loop": "Loop"}
        widths = {"slot": 52, "label": 245, "description": 270, "duration": 100, "channels": 48, "loop": 145}
        for col in headings:
            self.tree.heading(col, text=headings[col])
            self.tree.column(col, width=widths[col], anchor="w")
        yscroll = ttk.Scrollbar(card, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=yscroll.set)
        self.tree.grid(row=0, column=0, sticky="nsew"); yscroll.grid(row=0, column=1, sticky="ns")
        self.tree.bind("<<TreeviewSelect>>", self.select_slot)
        card.rowconfigure(0, weight=1); card.columnconfigure(0, weight=1)

        detail = ttk.Frame(outer, style="Card.TFrame", padding=14); detail.pack(fill="x", pady=(10, 0))
        self.detail_label = ttk.Label(detail, textvariable=self.detail, style="TLabel", wraplength=920)
        self.detail_label.grid(row=0, column=0, columnspan=4, sticky="w")
        ttk.Label(detail, text="Описание слота", style="TLabel").grid(row=1, column=0, sticky="w", pady=(12, 4))
        ttk.Entry(detail, textvariable=self.description).grid(row=1, column=1, columnspan=3, sticky="ew", padx=(12, 0), pady=(12, 4))
        ttk.Label(detail, text="Loop policy", style="TLabel").grid(row=2, column=0, sticky="w", pady=4)
        ttk.Combobox(detail, textvariable=self.loop_policy, values=("auto", "full", "none"), state="readonly", width=14).grid(row=2, column=1, sticky="w", padx=(12, 8), pady=4)
        ttk.Label(detail, text="auto: сохранить one-shot/loop-смысл оригинального слота", style="Hint.TLabel").grid(row=2, column=2, columnspan=2, sticky="w", pady=4)
        ttk.Label(detail, text="Replacement", style="TLabel").grid(row=3, column=0, sticky="w", pady=4)
        ttk.Entry(detail, textvariable=self.audio).grid(row=3, column=1, columnspan=2, sticky="ew", padx=(12, 8), pady=4)
        ttk.Button(detail, text="Выбрать…", command=self.pick_audio).grid(row=3, column=3, sticky="e", pady=4)
        ttk.Label(detail, text="Output", style="TLabel").grid(row=4, column=0, sticky="w", pady=4)
        ttk.Entry(detail, textvariable=self.output).grid(row=4, column=1, columnspan=2, sticky="ew", padx=(12, 8), pady=4)
        ttk.Button(detail, text="Выбрать…", command=self.pick_output).grid(row=4, column=3, sticky="e", pady=4)
        ttk.Button(detail, text="Подготовить replacement выбранного слота", style="Accent.TButton", command=self.build).grid(row=5, column=3, sticky="e", pady=(12, 0))
        detail.columnconfigure(1, weight=1); detail.columnconfigure(2, weight=1)
        ttk.Label(outer, textvariable=self.status, style="Sub.TLabel", wraplength=1000).pack(anchor="w", pady=(10, 0))

    def pick_stq(self):
        p = filedialog.askopenfilename(title="Выберите извлечённый STQ", filetypes=[("STQ", "*.stq"), ("Все файлы", "*.*")])
        if p: self.stq.set(p)

    def pick_audio(self):
        p = filedialog.askopenfilename(title="Выберите replacement OGG/Vorbis", filetypes=[("Audio", "*.ogg *.sngw"), ("Все файлы", "*.*")])
        if p: self.audio.set(p)

    def pick_output(self):
        p = filedialog.askdirectory(title="Выберите папку результата")
        if p: self.output.set(p)

    def load_stq(self):
        if not self.stq.get():
            messagebox.showwarning("Нет STQ", "Сначала выберите извлечённый STQ.")
            return
        try:
            # Import the proven parser from the MVP core.
            sys.path.insert(0, str(ROOT))
            from patch_stq import read_stq
            _, self.rows = read_stq(Path(self.stq.get()))
            self._refresh_tree()
            self.status.set(f"Загружено слотов: {len(self.rows)}. Выберите запись в таблице.")
        except Exception as e:
            self.rows = []; self._refresh_tree()
            messagebox.showerror("STQ не загружен", str(e))

    def _role(self, name):
        base = name.replace("/", "\\").rstrip("\\").split("\\")[-1]
        return self.roles.get(base, "Назначение не установлено")

    def _refresh_tree(self):
        if not hasattr(self, "tree"): return
        for item in self.tree.get_children(): self.tree.delete(item)
        needle = self.search.get().strip().lower()
        self.visible_rows = []
        for r in self.rows:
            desc = self._role(r["name"])
            hay = f"{r['index']} {r['name']} {desc}".lower()
            if needle and needle not in hay: continue
            loop = "one-shot" if r["loop_in"] is None else f"{r['loop_in']/48000:.1f} → {r['loop_out']/48000:.1f}s"
            item = self.tree.insert("", "end", values=(r["index"], r["name"], desc, f"{r['samples']/48000:.1f}s", r["channels"], loop))
            self.visible_rows.append((item, r))

    def select_slot(self, _event=None):
        selected = self.tree.selection()
        if not selected: return
        item = selected[0]
        row = next((r for iid, r in self.visible_rows if iid == item), None)
        if row is None: return
        self.selected_row = row
        desc = self._role(row["name"])
        loop = "one-shot" if row["loop_in"] is None else f"{row['loop_in']} → {row['loop_out']} samples"
        self.detail.set(f"Slot #{row['index']} · {row['name']}\n{desc}\n{row['channels']} channels · {row['samples']} samples · {loop}")
        self.description.set(desc)
        self.loop_policy.set("none" if row["loop_in"] is None else "full")

    def build(self):
        row = getattr(self, "selected_row", None)
        if row is None:
            messagebox.showwarning("Нет слота", "Выберите слот в таблице."); return
        if not all((self.audio.get(), self.output.get())):
            messagebox.showwarning("Не хватает данных", "Выберите replacement audio и папку результата."); return
        out_root = Path(self.output.get()); out_root.mkdir(parents=True, exist_ok=True)
        archive_dir = "title" if self.archive.get() == "title.arc" else "main"
        stq_name = "Tittle_bgm.stq" if self.archive.get() == "title.arc" else "bgm.stq"
        out_stq = out_root / "patched" / stq_name
        audio_path = Path(self.audio.get()); stem = audio_path.stem
        target_name = "DDDA_AI_Overhaul\\music\\" + archive_dir + "\\" + stem
        policy = self.loop_policy.get()
        loop = ("none" if policy == "none" else "full")
        cmd = [sys.executable, str(PATCHER), self.stq.get(), self.audio.get(), "--source", row["name"], "--out", str(out_stq), "--target", target_name, "--loop", loop]
        try:
            proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
            if proc.returncode: raise RuntimeError(proc.stderr.strip() or proc.stdout.strip())
            report = json.loads(proc.stdout); report["archive"] = self.archive.get(); report["slot_index"] = row["index"]; report["description"] = self.description.get()
            target = out_root / "nativePC" / "sound" / "stream" / "DDDA_AI_Overhaul" / "music" / archive_dir / (stem + ".sngw")
            target.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(audio_path, target)
            (out_root / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            self.status.set(f"Готово. Slot #{row['index']}\nSTQ: {out_stq}\nSNGW: {target}\nARC пока заменяется вручную.")
            messagebox.showinfo("Готово", f"Replacement подготовлен.\n\nSTQ пока нужно вернуть в {self.archive.get()}.")
        except Exception as e:
            self.status.set("Ошибка: " + str(e)); messagebox.showerror("Сборка не выполнена", str(e))

if __name__ == "__main__":
    App().mainloop()
