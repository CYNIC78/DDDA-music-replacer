#!/usr/bin/env python3
"""DDDA Music Replacer — build 0007: editable, sortable slot table."""
from __future__ import annotations
import json, shutil, subprocess, sys, tempfile, threading, tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

ROOT = Path(__file__).resolve().parent
PATCHER = ROOT / "patch_stq.py"
ROLES_FILE = ROOT / "catalog" / "known_roles.json"
BUILD = "0021"
DEFAULT_NAMESPACE = "DDDA_Music_Replacer"

class App(tk.Tk):
    def __init__(self):
        super().__init__(); self.title(f"DDDA Music Replacer — build {BUILD}")
        self.geometry("1180x660"); self.minsize(960, 520); self.configure(bg="#f4f5f7")
        sys.path.insert(0, str(ROOT))
        from core.settings import load as load_settings
        self.settings=load_settings()
        self.archive=tk.StringVar(value="title.arc"); self.namespace=tk.StringVar(value=DEFAULT_NAMESPACE); self.game_root=tk.StringVar(value=self.settings.get("last_game_root", "")); self.arctool=tk.StringVar(value=self.settings.get("arctool_path", "")); self.stq=tk.StringVar(); self.output=tk.StringVar(value=self.settings.get("last_build_output", "")); self.search=tk.StringVar(); self.game_status=tk.StringVar(value="Папка игры не выбрана."); self.unpack_status=tk.StringVar(value="")
        self.protocol("WM_DELETE_WINDOW", self.close_app)
        self.unpack_busy=False
        self.status=tk.StringVar(value="Выберите архив и нажмите «Распаковать и загрузить».")
        self.rows=[]; self.visible_rows=[]; self.selected_row=None; self.sort_col=None; self.sort_reverse=False
        self.archive_states={}; self.project_file=""
        self.roles=self._load_roles(); self._style(); self._build(); self.search.trace_add("write", lambda *_: self._refresh_tree())

    def _load_roles(self):
        try: return json.loads(ROLES_FILE.read_text(encoding="utf-8")).get("roles", {})
        except (OSError, ValueError): return {}

    def _style(self):
        s=ttk.Style(self)
        try: s.theme_use("clam")
        except tk.TclError: pass
        s.configure("TFrame", background="#f4f5f7"); s.configure("Card.TFrame", background="#fff")
        s.configure("Title.TLabel", background="#f4f5f7", foreground="#1d2433", font=("Segoe UI",15,"bold"))
        s.configure("Sub.TLabel", background="#f4f5f7", foreground="#5c6575", font=("Segoe UI",10))
        s.configure("TLabel", background="#fff", foreground="#283142", font=("Segoe UI",10))
        s.configure("Hint.TLabel", background="#fff", foreground="#687386", font=("Segoe UI",9))
        s.configure("Accent.TButton", font=("Segoe UI",10,"bold"), padding=(14,8))
        s.configure("Treeview", rowheight=26, font=("Segoe UI",9)); s.configure("Treeview.Heading", font=("Segoe UI",9,"bold"))

    def _build(self):
        outer=ttk.Frame(self,padding=14); outer.pack(fill="both",expand=True)
        ttk.Label(outer,text="DDDA Music Replacer",style="Title.TLabel").pack(anchor="w")
        ttk.Label(outer,text=f"Slot browser · build {BUILD}",style="Sub.TLabel").pack(anchor="w",pady=(1,7))
        top=ttk.Frame(outer,style="Card.TFrame",padding=9); top.pack(fill="x")
        ttk.Label(top,text="Архив",style="TLabel").grid(row=0,column=0,sticky="w")
        self.archive_box=ttk.Combobox(top,textvariable=self.archive,values=("title.arc","bbs_rpg.arc"),state="readonly",width=16)
        self.archive_box.grid(row=0,column=1,padx=(10,14),sticky="w"); self.archive_box.bind("<<ComboboxSelected>>", self.switch_archive)
        ttk.Label(top,text="Найденный STQ",style="TLabel").grid(row=0,column=2,sticky="w")
        ttk.Entry(top,textvariable=self.stq,state="readonly").grid(row=0,column=3,padx=(10,8),sticky="ew")
        ttk.Button(top,text="Загрузить слоты",style="Accent.TButton",command=self.load_stq).grid(row=0,column=4,padx=(0,8))
        ttk.Button(top,text="Сохранить проект",command=self.save_project).grid(row=0,column=5,padx=(0,6)); ttk.Button(top,text="Загрузить проект",command=self.load_project).grid(row=0,column=6)
        top.columnconfigure(3,weight=1)
        ttk.Label(top,text="Namespace",style="TLabel").grid(row=1,column=0,sticky="w",pady=(5,0))
        ttk.Entry(top,textvariable=self.namespace).grid(row=1,column=1,columnspan=3,padx=(10,8),sticky="ew",pady=(5,0))
        ttk.Label(top,text="папка под nativePC\\sound\\stream",style="Hint.TLabel").grid(row=1,column=4,columnspan=4,sticky="w",pady=(5,0))
        ttk.Label(top,text="Game root",style="TLabel").grid(row=2,column=0,sticky="w",pady=(5,0))
        ttk.Entry(top,textvariable=self.game_root).grid(row=2,column=1,columnspan=3,padx=(10,8),sticky="ew",pady=(5,0))
        ttk.Button(top,text="Выбрать…",command=self.pick_game_root).grid(row=2,column=4,padx=(0,8),pady=(5,0))
        ttk.Button(top,text="Проверить игру",command=self.scan_game_root).grid(row=2,column=5,columnspan=2,pady=(5,0))
        ttk.Label(top,textvariable=self.game_status,style="Hint.TLabel").grid(row=3,column=0,columnspan=8,sticky="w",pady=(4,0))
        ttk.Label(top,text="ARCtool.exe",style="TLabel").grid(row=4,column=0,sticky="w",pady=(5,0))
        ttk.Entry(top,textvariable=self.arctool).grid(row=4,column=1,columnspan=3,padx=(10,8),sticky="ew",pady=(5,0))
        ttk.Button(top,text="Выбрать…",command=self.pick_arctool).grid(row=4,column=4,padx=(0,8),pady=(5,0))
        self.unpack_button=ttk.Button(top,text="Распаковать и загрузить",command=self.unpack_selected)
        self.unpack_button.grid(row=4,column=5,columnspan=2,pady=(5,0))
        ttk.Label(top,textvariable=self.unpack_status,style="Hint.TLabel").grid(row=5,column=0,columnspan=8,sticky="w",pady=(4,0))
        filters=ttk.Frame(outer,style="Card.TFrame",padding=(12,9)); filters.pack(fill="x",pady=(5,0))
        ttk.Label(filters,text="Поиск",style="TLabel").pack(side="left"); ttk.Entry(filters,textvariable=self.search,width=38).pack(side="left",padx=(10,14)); ttk.Label(filters,text="Нажмите заголовок для сортировки · двойной клик редактирует ячейку",style="Hint.TLabel").pack(side="left")
        card=ttk.Frame(outer,style="Card.TFrame",padding=10); card.pack(fill="both",expand=True,pady=(5,0))
        cols=("slot","label","description","duration","channels","loop","replacement")
        self.tree=ttk.Treeview(card,columns=cols,show="headings",selectmode="browse")
        heads={"slot":"Slot","label":"Original label","description":"Описание","duration":"Длительность","channels":"Ch","loop":"Loop","replacement":"Replacement"}
        widths={"slot":52,"label":245,"description":270,"duration":95,"channels":42,"loop":145,"replacement":220}
        for c in cols:
            self.tree.heading(c,text=heads[c],command=lambda x=c:self.sort_by(x)); self.tree.column(c,width=widths[c],anchor="w")
        ys=ttk.Scrollbar(card,orient="vertical",command=self.tree.yview); xs=ttk.Scrollbar(card,orient="horizontal",command=self.tree.xview); self.tree.configure(yscrollcommand=ys.set,xscrollcommand=xs.set)
        self.tree.grid(row=0,column=0,sticky="nsew"); ys.grid(row=0,column=1,sticky="ns"); xs.grid(row=1,column=0,sticky="ew"); card.rowconfigure(0,weight=1); card.columnconfigure(0,weight=1)
        self.tree.bind("<<TreeviewSelect>>",self.select_slot); self.tree.bind("<Double-1>",self.double_click)
        bottom=ttk.Frame(outer,style="Card.TFrame",padding=12); bottom.pack(fill="x",pady=(5,0))
        ttk.Label(bottom,text="Build output",style="TLabel").grid(row=0,column=0,sticky="w"); ttk.Entry(bottom,textvariable=self.output).grid(row=0,column=1,padx=(12,8),sticky="ew"); ttk.Button(bottom,text="Выбрать…",command=self.pick_output).grid(row=0,column=2,padx=(0,8)); ttk.Button(bottom,text="Собрать пакет",style="Accent.TButton",command=self.build_project).grid(row=0,column=3,padx=(0,6)); ttk.Button(bottom,text="Установить мод",command=self.install_project).grid(row=0,column=4,padx=(0,6)); ttk.Button(bottom,text="Откатить последнюю",command=self.restore_project).grid(row=0,column=5,padx=(0,6)); ttk.Button(bottom,text="Удалить мод",command=self.restore_vanilla).grid(row=0,column=6)
        ttk.Label(bottom,text="Replacement и loop редактируются прямо в таблице. ARC собирается автоматически в Build output.",style="Hint.TLabel").grid(row=1,column=0,columnspan=7,sticky="w",pady=(5,0)); bottom.columnconfigure(1,weight=1)
        ttk.Label(outer,textvariable=self.status,style="Sub.TLabel",wraplength=1100).pack(anchor="w",pady=(5,0))

    def _capture_state(self):
        return {"stq": self.stq.get(), "output": self.output.get(), "rows": [dict(r) for r in self.rows]}

    def _save_current_state(self):
        self.archive_states[self.archive.get()] = self._capture_state()

    def _restore_state(self, archive):
        state = self.archive_states.get(archive, {"stq": "", "output": "", "rows": []})
        self.stq.set(state.get("stq", "")); self.output.set(state.get("output", ""))
        self.rows = [dict(r) for r in state.get("rows", [])]
        self.visible_rows=[]; self.selected_row=None; self._refresh_tree()
        self.status.set(f"Состояние {archive} восстановлено. Слотов загружено: {len(self.rows)}.")

    def switch_archive(self, _event=None):
        # Combobox has already changed self.archive; save the previous state
        # before the switch is normally handled by remembering it in the event.
        # For the MVP we keep both state snapshots whenever a loaded table exists.
        current = self.archive.get()
        other = "bbs_rpg.arc" if current == "title.arc" else "title.arc"
        if self.rows or self.stq.get():
            self.archive_states[other] = self._capture_state()
        self._restore_state(current)

    def validate_namespace(self):
        value=self.namespace.get().strip()
        bad=set('\\/:*?"<>|')
        if not value: raise ValueError("namespace не может быть пустым")
        if value in (".", "..") or ".." in value or any(ch in bad for ch in value) or any(ord(ch)>127 for ch in value):
            raise ValueError("namespace должен быть относительным ASCII-именем без запрещённых символов и ..")
        if len(value)>48: raise ValueError("namespace длиннее 48 символов")
        return value

    def save_project(self):
        self._save_current_state()
        from core.settings import existing_dir
        p = filedialog.asksaveasfilename(title="Сохранить проект", initialdir=existing_dir(self.settings.get("last_project_dir")), defaultextension=".json", filetypes=[("Music project", "*.json"), ("Все файлы", "*.*")])
        if not p: return
        payload = {"schema": 1, "build": BUILD, "namespace": self.namespace.get(), "arctool": self.arctool.get(), "game_root": self.game_root.get(), "active_archive": self.archive.get(), "archives": self.archive_states}
        try:
            Path(p).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            self.project_file=p; self.settings["last_project_dir"]=str(Path(p).parent); self.save_settings(); self.status.set(f"Проект сохранён: {p}")
        except OSError as e: messagebox.showerror("Проект не сохранён", str(e))

    def load_project(self):
        from core.settings import existing_dir
        p = filedialog.askopenfilename(title="Загрузить проект", initialdir=existing_dir(self.settings.get("last_project_dir")), filetypes=[("Music project", "*.json"), ("Все файлы", "*.*")])
        if not p: return
        try:
            payload=json.loads(Path(p).read_text(encoding="utf-8"))
            if payload.get("schema") != 1: raise ValueError("неизвестная версия project JSON")
            self.archive_states=payload.get("archives", {}); self.namespace.set(payload.get("namespace", DEFAULT_NAMESPACE)); self.arctool.set(payload.get("arctool", "")); self.game_root.set(payload.get("game_root", "")); self.validate_namespace(); active=payload.get("active_archive", "title.arc")
            if active not in ("title.arc", "bbs_rpg.arc"): active="title.arc"
            self.archive.set(active); self.archive_box.set(active); self.project_file=p; self.settings["last_project_dir"]=str(Path(p).parent); self.save_settings(); self._restore_state(active)
            self.status.set(f"Проект загружен: {p}. Можно продолжить настройку.")
        except (OSError, ValueError, TypeError) as e: messagebox.showerror("Проект не загружен", str(e))

    def save_settings(self):
        from core.settings import save
        data=dict(self.settings)
        if self.game_root.get(): data["last_game_root"]=self.game_root.get()
        if self.arctool.get(): data["arctool_path"]=self.arctool.get()
        if self.output.get(): data["last_build_output"]=self.output.get()
        data.setdefault("last_audio_dir", {})
        save(data); self.settings=data

    def close_app(self):
        try: self.save_settings()
        finally: self.destroy()

    def dialog_dir(self, key, fallback=None):
        from core.settings import existing_dir
        return existing_dir(self.settings.get(key), fallback)

    def pick_arctool(self):
        p=filedialog.askopenfilename(title="Выберите ARCtool.exe",initialdir=self.dialog_dir("arctool_path"),filetypes=[("ARCtool", "ARCtool.exe"), ("EXE", "*.exe"), ("Все файлы", "*.*")])
        if p: self.arctool.set(p); self.save_settings()

    def unpack_selected(self):
        if self.unpack_busy: return
        if not self.game_root.get():
            messagebox.showwarning("Нет папки игры", "Сначала выберите корень игры."); return
        self.unpack_busy=True; self.unpack_button.configure(state="disabled"); self.unpack_status.set(f"Распаковка {self.archive.get()} в фоне…")
        threading.Thread(target=self._unpack_worker, daemon=True).start()

    def _unpack_worker(self):
        try:
            sys.path.insert(0,str(ROOT))
            from core.arc_adapter import discover_game_root, find_arctool, unpack, locate_stq, inspect_stq
            info=discover_game_root(Path(self.game_root.get()))
            archive_name=self.archive.get(); arc=info["title"] if archive_name=="title.arc" else info["bbs_rpg"]
            tool=find_arctool(self.arctool.get().strip() or None, ROOT)
            work_base=Path(self.output.get()) if self.output.get() else ROOT
            work=work_base / "work" / archive_name.replace(".arc", "")
            if work.exists(): shutil.rmtree(work)
            unpack(arc, work, tool)
            stq=locate_stq(work, archive_name); check=inspect_stq(stq, archive_name)
            self.after(0, lambda: self._unpack_done(stq, check))
        except Exception as e:
            self.after(0, lambda: self._unpack_failed(str(e)))

    def _unpack_done(self, stq, check):
        self.unpack_busy=False; self.unpack_button.configure(state="normal"); self.stq.set(str(stq)); self.load_stq()
        suffix=(" Предупреждение: "+check["warning"]) if check.get("warning") else ""
        self.unpack_status.set(f"STQ найден: {stq.name}; слотов: {check['count']}.{suffix}")

    def _unpack_failed(self, error):
        self.unpack_busy=False; self.unpack_button.configure(state="normal"); self.unpack_status.set("Распаковка не выполнена")
        messagebox.showerror("ARCtool / STQ", error)

    def pick_game_root(self):
        p=filedialog.askdirectory(title="Выберите корень игры Dragon's Dogma",initialdir=self.dialog_dir("last_game_root"))
        if p: self.game_root.set(p); self.save_settings(); self.scan_game_root()

    def scan_game_root(self):
        if not self.game_root.get():
            messagebox.showwarning("Нет папки игры","Выберите корень игры."); return
        try:
            sys.path.insert(0,str(ROOT)); from core.arc_adapter import discover_game_root
            info=discover_game_root(Path(self.game_root.get()))
            found=[]
            for key,label in (("title","title.arc"),("bbs_rpg","bbs_rpg.arc")):
                found.append(f"✓ {label}" if info[key].is_file() else f"— {label} не найден")
            self.game_status.set("  ".join(found)+"  |  Источник только для чтения")
        except Exception as e:
            self.game_status.set("Ошибка проверки: "+str(e)); messagebox.showerror("Неверный корень игры",str(e))

    def pick_stq(self):
        key="title" if self.archive.get()=="title.arc" else "main"; dirs=self.settings.setdefault("last_stq_dir", {})
        from core.settings import existing_dir
        p=filedialog.askopenfilename(title="Выберите извлечённый STQ",initialdir=existing_dir(dirs.get(key)),filetypes=[("STQ","*.stq"),("Все файлы","*.*")])
        if p: self.stq.set(p); dirs[key]=str(Path(p).parent); self.save_settings()
    def pick_output(self):
        p=filedialog.askdirectory(title="Выберите папку сборки",initialdir=self.dialog_dir("last_build_output"))
        if p: self.output.set(p); self.save_settings()

    def load_stq(self):
        if not self.stq.get(): messagebox.showwarning("Нет STQ","Сначала выберите STQ."); return
        try:
            sys.path.insert(0,str(ROOT)); from patch_stq import read_stq
            _, self.rows=read_stq(Path(self.stq.get()))
            for r in self.rows:
                r["description"]=self._role(r["name"]); r["replacement"]=""; r["loop_mode"]="metadata" if r["loop_in"] is not None else "none"; r["custom_in"]=None; r["custom_out"]=None
            self._refresh_tree(); self.status.set(f"Загружено слотов: {len(self.rows)}. Replacement и loop настраиваются в строках таблицы.")
        except Exception as e: self.rows=[]; self._refresh_tree(); messagebox.showerror("STQ не загружен",str(e))

    def _role(self,name):
        base=name.replace("/","\\").rstrip("\\").split("\\")[-1]
        return self.roles.get(base,"Назначение не установлено")
    def _refresh_tree(self):
        if not hasattr(self,"tree"): return
        for i in self.tree.get_children(): self.tree.delete(i)
        needle=self.search.get().strip().lower(); rows=[r for r in self.rows if not needle or needle in f"{r['index']} {r['name']} {r['description']}".lower()]
        if self.sort_col:
            keymap={"slot":lambda r:r["index"],"label":lambda r:r["name"].lower(),"description":lambda r:r["description"].lower(),"duration":lambda r:r["samples"],"channels":lambda r:r["channels"],"loop":lambda r:0 if r["loop_mode"]=="none" else 1,"replacement":lambda r:r["replacement"].lower()}
            rows.sort(key=keymap[self.sort_col],reverse=self.sort_reverse)
        self.visible_rows=[]
        for r in rows:
            loop="one-shot" if r["loop_mode"]=="none" else (f"custom {r['custom_in']} → {r['custom_out']}" if r["loop_mode"]=="custom" else ("audio metadata" if r["loop_mode"]=="metadata" else "full cycle"))
            iid=self.tree.insert("","end",values=(r["index"],r["name"],r["description"],f"{r['samples']/48000:.1f}s",r["channels"],loop,Path(r["replacement"]).name if r["replacement"] else "—")); self.visible_rows.append((iid,r))

    def sort_by(self,col):
        self.sort_reverse=not self.sort_reverse if self.sort_col==col else False; self.sort_col=col; self._refresh_tree()
    def select_slot(self,_=None):
        s=self.tree.selection()
        if s: self.selected_row=next((r for i,r in self.visible_rows if i==s[0]),None)
    def double_click(self,event):
        row_id=self.tree.identify_row(event.y); col=self.tree.identify_column(event.x)
        if not row_id: return
        row=next((r for i,r in self.visible_rows if i==row_id),None)
        if not row: return
        if col=="#3": self.edit_description(row,row_id)
        elif col=="#6": self.edit_loop(row)
        elif col=="#7": self.choose_replacement(row)

    def edit_description(self,row,iid):
        bbox=self.tree.bbox(iid,"#3")
        if not bbox:return
        x,y,w,h=bbox; entry=tk.Entry(self.tree); entry.insert(0,row["description"]); entry.select_range(0,"end"); entry.place(x=x,y=y,width=w,height=h)
        entry.focus_set()
        def save(_=None): row["description"]=entry.get().strip() or "Назначение не установлено"; entry.destroy(); self._refresh_tree()
        entry.bind("<Return>",save); entry.bind("<Escape>",lambda _:entry.destroy()); entry.bind("<FocusOut>",save)

    def choose_replacement(self,row):
        category="title" if self.archive.get()=="title.arc" else "main"
        dirs=self.settings.setdefault("last_audio_dir", {})
        from core.settings import existing_dir
        p=filedialog.askopenfilename(title="Выберите replacement OGG/Vorbis",initialdir=existing_dir(dirs.get(category)),filetypes=[("Audio","*.ogg *.sngw"),("Все файлы","*.*")])
        if p:
            row["replacement"]=p; dirs[category]=str(Path(p).parent); self.save_settings(); self._refresh_tree()
    def edit_loop(self,row):
        win=tk.Toplevel(self); win.title(f"Loop · slot {row['index']}"); win.resizable(False,False); win.transient(self)
        mode=tk.StringVar(value=row["loop_mode"]); a=tk.StringVar(value="" if row["custom_in"] is None else str(row["custom_in"])); b=tk.StringVar(value="" if row["custom_out"] is None else str(row["custom_out"]))
        pad={"padx":12,"pady":6}; ttk.Label(win,text="Режим loop").grid(row=0,column=0,sticky="w",**pad); ttk.Combobox(win,textvariable=mode,values=("metadata","full","none","custom"),state="readonly",width=14).grid(row=0,column=1,**pad)
        ttk.Label(win,text="start samples").grid(row=1,column=0,sticky="w",**pad); ttk.Entry(win,textvariable=a,width=18).grid(row=1,column=1,**pad)
        ttk.Label(win,text="end samples").grid(row=2,column=0,sticky="w",**pad); ttk.Entry(win,textvariable=b,width=18).grid(row=2,column=1,**pad)
        def save():
            try:
                if mode.get()=="custom":
                    ai,bi=int(a.get()),int(b.get())
                    if not (0<=ai<bi): raise ValueError("loop points must satisfy 0 <= start < end; final range is checked against replacement audio")
                    row["custom_in"],row["custom_out"]=ai,bi
                row["loop_mode"]=mode.get(); win.destroy(); self._refresh_tree()
            except ValueError as e: messagebox.showerror("Неверный loop",str(e),parent=win)
        ttk.Button(win,text="Сохранить",command=save).grid(row=3,column=1,sticky="e",**pad)
        win.update_idletasks()
        x=self.winfo_rootx()+(self.winfo_width()-win.winfo_width())//2
        y=self.winfo_rooty()+(self.winfo_height()-win.winfo_height())//2
        win.geometry(f"+{max(0,x)}+{max(0,y)}")
        win.grab_set()

    def _extracted_root_from_stq(self, stq_path, archive_name):
        stem=archive_name.rsplit(".",1)[0].lower(); path=Path(stq_path).resolve()
        for parent in [path.parent, *path.parents]:
            if parent.name.lower()==stem: return parent
        return None

    def _run_patcher(self, source_stq, output_stq, row, namespace, category):
        audio=Path(row["replacement"]); stem=audio.stem
        target_name=f"{namespace}\\music\\{category}\\{stem}"
        loop=row["loop_mode"] if row["loop_mode"] in ("full","none","metadata") else "full"
        cmd=[sys.executable,str(PATCHER),str(source_stq),str(audio),"--index",str(row["index"]),"--out",str(output_stq),"--target",target_name,"--loop",loop]
        if row["loop_mode"]=="custom": cmd += ["--loop-in",str(row["custom_in"]),"--loop-out",str(row["custom_out"])]
        proc=subprocess.run(cmd,cwd=str(ROOT),capture_output=True,text=True)
        if proc.returncode: raise RuntimeError(proc.stderr.strip() or proc.stdout.strip())
        return json.loads(proc.stdout), stem

    def build_project(self):
        self._save_current_state()
        if not self.game_root.get(): messagebox.showwarning("Нет папки игры","Выберите корень игры перед сборкой."); return
        if not self.output.get(): messagebox.showwarning("Нет Build output","Укажите папку сборки."); return
        if Path(self.output.get()).resolve()==Path(self.game_root.get()).resolve(): messagebox.showerror("Небезопасная папка","Build output не может совпадать с папкой игры."); return
        try: namespace=self.validate_namespace()
        except ValueError as e: messagebox.showerror("Неверный namespace",str(e)); return
        try:
            sys.path.insert(0,str(ROOT)); from core.arc_adapter import discover_game_root, find_arctool, unpack, locate_stq, pack
            info=discover_game_root(Path(self.game_root.get())); tool=find_arctool(self.arctool.get().strip() or None, ROOT)
            root=Path(self.output.get()); root.mkdir(parents=True,exist_ok=True); workbase=root/"work"/"batch"; workbase.mkdir(parents=True,exist_ok=True)
            report={"build":BUILD,"namespace":namespace,"archives":{},"errors":[]}; total=0
            for archive_name, category in (("title.arc","title"),("bbs_rpg.arc","main")):
                state=self.archive_states.get(archive_name,{})
                rows=[r for r in state.get("rows",[]) if r.get("replacement")]
                if not rows: continue
                if not info["title" if archive_name=="title.arc" else "bbs_rpg"].is_file(): raise RuntimeError(f"{archive_name} not found in Game root")
                archive_work=workbase/archive_name.replace(".arc","")
                if archive_work.exists(): shutil.rmtree(archive_work)
                unpack(info["title" if archive_name=="title.arc" else "bbs_rpg"],archive_work,tool)
                stq=locate_stq(archive_work,archive_name); extracted_root=self._extracted_root_from_stq(stq,archive_name)
                if extracted_root is None: raise RuntimeError(f"не найдена корневая папка распакованного {archive_name}")
                current=stq; entries=[]
                for n,row in enumerate(rows):
                    next_stq=archive_work/f".patched_{n}.stq"
                    item,stem=self._run_patcher(current,next_stq,row,namespace,category)
                    shutil.copyfile(next_stq,stq); next_stq.unlink(missing_ok=True); current=stq
                    target=root/"nativePC"/"sound"/"stream"/namespace/"music"/category/(stem+".sngw"); target.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(row["replacement"],target)
                    entries.append({"slot_index":row["index"],"source":row["name"],"replacement":str(row["replacement"]),"report":item}); total+=1
                packed=pack(extracted_root,archive_work,tool); arc_out=root/"nativePC"/"rom"/archive_name; arc_out.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(packed,arc_out)
                report["archives"][archive_name]={"slots":entries,"output_arc":str(arc_out),"stq":str(stq)}
            if not report["archives"]: raise RuntimeError("не выбран ни один replacement")
            report["replacement_count"]=total; (root/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
            self.status.set(f"Пакет собран: {total} replacement(s)\n{root}")
            messagebox.showinfo("Пакет собран",f"Обработано replacement-ов: {total}\n\nГотовый пакет: {root}")
        except Exception as e:
            self.status.set("Сборка не выполнена: "+str(e)); messagebox.showerror("Сборка не выполнена",str(e))

    def _affected_archives(self):
        self._save_current_state()
        return [a for a in ("title.arc", "bbs_rpg.arc") if any(r.get("replacement") for r in self.archive_states.get(a, {}).get("rows", []))]

    def _snapshot_current_archives(self, archives):
        from core.arc_adapter import discover_game_root, find_arctool, unpack, locate_stq
        from core.stq_backup import create_snapshot, sha256
        info=discover_game_root(Path(self.game_root.get())); tool=find_arctool(self.arctool.get().strip() or None, ROOT)
        backup_root=Path(self.game_root.get())/".DDDA_Music_Replacer"/"backups"; baseline_root=backup_root/"baseline"; baseline_root.mkdir(parents=True,exist_ok=True)
        temp=Path(tempfile.mkdtemp(prefix="ddda_backup_")); snapshots=[]
        try:
            for archive_name in archives:
                arc=info["title"] if archive_name=="title.arc" else info["bbs_rpg"]
                work=temp/archive_name.replace(".arc",""); unpack(arc,work,tool); stq=locate_stq(work,archive_name)
                baseline=baseline_root/archive_name.replace(".arc",""); baseline.mkdir(parents=True,exist_ok=True); bfile=baseline/stq.name; manifest_path=baseline/"manifest.json"
                if not manifest_path.is_file():
                    # Migrate the earliest pre-install snapshot from older builds
                    # when available, so the first 0021 run cannot mistake a
                    # previously installed mod for vanilla.
                    candidates=[]
                    for container in [backup_root, backup_root/"history"]:
                        for item in container.glob("*"):
                            candidate=item/archive_name.replace(".arc","")
                            cm=candidate/"manifest.json"
                            if cm.is_file():
                                try:
                                    old=json.loads(cm.read_text(encoding="utf-8"))
                                    if old.get("archive")==archive_name and (candidate/old.get("file","")).is_file(): candidates.append((old.get("created_at",item.name),candidate,old))
                                except (OSError,ValueError,TypeError): pass
                    if candidates:
                        _, source_dir, old = sorted(candidates,key=lambda x:x[0])[0]; source=source_dir/old["file"]; shutil.copy2(source,bfile); vanilla_hash=sha256(bfile); manifest={"kind":"stq_baseline","archive":archive_name,"file":bfile.name,"size":bfile.stat().st_size,"sha256":vanilla_hash,"metadata":{"source":"migrated_earliest_snapshot","vanilla_stq_sha256":vanilla_hash}}
                    else:
                        shutil.copy2(stq,bfile); vanilla_hash=sha256(bfile); manifest={"kind":"stq_baseline","archive":archive_name,"file":bfile.name,"size":bfile.stat().st_size,"sha256":vanilla_hash,"metadata":{"source_arc":str(arc),"vanilla_stq_sha256":vanilla_hash,"source":"first_install"}}
                    manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
                dest,manifest=create_snapshot(stq,backup_root/"history",archive_name,{"source_arc":str(arc),"source_stq_sha256":sha256(stq),"status":"pre_install"})
                snapshots.append((archive_name,dest,manifest,baseline))
            return snapshots
        finally: shutil.rmtree(temp,ignore_errors=True)

    def install_project(self):
        archives=self._affected_archives()
        if not archives:
            messagebox.showwarning("Нет replacement-ов","Сначала настройте хотя бы один replacement."); return
        if not self.game_root.get() or not self.output.get():
            messagebox.showwarning("Не заданы пути","Укажите Game root и Build output."); return
        if not messagebox.askyesno("Установить мод","Будут изменены только архивы с настроенными replacement-ами.\n\nПеред установкой будет создан STQ-only backup. Продолжить?"): return
        try:
            root=Path(self.output.get()); stale=root/"report.json"
            if stale.exists(): stale.unlink()
            snapshots=self._snapshot_current_archives(archives)
            self.build_project()
            report_path=root/"report.json"
            if not report_path.is_file(): raise RuntimeError("Сборка пакета не создала report.json")
            report=json.loads(report_path.read_text(encoding="utf-8")); game=Path(self.game_root.get())
            for archive_name in archives:
                src=root/"nativePC"/"rom"/archive_name; dst=game/"nativePC"/"rom"/archive_name; dst.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(src,dst)
            ns=root/"nativePC"/"sound"/"stream"/self.namespace.get()
            if ns.is_dir():
                dest=game/"nativePC"/"sound"/"stream"/self.namespace.get()
                for src in ns.rglob("*"):
                    if src.is_file(): out=dest/src.relative_to(ns); out.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(src,out)
            from core.arc_adapter import discover_game_root, find_arctool, unpack, locate_stq
            from core.stq_backup import sha256
            info=discover_game_root(game); tool=find_arctool(self.arctool.get().strip() or None,ROOT); installed_temp=Path(tempfile.mkdtemp(prefix="ddda_installed_"))
            try:
                for archive_name,dest,manifest,baseline in snapshots:
                    arc=info["title"] if archive_name=="title.arc" else info["bbs_rpg"]; work=installed_temp/archive_name.replace(".arc",""); unpack(arc,work,tool); installed=locate_stq(work,archive_name); manifest["metadata"]["installed_stq_sha256"]=sha256(installed); (dest/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
                    baseline_manifest=json.loads((baseline/"manifest.json").read_text(encoding="utf-8")); baseline_manifest.setdefault("metadata",{})["installed_stq_sha256"]=sha256(installed); (baseline/"manifest.json").write_text(json.dumps(baseline_manifest,ensure_ascii=False,indent=2),encoding="utf-8")
            finally: shutil.rmtree(installed_temp,ignore_errors=True)
            self.status.set(f"Мод установлен в игру. Архивов: {len(archives)}")
            messagebox.showinfo("Мод установлен","Установка завершена.\nSTQ-only backup сохранён в папке игры: .DDDA_Music_Replacer/backups")
        except Exception as e:
            self.status.set("Установка не выполнена: "+str(e)); messagebox.showerror("Установка не выполнена",str(e))

    def restore_project(self):
        if not self.game_root.get(): messagebox.showwarning("Нет папки игры","Выберите Game root."); return
        try:
            from core.arc_adapter import discover_game_root, find_arctool, unpack, locate_stq, pack
            from core.stq_backup import verify_snapshot, sha256
            game=Path(self.game_root.get()); backup_root=game/".DDDA_Music_Replacer"/"backups"
            latest={}
            for d in sorted(backup_root.glob("*") if backup_root.is_dir() else [], key=lambda p:p.name, reverse=True):
                if not d.is_dir(): continue
                for archive_dir in d.iterdir():
                    m=archive_dir/"manifest.json"
                    if m.is_file():
                        manifest=json.loads(m.read_text(encoding="utf-8")); latest.setdefault(manifest.get("archive", archive_dir.name+".arc"),(archive_dir,manifest))
            candidates=list(latest.values())
            if not candidates: raise RuntimeError("STQ-only backup не найден")
            if not messagebox.askyesno("Восстановить STQ","Будут восстановлены последние сохранённые STQ.\nПроверить текущие hash и продолжить?"): return
            info=discover_game_root(game); tool=find_arctool(self.arctool.get().strip() or None,ROOT); temp=Path(tempfile.mkdtemp(prefix="ddda_restore_")); restored=[]
            try:
                for snapshot,manifest in candidates:
                    archive_name=manifest["archive"]; arc=info["title"] if archive_name=="title.arc" else info["bbs_rpg"]; work=temp/archive_name.replace(".arc",""); unpack(arc,work,tool); current=locate_stq(work,archive_name)
                    expected=manifest.get("metadata",{}).get("installed_stq_sha256")
                    if expected and sha256(current)!=expected: raise RuntimeError(f"{archive_name}: текущий STQ изменён после установки; восстановление отменено")
                    if not verify_snapshot(snapshot): raise RuntimeError(f"{archive_name}: backup повреждён")
                    backup= snapshot/manifest["file"]; shutil.copy2(backup,current); extracted=None
                    for parent in [current.parent,*current.parents]:
                        if parent.name.lower()==archive_name.replace(".arc",""): extracted=parent; break
                    if extracted is None: raise RuntimeError(f"{archive_name}: не найдена extracted root")
                    packed=pack(extracted,work,tool); shutil.copy2(packed,arc); restored.append(archive_name)
            finally: shutil.rmtree(temp,ignore_errors=True)
            self.status.set("Восстановлено: "+", ".join(restored)); messagebox.showinfo("Восстановление завершено","Восстановлены только STQ: "+", ".join(restored))
        except Exception as e:
            self.status.set("Восстановление не выполнено: "+str(e)); messagebox.showerror("Восстановление не выполнено",str(e))

    def restore_vanilla(self):
        if not self.game_root.get(): messagebox.showwarning("Нет папки игры","Выберите Game root."); return
        try:
            from core.arc_adapter import discover_game_root, find_arctool, unpack, locate_stq, pack
            from core.stq_backup import sha256
            game=Path(self.game_root.get()); baseline_root=game/".DDDA_Music_Replacer"/"backups"/"baseline"; entries=[]
            for d in sorted(baseline_root.glob("*") if baseline_root.is_dir() else []):
                m=d/"manifest.json"
                if m.is_file(): entries.append((d,json.loads(m.read_text(encoding="utf-8"))))
            if not entries: raise RuntimeError("vanilla STQ baseline не найден. Он создаётся при первой установке.")
            if not messagebox.askyesno("Удалить мод","Будут восстановлены исходные vanilla STQ из baseline.\nТекущие изменения Music Replacer будут удалены. Продолжить?"): return
            info=discover_game_root(game); tool=find_arctool(self.arctool.get().strip() or None,ROOT); temp=Path(tempfile.mkdtemp(prefix="ddda_vanilla_")); restored=[]
            try:
                for snapshot,manifest in entries:
                    archive_name=manifest["archive"]; arc=info["title"] if archive_name=="title.arc" else info["bbs_rpg"]; work=temp/archive_name.replace(".arc",""); unpack(arc,work,tool); current=locate_stq(work,archive_name); expected=manifest.get("metadata",{}).get("installed_stq_sha256")
                    if expected and sha256(current)!=expected: raise RuntimeError(f"{archive_name}: текущий STQ изменён после установки; vanilla restore отменён")
                    backup=snapshot/manifest["file"]
                    if not backup.is_file() or sha256(backup)!=manifest["sha256"]: raise RuntimeError(f"{archive_name}: vanilla baseline повреждён")
                    shutil.copy2(backup,current); extracted=None
                    for parent in [current.parent,*current.parents]:
                        if parent.name.lower()==archive_name.replace(".arc",""): extracted=parent; break
                    if extracted is None: raise RuntimeError(f"{archive_name}: не найдена extracted root")
                    packed=pack(extracted,work,tool); shutil.copy2(packed,arc); restored.append(archive_name)
            finally: shutil.rmtree(temp,ignore_errors=True)
            self.status.set("Vanilla восстановлена: "+", ".join(restored)); messagebox.showinfo("Мод удалён","Vanilla STQ восстановлены: "+", ".join(restored))
        except Exception as e:
            self.status.set("Vanilla restore не выполнен: "+str(e)); messagebox.showerror("Vanilla restore не выполнен",str(e))

if __name__=="__main__": App().mainloop()
