"""mobility 처음 설정 — 조리법(모듈 setup.json)대로 재고, 답을 받아 개인 값 파일과 설정 노트를 채운다(LLM 0 · Claude 는 묻고 고르게만).

  py -3 .claude/skills/mobility/scripts/setup.py plan [--again] [--json]          # 물음 목록(지금 값 · ✦ 추천 · 물을지 · 까닭)
  py -3 .claude/skills/mobility/scripts/setup.py apply --answers <파일> [--json]  # 빈 칸만 쓴다 · 설정 노트가 어디에도 없으면 틀로 만든다
  py -3 .claude/skills/mobility/scripts/setup.py apply --answers <파일> --again --dry   # 다시(재보정): 바뀔 config 값 diff 만(안 씀)
  py -3 .claude/skills/mobility/scripts/setup.py apply --answers <파일> --again         # 확인 뒤 — 바뀐 config 값만 쓴다
  py -3 .claude/skills/mobility/scripts/setup.py status                           # 한 줄: 설정 됨 · 안 됨(빈 칸)

이 대본이 든 볼트를 다룬다(시험 볼트는 모듈을 복사해 그 안의 대본을 부른다).
답 파일 = {id: 값} JSON · 빠진 id 는 ✦ 추천(재기) → 없으면 기본값. 값은 조리법 «꼴»로 재고, 틀리면 아무것도 안 쓰고 종료 2.
쓰는 곳: config 키 = <볼트>/3_시스템/_index/server/config.json(git 밖 · 다른 키는 그대로) · 노트 칸 = 모듈 선언(contributes.notes) 자리의 노트 json.
이미 있는 config 값은 덮지 않는다(--again 뿐). 이미 있는 노트는 고치지 않는다 — 바꿀 값은 노트에서 고친다(사람 글이 든 노트라).
비밀(열쇠)은 다루지 않는다 — 서버가 처음 켤 때 만들고 짝짓기가 넘긴다.
"""
import argparse
import datetime
import json
import os
import re
import socket
import subprocess
import sys

MOD = os.path.dirname(os.path.abspath(__file__))
MODULE = os.path.dirname(MOD)
sys.path.insert(0, MOD)
import conf  # noqa: E402

VAULT = conf.vault_of()
sys.path.insert(0, os.path.join(VAULT, "3_시스템"))
import roles  # noqa: E402 — 일정 폴더·노트 이름 찾기는 코어 한 곳

NOWIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)
JSON_BLOCK = re.compile(r"^```json[ \t]*\r?\n(.*?)^```", re.M | re.S)
HHMM = re.compile(r"^([01]?\d|2[0-3]):([0-5]\d)$")
ALL = "*"


# ───────── 재기(조리법 «재기» 이름) ─────────
def port_free(p):
    s = socket.socket()
    try:
        s.bind(("127.0.0.1", p))
        return True
    except OSError:
        return False
    finally:
        s.close()


def free_port(item, cfg):
    """기본 문이 비었으면 그것 · 이 볼트 config 에 이미 있으면 그것 · 막혔으면 다음 빈 문(묻는다)."""
    d = int(item["기본값"])
    if type(cfg.get("port")) is int:
        return cfg["port"], True, "이 볼트 config 값"
    if port_free(d):
        return d, True, "비어 있음"
    for p in range(d + 1, d + 30):
        if port_free(p):
            return p, False, "%d 을 다른 프로그램(또는 다른 볼트 서버)이 씀 — %d 가 비었음" % (d, p)
    return d, False, "%d~%d 이 다 쓰이는 중" % (d, d + 29)


SSID = re.compile(r"^\s*SSID\s*:\s*(.+?)\s*$", re.M)


def wifi_now(item, cfg):
    """지금 붙은 Wi-Fi 이름(netsh 읽기) · 유선·없음이면 빈 목록."""
    try:
        r = subprocess.run(["netsh", "wlan", "show", "interfaces"], capture_output=True, timeout=10, creationflags=NOWIN)
        out = r.stdout.decode("mbcs" if os.name == "nt" else "utf-8", "replace")
    except (OSError, subprocess.TimeoutExpired, LookupError):
        return [], False, "Wi-Fi 를 못 읽음"
    names = sorted({m.group(1) for m in SSID.finditer(out)})
    return (names, True, "지금 붙은 Wi-Fi") if names else ([], True, "Wi-Fi 에 안 붙음(유선이면 빈 목록)")


