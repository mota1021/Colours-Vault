"""
Jira 依存関係・作業日程 整備差分 生成スクリプト（read-only）

Colours プロジェクト（Jira: SCRUM）の現行チケットを REST API v3 から読み取り、
- 依存リンク（Blocks）を設計DAG（010_チケット原案.md）に揃える追加/削除リスト
- レーン稼働＋工数からの開始日/期限の本格再計算
- エピック期限の再設定
を計算し、`../Jira依存日程整備_差分.md` を生成する。

**このスクリプトは Jira へ一切書き込まない。** 出力した差分は Vault 側セッションの
Atlassian MCP で適用する（正本の適用手順は差分md末尾に記載）。

正本: 創作/ゲーム/Colours/個人計画/archive/Jira移行/010_チケット原案.md（依存DAG）
      創作/ゲーム/Colours/shared/070.開発/070.010.ロードマップ.md（稼働・工数・締切）

実行: python jira_dep_schedule_plan.py
依存: requests のみ（.env は手動パース）
"""

import math
import re
import sys
from datetime import date, timedelta
from pathlib import Path

import requests

# ──────────────────────────────────────────────
# 定数・パラメータ（差分レビューで調整可）
# ──────────────────────────────────────────────
ENV_PATH = Path(r"D:\document\ObsidianVault\.env")
OUTPUT_PATH = Path(__file__).resolve().parents[3] / "900.AIエージェント用" / "Jira依存日程整備_差分.md"
START_FIELD = "customfield_10015"  # 「開始日」

SCHED_START = date(2026, 7, 6)     # 再計算の起点
DEADLINE = date(2026, 12, 20)      # ステージ1締切（M6）
MVP_TARGET = date(2026, 8, 2)      # MVP完了目安
WEEKLY_HOURS = {"Mori": 7.0, "Hiruta": 3.0}   # レーン週次稼働
DAILY_HOURS = {k: v / 7.0 for k, v in WEEKLY_HOURS.items()}  # 暦日ベース

# 完了/レビュー中で再計算対象外（凍結）。後続の先行期限に使う。
FROZEN_DUE = {
    "CS-1": date(2026, 7, 1),
    "PL-2": date(2026, 7, 3),
    "EW-1": SCHED_START - timedelta(days=1),  # 期限なし→即利用可
}

# MVP クリティカルパス（レーン先頭に来るよう最優先）
# 2026-07-05 確定: PL-3b（SCRUM-68・モノを固定設置）を MVP必須として追加
MVP_PRIORITY = {"CS-3", "EW-5", "EW-4", "PL-2", "PL-3", "PL-3b", "MVP-LV", "MVP-GE"}

# ── 設計DAG（元ID: [先行元ID]）: 010_チケット原案.md の依存表 ──
# 2026-07-05 確定: PL-3b（SCRUM-68・モノを固定設置。SP-11仕様策定が別途block）を追加。
#   先行=PL-3（拾う/仮設置の基本実装）のみ。MVP-LVをblockするMVP必須スコープ。
DESIGN = {
    "CS-1": [], "CS-2": ["CS-1"], "CS-3": ["CS-1"],
    "PL-1": [], "PL-2": [], "PL-3": ["PL-2", "CS-1"], "PL-3b": ["PL-3"], "PL-4": ["PL-3"], "PL-5": ["PL-3"], "PL-6": ["PL-2"],
    "EW-1": [], "EW-5": ["CS-3", "EW-1"], "EW-2": ["CS-3"], "EW-3": ["EW-1", "EW-2"], "EW-4": ["CS-1"],
    "FL-1": ["PL-2", "CS-1"], "FL-2": ["FL-1"],
    "SD-1": ["CS-3"], "SD-2": ["SD-1"], "SD-3": ["SD-1"], "SD-4": ["SD-1", "SD-3"],
    "GL-1": ["CS-2"], "GL-2": ["GL-1"], "GL-3": ["GL-1", "GL-2"],
    "MB-1": ["CS-1"], "MB-2": ["EW-1", "MB-1"], "MB-3a": [], "MB-3b": [], "MB-3c": ["MB-3a", "MB-3b"],
    "MB-4": ["MB-1", "MB-2", "MB-3a", "MB-3b", "MB-3c"],
    "LV-1": ["PL-1"], "LV-2": ["PL-3"], "LV-3": ["EW-5"], "LV-4": ["EW-5", "EW-4", "CS-3"],
    "LV-5": ["SD-4"], "LV-6": ["FL-2"], "LV-7": ["GL-3"], "LV-8": ["MB-4"],
    "LV-9": ["MB-2", "EW-2"], "LV-10": ["SD-1", "EW-2"],
    "GE-1": ["LV-10"], "MVP-LV": ["PL-3", "EW-5", "EW-4", "PL-3b"], "MVP-GE": ["MVP-LV"],
}

