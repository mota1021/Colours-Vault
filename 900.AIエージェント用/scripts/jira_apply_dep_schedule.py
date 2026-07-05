"""
Jira 依存関係・作業日程 整備差分 適用スクリプト（書込あり）

`Jira依存日程整備_差分.md`（2026-07-05 11:37 再生成版。PL-1→Mori・PL-3b(SCRUM-68)追加を反映済み）
の内容を Jira (SCRUM) へ REST API v3 で適用する。各操作の成功/失敗を記録し、最後に一覧出力する。

正本: ../Jira依存日程整備_差分.md
認証: D:\\document\\ObsidianVault\\.env
"""

import json
import sys
from pathlib import Path

import requests

ENV_PATH = Path(r"D:\document\ObsidianVault\.env")
START_FIELD = "customfield_10015"

MORI_ID = "5ebf9b4b9ce9ee0b89d04c15"
HIRUTA_ID = "712020:d8971bf4-5608-46c4-b657-c69f8f6e8f11"

# ── 3a. リンク追加（39件・先行→被依存） ──
LINK_ADDS = [
    ("SCRUM-10", "SCRUM-11"), ("SCRUM-15", "SCRUM-16"), ("SCRUM-15", "SCRUM-17"),
    ("SCRUM-14", "SCRUM-18"), ("SCRUM-10", "SCRUM-24"), ("SCRUM-14", "SCRUM-24"),
    ("SCRUM-24", "SCRUM-25"), ("SCRUM-26", "SCRUM-27"), ("SCRUM-26", "SCRUM-28"),
    ("SCRUM-26", "SCRUM-29"), ("SCRUM-28", "SCRUM-29"), ("SCRUM-30", "SCRUM-31"),
    ("SCRUM-30", "SCRUM-32"), ("SCRUM-31", "SCRUM-32"), ("SCRUM-19", "SCRUM-34"),
    ("SCRUM-33", "SCRUM-34"), ("SCRUM-33", "SCRUM-38"), ("SCRUM-34", "SCRUM-38"),
    ("SCRUM-35", "SCRUM-38"), ("SCRUM-36", "SCRUM-38"), ("SCRUM-37", "SCRUM-38"),
    ("SCRUM-13", "SCRUM-39"), ("SCRUM-15", "SCRUM-40"), ("SCRUM-20", "SCRUM-41"),
    ("SCRUM-12", "SCRUM-42"), ("SCRUM-20", "SCRUM-42"), ("SCRUM-23", "SCRUM-42"),
    ("SCRUM-29", "SCRUM-43"), ("SCRUM-25", "SCRUM-44"), ("SCRUM-32", "SCRUM-45"),
    ("SCRUM-38", "SCRUM-46"), ("SCRUM-21", "SCRUM-47"), ("SCRUM-34", "SCRUM-47"),
    ("SCRUM-21", "SCRUM-48"), ("SCRUM-26", "SCRUM-48"), ("SCRUM-23", "SCRUM-50"),
    ("SCRUM-68", "SCRUM-50"), ("SCRUM-50", "SCRUM-51"), ("SCRUM-15", "SCRUM-68"),
]

# ── 3b. リンク削除（4件・linkId） ──
LINK_DELETES = [10007, 10008, 10010, 10006]

# ── 3d. 担当者 ──
ASSIGN_MORI = ["SCRUM-11", "SCRUM-60", "SCRUM-64", "SCRUM-13", "SCRUM-61", "SCRUM-62", "SCRUM-63", "SCRUM-68"]
ASSIGN_HIRUTA = ["SCRUM-16", "SCRUM-17", "SCRUM-18"]

# ── 3e. 親エピック解除（M2→Phase2扱い） ──
DETACH_PARENT = ["SCRUM-61", "SCRUM-62", "SCRUM-63"]