def schedule_files():
    try:
        d = roles.abs("schedule")
    except (KeyError, OSError, ValueError):
        return []
    return sorted(f for f in os.listdir(d) if f.endswith(".md")) if os.path.isdir(d) else []


def schedule_pick(item, cfg):
    files = schedule_files()
    if item["id"] == "write_schedule":
        d = item["기본값"]
        rec = d if d in files or not files else files[0]
        return rec, len(files) <= 1, "일정 파일 %d개" % len(files)
    return (files or ALL), True, ("일정 폴더의 파일 %d개 — 다 울림(뺄 것만 고름)" % len(files)) if files else "일정 파일이 아직 없음 — 일정 폴더 전부(*)"


def declared_notes():
    with open(os.path.join(MODULE, "module.json"), encoding="utf-8") as f:
        notes = (json.load(f).get("contributes") or {}).get("notes") or []
    return [n for n in notes if isinstance(n, dict) and n.get("id")]


def note_where(n):
    """(볼트 상대 자리, 있음) — 선언 자리 → 이름으로 찾은 자리 → 선언 자리(만들 곳). alarms.note_path 와 같은 차례."""
    if os.path.isfile(os.path.join(VAULT, *n["path"].split("/"))):
        return n["path"], True
    found = roles.find_note(n["name"])
    return (found, True) if found else (n["path"], False)


def notes_where(item, cfg):
    got = {n["id"]: note_where(n) for n in declared_notes()}
    return {k: v[0] for k, v in got.items()}, True, " · ".join("%s %s" % (k, "있음" if v[1] else "만들 곳") for k, v in got.items())


MEASURE = {"free_port": free_port, "wifi_now": wifi_now, "schedule_files": schedule_pick, "notes_where": notes_where}


# ───────── 꼴 ─────────
def rule_ok(v, keys=("며칠_전", "시각")):
    if not isinstance(v, dict) or set(v) - set(keys):
        return False
    d, t = v.get("며칠_전", [1]), v.get("시각", ["20:00"])
    return (isinstance(d, list) and d and all(type(x) is int and 0 <= x <= 365 for x in d)
            and isinstance(t, list) and t and all(isinstance(x, str) and HHMM.match(x) for x in t))


def valid(item, v):
    i = item["id"]
    if i == "port":
        return type(v) is int and 1024 <= v <= 65535
    if i == "home_wifi":
        return isinstance(v, list) and all(isinstance(x, str) and x.strip() for x in v)
    if i in ("phone_sensitive", "rc_mode"):
        return v in item["꼴"]
    if i == "write_schedule":
        return isinstance(v, str) and v.endswith(".md") and "/" not in v and "\\" not in v
    if i == "alarm_files":
        return v == ALL or (isinstance(v, list) and v and all(isinstance(x, str) and (x == ALL or x.endswith(".md")) for x in v))
    if i == "alarm_default":
        return rule_ok(v)
    if i == "quiet":
        return (isinstance(v, dict) and {"부터", "까지"} <= set(v) <= {"켬", "부터", "까지"} and isinstance(v.get("켬", True), bool)
                and all(isinstance(v[x], str) and HHMM.match(v[x]) for x in ("부터", "까지")))     # 켬 = 방해 금지 켬·끔(없으면 켬 · 11-19)
    if i == "lock_ttl":
        return type(v) is int and 30 <= v <= 600
    return True


# ───────── plan ─────────
def recipe():
    with open(conf.RECIPE, encoding="utf-8") as f:
        return json.load(f)


