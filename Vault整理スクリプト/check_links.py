#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Obsidian wikilink broken-link checker for Colours project"""
import os, re, sys
from pathlib import Path

VAULT = Path("D:/document/ObsidianVault")
SEARCH_ROOT = VAULT / "創作/ゲーム/Colours"

# Build index: stem -> list of paths
file_index: dict[str, list[Path]] = {}
for p in VAULT.rglob("*.md"):
    key = p.stem
    file_index.setdefault(key, []).append(p)

PATTERN = re.compile(r'\[\[([^\]|#]+?)(?:[|#][^\]]*)?\]\]')

broken: list[tuple[Path, str]] = []

md_files = list(SEARCH_ROOT.rglob("*.md"))
for md in md_files:
    text = md.read_text(encoding="utf-8", errors="ignore")
    for m in PATTERN.finditer(text):
        target = m.group(1).strip()
        # Use last path segment; strip .md suffix if present (Obsidian omits it)
        last = target.split("/")[-1].split("\\")[-1]
        stem = last[:-3] if last.lower().endswith(".md") else last
        if not stem:
            continue
        if stem not in file_index:
            broken.append((md, target))

print(f"\n=== BROKEN LINKS ({len(broken)}) ===")
by_file: dict[str, list[str]] = {}
for src, link in broken:
    rel = str(src.relative_to(SEARCH_ROOT))
    by_file.setdefault(rel, []).append(link)

for src_rel, links in by_file.items():
    print(f"\n[{src_rel}]")
    for lnk in links:
        print(f"  [[{lnk}]]")

print(f"\nTotal files scanned: {len(md_files)}")
print(f"Total broken links : {len(broken)}")
