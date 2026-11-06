#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Giao diện tkinter đơn giản cho edl.py.
Chỉ dùng subprocess gọi edl.py, không sửa gì trong edlclient.

Chạy:  python edl_gui.py
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

# (ten lenh, [(nhan, kieu)]) - kieu: text | in | out | indir | outdir | resetmode
COMMANDS = [
    ("printgpt", []),
    ("gpt", [("Thư mục lưu GPT", "outdir")]),
    ("r", [("Tên partition", "text"), ("File lưu", "out")]),
    ("rl", [("Thư mục lưu", "outdir")]),
    ("rf", [("File lưu", "out")]),
    ("rs", [("Sector bắt đầu", "text"), ("Số sector", "text"), ("File lưu", "out")]),
    ("w", [("Tên partition", "text"), ("File ghi", "in")]),
    ("wl", [("Thư mục chứa file", "indir")]),
    ("wf", [("File ghi", "in")]),
    ("ws", [("Sector bắt đầu", "text"), ("File ghi", "in")]),
    ("e", [("Tên partition", "text")]),
    ("es", [("Sector bắt đầu", "text"), ("Số sector", "text")]),
    ("ep", [("Tên partition", "text"), ("Số sector", "text")]),
    ("getstorageinfo", []),
    ("secureboot", []),
    ("pbl", [("File lưu", "out")]),
    ("qfp", [("File lưu", "out")]),
    ("memtbl", [("File lưu", "out")]),
    ("footer", [("File lưu", "out")]),
    ("peekhex", [("Offset", "text"), ("Độ dài", "text")]),
    ("getactiveslot", []),
    ("setactiveslot", [("Slot (a/b)", "text")]),
    ("setbootablestoragedrive", [("LUN", "text")]),
    ("xml", [("File xml", "in")]),
    ("rawxml", [("Chuỗi xml", "text")]),
    ("send", [("Lệnh", "text")]),
    ("nop", []),
    ("reset", [("Chế độ (reset/off/edl, để trống = mặc định)", "resetmode")]),
    ("qfil", [("rawprogram xml", "in"), ("patch xml", "in"), ("Thư mục image", "indir")]),
    ("provision", [("File xml", "in")]),
]

# Lệnh ghi/xóa/đổi trạng thái máy: hỏi xác nhận trước khi chạy
DANGEROUS = {"w", "wl", "wf", "ws", "e", "es", "ep", "qfil", "provision",
             "setbootablestoragedrive", "setactiveslot"}

FLAGS = [
    ("debugmode", "debugmode"),
    ("skipwrite", "skipwrite (mô phỏng, không ghi)"),
    ("skipresponse", "skipresponse"),
    ("skipstorageinit", "skipstorageinit"),
]


def find_edl():
    for p in (os.path.join(HERE, "edl.py"), os.path.join(HERE, "edlclient", "edl.py")):
        if os.path.isfile(p):
            return p
    return None


def load_usage(path):
    """Đọc docstring của edl.py: {lệnh: {option hợp lệ}}, {lệnh: mô tả}."""
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


def build_args(cmd, values, state, valid=None):
    """Ghép tham số edl. valid=None: không lọc option.
    Trả về (args, danh sách option bị bỏ)."""
    args = [cmd] + list(values)
    dropped = []

    def add(name, value=None):
        if valid is not None and name not in valid:
            dropped.append(name)
            return
        args.append("--%s" % name if value is None else "--%s=%s" % (name, value))

    if state.get("loader", "").strip():
        add("loader", state["loader"].strip())
    mem = state.get("memory", "")
    if mem and mem != "auto":
        add("memory", mem)
    if state.get("lun", "").strip():
        add("lun", state["lun"].strip())
    if state.get("serial"):
        add("serial")
    if state.get("portname", "").strip():
        add("portname", state["portname"].strip())
    for name, _ in FLAGS:
        if state.get(name):
            add(name)
    if state.get("resetmode", "").strip():
        add("resetmode", state["resetmode"].strip())
    args += list(state.get("extra", []))
    return args, dropped


def cmdline_text(argv):
    if os.name == "nt":
        return subprocess.list2cmdline(argv)
    return " ".join(shlex.quote(a) for a in argv)


