#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Plain tkinter front end for edl.py.
It only runs edl.py through subprocess and does not touch edlclient.

Run:  python edl_gui.py

Source file is ASCII-only on purpose: Vietnamese UI text is stored as \\u escapes.
"""
import codecs
import os
import queue
import re
import shlex
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

HERE = os.path.dirname(os.path.abspath(__file__))

# UI text. Keys are shared by all languages; add a language by adding a dict here.
STR = {
    "en": {
        "lang_name": "English",
        "language": "Language",
        "loader": "Loader",
        "browse": "Browse...",
        "auto": "Auto",
        "memory": "Memory",
        "lun": "LUN",
        "serial": "Serial",
        "port": "Port",
        "flag_skipwrite": "skipwrite (simulate, no writes)",
        "extra": "Extra args",
        "command": "Command",
        "run": "Run",
        "stop": "Stop",
        "detect": "Detect device",
        "clear": "Clear log",
        "a_part": "Partition name",
        "a_outfile": "Output file",
        "a_outdir": "Output folder",
        "a_infile": "Input file",
        "a_indir": "Input folder",
        "a_start": "Start sector",
        "a_count": "Sector count",
        "a_offset": "Offset",
        "a_len": "Length",
        "a_slot": "Slot (a/b)",
        "a_lun": "LUN",
        "a_xmlfile": "XML file",
        "a_xmlstr": "XML string",
        "a_cmd": "Command",
        "a_resetmode": "Mode (reset/off/edl, empty = default)",
        "a_rawprog": "rawprogram XML",
        "a_patch": "patch XML",
        "a_imgdir": "Image folder",
        "pick_loader": "Select loader",
        "ft_loader": "Loader",
        "ft_all": "All files",
        "err_title": "Error",
        "err_missing": "Missing: {0}",
        "err_nofile": "File not found: {0}",
        "err_nodir": "Folder not found: {0}",
        "err_extra": "Bad extra args: {0}",
        "err_run": "Cannot run: {0}",
        "confirm_title": "Confirm",
        "confirm_body": "This command may write or erase data on the device:\n\n{0}\n\nRun it?",
        "dropped": "(ignored, not supported by this command: {0})",
        "done": "[done, exit code {0}]",
        "quit_title": "Quit",
        "quit_body": "A command is running. Stop it and quit?",
        "no_edl": "edl.py not found next to edl_gui.py",
        "d_noload": "Cannot load pyusb/usb_ids: {0}",
        "d_nolist": "Cannot list USB devices (missing libusb backend?): {0}",
        "d_edl": "EDL device: {0}",
        "d_qc": "Qualcomm device, not in EDL mode: {0}",
        "d_none": "No EDL device found.",
    },
    "vi": {
        "lang_name": "Ti\u1ebfng Vi\u1ec7t",
        "language": "Ng\u00f4n ng\u1eef",
        "loader": "Loader",
        "browse": "Ch\u1ecdn...",
        "auto": "T\u1ef1 \u0111\u1ed9ng",
        "memory": "B\u1ed9 nh\u1edb",
        "lun": "LUN",
        "serial": "Serial",
        "port": "C\u1ed5ng",
        "flag_skipwrite": "skipwrite (m\u00f4 ph\u1ecfng, kh\u00f4ng ghi)",
        "extra": "Tham s\u1ed1 th\u00eam",
        "command": "L\u1ec7nh",
        "run": "Ch\u1ea1y",
        "stop": "D\u1eebng",
        "detect": "D\u00f2 thi\u1ebft b\u1ecb",
        "clear": "X\u00f3a log",
        "a_part": "T\u00ean partition",
        "a_outfile": "File l\u01b0u",
        "a_outdir": "Th\u01b0 m\u1ee5c l\u01b0u",
        "a_infile": "File ghi",
        "a_indir": "Th\u01b0 m\u1ee5c ch\u1ee9a file",
        "a_start": "Sector b\u1eaft \u0111\u1ea7u",
        "a_count": "S\u1ed1 sector",
        "a_offset": "Offset",
        "a_len": "\u0110\u1ed9 d\u00e0i",
        "a_slot": "Slot (a/b)",
        "a_lun": "LUN",
        "a_xmlfile": "File xml",
        "a_xmlstr": "Chu\u1ed7i xml",
        "a_cmd": "L\u1ec7nh",
        "a_resetmode": "Ch\u1ebf \u0111\u1ed9 (reset/off/edl, \u0111\u1ec3 tr\u1ed1ng = m\u1eb7c \u0111\u1ecbnh)",
        "a_rawprog": "rawprogram xml",
        "a_patch": "patch xml",
        "a_imgdir": "Th\u01b0 m\u1ee5c image",
        "pick_loader": "Ch\u1ecdn loader",
        "ft_loader": "Loader",
        "ft_all": "T\u1ea5t c\u1ea3 file",
        "err_title": "L\u1ed7i",
        "err_missing": "Thi\u1ebfu: {0}",
        "err_nofile": "Kh\u00f4ng th\u1ea5y file: {0}",
        "err_nodir": "Kh\u00f4ng th\u1ea5y th\u01b0 m\u1ee5c: {0}",
        "err_extra": "Tham s\u1ed1 th\u00eam sai c\u00fa ph\u00e1p: {0}",
        "err_run": "Kh\u00f4ng ch\u1ea1y \u0111\u01b0\u1ee3c: {0}",
        "confirm_title": "X\u00e1c nh\u1eadn",
        "confirm_body": "L\u1ec7nh n\u00e0y c\u00f3 th\u1ec3 ghi ho\u1eb7c x\u00f3a d\u1eef li\u1ec7u tr\u00ean m\u00e1y:\n\n{0}\n\nCh\u1ea1y?",
        "dropped": "(b\u1ecf qua, l\u1ec7nh n\u00e0y kh\u00f4ng h\u1ed7 tr\u1ee3: {0})",
        "done": "[xong, m\u00e3 tho\u00e1t {0}]",
        "quit_title": "Tho\u00e1t",
        "quit_body": "\u0110ang ch\u1ea1y l\u1ec7nh. D\u1eebng v\u00e0 tho\u00e1t?",
        "no_edl": "Kh\u00f4ng th\u1ea5y edl.py c\u1ea1nh edl_gui.py",
        "d_noload": "Kh\u00f4ng n\u1ea1p \u0111\u01b0\u1ee3c pyusb/usb_ids: {0}",
        "d_nolist": "Kh\u00f4ng li\u1ec7t k\u00ea \u0111\u01b0\u1ee3c USB (thi\u1ebfu libusb backend?): {0}",
        "d_edl": "Thi\u1ebft b\u1ecb EDL: {0}",
        "d_qc": "Thi\u1ebft b\u1ecb Qualcomm, kh\u00f4ng \u1edf ch\u1ebf \u0111\u1ed9 EDL: {0}",
        "d_none": "Kh\u00f4ng th\u1ea5y thi\u1ebft b\u1ecb EDL.",
    },
}
LANGS = ["en", "vi"]

# (command, [(label key, kind)])
# kind: text | in | out | indir | outdir | resetmode
COMMANDS = [
    ("printgpt", []),
    ("gpt", [("a_outdir", "outdir")]),
    ("r", [("a_part", "text"), ("a_outfile", "out")]),
    ("rl", [("a_outdir", "outdir")]),
    ("rf", [("a_outfile", "out")]),
    ("rs", [("a_start", "text"), ("a_count", "text"), ("a_outfile", "out")]),
    ("w", [("a_part", "text"), ("a_infile", "in")]),
    ("wl", [("a_indir", "indir")]),
    ("wf", [("a_infile", "in")]),
    ("ws", [("a_start", "text"), ("a_infile", "in")]),
    ("e", [("a_part", "text")]),
    ("es", [("a_start", "text"), ("a_count", "text")]),
    ("ep", [("a_part", "text"), ("a_count", "text")]),
    ("getstorageinfo", []),
    ("secureboot", []),
    ("pbl", [("a_outfile", "out")]),
    ("qfp", [("a_outfile", "out")]),
    ("memtbl", [("a_outfile", "out")]),
    ("footer", [("a_outfile", "out")]),
    ("peekhex", [("a_offset", "text"), ("a_len", "text")]),
    ("getactiveslot", []),
    ("setactiveslot", [("a_slot", "text")]),
    ("setbootablestoragedrive", [("a_lun", "text")]),
    ("xml", [("a_xmlfile", "in")]),
    ("rawxml", [("a_xmlstr", "text")]),
    ("send", [("a_cmd", "text")]),
    ("nop", []),
    ("reset", [("a_resetmode", "resetmode")]),
    ("qfil", [("a_rawprog", "in"), ("a_patch", "in"), ("a_imgdir", "indir")]),
    ("provision", [("a_xmlfile", "in")]),
]

PATH_KINDS = ("in", "out", "indir", "outdir")

# Commands that write/erase or change device state: ask before running
DANGEROUS = {"w", "wl", "wf", "ws", "e", "es", "ep", "qfil", "provision",
             "setbootablestoragedrive", "setactiveslot"}

FLAGS = ["debugmode", "skipwrite", "skipresponse", "skipstorageinit"]


def find_edl():
    for p in (os.path.join(HERE, "edl.py"), os.path.join(HERE, "edlclient", "edl.py")):
        if os.path.isfile(p):
            return p
    return None


def load_usage(path):
    """Parse the edl.py docstring: ({cmd: {valid options}}, {cmd: description})."""
    valid, desc = {}, {}
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            text = f.read()
    except (OSError, TypeError):
        return valid, desc
    parts = text.split('"""')
    if len(parts) < 3:
        return valid, desc
    for line in parts[1].splitlines():
        m = re.match(r"\s+edl\.py\s+([a-z]\w*)\b(.*)", line)
        if m:
            valid.setdefault(m.group(1), set()).update(re.findall(r"--([\w-]+)", m.group(2)))
        m = re.match(r"\s{4}([a-z]\w*)\s+# (.*)$", line)
        if m:
            desc[m.group(1)] = m.group(2).strip()
    return valid, desc


