#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
壊れたリンク・パス参照を修正する。

スクリプトのリンク置換ロジックが短い数字プレフィックス（010. 020. 等）を
ファイル内テキストにも再帰適用してしまった結果、
`030.演出・UI` → `030.040.020.010....演出・UI` のように連鎖展開された箇所を元に戻す。

修正パターン: `(\d{3}\.){2,}(日本語名)` → `NNN.(日本語名)` （最後の NNN. だけ残す）

Usage:
  fix_broken_links.py             # 実行
  fix_broken_links.py --dry-run   # プレビューのみ
"""
import re
import sys
import argparse
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ('utf-8', 'utf8'):
    sys.stdout.reconfigure(encoding='utf-8')

SHARED_ROOT = Path(__file__).parent.parent

# `(\d{3}\.){2,}` の繰り返しを「最初の NNN. だけ」に圧縮する
# ただし次の文字が数字（040.000.index の 000 等）の場合は圧縮しない
# 例: `030.040.020.010.演出・UI` → `030.演出・UI`
# 例: `040.000.index` → そのまま
BROKEN_PATTERN = re.compile(r'(\d{3}\.){2,}(?=[^\x00-\x7F])')


def fix_text(text: str) -> str:
    """繰り返し数字プレフィックスを最初の NNN. だけに圧縮する。"""
    def replace(m: re.Match) -> str:
        return m.group(0)[:4]  # 最初の "NNN." だけ返す
    return BROKEN_PATTERN.sub(replace, text)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    label = '[DRY RUN] ' if args.dry_run else ''
    changed = 0

    for md in sorted(SHARED_ROOT.rglob('*.md')):
        text = md.read_text(encoding='utf-8')
        new_text = fix_text(text)
        if new_text != text:
            print(f'  {label}FIX  {md.relative_to(SHARED_ROOT)}')
            if not args.dry_run:
                md.write_text(new_text, encoding='utf-8')
            changed += 1

    print(f'\n  {label}修正: {changed} ファイル')
    if args.dry_run:
        print('[DRY RUN 完了 — 変更は適用されていません]')


if __name__ == '__main__':
    main()
