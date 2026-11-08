#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Filter a Loaders folder: keep only the files that edl recognizes.

"Recognized" uses the same rules as loader_db.init_loader_db:
  - extension is .bin / .mbn / .elf
  - name looks like <hwid>_<pkhash>... (hwid = 8 char msmid + non-empty devid)
  - msmid can be mapped by convertmsmid (ends with e1, or is in sochw/msmids)

Usage:
  python filter_loaders.py <source_Loaders_dir> <destination_dir> [--dedupe] [--dry-run]

  --dedupe   keep one file per (hwid, pkhash) pair. edl only uses the first file of
             each pair, so variants such as _peek or _EDLAuth are dropped.
  --dry-run  only print what would be kept, copy nothing.
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
    """(hwid, pkhash) pairs edl would register for this file; empty if not recognized."""
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
    ap = argparse.ArgumentParser(description="Keep only the loaders that edl recognizes")
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--dedupe", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    if not os.path.isdir(a.src):
        sys.exit("Source folder not found: %s" % a.src)
    if os.path.abspath(a.src) == os.path.abspath(a.dst):
        sys.exit("Source and destination must be different")

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
                print("keep:", rel)
                continue
            out = os.path.join(a.dst, rel)
            os.makedirs(os.path.dirname(out), exist_ok=True)
            shutil.copy2(path, out)

    mb = 1024 * 1024
    print("Total %d files (%.1f MB) | recognized %d | kept %d (%.1f MB)%s" % (
        total, size_all / mb, recognized, kept, size_kept / mb, " [dry-run]" if a.dry_run else ""))


if __name__ == "__main__":
    main()