class App:
    def __init__(self, root):
        self.root = root
        root.title("EDL")
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
        self.flags = {n: tk.BooleanVar() for n, _ in FLAGS}
        self.extra = tk.StringVar()
        self.cmd = tk.StringVar(value=names[0] if names else "")
        self.argvars = [tk.StringVar() for _ in range(3)]

        top = ttk.Frame(root, padding=6)
        top.pack(fill="x")
        top.columnconfigure(1, weight=1)

        ttk.Label(top, text="Loader").grid(row=0, column=0, sticky="w")
        ttk.Entry(top, textvariable=self.loader).grid(row=0, column=1, sticky="ew", padx=4)
        ttk.Button(top, text="Chọn...", command=self.pick_loader).grid(row=0, column=2)
        ttk.Button(top, text="Tự dò", command=lambda: self.loader.set("")).grid(row=0, column=3, padx=(4, 0))

        opt = ttk.Frame(top)
        opt.grid(row=1, column=0, columnspan=4, sticky="w", pady=(4, 0))
        ttk.Label(opt, text="Memory").pack(side="left")
        ttk.Combobox(opt, textvariable=self.memory, width=7, state="readonly",
                     values=["auto", "UFS", "eMMC", "NAND", "spinor"]).pack(side="left", padx=4)
        ttk.Label(opt, text="LUN").pack(side="left")
        ttk.Entry(opt, textvariable=self.lun, width=4).pack(side="left", padx=4)
        ttk.Checkbutton(opt, text="Serial", variable=self.serial).pack(side="left", padx=(8, 0))
        ttk.Label(opt, text="Port").pack(side="left", padx=(4, 0))
        ttk.Entry(opt, textvariable=self.portname, width=12).pack(side="left", padx=4)

        fl = ttk.Frame(top)
        fl.grid(row=2, column=0, columnspan=4, sticky="w")
        for name, label in FLAGS:
            ttk.Checkbutton(fl, text=label, variable=self.flags[name]).pack(side="left", padx=(0, 8))

        ttk.Label(top, text="Tham số thêm").grid(row=3, column=0, sticky="w", pady=(4, 0))
        ttk.Entry(top, textvariable=self.extra).grid(row=3, column=1, columnspan=3, sticky="ew", padx=4, pady=(4, 0))

        mid = ttk.Frame(root, padding=6)
        mid.pack(fill="x")
        mid.columnconfigure(1, weight=1)
        ttk.Label(mid, text="Lệnh").grid(row=0, column=0, sticky="w")
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
        self.run_btn = ttk.Button(bar, text="Chạy", command=self.run)
        self.run_btn.pack(side="left")
        self.stop_btn = ttk.Button(bar, text="Dừng", command=self.stop, state="disabled")
        self.stop_btn.pack(side="left", padx=4)
        ttk.Button(bar, text="Dò thiết bị", command=self.detect).pack(side="left")
        ttk.Button(bar, text="Xóa log", command=self.clear).pack(side="left", padx=4)

        logf = ttk.Frame(root, padding=6)
        logf.pack(fill="both", expand=True)
        self.log = tk.Text(logf, height=22, width=100, wrap="none", state="disabled")
        sb = ttk.Scrollbar(logf, command=self.log.yview)
        self.log.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.log.pack(side="left", fill="both", expand=True)

        self.refresh_args()
        root.protocol("WM_DELETE_WINDOW", self.close)
        root.after(50, self.pump)
        if not self.edl:
            self.write("Không thấy edl.py cạnh edl_gui.py\n")

    # ---- giao diện ----
    def refresh_args(self):
        spec = self.specs.get(self.cmd.get(), [])
        self.desc_lbl.configure(text=self.desc.get(self.cmd.get(), ""))
        for i, (lbl, ent, btn) in enumerate(self.arg_widgets):
            if i < len(spec):
                label, kind = spec[i]
                lbl.configure(text=label)
                self.argvars[i].set("")
                lbl.grid()
                ent.grid()
                if kind in ("in", "out", "indir", "outdir"):
                    btn.grid()
                else:
                    btn.grid_remove()
            else:
                lbl.grid_remove()
                ent.grid_remove()
                btn.grid_remove()

    def pick_loader(self):
        p = filedialog.askopenfilename(title="Chọn loader",
                                       filetypes=[("Loader", "*.bin *.mbn *.elf"), ("Tất cả", "*.*")])
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

    def write(self, s):
        s = s.replace("\r\n", "\n")
        self.log.configure(state="normal")
        for p in re.split(r"(\r|\n)", s):
            if p == "\r":
                self._cr = True
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

    # ---- chạy lệnh ----
    def collect(self):
        cmd = self.cmd.get()
        values = []
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
            raise ValueError("Tham số thêm sai cú pháp: %s" % e)
        for i, (label, kind) in enumerate(self.specs[cmd]):
            v = self.argvars[i].get().strip()
            if kind == "resetmode":
                state["resetmode"] = v
                continue
            if not v:
                raise ValueError("Thiếu: %s" % label)
            if kind == "in" and not os.path.isfile(v):
                raise ValueError("Không thấy file: %s" % v)
            if kind == "indir" and not os.path.isdir(v):
                raise ValueError("Không thấy thư mục: %s" % v)
            if kind == "outdir":
                os.makedirs(v, exist_ok=True)
            if kind == "out":
                d = os.path.dirname(os.path.abspath(v))
                os.makedirs(d, exist_ok=True)
            values.append(v)
        return cmd, values, state

    def run(self):
        if self.proc or not self.edl:
            return
        try:
            cmd, values, state = self.collect()
        except (ValueError, OSError) as e:
            messagebox.showerror("Lỗi", str(e))
            return
        args, dropped = build_args(cmd, values, state, self.valid.get(cmd) if self.valid else None)
        argv = [sys.executable, "-u", self.edl] + args
        if cmd in DANGEROUS and not state.get("skipwrite"):
            if not messagebox.askyesno("Xác nhận", "Lệnh có thể ghi/xóa dữ liệu trên máy:\n\n%s\n\nChạy?" % cmdline_text(argv)):
                return
        self.write("> %s\n" % cmdline_text(argv))
        if dropped:
            self.write("(bỏ qua option không hỗ trợ cho lệnh này: %s)\n" % ", ".join("--" + d for d in dropped))
        env = dict(os.environ, PYTHONUNBUFFERED="1", PYTHONIOENCODING="utf-8")
        kw = {}
        if os.name == "nt":
            kw["creationflags"] = subprocess.CREATE_NO_WINDOW
        try:
            self.proc = subprocess.Popen(argv, cwd=HERE, env=env, stdin=subprocess.DEVNULL,
                                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=0, **kw)
        except OSError as e:
            self.write("Không chạy được: %s\n" % e)
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
                self.q.put(dec.decode(data))
        except OSError:
            pass
        self.q.put(("done", proc.wait()))

    def pump(self):
        try:
            while True:
                item = self.q.get_nowait()
                if isinstance(item, tuple):
                    self.write("\n[xong, mã thoát %s]\n" % item[1])
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
            if not messagebox.askyesno("Thoát", "Đang chạy lệnh, dừng và thoát?"):
                return
            self.proc.terminate()
        self.root.destroy()

    # ---- dò thiết bị ----
    def detect(self):
        try:
            import usb.core
            sys.path.insert(0, HERE)
            from edlclient.Config.usb_ids import default_ids
        except Exception as e:
            self.write("Không nạp được pyusb/usb_ids: %s\n" % e)
            return
        try:
            devs = list(usb.core.find(find_all=True))
        except Exception as e:
            self.write("Không liệt kê được USB (thiếu libusb backend?): %s\n" % e)
            return
        known = {(v, p) for v, p, _ in default_ids}
        found = False
        for d in devs:
            if (d.idVendor, d.idProduct) in known:
                self.write("EDL: %04x:%04x\n" % (d.idVendor, d.idProduct))
                found = True
            elif d.idVendor == 0x05C6:
                self.write("Qualcomm nhưng không phải EDL: %04x:%04x\n" % (d.idVendor, d.idProduct))
                found = True
        if not found:
            self.write("Không thấy thiết bị EDL.\n")


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
