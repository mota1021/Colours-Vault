#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Obsidian wikilink fixer for Colours project.

Usage:
  fix_links.py OLD NEW           # rename [[OLD]] → [[NEW]] across all .md files
  fix_links.py OLD               # delete every [[OLD]] token (bare removal)
  fix_links.py --dry-run OLD NEW # preview only, no writes
  fix_links.py --root PATH OLD NEW  # operate on a different directory

OLD / NEW are the link targets as they appear inside [[ ]], e.g.:
  fix_links.py "実装バックログ" "要チケット化リスト"
  fix_links.py "仕様/05_懸念点"
"""
import argparse
import sys
from pathlib import Path

DEFAULT_ROOT = Path(__file__).parent


def fix_links(root: Path, old: str, new: str, dry_run: bool) -> None:
    old_token = f"[[{old}]]"
    new_token = f"[[{new}]]" if new else ""

    changed: list[tuple[Path, int]] = []

    for md in sorted(root.rglob("*.md")):
        text = md.read_text(encoding="utf-8")
        count = text.count(old_token)
        if count == 0:
            continue
        if not dry_run:
            md.write_text(text.replace(old_token, new_token), encoding="utf-8")
        changed.append((md, count))

    label = "[DRY RUN] " if dry_run else ""
    arrow = f"→ [[{new}]]" if new else "→ (削除)"
    print(f"\n{label}[[{old}]] {arrow}  ({sum(c for _, c in changed)} 箇所, {len(changed)} ファイル)\n")
    for path, count in changed:
        rel = path.relative_to(root)
        print(f"  {'(would) ' if dry_run else ''}{rel}  ({count}箇所)")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rename or delete Obsidian wikilinks across .md files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("old", help="Link target to find (inside [[...]])")
    parser.add_argument("new", nargs="?", default="", help="Replacement target (omit to delete)")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="Search root directory")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")

    args = parser.parse_args()

    if not args.root.is_dir():
        print(f"ERROR: root not found: {args.root}", file=sys.stderr)
        sys.exit(1)

    fix_links(args.root, args.old, args.new, args.dry_run)


if __name__ == "__main__":
    main()
