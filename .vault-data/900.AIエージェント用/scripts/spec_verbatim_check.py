# -*- coding: utf-8 -*-
"""逐語照合チェック — ラフに無い記述が仕様書へ混入していないか検出する

Colours の仕様生成には「ラフに書かれた内容のみを使う」という逐語原則がある
（`/colours-spec-from-rough`）。現状この原則は AI の自制に依存しており、
守られたかどうかを機械的に確認する手段が無い。本スクリプトはその検証子。

**検出するのは「トークンの混入」だけ**:
  - 数値（単位つきを含む）  … ラフに無い数値＝AIが決めた値
  - 英数字の識別子          … 存在しないクラス名・関数名・パラメータ名の捏造
  - 鉤括弧「」の中の語      … 存在しない機構名・状態名の新設
  - カタカナ語（3文字以上） … 同上

**検出しないもの**: 文章表現・構造化・分割・具体例の言い換え。
「実体はラフのみ／表現の整形は可」が既定ルールのため、文単位の照合はしない。

テンプレート由来の定型語は自動で除外する（同じ役割のテンプレートを読んで差し引く）。

出力はあくまで**混入候補**であり、確定した違反ではない。
呼び出し側（スキル）は候補をユーザーに提示して判断を仰ぐこと。

使い方:
    python spec_verbatim_check.py <仕様フォルダ>
    例) python spec_verbatim_check.py shared/050.仕様/050.020.プレイヤー/020.020.モノを置く

終了コード: 常に 0（非ブロッキング。仕様作業を止めないため）
"""

import re
import sys
from pathlib import Path

# 役割番号 -> 対応するテンプレート名
ROLE_TEMPLATES = {
    "020": "テンプレート.020.仕様.md",
    "030": "テンプレート.030.演出・UI.md",
    "040": "テンプレート.040.実装.md",
}
TEMPLATE_DIR_NAME = "050.001.テンプレート"

PATTERNS = (
    # 単位つきの数値を優先して拾う（`0.5秒` を `0.5` と `秒` に割らない）
    ("数値", re.compile(r"\d+(?:\.\d+)?\s*(?:%|％|秒|ms|fps|回|個|人|色|段|枚|本|倍|px|m|cm|度)?")),
    ("識別子", re.compile(r"\b[A-Za-z][A-Za-z0-9_]{2,}\b")),
    ("鉤括弧語", re.compile(r"「([^」\n]{1,24})」")),
    ("カタカナ語", re.compile(r"[ァ-ヴ][ァ-ヴー]{2,}")),
)

# Markdown の装飾・記法そのものは対象外
FENCE_RE = re.compile(r"```.*?```", re.S)
DECORATION_RE = re.compile(r"[*_`~\s]+")

# 語句系は「ラフのどこかに書かれていれば可」とする。
# ラフが `クールタイム` と地の文で書き、仕様が「**手を離してからのクールタイム**」と
# 見出し化するのは “表現の整形” であって混入ではないため（逐語原則の範囲内）。
SUBSTRING_LABELS = {"鉤括弧語", "カタカナ語"}


def _normalize(token):
    return DECORATION_RE.sub("", token).strip().lower()


def _extract(text):
    """カテゴリ -> {正規化トークン: 原文} を返す"""
    text = FENCE_RE.sub("", text)
    out = {}
    for label, rx in PATTERNS:
        bucket = {}
        for m in rx.finditer(text):
            raw = (m.group(1) if rx.groups else m.group(0)).strip()
            key = _normalize(raw)
            if key:
                bucket.setdefault(key, raw)
        out[label] = bucket
    return out


def _extract_with_lines(path):
    """カテゴリ -> [(正規化トークン, 原文, 行番号)] を返す"""
    lines = FENCE_RE.sub("", path.read_text(encoding="utf-8")).splitlines()
    out = {label: [] for label, _ in PATTERNS}
    for lineno, line in enumerate(lines, start=1):
        for label, rx in PATTERNS:
            for m in rx.finditer(line):
                raw = (m.group(1) if rx.groups else m.group(0)).strip()
                key = _normalize(raw)
                if key:
                    out[label].append((key, raw, lineno))
    return out


def _find_template_dir(spec_dir):
    """上位方向に 050.001.テンプレート を探す"""
    for parent in spec_dir.resolve().parents:
        candidate = parent / TEMPLATE_DIR_NAME
        if candidate.is_dir():
            return candidate
    return None


def _role_of(path):
    parts = path.name.split(".")
    return parts[1] if len(parts) > 2 else None


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

    if len(sys.argv) != 2:
        print("使い方: python spec_verbatim_check.py <仕様フォルダ>")
        return 0

    spec_dir = Path(sys.argv[1])
    if not spec_dir.is_dir():
        print("フォルダが見つかりません: {}".format(spec_dir))
        return 0

    roughs = sorted(spec_dir.glob("*.010.ラフ.md"))
    if not roughs:
        print("ラフ（*.010.ラフ.md）が見つかりません: {}".format(spec_dir))
        return 0
    rough_text = "\n".join(p.read_text(encoding="utf-8") for p in roughs)
    rough_tokens = _extract(rough_text)
    rough_flat = _normalize(rough_text)

    template_dir = _find_template_dir(spec_dir)
    total = 0

    for role in sorted(ROLE_TEMPLATES):
        for spec in sorted(spec_dir.glob("*.{}.*.md".format(role))):
            if _role_of(spec) != role:
                continue

            allowed = {label: dict(bucket) for label, bucket in rough_tokens.items()}
            flat = rough_flat
            if template_dir:
                tpl = template_dir / ROLE_TEMPLATES[role]
                if tpl.exists():
                    tpl_text = tpl.read_text(encoding="utf-8")
                    for label, bucket in _extract(tpl_text).items():
                        allowed[label].update(bucket)
                    flat = flat + _normalize(tpl_text)

            reported = set()
            hits = []
            for label, entries in _extract_with_lines(spec).items():
                for key, raw, lineno in entries:
                    if key in allowed[label] or (label, key) in reported:
                        continue
                    if label in SUBSTRING_LABELS and key in flat:
                        continue
                    reported.add((label, key))
                    hits.append((lineno, label, raw))

            if hits:
                print("\n■ {}".format(spec.name))
                for lineno, label, raw in sorted(hits):
                    print("  {}行目 [{}] {}".format(lineno, label, raw))
                total += len(hits)

    print("\n---")
    if total:
        print("混入候補 {} 件。ラフに無いトークンが仕様側に現れています。".format(total))
        print("各件について「削除する / ラフに追記する / 誤検出として無視する」を確認してください。")
    else:
        print("混入候補は検出されませんでした。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
