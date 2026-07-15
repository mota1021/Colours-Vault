# -*- coding: utf-8 -*-
"""
参照整合性チェックスクリプト

指定フォルダ配下の .md を走査し、以下2種類の参照が実在するかを確認する:
  1. Obsidian wikilink [[target]] / [[target|alias]] / [[target#heading]]
  2. バッククォート内のパス様文字列（"/" を含み .md で終わるもの）

wikilink は Obsidian の実際の解決規則に合わせ、Vault全体（.git のあるフォルダ）を
対象に basename で解決する。パス参照は カレントディレクトリ / 参照元ファイルのディレクトリ /
Vaultルート の3箇所を基準に解決する。

誤検知を避けるため、プレースホルダーを含む行（<...> {{...}} YYYY NNN XXX 等）は対象外とし、
archive/ 配下（過去スナップショット、直すべきでない凍結記録）は走査対象から除外する。
決定ログ.md（追記専用の凍結履歴。当時の記録として旧名・旧パスのまま保存する方針）も走査対象から
除外する。実装ログ（*実装ログ*/ 配下）はUEプロジェクト側（別リポジトリ）のパスを含むためパス参照
チェックの対象外とする（wikilinkチェックは対象のまま）。

意図的で恒久的な参照（例: Obsidian導入前オンボーディングのパス表記）は、その行に
明示マーカー `check-links-ignore` を書けばその行の検査をスキップする。毎回「問題なし」と
再判定するコストを避けるための仕組み。Obsidian上で不可視なHTMLコメントで理由を併記する運用:
    ... `030.環境整備/ドキュメント閲覧ガイド.md`<!-- check-links-ignore: 理由 --> ...

結果は標準出力に一覧表示するのみ。非ブロッキングのツールのため、呼び出し側は終了コードで
処理を止める必要はない（0=検出なし / 1=検出あり、の情報用途のみ）。

使い方:
    python shared/Vault整理スクリプト/check_links.py 個人計画 shared
    （Colours プロジェクト直下から実行する想定。相対パスの解決基準はカレントディレクトリ）
"""

import re
import sys
from pathlib import Path

WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")
PATH_REF_RE = re.compile(r"`([^`\s]+/[^`\s]+\.md)`")

PLACEHOLDER_TOKEN_RE = re.compile(r"<[^<>]+>|\{\{[^{}]+\}\}|\{[^{}]+\}")
PLACEHOLDER_MARKERS = ("YYYY", "NNN", "XXX")
# archive/ とテンプレート系(_で始まるフォルダ・ファイル)は「スキャン対象(参照元)」からは除外する。
# ただし他ファイルからそこへ向かうリンクは正当なので、basenameインデックス(リンク先)には含める。
EXCLUDED_SCAN_DIR_NAMES = ("archive",)
# 追記専用の凍結履歴ファイル。当時の記録として旧名・旧パスのまま保存する方針のため、
# 参照元としては走査しない(archive/ と同思想)。リンク先indexには含める。
EXCLUDED_SCAN_FILE_NAMES = ("決定ログ.md",)
IMPL_LOG_MARKER = "実装ログ"
# この文字列を含む行は検査をスキップする。意図的で恒久的な参照を毎回再判定しないための明示マーカー。
# HTMLコメント <!-- check-links-ignore: 理由 --> として書けばObsidian上は不可視のまま注記できる。
IGNORE_LINE_MARKER = "check-links-ignore"


def has_placeholder(text):
    if PLACEHOLDER_TOKEN_RE.search(text):
        return True
    return any(marker in text for marker in PLACEHOLDER_MARKERS)


def is_excluded_from_scan(path):
    if path.name in EXCLUDED_SCAN_FILE_NAMES:
        return True
    if any(part in EXCLUDED_SCAN_DIR_NAMES for part in path.parts):
        return True
    return any(part.startswith("_") for part in path.parts)


def is_impl_log(path):
    return any(IMPL_LOG_MARKER in part for part in path.parts)


def find_vault_root(start):
    """start から親方向に辿り、.git を含むフォルダを Vault ルートとする"""
    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return candidate
    return current


def build_basename_index(vault_root):
    """Vault全体の .md を basename(拡張子なし) -> [Path,...] で索引化する。

    archive/やテンプレートも「リンク先」としては正当なため索引から除外しない
    （除外するのは後述の「スキャン対象(参照元)」のみ）。
    """
    index = {}
    for md_path in vault_root.rglob("*.md"):
        index.setdefault(md_path.stem, []).append(md_path)
    return index


def wikilink_basename(target):
    """wikilinkのtarget文字列からbasenameを取り出す。

    採番ファイル名(例: 001.001.仕様規約)はドットを複数含み拡張子を持たないため、
    Path.stem を使うと最後のドット以降を誤って拡張子とみなし切り捨ててしまう。
    wikilinkは元々拡張子なし表記が基本のため、末尾が明示的に .md の場合のみそれを除去する。
    """
    name = Path(target).name
    if name.lower().endswith(".md"):
        name = name[:-3]
    return name


def resolve_path_ref(ref_text, source_file, cwd, vault_root):
    """カレントディレクトリ相対 → 参照元ファイルのディレクトリ相対 → Vaultルート相対、の順で確認する"""
    candidates = [cwd / ref_text, source_file.parent / ref_text, vault_root / ref_text]
    return any(c.exists() for c in candidates)


def check_file(md_path, basename_index, cwd, vault_root):
    findings = []
    try:
        lines = md_path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        return findings

    skip_path_ref = is_impl_log(md_path)

    for lineno, line in enumerate(lines, start=1):
        if has_placeholder(line) or IGNORE_LINE_MARKER in line:
            continue

        for m in WIKILINK_RE.finditer(line):
            target = m.group(1).strip()
            basename = wikilink_basename(target)
            if basename not in basename_index:
                findings.append((lineno, f'壊れたwikilink: [[{target}]]'))

        if skip_path_ref:
            continue

        for m in PATH_REF_RE.finditer(line):
            ref_text = m.group(1)
            if not resolve_path_ref(ref_text, md_path, cwd, vault_root):
                findings.append((lineno, f'壊れたパス参照: `{ref_text}`'))

    return findings


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

    if len(sys.argv) < 2:
        print("使い方: python check_links.py <フォルダ1> [フォルダ2 ...]")
        return 1

    cwd = Path.cwd()
    vault_root = find_vault_root(cwd)
    roots = [Path(arg) for arg in sys.argv[1:]]
    for root in roots:
        if not root.exists():
            print(f"警告: 指定フォルダが見つかりません: {root}")

    roots = [r for r in roots if r.exists()]
    if not roots:
        print("チェック対象フォルダが1つも見つかりませんでした。")
        return 1

    basename_index = build_basename_index(vault_root)

    total_findings = 0
    for root in roots:
        for md_path in sorted(root.rglob("*.md")):
            if is_excluded_from_scan(md_path):
                continue
            findings = check_file(md_path, basename_index, cwd, vault_root)
            for lineno, message in findings:
                rel = md_path.relative_to(cwd) if md_path.is_relative_to(cwd) else md_path
                print(f"{rel}:{lineno}: {message}")
                total_findings += 1

    print(f"---\n合計 {total_findings} 件の参照切れ候補を検出しました。" if total_findings
          else "---\n参照切れは検出されませんでした。")
    return 1 if total_findings else 0


if __name__ == "__main__":
    sys.exit(main())