# ── レーン割り（070.010.ロードマップ 2026-07-03。ヒルタ=Hiruta）──
# 2026-07-05 確定: PL-1（SCRUM-13・走り速度調整）は Mori に確定（従来の LANE_CONFLICTS 解消）。
#   PL-3b はPL系列既定どおり Hiruta。
LANE = {}
for mid in DESIGN:
    cat = re.match(r"([A-Z]+)", mid).group(1)
    LANE[mid] = {"CS": "Mori", "EW": "Mori", "GL": "Mori", "GE": "Mori",
                 "PL": "Hiruta", "FL": "Hiruta", "SD": "Hiruta", "MB": "Hiruta"}.get(cat, "Mori")
LANE.update({"EW-4": "Hiruta", "GL-3": "Hiruta",
             "MB-3a": "Mori", "MB-3b": "Mori", "MB-3c": "Mori",
             "LV-1": "Hiruta", "LV-2": "Hiruta", "LV-3": "Hiruta", "LV-4": "Hiruta", "LV-5": "Hiruta",
             "LV-6": "Mori", "LV-7": "Mori", "LV-8": "Mori", "LV-9": "Mori", "LV-10": "Mori",
             "MVP-LV": "Mori", "MVP-GE": "Mori",
             "PL-1": "Mori"})

# ── 工数（h）: 実装4h / 配置・アセット2h ──
PLACEMENT = {"PL-4", "EW-4", "FL-2", "SD-4", "GL-3", "MB-4",
             "LV-1", "LV-2", "LV-3", "LV-4", "LV-5", "LV-6", "LV-7", "LV-8", "LV-9", "LV-10", "MVP-LV"}
EFFORT_H = {mid: (2.0 if mid in PLACEMENT else 4.0) for mid in DESIGN}

# 010原案の per-ticket担当 と ロードマップ(新)レーン割りが食い違うもの（要確認）
# 2026-07-05: PL-1 は Mori に確定したため一覧から除外。
LANE_CONFLICTS = ["PL-6", "SD-2", "EW-3", "GE-1"]


def fail(msg):
    print(f"[ERROR] {msg}", file=sys.stderr)
    sys.exit(1)


def load_env(path):
    if not path.exists():
        fail(f".env が見つかりません: {path}")
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
    for k in ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN"):
        if not env.get(k):
            fail(f".env に {k} がありません")
    return env


def fetch_issues(base, auth):
    url = f"{base.rstrip('/')}/rest/api/3/search/jql"
    flds = f"summary,issuetype,labels,status,parent,issuelinks,duedate,{START_FIELD}"
    issues, token = [], None
    while True:
        params = {"jql": "project = SCRUM ORDER BY key ASC", "fields": flds, "maxResults": 100}
        if token:
            params["nextPageToken"] = token
        r = requests.get(url, params=params, auth=auth, headers={"Accept": "application/json"}, timeout=30)
        if not r.ok:
            fail(f"Jira API エラー HTTP {r.status_code}: {r.text[:300]}")
        d = r.json()
        issues += d.get("issues", [])
        if d.get("isLast", True):
            break
        token = d.get("nextPageToken")
        if not token:
            break
    return issues