def plan(again=False):
    cfg = conf.load()
    out = []
    for it in recipe()["항목"]:
        where = it["쓰는 곳"]
        now = cfg.get(where["config"]) if "config" in where else None
        rec, measured, why = it.get("기본값"), True, ""
        if it.get("재기") in MEASURE:
            rec, measured, why = MEASURE[it["재기"]](it, cfg)
        set_already = now is not None
        if it.get("꼴") == "글 목록" and isinstance(now, list) and isinstance(rec, list):
            # 여러 값 칸은 합친다(11-18) — 다시 재기가 지금 붙은 Wi-Fi 하나만 추천해 집 Wi-Fi 둘(2.4·5G) 중 하나를 버렸다
            more = [x for x in rec if x not in now]
            rec = now + more
            why = (why + " · " if why else "") + ("지금 값에 새로 잰 값 %d개를 더함" % len(more) if more else "지금 값 그대로(새로 잰 값이 이미 들어 있음)")
        ask = {"늘": True, "못 잴 때만": not measured, "여럿일 때": not measured, "안 물음": False}[it["묻기"]]
        if set_already:
            ask = bool(again and it.get("다시"))
        if "note" in where:
            n = next((x for x in declared_notes() if x["id"] == where["note"]), None)
            if n and note_where(n)[1]:
                ask, why = False, "노트가 이미 있음(%s) — 바꿀 값은 노트에서 고친다" % note_where(n)[0]
        out.append({"id": it["id"], "물음": it["물음"], "지금": now, "추천": rec, "기본값": it.get("기본값"),
                    "묻기": ask, "까닭": why, "꼴": it.get("꼴"), "쓰는 곳": where})
    return out


def plan_text(rows):
    L = ["mobility 처음 설정 — 물을 것 %d · 재서 정한 것 %d" % (sum(r["묻기"] for r in rows), sum(not r["묻기"] for r in rows))]
    for r in rows:
        mark = "?" if r["묻기"] else "·"
        now = "" if r["지금"] is None else " · 지금 %s" % json.dumps(r["지금"], ensure_ascii=False)
        L.append("%s %s — %s · ✦ %s%s%s" % (mark, r["id"], r["물음"], json.dumps(r["추천"], ensure_ascii=False), now, (" · " + r["까닭"]) if r["까닭"] else ""))
    return "\n".join(L)


# ───────── apply ─────────
def dump_block(d):
    """노트 json 블록 — 맨 위 칸 한 줄씩 · «파일»만 파일마다 한 줄(사람이 고치기 쉽게)."""
    rows = []
    for k, v in d.items():
        if k == "파일" and isinstance(v, dict) and v:
            inner = ",\n".join("  %s: %s" % (json.dumps(n, ensure_ascii=False), json.dumps(r, ensure_ascii=False)) for n, r in v.items())
            rows.append(" %s: {\n%s\n }" % (json.dumps(k, ensure_ascii=False), inner))
        else:
            rows.append(" %s: %s" % (json.dumps(k, ensure_ascii=False), json.dumps(v, ensure_ascii=False, separators=(", ", ": "))))
    return "{\n" + ",\n".join(rows) + "\n}\n"


def make_note(n, fields):
    """틀 → 선언 자리 노트(날짜 · json 칸 채움). 이미 어디에 있으면 안 만든다."""
    rel, there = note_where(n)
    if there:
        return rel, False
    with open(os.path.join(VAULT, *n["template"].split("/")), encoding="utf-8") as f:
        text = f.read().replace("{{날짜}}", datetime.date.today().isoformat())
    if fields:
        m = JSON_BLOCK.search(text)
        block = json.loads(m.group(1))
        block.update(fields)
        text = text[:m.start(1)] + dump_block(block) + text[m.end(1):]
    p = os.path.join(VAULT, *n["path"].split("/"))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "x", encoding="utf-8", newline="\n") as f:
        f.write(text)
    return rel, True


def note_fields(it, v):
    if it["id"] == "alarm_files":
        return {"파일": {ALL: {}} if v == ALL else {x: {} for x in v}}
    return {it["쓰는 곳"]["칸"]: v}