def basename(v):
    parts = re.split(r"[\\/]", v.rstrip("\\/"))
    return parts[-1] or v


def build_args(cmd, values, state, valid=None, kinds=None, short=False):
    """Build edl arguments.

    valid: set of options the command accepts (None = do not filter).
    kinds: kind of each positional value (used with short=True).
    short: show only the file name for path values (for display, not for running).
    Returns (args, dropped options).
    """
    kinds = kinds or []
    args = [cmd]
    for i, v in enumerate(values):
        if short and i < len(kinds) and kinds[i] in PATH_KINDS:
            v = basename(v)
        args.append(v)
    dropped = []

    def add(name, value=None):
        if valid is not None and name not in valid:
            dropped.append(name)
            return
        args.append("--%s" % name if value is None else "--%s=%s" % (name, value))

    loader = state.get("loader", "").strip()
    if loader:
        add("loader", basename(loader) if short else loader)
    mem = state.get("memory", "")
    if mem and mem != "auto":
        add("memory", mem)
    if state.get("lun", "").strip():
        add("lun", state["lun"].strip())
    if state.get("serial"):
        add("serial")
    if state.get("portname", "").strip():
        add("portname", state["portname"].strip())
    for name in FLAGS:
        if state.get(name):
            add(name)
    if state.get("resetmode", "").strip():
        add("resetmode", state["resetmode"].strip())
    args += list(state.get("extra", []))
    return args, dropped