# ── 3f. 開始日/期限（40件） ──
DATES = {
    "SCRUM-12": ("2026-07-06", "2026-07-09"), "SCRUM-15": ("2026-07-06", "2026-07-15"),
    "SCRUM-20": ("2026-07-10", "2026-07-13"), "SCRUM-23": ("2026-07-16", "2026-07-20"),
    "SCRUM-68": ("2026-07-21", "2026-07-30"), "SCRUM-16": ("2026-07-31", "2026-08-04"),
    "SCRUM-50": ("2026-07-31", "2026-08-01"), "SCRUM-51": ("2026-08-02", "2026-08-05"),
    "SCRUM-17": ("2026-08-05", "2026-08-14"), "SCRUM-11": ("2026-08-06", "2026-08-09"),
    "SCRUM-13": ("2026-08-10", "2026-08-13"), "SCRUM-21": ("2026-08-14", "2026-08-17"),
    "SCRUM-18": ("2026-08-15", "2026-08-24"), "SCRUM-22": ("2026-08-18", "2026-08-21"),
    "SCRUM-30": ("2026-08-22", "2026-08-25"), "SCRUM-24": ("2026-08-25", "2026-09-03"),
    "SCRUM-31": ("2026-08-26", "2026-08-29"), "SCRUM-35": ("2026-08-30", "2026-09-02"),
    "SCRUM-36": ("2026-09-03", "2026-09-06"), "SCRUM-26": ("2026-09-04", "2026-09-13"),
    "SCRUM-37": ("2026-09-07", "2026-09-10"), "SCRUM-27": ("2026-09-14", "2026-09-23"),
    "SCRUM-28": ("2026-09-24", "2026-10-03"), "SCRUM-33": ("2026-10-04", "2026-10-13"),
    "SCRUM-34": ("2026-10-14", "2026-10-23"), "SCRUM-25": ("2026-10-24", "2026-10-28"),
    "SCRUM-29": ("2026-10-29", "2026-11-02"), "SCRUM-44": ("2026-10-29", "2026-10-30"),
    "SCRUM-32": ("2026-11-03", "2026-11-07"), "SCRUM-38": ("2026-11-08", "2026-11-12"),
    "SCRUM-45": ("2026-11-08", "2026-11-09"), "SCRUM-39": ("2026-11-13", "2026-11-17"),
    "SCRUM-46": ("2026-11-13", "2026-11-14"), "SCRUM-47": ("2026-11-15", "2026-11-16"),
    "SCRUM-48": ("2026-11-17", "2026-11-18"), "SCRUM-40": ("2026-11-18", "2026-11-22"),
    "SCRUM-49": ("2026-11-19", "2026-11-22"), "SCRUM-41": ("2026-11-23", "2026-11-27"),
    "SCRUM-42": ("2026-11-28", "2026-12-02"), "SCRUM-43": ("2026-12-03", "2026-12-07"),
}

# ── 3g. エピック期限 ──
EPIC_DATES = {
    "SCRUM-5": ("2026-07-06", "2026-08-05"), "SCRUM-6": ("2026-07-31", "2026-08-24"),
    "SCRUM-7": ("2026-08-14", "2026-10-23"), "SCRUM-8": ("2026-10-24", "2026-12-07"),
    "SCRUM-9": ("2026-11-19", "2026-11-22"),
}