def apply(answers, again=False, dry=False):
    rows = {r["id"]: r for r in plan(again)}
    items = recipe()["항목"]
    bad = []
    vals = {}
    for it in items:
        v = answers.get(it["id"], rows[it["id"]]["추천"])
        if it["id"] == "alarm_notes":
            continue
        if not valid(it, v):
            bad.append("%s: %s 은 꼴이 아님(%s)" % (it["id"], json.dumps(v, ensure_ascii=False), it.get("꼴")))
        vals[it["id"]] = v
    if bad:
        return {"ok": False, "틀림": bad}
    cfg = conf.load()
    new, wrote, kept, diff = dict(cfg), {}, {}, []
    for it in items:
        key = it["쓰는 곳"].get("config")
        if not key:
            continue
        v = vals[it["id"]]
        if key not in cfg:
            new[key] = wrote[key] = v
        elif cfg[key] != v and again:
            diff.append({"칸": key, "지금": cfg[key], "새": v})
            new[key] = wrote[key] = v
        else:
            kept[key] = cfg[key]
    made, have = [], []
    if not dry:
        if wrote:
            p = conf.config_path()
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p + ".tmp", "w", encoding="utf-8", newline="\n") as f:
                json.dump(new, f, ensure_ascii=False, indent=1)
                f.write("\n")
            os.replace(p + ".tmp", p)
        for n in declared_notes():
            fields = {}
            for it in items:
                if it["쓰는 곳"].get("note") == n["id"]:
                    fields.update(note_fields(it, vals[it["id"]]))
            rel, did = make_note(n, fields)
            (made if did else have).append(rel)
    return {"ok": True, "config": {"씀": wrote, "그대로": kept, "다시 바뀜": diff, "자리": os.path.relpath(conf.config_path(), VAULT).replace(os.sep, "/")},
            "노트": {"만듦": made, "있음(안 고침)": have}, "dry": dry}


def apply_text(r):
    if not r["ok"]:
        return "안 씀 — 꼴이 틀림:\n" + "\n".join("  " + x for x in r["틀림"])
    c, n = r["config"], r["노트"]
    L = ["%s개인 값 %s — 씀 %d · 그대로 %d%s" % ("(미리 보기) " if r["dry"] else "", c["자리"], len(c["씀"]), len(c["그대로"]),
                                         " · 다시 바뀜 %d" % len(c["다시 바뀜"]) if c["다시 바뀜"] else "")]
    L += ["  바뀜 %s: %s → %s" % (d["칸"], json.dumps(d["지금"], ensure_ascii=False), json.dumps(d["새"], ensure_ascii=False)) for d in c["다시 바뀜"]]
    if not r["dry"]:
        L.append("설정 노트 — 만듦 %s · 있음(안 고침) %s" % (", ".join(n["만듦"]) or "0", ", ".join(n["있음(안 고침)"]) or "0"))
    L.append("다음: 바깥 설정 점검(dist-sync:outside) → 서버 등록 → 폰 짝짓기")
    return "\n".join(L)


def status():
    """사람이 정할 칸(묻기 «늘»)이 비었거나 설정 노트가 어디에도 없으면 안 됨 — 나머지 빈 칸은 서버가 기본값으로 돈다."""
    rows = plan()
    always = {it["id"] for it in recipe()["항목"] if it["묻기"] == "늘"}
    empty = [r["id"] for r in rows if "config" in r["쓰는 곳"] and r["지금"] is None and r["id"] in always]
    notes = [n["id"] for n in declared_notes() if not note_where(n)[1]]
    if not empty and not notes:
        return 0, "모바일 연결 설정 됨"
    return 1, "모바일 연결 설정 안 됨(빈 칸 %s) — Claude 에게 «모바일 연결 설정»" % ", ".join(empty + notes)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="mobility 처음 설정 — 조리법 재기·채우기")
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("plan")
    p.add_argument("--again", action="store_true")
    p.add_argument("--json", action="store_true")
    a = sp.add_parser("apply")
    a.add_argument("--answers", required=True)
    a.add_argument("--again", action="store_true")
    a.add_argument("--dry", action="store_true")
    a.add_argument("--json", action="store_true")
    sp.add_parser("status")
    x = ap.parse_args()
    if x.cmd == "plan":
        rows = plan(x.again)
        print(json.dumps(rows, ensure_ascii=False, indent=1) if x.json else plan_text(rows))
        return 0
    if x.cmd == "status":
        code, line = status()
        print(line)
        return code
    with open(x.answers, encoding="utf-8") as f:
        answers = json.load(f)
    r = apply(answers if isinstance(answers, dict) else {}, x.again, x.dry)
    print(json.dumps(r, ensure_ascii=False, indent=1) if x.json else apply_text(r))
    return 0 if r["ok"] else 2


if __name__ == "__main__":
    sys.exit(main())
