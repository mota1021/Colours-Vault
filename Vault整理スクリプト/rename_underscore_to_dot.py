#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
番号と名前の間の _ を . に統一し、カラーシステム構造を追加する。

Usage:
  rename_underscore_to_dot.py             # 実行
  rename_underscore_to_dot.py --dry-run   # プレビューのみ
"""
import re
import shutil
import argparse
import sys
from pathlib import Path

# Windows PowerShell での日本語出力対応
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ('utf-8', 'utf8'):
    sys.stdout.reconfigure(encoding='utf-8')

SHARED_ROOT = Path(__file__).parent.parent

# 名前中の NNN_ パターンを NNN. に変換（先頭 _ のテンプレートは除外）
_NUM_UNDERSCORE = re.compile(r'(\d{3})_')


def new_name(name: str) -> str | None:
    """名前中の NNN_ を NNN. に変換。先頭 _ のテンプレートは除外。変更なければ None。"""
    if name.startswith('_'):
        return None
    new = _NUM_UNDERSCORE.sub(r'\1.', name)
    return new if new != name else None


def collect_renames(root: Path) -> list[tuple[Path, Path]]:
    """深い階層から順に (old, new) ペアを列挙。"""
    renames: list[tuple[Path, Path]] = []
    # 深い順（ファイルとディレクトリ両方）
    all_paths = sorted(root.rglob("*"), key=lambda p: len(p.parts), reverse=True)
    for path in all_paths:
        n = new_name(path.name)
        if n is None:
            continue
        renames.append((path, path.parent / n))
    return renames


def collect_link_replacements(renames: list[tuple[Path, Path]], root: Path) -> list[tuple[str, str]]:
    """
    リネームペアから wikiリンク / 相対パス参照の置換ペアを生成。
    シンプルに「旧名 → 新名」のステム・ディレクトリ名レベルで置換する。
    """
    replacements: list[tuple[str, str]] = []
    seen: set[str] = set()
    for old, new in renames:
        old_name = old.name if old.is_dir() else old.stem
        new_name_str = new.name if old.is_dir() else new.stem  # new はまだ存在しない場合あり
        # ディレクトリ名の場合はそのまま、ファイルは stem
        if old.suffix == ".md":
            old_name = old.stem
            new_name_str = new.stem
        pair = (old_name, new_name_str)
        if pair not in seen and old_name != new_name_str:
            seen.add(pair)
            replacements.append(pair)
    return replacements


def apply_renames(renames: list[tuple[Path, Path]], dry_run: bool) -> None:
    for old, new in renames:
        if not old.exists():
            continue
        label = "[DRY RUN] " if dry_run else ""
        print(f"  {label}RENAME  {old.relative_to(SHARED_ROOT)}  →  {new.name}")
        if not dry_run:
            old.rename(new)


def move_colour_system(dry_run: bool) -> list[tuple[str, str]]:
    """
    カラーシステム構造への移動。
    リネーム後のパスを前提にする（先に apply_renames を呼ぶこと）。

    050.仕様/050.010.混色システム/ → 050.仕様/050.010.カラーシステム/010.010.光/
    050.仕様/050.060.インク混色/   → 050.仕様/050.010.カラーシステム/010.020.インク/
    060.xxx ファイルは 020.xxx にリナンバー。
    """
    spec = SHARED_ROOT / "050.仕様"
    colour_sys = spec / "050.010.カラーシステム"
    light_dst = colour_sys / "010.010.光"
    ink_dst = colour_sys / "010.020.インク"

    light_src = spec / "050.010.混色システム"
    ink_src = spec / "050.060.インク混色"

    # リンク置換ペア（内容更新用に返す）
    link_pairs: list[tuple[str, str]] = []

    label = "[DRY RUN] " if dry_run else ""

    # --- 光（混色システム → カラーシステム/光） ---
    if light_src.exists():
        print(f"\n  {label}MOVE  {light_src.relative_to(SHARED_ROOT)}  →  {light_dst.relative_to(SHARED_ROOT)}")
        if not dry_run:
            light_dst.parent.mkdir(parents=True, exist_ok=True)
            # pending index を本来の場所に移動してからフォルダを移動
            pending = light_src / "_カラーシステム_index_pending.md"
            if pending.exists():
                colour_sys.mkdir(parents=True, exist_ok=True)
                pending.rename(colour_sys / "010.000.index.md")
            shutil.move(str(light_src), str(light_dst))
        else:
            pending = light_src / "_カラーシステム_index_pending.md"
            if pending.exists():
                print(f"  {label}MOVE  {pending.relative_to(SHARED_ROOT)}  →  050.仕様/050.010.カラーシステム/010.000.index.md")
        link_pairs.append(("050.010.混色システム", "050.010.カラーシステム/010.010.光"))
        link_pairs.append(("混色システム", "光"))

    # --- インク（インク混色 → カラーシステム/インク、060.xxx → 020.xxx） ---
    if ink_src.exists():
        print(f"  {label}MOVE  {ink_src.relative_to(SHARED_ROOT)}  →  {ink_dst.relative_to(SHARED_ROOT)}")
        if not dry_run:
            ink_dst.parent.mkdir(parents=True, exist_ok=True)
            tmp = spec / "_ink_tmp"
            shutil.move(str(ink_src), str(tmp))
            # 060.xxx → 020.xxx リナンバー
            for child in sorted(tmp.iterdir()):
                new_child_name = re.sub(r'^060\.', '020.', child.name)
                child.rename(tmp / new_child_name)
            shutil.move(str(tmp), str(ink_dst))
        link_pairs.append(("050.060.インク混色", "050.010.カラーシステム/010.020.インク"))
        link_pairs.append(("インク混色", "インク"))
        # 060.xxx → 020.xxx のリンク置換
        for n in ["060.000.index", "060.010.ラフ", "060.020.仕様", "060.030.演出・UI", "060.040.実装"]:
            link_pairs.append((n, n.replace("060.", "020.")))

    return link_pairs


def update_links(extra_pairs: list[tuple[str, str]], dry_run: bool) -> None:
    """全 .md ファイル内のリンク・パス参照を一括置換。"""
    # extra_pairs: (old_str, new_str) — ファイル内テキストをそのまま置換
    if not extra_pairs:
        return

    label = "[DRY RUN] " if dry_run else ""
    changed_files = 0

    for md in sorted(SHARED_ROOT.rglob("*.md")):
        text = md.read_text(encoding="utf-8")
        new_text = text
        for old_str, new_str in extra_pairs:
            new_text = new_text.replace(old_str, new_str)
        if new_text != text:
            print(f"  {label}LINKS  {md.relative_to(SHARED_ROOT)}")
            if not dry_run:
                md.write_text(new_text, encoding="utf-8")
            changed_files += 1

    print(f"\n  {label}リンク更新: {changed_files} ファイル")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="プレビューのみ（変更しない）")
    args = parser.parse_args()

    print(f"ROOT: {SHARED_ROOT}\n")

    # 1. リネーム対象を収集
    print("=== STEP 1: NNN_名前 → NNN.名前 リネーム ===")
    renames = collect_renames(SHARED_ROOT)
    if renames:
        apply_renames(renames, args.dry_run)
    else:
        print("  (対象なし)")

    # 2. カラーシステム構造への移動
    print("\n=== STEP 2: カラーシステム構造への移動 ===")
    extra_link_pairs = move_colour_system(args.dry_run)

    # 3. wikiリンク・パス参照の更新
    print("\n=== STEP 3: wikiリンク・パス参照の更新 ===")
    # リネームから生成した置換ペア（ディレクトリ名・ファイルステムレベル）
    rename_link_pairs = collect_link_replacements(renames, SHARED_ROOT)
    all_pairs = rename_link_pairs + extra_link_pairs
    update_links(all_pairs, args.dry_run)

    print("\n完了。" if not args.dry_run else "\n[DRY RUN 完了 — 変更は適用されていません]")


if __name__ == "__main__":
    main()