def load_env(path):
    env = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k = k.strip(); v = v.strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "'\"":
            v = v[1:-1]
        env[k] = v
    return env


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

    env = load_env(ENV_PATH)
    base = env["JIRA_BASE_URL"].rstrip("/")
    auth = (env["JIRA_EMAIL"], env["JIRA_API_TOKEN"])
    H = {"Accept": "application/json", "Content-Type": "application/json"}

    results = []  # (section, item, ok, detail)

    def record(section, item, r, ok_codes=(200, 201, 204)):
        ok = r.status_code in ok_codes
        detail = "" if ok else f"HTTP {r.status_code}: {r.text[:200]}"
        results.append((section, item, ok, detail))
        return ok

    # 3a. リンク追加
    for blocker, blocked in LINK_ADDS:
        body = {"type": {"name": "Blocks"},
                "outwardIssue": {"key": blocker}, "inwardIssue": {"key": blocked}}
        r = requests.post(f"{base}/rest/api/3/issueLink", auth=auth, headers=H, json=body, timeout=30)
        record("3a-リンク追加", f"{blocker}->{blocked}", r)

    # 3b. リンク削除
    for lid in LINK_DELETES:
        r = requests.delete(f"{base}/rest/api/3/issueLink/{lid}", auth=auth, headers=H, timeout=30)
        record("3b-リンク削除", f"linkId {lid}", r)

    # 3c. SCRUM-53: 親→M1 / 担当→Mori / ステータス→Done
    r = requests.put(f"{base}/rest/api/3/issue/SCRUM-53", auth=auth, headers=H,
                      json={"fields": {"parent": {"key": "SCRUM-5"}}}, timeout=30)
    record("3c-SCRUM53親変更", "parent->SCRUM-5", r)

    r = requests.put(f"{base}/rest/api/3/issue/SCRUM-53/assignee", auth=auth, headers=H,
                      json={"accountId": MORI_ID}, timeout=30)
    record("3c-SCRUM53担当", "assignee->Mori", r)

    r = requests.get(f"{base}/rest/api/3/issue/SCRUM-53/transitions", auth=auth, headers=H, timeout=30)
    done_tid = None
    if r.ok:
        for t in r.json().get("transitions", []):
            name = t.get("name", "")
            if name in ("Done", "完了") or (t.get("to") or {}).get("name") in ("Done", "完了"):
                done_tid = t["id"]
                break
    if done_tid:
        r2 = requests.post(f"{base}/rest/api/3/issue/SCRUM-53/transitions", auth=auth, headers=H,
                            json={"transition": {"id": done_tid}}, timeout=30)
        record("3c-SCRUM53ステータス", "status->Done", r2)
    else:
        results.append(("3c-SCRUM53ステータス", "status->Done", False,
                         f"Done/完了 遷移が見つからない (transitions={r.text[:200] if not r.ok else [t.get('name') for t in r.json().get('transitions', [])]})"))

    # 3d. 担当者
    for key in ASSIGN_MORI:
        r = requests.put(f"{base}/rest/api/3/issue/{key}/assignee", auth=auth, headers=H,
                          json={"accountId": MORI_ID}, timeout=30)
        record("3d-担当者(Mori)", key, r)
    for key in ASSIGN_HIRUTA:
        r = requests.put(f"{base}/rest/api/3/issue/{key}/assignee", auth=auth, headers=H,
                          json={"accountId": HIRUTA_ID}, timeout=30)
        record("3d-担当者(Hiruta)", key, r)

    # SCRUM-68: 元IDラベル付与（分類は保持しつつ元ID:PL-3b・ブロック中:PL-3・mvpを追加）
    r = requests.get(f"{base}/rest/api/3/issue/SCRUM-68", auth=auth, headers=H,
                      params={"fields": "labels"}, timeout=30)
    cur_labels = r.json().get("fields", {}).get("labels", []) if r.ok else []
    new_labels = sorted(set(cur_labels) | {"元ID:PL-3b", "ブロック中:PL-3", "mvp"})
    r = requests.put(f"{base}/rest/api/3/issue/SCRUM-68", auth=auth, headers=H,
                      json={"fields": {"labels": new_labels}}, timeout=30)
    record("3d-SCRUM68ラベル", "元ID:PL-3b付与", r)

    # 3e. 親エピック解除（M2→Phase2扱い）
    for key in DETACH_PARENT:
        r = requests.put(f"{base}/rest/api/3/issue/{key}", auth=auth, headers=H,
                          json={"fields": {"parent": None}}, timeout=30)
        record("3e-親解除", key, r)

    # 3f. 開始日/期限
    for key, (start, due) in DATES.items():
        r = requests.put(f"{base}/rest/api/3/issue/{key}", auth=auth, headers=H,
                          json={"fields": {START_FIELD: start, "duedate": due}}, timeout=30)
        record("3f-日付", key, r)

    # 3g. エピック期限
    for key, (start, due) in EPIC_DATES.items():
        r = requests.put(f"{base}/rest/api/3/issue/{key}", auth=auth, headers=H,
                          json={"fields": {START_FIELD: start, "duedate": due}}, timeout=30)
        record("3g-エピック期限", key, r)

    # ── 集計・出力 ──
    by_section = {}
    for section, item, ok, detail in results:
        by_section.setdefault(section, []).append((item, ok, detail))

    lines = []
    total_ok = total_fail = 0
    for section, items in by_section.items():
        ok_n = sum(1 for _, ok, _ in items if ok)
        fail_n = len(items) - ok_n
        total_ok += ok_n
        total_fail += fail_n
        lines.append(f"\n## {section} ({ok_n}/{len(items)} 成功)")
        for item, ok, detail in items:
            mark = "OK" if ok else "NG"
            lines.append(f"- [{mark}] {item}" + (f" — {detail}" if detail else ""))

    lines.insert(0, f"# Jira適用結果  総計 {total_ok}成功 / {total_fail}失敗")
    out_path = Path(__file__).resolve().parent.parent / "Jira依存日程整備_適用結果.md"
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[INFO] 総計 {total_ok}成功 / {total_fail}失敗")
    print(f"[INFO] 詳細: {out_path}")


if __name__ == "__main__":
    main()
