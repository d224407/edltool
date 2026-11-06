#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lọc Loaders: chỉ giữ những file mà edl nhận ra.

"Nhận ra" dùng đúng logic của loader_db.init_loader_db:
  - đuôi .bin / .mbn / .elf
  - tên dạng <hwid>_<pkhash>...  (hwid = msmid 8 ký tự + devid, devid không rỗng)
  - msmid map được qua convertmsmid (đuôi e1 hoặc có trong bảng sochw/msmids)

Dùng:
  python filter_loaders.py <thư_mục_Loaders_gốc> <thư_mục_đích> [--dedupe] [--dry-run]

  --dedupe   chỉ giữ 1 file cho mỗi cặp (hwid, pkhash); edl chỉ dùng file đầu tiên
             của mỗi cặp, các file còn lại (vd. biến thể _peek, _EDLAuth) sẽ bị bỏ
  --dry-run  chỉ in kết quả, không copy
"""
import argparse
import logging
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from edlclient.Library.loader_db import loader_utils  # noqa: E402

EXTS = (".bin", ".mbn", ".elf")


def keys_for(filename, lu):
    """Danh sách (hwid, pkhash) mà edl sẽ đăng ký cho file này; rỗng nếu không nhận ra."""
    if not filename.endswith(EXTS):
        return []
    try:
        parts = filename.split("_")
        hwid = parts[0].lower()
        msmid = hwid[:8]
        int(msmid, 16)
        devid = hwid[8:]
        if devid == "" or len(parts) < 2:
            return []
        pkhash = parts[1].lower()
        return [((m + devid).lower(), pkhash) for m in lu.convertmsmid(msmid)]
    except Exception:
        return []


def main():
    ap = argparse.ArgumentParser(description="Giữ lại những loader mà edl nhận ra")
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--dedupe", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    if not os.path.isdir(a.src):
        sys.exit("Không thấy thư mục nguồn: %s" % a.src)
    if os.path.abspath(a.src) == os.path.abspath(a.dst):
        sys.exit("Nguồn và đích phải khác nhau")

    lu = loader_utils(logging.ERROR)
    seen = set()
    total = recognized = kept = 0
    size_all = size_kept = 0
    for dirpath, dirnames, filenames in os.walk(a.src):
        dirnames[:] = sorted(d for d in dirnames if d != ".git")
        for name in sorted(filenames):
            path = os.path.join(dirpath, name)
            size = os.path.getsize(path)
            total += 1
            size_all += size
            keys = keys_for(name, lu)
            if not keys:
                continue
            recognized += 1
            if a.dedupe:
                if all(k in seen for k in keys):
                    continue
                seen.update(keys)
            kept += 1
            size_kept += size
            rel = os.path.relpath(path, a.src)
            if a.dry_run:
                print("giữ:", rel)
                continue
            out = os.path.join(a.dst, rel)
            os.makedirs(os.path.dirname(out), exist_ok=True)
            shutil.copy2(path, out)

    mb = 1024 * 1024
    print("Tổng %d file (%.1f MB) | nhận ra %d | giữ %d (%.1f MB)%s" % (
        total, size_all / mb, recognized, kept, size_kept / mb, " [dry-run]" if a.dry_run else ""))


if __name__ == "__main__":
    main()