def quote_args(argv):
    if os.name == "nt":
        return subprocess.list2cmdline(argv)
    return " ".join(shlex.quote(a) for a in argv)


class App:
    def __init__(self, root):
        self.root = root
        root.title("EDL")
        self.lang = "en"
        self.i18n = []  # (widget, option, key)
        self.edl = find_edl()
        self.valid, self.desc = load_usage(self.edl) if self.edl else ({}, {})
        self.proc = None
        self.q = queue.Queue()
        self._cr = False
        self.specs = {name: spec for name, spec in COMMANDS}
        names = [n for n, _ in COMMANDS if not self.valid or n in self.valid]

        self.loader = tk.StringVar()
        self.memory = tk.StringVar(value="auto")
        self.lun = tk.StringVar()
        self.serial = tk.BooleanVar()
        self.portname = tk.StringVar()
        self.flags = {n: tk.BooleanVar() for n in FLAGS}
        self.extra = tk.StringVar()
        self.cmd = tk.StringVar(value=names[0] if names else "")
        self.argvars = [tk.StringVar() for _ in range(3)]

        top = ttk.Frame(root, padding=6)
        top.pack(fill="x")
        top.columnconfigure(1, weight=1)

        self.lbl(top, "loader").grid(row=0, column=0, sticky="w")
        ttk.Entry(top, textvariable=self.loader).grid(row=0, column=1, sticky="ew", padx=4)
        self.btn(top, "browse", self.pick_loader).grid(row=0, column=2)
        self.btn(top, "auto", lambda: self.loader.set("")).grid(row=0, column=3, padx=(4, 0))

        opt = ttk.Frame(top)
        opt.grid(row=1, column=0, columnspan=4, sticky="w", pady=(4, 0))
        self.lbl(opt, "memory").pack(side="left")
        ttk.Combobox(opt, textvariable=self.memory, width=7, state="readonly",
                     values=["auto", "UFS", "eMMC", "NAND", "spinor"]).pack(side="left", padx=4)
        self.lbl(opt, "lun").pack(side="left")
        ttk.Entry(opt, textvariable=self.lun, width=4).pack(side="left", padx=4)
        self.chk(opt, "serial", self.serial).pack(side="left", padx=(8, 0))
        self.lbl(opt, "port").pack(side="left", padx=(4, 0))
        ttk.Entry(opt, textvariable=self.portname, width=12).pack(side="left", padx=4)

        fl = ttk.Frame(top)
        fl.grid(row=2, column=0, columnspan=4, sticky="w")
        for name in FLAGS:
            if name == "skipwrite":
                w = self.chk(fl, "flag_skipwrite", self.flags[name])
            else:
                w = ttk.Checkbutton(fl, text=name, variable=self.flags[name])
            w.pack(side="left", padx=(0, 8))

        self.lbl(top, "extra").grid(row=3, column=0, sticky="w", pady=(4, 0))
        ttk.Entry(top, textvariable=self.extra).grid(row=3, column=1, columnspan=3,
                                                     sticky="ew", padx=4, pady=(4, 0))

        mid = ttk.Frame(root, padding=6)
        mid.pack(fill="x")
        mid.columnconfigure(1, weight=1)
        self.lbl(mid, "command").grid(row=0, column=0, sticky="w")
        cb = ttk.Combobox(mid, textvariable=self.cmd, values=names, state="readonly", width=24)
        cb.grid(row=0, column=1, sticky="w", padx=4)
        cb.bind("<<ComboboxSelected>>", lambda e: self.refresh_args())
        self.desc_lbl = ttk.Label(mid, text="")
        self.desc_lbl.grid(row=1, column=1, columnspan=2, sticky="w", padx=4)

        self.arg_widgets = []
        for i in range(3):
            lbl = ttk.Label(mid)
            ent = ttk.Entry(mid, textvariable=self.argvars[i])
            btn = ttk.Button(mid, text="...", width=4, command=lambda i=i: self.browse(i))
            self.arg_widgets.append((lbl, ent, btn))
            lbl.grid(row=2 + i, column=0, sticky="w")
            ent.grid(row=2 + i, column=1, sticky="ew", padx=4, pady=1)
            btn.grid(row=2 + i, column=2)

        bar = ttk.Frame(root, padding=(6, 0))
        bar.pack(fill="x")
        self.run_btn = self.btn(bar, "run", self.run)
        self.run_btn.pack(side="left")
        self.stop_btn = self.btn(bar, "stop", self.stop)
        self.stop_btn.configure(state="disabled")
        self.stop_btn.pack(side="left", padx=4)
        self.btn(bar, "detect", self.detect).pack(side="left")
        self.btn(bar, "clear", self.clear).pack(side="left", padx=4)
        self.lang_box = ttk.Combobox(bar, state="readonly", width=12,
                                     values=[STR[c]["lang_name"] for c in LANGS])
        self.lang_box.current(0)
        self.lang_box.pack(side="right")
        self.lbl(bar, "language").pack(side="right", padx=4)
        self.lang_box.bind("<<ComboboxSelected>>", self.on_lang)

        logf = ttk.Frame(root, padding=6)
        logf.pack(fill="both", expand=True)
        self.log = tk.Text(logf, height=22, width=100, wrap="none", state="disabled")
        sb = ttk.Scrollbar(logf, command=self.log.yview)
        self.log.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.log.pack(side="left", fill="both", expand=True)

        self.refresh_args()
        self.apply_lang()
        root.protocol("WM_DELETE_WINDOW", self.close)
        root.after(50, self.pump)
        if not self.edl:
            self.write(self.t("no_edl") + "\n")

    # ---- language ----
    def t(self, key, *args):
        s = STR[self.lang].get(key) or STR["en"][key]
        return s.format(*args) if args else s

    def lbl(self, parent, key):
        w = ttk.Label(parent)
        self.i18n.append((w, "text", key))
        return w

    def btn(self, parent, key, cmd):
        w = ttk.Button(parent, command=cmd)
        self.i18n.append((w, "text", key))
        return w

    def chk(self, parent, key, var):
        w = ttk.Checkbutton(parent, variable=var)
        self.i18n.append((w, "text", key))
        return w

    def apply_lang(self):
        for w, opt, key in self.i18n:
            w.configure(**{opt: self.t(key)})
        self.update_arg_labels()

    def on_lang(self, _event=None):
        self.lang = LANGS[self.lang_box.current()]
        self.apply_lang()

    # ---- layout ----
    def update_arg_labels(self):
        spec = self.specs.get(self.cmd.get(), [])
        for i, (lbl, _ent, _btn) in enumerate(self.arg_widgets):
            if i < len(spec):
                lbl.configure(text=self.t(spec[i][0]))

    def refresh_args(self):
        spec = self.specs.get(self.cmd.get(), [])
        self.desc_lbl.configure(text=self.desc.get(self.cmd.get(), ""))
        for i, (lbl, ent, btn) in enumerate(self.arg_widgets):
            if i < len(spec):
                self.argvars[i].set("")
                lbl.grid()
                ent.grid()
                if spec[i][1] in PATH_KINDS:
                    btn.grid()
                else:
                    btn.grid_remove()
            else:
                lbl.grid_remove()
                ent.grid_remove()
                btn.grid_remove()
        self.update_arg_labels()

    def pick_loader(self):
        p = filedialog.askopenfilename(
            title=self.t("pick_loader"),
            filetypes=[(self.t("ft_loader"), "*.bin *.mbn *.elf"), (self.t("ft_all"), "*.*")])
        if p:
            self.loader.set(p)

    def browse(self, i):
        kind = self.specs[self.cmd.get()][i][1]
        if kind == "in":
            p = filedialog.askopenfilename()
        elif kind == "out":
            p = filedialog.asksaveasfilename()
        else:
            p = filedialog.askdirectory()
        if p:
            self.argvars[i].set(p)

    # ---- log ----
    def write(self, s):
        s = s.replace("\r\n", "\n")
        self.log.configure(state="normal")
        for p in re.split(r"(\r|\n)", s):
            if p == "\r":
                self._cr = True  # next text overwrites the current line (progress output)
            elif p == "\n":
                self.log.insert("end", "\n")
                self._cr = False
            elif p:
                if self._cr:
                    self.log.delete("end-1c linestart", "end-1c")
                    self._cr = False
                self.log.insert("end", p)
        self.log.see("end")
        self.log.configure(state="disabled")

    def clear(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    # ---- run ----
    def collect(self):
        cmd = self.cmd.get()
        values, kinds = [], []
        state = {
            "loader": self.loader.get(),
            "memory": self.memory.get(),
            "lun": self.lun.get(),
            "serial": self.serial.get(),
            "portname": self.portname.get(),
        }
        for n, v in self.flags.items():
            state[n] = v.get()
        try:
            state["extra"] = shlex.split(self.extra.get(), posix=(os.name != "nt"))
        except ValueError as e:
            raise ValueError(self.t("err_extra", e))
        for i, (key, kind) in enumerate(self.specs[cmd]):
            v = self.argvars[i].get().strip()
            if kind == "resetmode":
                state["resetmode"] = v
                continue
            if not v:
                raise ValueError(self.t("err_missing", self.t(key)))
            if kind == "in" and not os.path.isfile(v):
                raise ValueError(self.t("err_nofile", v))
            if kind == "indir" and not os.path.isdir(v):
                raise ValueError(self.t("err_nodir", v))
            if kind == "outdir":
                os.makedirs(v, exist_ok=True)
            if kind == "out":
                os.makedirs(os.path.dirname(os.path.abspath(v)), exist_ok=True)
            values.append(v)
            kinds.append(kind)
        return cmd, values, kinds, state

    def run(self):
        if self.proc or not self.edl:
            return
        try:
            cmd, values, kinds, state = self.collect()
        except (ValueError, OSError) as e:
            messagebox.showerror(self.t("err_title"), str(e))
            return
        valid = self.valid.get(cmd) if self.valid else None
        args, dropped = build_args(cmd, values, state, valid)
        shown, _ = build_args(cmd, values, state, valid, kinds, short=True)
        shown_text = "edl " + quote_args(shown)
        if cmd in DANGEROUS and not state.get("skipwrite"):
            if not messagebox.askyesno(self.t("confirm_title"), self.t("confirm_body", shown_text)):
                return
        self.write("> %s\n" % shown_text)
        if dropped:
            self.write(self.t("dropped", ", ".join("--" + d for d in dropped)) + "\n")
        argv = [sys.executable, "-u", self.edl] + args
        env = dict(os.environ, PYTHONUNBUFFERED="1", PYTHONIOENCODING="utf-8")
        kw = {}
        if os.name == "nt":
            kw["creationflags"] = subprocess.CREATE_NO_WINDOW
        try:
            self.proc = subprocess.Popen(argv, cwd=HERE, env=env, stdin=subprocess.DEVNULL,
                                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                         bufsize=0, **kw)
        except OSError as e:
            self.write(self.t("err_run", e) + "\n")
            return
        self.run_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        threading.Thread(target=self.reader, args=(self.proc,), daemon=True).start()

    def reader(self, proc):
        dec = codecs.getincrementaldecoder("utf-8")("replace")
        fd = proc.stdout.fileno()
        try:
            while True:
                data = os.read(fd, 4096)
                if not data:
                    break
                self.q.put(self.shorten(dec.decode(data)))
        except OSError:
            pass
        self.q.put(("done", proc.wait()))

    @staticmethod
    def shorten(text):
        """Drop this folder's absolute prefix from edl output paths."""
        for sep in (os.sep, "/"):
            text = text.replace(HERE + sep, "")
        return text

    def pump(self):
        try:
            while True:
                item = self.q.get_nowait()
                if isinstance(item, tuple):
                    self.write("\n" + self.t("done", item[1]) + "\n")
                    self.proc = None
                    self.run_btn.configure(state="normal")
                    self.stop_btn.configure(state="disabled")
                else:
                    self.write(item)
        except queue.Empty:
            pass
        self.root.after(50, self.pump)

    def stop(self):
        if self.proc:
            self.proc.terminate()

    def close(self):
        if self.proc:
            if not messagebox.askyesno(self.t("quit_title"), self.t("quit_body")):
                return
            self.proc.terminate()
        self.root.destroy()

    # ---- device detection ----
    def detect(self):
        try:
            import usb.core
            sys.path.insert(0, HERE)
            from edlclient.Config.usb_ids import default_ids
        except Exception as e:
            self.write(self.t("d_noload", e) + "\n")
            return
        try:
            devs = list(usb.core.find(find_all=True))
        except Exception as e:
            self.write(self.t("d_nolist", e) + "\n")
            return
        known = {(v, p) for v, p, _ in default_ids}
        found = False
        for d in devs:
            ident = "%04x:%04x" % (d.idVendor, d.idProduct)
            if (d.idVendor, d.idProduct) in known:
                self.write(self.t("d_edl", ident) + "\n")
                found = True
            elif d.idVendor == 0x05C6:
                self.write(self.t("d_qc", ident) + "\n")
                found = True
        if not found:
            self.write(self.t("d_none") + "\n")


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