def lbl(labels, pre):
    for l in labels or []:
        m = re.match(r"^" + pre + r":(.+)$", l)
        if m:
            return m.group(1)
    return ""


def d(x):
    return date.fromisoformat(x) if x else None


def add_days(dt, n):
    return dt + timedelta(days=n)


def duration_days(mid):
    return max(1, math.ceil(EFFORT_H[mid] / DAILY_HOURS[LANE[mid]]))


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

    env = load_env(ENV_PATH)
    base = env["JIRA_BASE_URL"]
    auth = (env["JIRA_EMAIL"], env["JIRA_API_TOKEN"])
    issues = fetch_issues(base, auth)

    # ── インデックス構築 ──
    info = {}   # key -> dict
    byid = {}   # 元ID -> key
    for it in issues:
        f = it.get("fields") or {}
        key = it["key"]
        mid = lbl(f.get("labels"), "元ID")
        blockers = []  # (key, linkId) このチケットを塞ぐ先行
        for lk in f.get("issuelinks") or []:
            if (lk.get("type") or {}).get("name") != "Blocks":
                continue
            if "inwardIssue" in lk:
                blockers.append((lk["inwardIssue"]["key"], lk["id"]))
        info[key] = dict(mid=mid, typ=(f.get("issuetype") or {}).get("name", ""),
                         st=(f.get("status") or {}).get("name", ""),
                         parent=(f.get("parent") or {}).get("key", ""),
                         start=f.get(START_FIELD), due=f.get("duedate"),
                         blockers=blockers)
        if mid:
            byid[mid] = key

    # 2026-07-05 確定: SCRUM-68 に元IDラベル未付与のため一時オーバーライド
    # （実ラベル付与はStep3の適用時にJiraへ書込む。読取専用の本再生成では書込まない）
    if "SCRUM-68" in info and not info["SCRUM-68"]["mid"]:
        info["SCRUM-68"]["mid"] = "PL-3b"
        byid["PL-3b"] = "SCRUM-68"

    def k(mid):
        return byid.get(mid, "?")

    # ══════════════════════════════════════════
    # 1) 依存リンク差分
    # ══════════════════════════════════════════
    additions = []   # (blocker_mid, child_mid)
    removals = []    # (blocker_key, child_mid, linkId)
    conflicts_53 = []  # 非元ID(SCRUM-53等)によるブロック → 要確認
    for child_mid, deps in DESIGN.items():
        ckey = byid.get(child_mid)
        if not ckey:
            continue
        cur = info[ckey]["blockers"]
        cur_ids = {}
        for bkey, lid in cur:
            bmid = info.get(bkey, {}).get("mid", "")
            cur_ids[bmid or bkey] = (bkey, lid)
        # 追加: 設計にありJira未設定
        for dep in deps:
            if dep not in cur_ids:
                additions.append((dep, child_mid))
        # 削除: impl→impl で設計外
        for token_id, (bkey, lid) in cur_ids.items():
            if token_id in DESIGN:  # impl 元ID
                if token_id not in deps:
                    removals.append((bkey, child_mid, lid))
            elif not str(token_id).startswith("SP-"):
                # 非元ID(SCRUM-53/68等・SP以外) → 自動削除せず要確認
                conflicts_53.append((bkey, child_mid, lid))

    # ── 再構成後DAGの循環検証 ──
    graph = {mid: set(DESIGN[mid]) for mid in DESIGN}
    # additions/removals は設計に一致させるので graph=DESIGN と等価。トポロジカル可能性を確認。
    indeg = {m: 0 for m in graph}
    for m, ds in graph.items():
        for dep in ds:
            indeg[m] += 1
    q = [m for m in graph if indeg[m] == 0]
    seen = 0
    while q:
        n = q.pop()
        seen += 1
        for m, ds in graph.items():
            if n in ds:
                indeg[m] -= 1
                if indeg[m] == 0:
                    q.append(m)
    dag_ok = (seen == len(graph))

    # ══════════════════════════════════════════
    # 2) スケジュール本格再計算（list scheduling・2レーン）
    # ══════════════════════════════════════════
    def mrank(mid):
        return {"SCRUM-5": 1, "SCRUM-6": 2, "SCRUM-7": 3, "SCRUM-8": 4, "SCRUM-9": 5}.get(info[k(mid)]["parent"], 9)

    def keynum(mid):
        kk = byid.get(mid, "SCRUM-999")
        return int(kk.split("-")[1])

    def prio(mid):
        return (0 if mid in MVP_PRIORITY else 1, mrank(mid), keynum(mid))

    done = set(FROZEN_DUE)  # 凍結=完了扱い
    sched = {}              # 元ID -> dict(start,due,lane,dur)
    avail = {"Mori": SCHED_START, "Hiruta": SCHED_START}
    remaining = [m for m in DESIGN if m not in FROZEN_DUE]

    def due_of(mid):
        if mid in FROZEN_DUE:
            return FROZEN_DUE[mid]
        return sched[mid]["due"]

    guard = 0
    while remaining:
        guard += 1
        if guard > 10000:
            fail("スケジューリングが収束しません（循環の疑い）")
        ready = [m for m in remaining if all(dep in done for dep in DESIGN[m])]
        if not ready:
            fail(f"依存を満たせない残チケット: {remaining}")
        mid = min(ready, key=prio)
        lane = LANE[mid]
        dur = duration_days(mid)
        earliest = avail[lane]
        for dep in DESIGN[mid]:
            earliest = max(earliest, add_days(due_of(dep), 1))
        start = earliest
        due = add_days(start, dur - 1)
        sched[mid] = dict(start=start, due=due, lane=lane, dur=dur)
        avail[lane] = add_days(due, 1)
        done.add(mid)
        remaining.remove(mid)

    # 依存整合の自動検証（先行期限 < 被依存開始）
    viol = []
    for mid, ds in DESIGN.items():
        if mid not in sched:
            continue
        for dep in ds:
            if due_of(dep) >= sched[mid]["start"]:
                viol.append((dep, mid))

    # 締切/ MVP 判定
    overflow = sorted([(mid, s["due"]) for mid, s in sched.items() if s["due"] > DEADLINE],
                      key=lambda x: x[1], reverse=True)
    mvp_due = max(due_of(m) for m in ["MVP-LV", "MVP-GE"])
    lane_last = {ln: max((s["due"] for s in sched.values() if s["lane"] == ln), default=None) for ln in ("Mori", "Hiruta")}

    # ══════════════════════════════════════════
    # 3) エピック期限（配下ストーリーの min開始 / max期限）
    # ══════════════════════════════════════════
    epic_children = {"SCRUM-5": [], "SCRUM-6": [], "SCRUM-7": [], "SCRUM-8": [], "SCRUM-9": []}
    for mid, s in sched.items():
        p = info[k(mid)]["parent"]
        if p in epic_children:
            epic_children[p].append(mid)
    # 凍結分も窓に含める
    for mid, du in FROZEN_DUE.items():
        p = info.get(k(mid), {}).get("parent", "")
        if p in epic_children:
            epic_children[p].append(mid)

    def epic_start(mid):
        return sched[mid]["start"] if mid in sched else (info[k(mid)]["start"] and d(info[k(mid)]["start"]))

    epic_new = {}
    for ep, kids in epic_children.items():
        starts = [sched[m]["start"] for m in kids if m in sched]
        dues = [due_of(m) for m in kids]
        if starts and dues:
            epic_new[ep] = (min(starts), max(dues))

    # ══════════════════════════════════════════
    # 出力
    # ══════════════════════════════════════════
    from datetime import datetime
    L = []
    L.append(f"最終生成: {datetime.now():%Y-%m-%d %H:%M}（read-only計算・Jira未適用）")
    L.append("")
    L.append("# Jira 依存関係・作業日程 整備差分")
    L.append("")
    L.append("> 生成: `創作/ゲーム/Colours/shared/.vault-data/900.AIエージェント用/scripts/jira_dep_schedule_plan.py`（Jira書込なし）。適用は Vault セッションの Atlassian MCP で行う（末尾の手順参照）。")
    L.append(f"> パラメータ: 起点={SCHED_START} / 締切={DEADLINE} / 稼働 Mori {WEEKLY_HOURS['Mori']}h·Hiruta {WEEKLY_HOURS['Hiruta']}h/週 / 実装4h·配置2h")
    L.append("")

    L.append("## 1. 依存リンク差分")
    L.append("")
    L.append(f"### 追加（{len(additions)}件） — 先行 → 被依存（先行が blocks / 被依存が is blocked by）")
    L.append("")
    L.append("| # | 先行(blocker) | 被依存(blocked) |")
    L.append("|---|---|---|")
    for i, (b, c) in enumerate(sorted(additions, key=lambda x: (keynum(x[1]), keynum(x[0]))), 1):
        L.append(f"| {i} | {b} ({k(b)}) | {c} ({k(c)}) |")
    L.append("")
    L.append(f"### 削除（{len(removals)}件） — 設計外の誤リンク")
    L.append("")
    L.append("| # | 先行 | 被依存 | linkId(REST削除用) |")
    L.append("|---|---|---|---|")
    for i, (bk, c, lid) in enumerate(removals, 1):
        bmid = info.get(bk, {}).get("mid", bk)
        L.append(f"| {i} | {bmid} ({bk}) | {c} ({k(c)}) | {lid} |")
    L.append("")
    if conflicts_53:
        L.append(f"### ⚠️ 要確認リンク（{len(conflicts_53)}件） — 非元ID(SCRUM-53等)による block。自動削除せず判断を仰ぐ")
        L.append("")
        L.append("| 先行(key) | 被依存 | linkId | 備考 |")
        L.append("|---|---|---|---|")
        for bk, c, lid in conflicts_53:
            note = "移行検証用テストチケットの疑い（Step6でSCRUM-53検証）" if bk == "SCRUM-53" else ""
            L.append(f"| {bk} | {c} ({k(c)}) | {lid} | {note} |")
        L.append("")
    L.append(f"- 再構成後DAG循環チェック: {'OK（循環なし）' if dag_ok else '❌ 循環あり'}")
    L.append("")

    L.append("## 2. 開始日/期限の差分（本格再計算・変更行のみ）")
    L.append("")
    L.append("| 元ID | key | レーン | 旧開始→新開始 | 旧期限→新期限 | 工数 |")
    L.append("|---|---|---|---|---|---|")
    for mid in sorted(sched, key=lambda m: (sched[m]["start"], keynum(m))):
        s = sched[mid]
        old_s = info[k(mid)]["start"] or "—"
        old_d = info[k(mid)]["due"] or "—"
        ns, nd = s["start"].isoformat(), s["due"].isoformat()
        if old_s == ns and old_d == nd:
            continue
        L.append(f"| {mid} | {k(mid)} | {s['lane']} | {old_s} → **{ns}** | {old_d} → **{nd}** | {EFFORT_H[mid]:.0f}h |")
    L.append("")
    L.append(f"- 依存整合（先行期限 < 被依存開始）違反: {len(viol)}件" + ("" if not viol else f" → {viol}"))
    L.append("")

    L.append("## 3. エピック期限の差分")
    L.append("")
    L.append("| エピック | M | 旧開始 | 旧期限 | 新開始 | 新期限 |")
    L.append("|---|---|---|---|---|---|")
    mlabel = {"SCRUM-5": "M1/MVP", "SCRUM-6": "M2", "SCRUM-7": "M3", "SCRUM-8": "M4", "SCRUM-9": "M5"}
    for ep in ["SCRUM-5", "SCRUM-6", "SCRUM-7", "SCRUM-8", "SCRUM-9"]:
        if ep in epic_new:
            ns, nd = epic_new[ep]
            L.append(f"| {ep} | {mlabel[ep]} | {info[ep]['start'] or '—'} | {info[ep]['due'] or '—'} | {ns} | {nd} |")
    L.append("")

    L.append("## 4. 容量レポート（重要）")
    L.append("")
    L.append(f"- MVP（MVP-LV/MVP-GE）完了: **{mvp_due}**（目安 {MVP_TARGET} → {'間に合う' if mvp_due <= MVP_TARGET else '⚠️超過'}）")
    L.append(f"- レーン最終完了: Mori **{lane_last['Mori']}** / Hiruta **{lane_last['Hiruta']}**")
    L.append(f"- ステージ1締切 {DEADLINE} 超過: **{len(overflow)}件**")
    if overflow:
        L.append("")
        L.append("| 元ID | key | レーン | 新期限 | 超過日数 |")
        L.append("|---|---|---|---|---|")
        for mid, du in overflow:
            L.append(f"| {mid} | {k(mid)} | {LANE[mid]} | {du} | +{(du - DEADLINE).days}日 |")
        L.append("")
        L.append("> 締切超過は圧縮せず提示。対応案は下記「要確認」を参照（稼働増 / Mori がHirutaキューのC++系を引取 / スコープ削減 / 締切延長）。")
    L.append("")

    L.append("## 5. 要確認（勝手に確定しない事項）")
    L.append("")
    L.append(f"- **レーン競合**: 010原案の担当と2026-07-03ロードマップのレーン割りが食い違う → ロードマップ(新)採用で計算: {', '.join(LANE_CONFLICTS)}。")
    L.append("- **稼働→暦日換算**: Mori 7h/週=1.0h/日・Hiruta 3h/週≈0.43h/日（暦日ベース・週末含む）。実働が平日集中なら要調整。")
    L.append("- **起点2026-07-06**・凍結(CS-1/EW-1/PL-2 完了扱い)前提。")
    L.append("- **SP(仕様策定)チケットは稼働非消費**で計算（多くは完了）。未完SPが先行にある実装は着手前にSP完了が必要。")
    if lane_last["Hiruta"] and lane_last["Hiruta"] > DEADLINE:
        L.append(f"- **Hiruta レーンが締切超過**（3h/週では負荷過多）。C++/システム系（FL-1/SD-1〜3/MB-1〜2 等）を Mori 引取に回す再計算を推奨（ロードマップ「Moriが空き次第Hirutaキューから引取可」）。")
    L.append("")

    L.append("## 適用手順（Vault セッション / Atlassian MCP）")
    L.append("")
    L.append("1. **リンク追加**: 各行、先行チケットに『blocks → 被依存』の Blocks リンクを作成。")
    L.append("2. **リンク削除**: linkId 指定で削除（MCPに削除がなければ REST `DELETE /rest/api/3/issueLink/{linkId}` か UI）。")
    L.append(f"3. **日付更新**: 各 key の `{START_FIELD}`(開始日) と `duedate`(期限) を新値に更新。")
    L.append("4. **エピック期限**: SCRUM-5〜9 の開始/期限を §3 の新値に更新。")
    L.append("5. 適用後、タイムラインで依存線・バー長・順序を目視確認。")

    OUTPUT_PATH.write_text("\n".join(L) + "\n", encoding="utf-8")

    # コンソール要約
    print(f"[INFO] 追加リンク {len(additions)} / 削除リンク {len(removals)} / 要確認リンク {len(conflicts_53)}")
    print(f"[INFO] 日付再計算 {len(sched)}件 / 依存違反 {len(viol)}件 / DAG={'OK' if dag_ok else 'NG'}")
    print(f"[INFO] MVP完了 {mvp_due} / Mori最終 {lane_last['Mori']} / Hiruta最終 {lane_last['Hiruta']} / 締切超過 {len(overflow)}件")
    print(f"[INFO] 出力: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
