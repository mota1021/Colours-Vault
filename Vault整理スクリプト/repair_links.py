#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
repair_links.py
Colours shared リンク破損修復スクリプト
──────────────────────────────────────
破損原因: rename_underscore_to_dot.py の collect_link_replacements が
短いプレフィックス(010., 020. 等)をファイル内テキストへ再帰適用し
wikiリンク・パス記述の数字プレフィックスが指数的に自己増殖した。

修復方針:
  - ディスクの正しい構造を「正解データ」として使用
  - wikiリンクのラベル(|LABEL)と残存日本語から正しいターゲットを特定
  - ドライランで差分レポート後、確認を経てファイル書き込み
"""

import os
import re
import sys
import argparse
from pathlib import Path
from typing import Optional

SHARED = Path(__file__).resolve().parent.parent  # …/shared/

# ──────────────────────────
#  ユーティリティ
# ──────────────────────────

def is_corrupted(s: str) -> bool:
    """3段以上連続する NNN. チェーンを「破損」と判定する。"""
    return bool(re.search(r'(\d{3}\.){3,}', s))

def japanese_tail(name: str) -> str:
    """先頭の連続する NNN. チェーンを除去し、日本語部分を返す。"""
    return re.sub(r'^(\d{3}\.)+', '', name)

def extract_japanese(s: str) -> Optional[str]:
    """破損した文字列から日本語ラベルを抽出する。
    優先順: 最後の _ の後 → 末尾の非ASCII連続部分。
    注意: '演出・UI' の UI など、ラベル内 ASCII は保持する。
          除去するのは .md / .000.index / .index などの拡張子のみ。
    """
    EXT_PATTERN = re.compile(r'\.(md|000\.index|index)$')

    # パターン1: _JAPANESE (旧 _ 区切りディレクトリ名の残影)
    if '_' in s:
        after = s.rsplit('_', 1)[-1]
        # / 以降はファイル部分なので除去
        after = after.split('/')[0]
        after = EXT_PATTERN.sub('', after)
        if re.search(r'[^\x00-\x7F]', after):
            return after.strip()

    # パターン2: 末尾の日本語開始点から末尾まで
    m = re.search(r'[^\x00-\x7F].*$', s)
    if m:
        tail = m.group(0)
        # 拡張子パターンのみ除去（ラベル内 ASCII は残す）
        tail = EXT_PATTERN.sub('', tail)
        if re.search(r'[^\x00-\x7F]', tail):
            return tail.strip()

    return None

# ──────────────────────────
#  ディスクインデックス構築
# ──────────────────────────

def build_disk_index():
    """
    shared/ を走査し以下を返す:
        files : {rel_path(from shared/) -> Path}  (.md ファイル)
        dirs  : {rel_path(from shared/) -> Path}  (ディレクトリ)
        label_to_dirs  : {japanese_tail -> [rel_dir_path, ...]}
        label_to_files : {japanese_tail -> [rel_file_path, ...]}
    """
    files = {}
    dirs = {}
    label_to_dirs: dict[str, list[str]] = {}
    label_to_files: dict[str, list[str]] = {}

    for root, dirnames, filenames in os.walk(SHARED):
        root_path = Path(root)

        for d in dirnames:
            if d.startswith('.'):
                continue
            dir_path = root_path / d
            rel = dir_path.relative_to(SHARED).as_posix()
            dirs[rel] = dir_path
            tail = japanese_tail(d)
            if tail and re.search(r'[^\x00-\x7F]', tail):
                label_to_dirs.setdefault(tail, []).append(rel)

        for f in filenames:
            if not f.endswith('.md'):
                continue
            file_path = root_path / f
            rel = file_path.relative_to(SHARED).as_posix()
            files[rel] = file_path
            stem = f[:-3]  # .md を除去
            tail = japanese_tail(stem)
            if tail and re.search(r'[^\x00-\x7F]', tail):
                label_to_files.setdefault(tail, []).append(rel)

    return files, dirs, label_to_dirs, label_to_files

def find_index_in_dir(dir_abs: Path) -> Optional[str]:
    """ディレクトリ内の NNN.000.index.md を探し、stem を返す。"""
    try:
        for f in dir_abs.iterdir():
            if re.match(r'^\d{3}\.000\.index\.md$', f.name):
                return f.stem  # 拡張子なし
    except FileNotFoundError:
        pass
    return None

# ──────────────────────────
#  wikiリンク修復
# ──────────────────────────

def resolve_dir(label: str, source_dir_rel: str,
                label_to_dirs: dict) -> Optional[str]:
    """ラベルからディレクトリの rel_path を解決。複数候補は文脈で絞る。"""
    candidates = label_to_dirs.get(label, [])
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]

    # 文脈解決: source_dir の最も近い祖先に属するものを優先
    source_parts = source_dir_rel.split('/')
    best = None
    best_common = -1
    for cand in candidates:
        cand_parts = cand.split('/')
        common = sum(1 for a, b in zip(source_parts, cand_parts) if a == b)
        if common > best_common:
            best_common = common
            best = cand
    return best

def resolve_file(label: str, source_dir_rel: str,
                 label_to_files: dict) -> Optional[str]:
    """ラベルからファイルの rel_path を解決。同ディレクトリ優先。"""
    candidates = label_to_files.get(label, [])
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]

    # 同ディレクトリ内優先
    for cand in candidates:
        if str(Path(cand).parent.as_posix()) == source_dir_rel:
            return cand

    # 近い祖先
    source_parts = source_dir_rel.split('/')
    best = None
    best_common = -1
    for cand in candidates:
        cand_parts = cand.split('/')
        common = sum(1 for a, b in zip(source_parts, cand_parts) if a == b)
        if common > best_common:
            best_common = common
            best = cand
    return best

def repair_wikilink(match_text: str, source_dir_rel: str,
                    label_to_dirs: dict, label_to_files: dict) -> Optional[str]:
    """
    破損した wikilink を修復して返す。修復不能なら None。
    match_text: [[...]] 全体文字列
    """
    inner = match_text[2:-2]  # [[ と ]] を除去

    # パイプを分解 (テーブル内 \| または通常 |)
    table_pipe = '\\|' in inner
    if table_pipe:
        parts = inner.split('\\|', 1)
    elif '|' in inner:
        parts = inner.split('|', 1)
    else:
        parts = [inner]

    target = parts[0]
    label = parts[1].strip() if len(parts) > 1 else None

    if not is_corrupted(target):
        return None  # 破損なし→スキップ

    # ../ プレフィックス保持
    prefix_m = re.match(r'^((?:\.\./)+)', target)
    prefix = prefix_m.group(1) if prefix_m else ''
    body = target[len(prefix):]

    # ディレクトリ/ファイル分割
    if '/' in body:
        dir_part, file_part = body.rsplit('/', 1)
    else:
        dir_part = None
        file_part = body

    # 解決キー: ラベル → dir_part の日本語 → file_part の日本語
    if label:
        search_key = label
    elif dir_part:
        search_key = extract_japanese(dir_part)
    else:
        search_key = extract_japanese(file_part)

    if not search_key:
        return None

    # index ファイルへのリンクかどうか
    is_index = dir_part is not None and bool(
        re.search(r'index$', file_part)
    )

    pipe_char = '\\|' if table_pipe else '|'

    # ラベルの正規化: 末尾 .md / / を除去して lookup キーにする
    def normalize_label(lbl: Optional[str]) -> Optional[str]:
        if lbl is None:
            return None
        s = lbl.rstrip('/')
        if s.endswith('.md'):
            s = s[:-3]
        return s.strip() if s else None

    # lookup に使うキー（label → normalized label → search_key）
    if label:
        lookup_key = normalize_label(label) or search_key
    else:
        lookup_key = search_key

    if is_index:
        # ディレクトリ → index ファイル
        # まず lookup_key で試みる
        dir_rel = resolve_dir(lookup_key, source_dir_rel, label_to_dirs)
        # 見つからなければ dir_part の日本語でフォールバック
        if not dir_rel and dir_part:
            alt_key = extract_japanese(dir_part)
            if alt_key and alt_key != lookup_key:
                dir_rel = resolve_dir(alt_key, source_dir_rel, label_to_dirs)
        if not dir_rel:
            return None
        dir_abs = SHARED / dir_rel
        index_stem = find_index_in_dir(dir_abs)
        if not index_stem:
            return None
        dir_basename = Path(dir_rel).name
        new_target = f"{prefix}{dir_basename}/{index_stem}"
        return f"[[{new_target}{pipe_char}{label}]]" if label else f"[[{new_target}]]"

    else:
        # ラベルが / で終わるならディレクトリリンクとして扱う
        if label and label.endswith('/'):
            dir_rel = resolve_dir(lookup_key, source_dir_rel, label_to_dirs)
            if not dir_rel:
                return None
            dir_basename = Path(dir_rel).name
            return f"[[{prefix}{dir_basename}{pipe_char}{label}]]"

        # 通常ファイルへのリンク
        file_rel = resolve_file(lookup_key, source_dir_rel, label_to_files)
        if not file_rel and lookup_key != search_key:
            file_rel = resolve_file(search_key, source_dir_rel, label_to_files)
        if not file_rel:
            return None
        stem = Path(file_rel).stem
        new_target = f"{prefix}{stem}"
        return f"[[{new_target}{pipe_char}{label}]]" if label else f"[[{new_target}]]"

# ──────────────────────────
#  backtick 参照修復
# ──────────────────────────

# 仕様ファイル内の兄弟ファイルが持つ日本語サフィックスの標準マッピング
SUFFIX_MAP = {
    'ラフ':    '010',
    '仕様':    '020',
    '演出・UI': '030',
    '実装':    '040',
}

def repair_backtick(inner: str, source_dir_rel: str,
                    label_to_files: dict) -> Optional[str]:
    """
    破損した backtick 内テキストを修復して返す。
    inner: バッククォートの中身
    """
    if not is_corrupted(inner):
        return None

    # 先頭の . は suffix パターン (.020.仕様 形式)
    is_suffix_pattern = inner.startswith('.')

    jp = extract_japanese(inner)
    if not jp:
        # 末尾 .000.index だけの場合はスキップ
        return None

    if is_suffix_pattern:
        # 標準マッピングで解決
        if jp in SUFFIX_MAP:
            return f".{SUFFIX_MAP[jp]}.{jp}"
        # ファイルから探す
        candidates = label_to_files.get(jp, [])
        for c in candidates:
            if str(Path(c).parent.as_posix()) == source_dir_rel:
                stem = Path(c).stem
                # 末尾の NNN.JAPANESE を .NNN.JAPANESE に変換
                m = re.match(r'.*?(\d{3})\.([^\d].*)$', stem)
                if m:
                    return f".{m.group(1)}.{m.group(2)}"
        return None

    else:
        # 具体的なファイル参照 (例: 010.030.演出・UI)
        candidates = label_to_files.get(jp, [])

        # 同ディレクトリ内のファイルを優先（プレフィックスは問わない）
        for c in candidates:
            if str(Path(c).parent.as_posix()) == source_dir_rel:
                return Path(c).stem

        return None

# ──────────────────────────
#  ファイル単位の処理
# ──────────────────────────

WIKILINK_RE = re.compile(r'\[\[[^\]]+\]\]')
BACKTICK_RE = re.compile(r'`([^`\n]+)`')

def process_file(filepath: Path, label_to_dirs: dict, label_to_files: dict,
                 dry_run: bool = True):
    """
    1ファイルを処理する。
    返り値: (original_text, modified_text, changes: list[tuple])
    changes は (種別, 旧内容, 新内容) のリスト。
    """
    content = filepath.read_text(encoding='utf-8')

    if not is_corrupted(content):
        return content, content, []

    source_dir_rel = filepath.parent.relative_to(SHARED).as_posix()
    modified = content
    changes = []
    unresolved = []

    # 1. wikiリンク修復
    def fix_wikilink(m):
        orig = m.group(0)
        if not is_corrupted(orig):
            return orig
        fixed = repair_wikilink(orig, source_dir_rel, label_to_dirs, label_to_files)
        if fixed and fixed != orig:
            changes.append(('wiki', orig, fixed))
            return fixed
        unresolved.append(('wiki', orig))
        return orig  # 変更なし

    modified = WIKILINK_RE.sub(fix_wikilink, modified)

    # 2. backtick 参照修復
    def fix_backtick(m):
        inner = m.group(1)
        if not is_corrupted(inner):
            return m.group(0)
        fixed_inner = repair_backtick(inner, source_dir_rel, label_to_files)
        if fixed_inner and fixed_inner != inner:
            fixed = f'`{fixed_inner}`'
            changes.append(('btick', m.group(0), fixed))
            return fixed
        unresolved.append(('btick', m.group(0)))
        return m.group(0)

    modified = BACKTICK_RE.sub(fix_backtick, modified)

    return content, modified, changes, unresolved

# ──────────────────────────
#  メイン
# ──────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Colours shared リンク修復')
    parser.add_argument('--apply', action='store_true',
                        help='実際にファイルを書き換える（指定なしはドライラン）')
    parser.add_argument('--file', type=str, default=None,
                        help='特定ファイルのみ処理 (shared/ からの相対パス)')
    args = parser.parse_args()

    # stdout を UTF-8 に強制
    sys.stdout.reconfigure(encoding='utf-8')

    print("=== disk index building... ===")
    files, dirs, label_to_dirs, label_to_files = build_disk_index()
    print(f"  files: {len(files)}, dirs: {len(dirs)}")
    print(f"  label->dirs: {len(label_to_dirs)}, label->files: {len(label_to_files)}")
    print()

    # 処理対象ファイルを収集
    if args.file:
        target_files = [SHARED / args.file]
    else:
        target_files = [
            SHARED / rel for rel, path in files.items()
            if is_corrupted(path.read_text(encoding='utf-8'))
        ]

    print(f"target: {len(target_files)} files")
    print(f"mode: {'APPLY' if args.apply else 'DRY-RUN (no changes)'}")
    print("=" * 60)
    print()

    total_fixed = 0
    total_unresolved = 0

    for fp in sorted(target_files):
        rel = fp.relative_to(SHARED).as_posix()
        result = process_file(fp, label_to_dirs, label_to_files, dry_run=not args.apply)

        # process_file は (original, modified, changes, unresolved) を返す
        original, modified, changes, unresolved = result

        if not changes and not unresolved:
            continue

        print(f"[FILE] {rel}")

        for kind, old, new in changes:
            tag = "[wiki]" if kind == 'wiki' else "[btick]"
            old_s = (old[:100] + '...') if len(old) > 100 else old
            new_s = (new[:100] + '...') if len(new) > 100 else new
            print(f"  {tag} FIXED:")
            print(f"     OLD: {old_s}")
            print(f"     NEW: {new_s}")

        for kind, text in unresolved:
            tag = "[wiki]" if kind == 'wiki' else "[btick]"
            text_s = (text[:100] + '...') if len(text) > 100 else text
            print(f"  {tag} UNRESOLVED: {text_s}")

        total_fixed += len(changes)
        total_unresolved += len(unresolved)

        if args.apply and modified != original:
            fp.write_text(modified, encoding='utf-8')
            print(f"  -> written ({len(changes)} fixes)")

        print()

    print("=" * 60)
    print(f"fixed:      {total_fixed}")
    print(f"unresolved: {total_unresolved}  (manual review needed)")
    if not args.apply:
        print()
        print("DRY-RUN complete. Re-run with --apply to write changes.")


if __name__ == '__main__':
    main()
