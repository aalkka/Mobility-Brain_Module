"""폰 «준비 목록» (M7 · 계획서 §5.3 · 11-17) — 목록은 모듈 outside.json 의 «기기: 폰» 항목 한 곳 · 손발 앱이 잰 값을 기기마다 담고 바깥 설정 «앱» 재기에 한 벌로 낸다.

  py -3 .claude/skills/mobility/scripts/ready.py json    # {보고 id: 참|거짓|null} — external.py check 가 부른다(outside.json «report»)
  py -3 .claude/skills/mobility/scripts/ready.py show    # 기기마다 보고(사람이 볼 때 · 값 = 됨/안 됨만)

서버 길(server.py 가 이 대본의 함수를 부른다)
  GET  /v1/ready/list  → {items:[{id, name, need, how, guide, icon}]} — how = app(앱이 잼) · screen(못 잼 · 안내 + «했어요») · server(서버 기록 · 앱 목록에 안 보임)
  POST /v1/ready {ver, items:{id: 참|거짓|null}, human:{id: 참}} — 기기 이름(X-Brain-Device)마다 _index/server/ready.json 에 담음(기기 20 · 항목 64 상한)
판정(json): 7일 안에 보고한 기기가 모두 참 = 참 · 하나라도 거짓 = 거짓 · 보고 없음 = null(«먼저 짝짓기»). 사람 «했어요»는 잰 값과 갈라 human 에만(과대 마감 금지).
서버 기록: plugin = 7일 안에 폰 옵시디언(brain-server)이 닿음 · viewer = 7일 안에 폰 보기 판을 받아 감(seen.json).
"""
import json
import os
import re
import sys
import time

MOD = os.path.dirname(os.path.abspath(__file__))
MODULE = os.path.dirname(MOD)
OUTSIDE = os.path.join(MODULE, "outside.json")
sys.path.insert(0, MOD)
import conf  # noqa: E402

WEEK = 7 * 86400
DEV_MAX, ITEM_MAX = 20, 64
ID = re.compile(r"[a-z0-9-]{1,32}")
SERVER_IDS = ("plugin", "viewer")


def state_dir(vault=None):
    return os.path.join(conf.vault_of(vault), "3_시스템", "_index", "server")


def _read(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, type(default)) else default
    except (OSError, ValueError):
        return default


def report_id(it):
    m = it.get("재기") if isinstance(it.get("재기"), dict) else {}
    if "앱" in m:
        return str(m["앱"])
    return str(it.get("id", "")).split(".", 1)[-1].replace("phone-", "")


def items(outside=OUTSIDE):
    """앱이 그릴 목록(글은 outside.json 한 곳)."""
    d = _read(outside, {})
    out = []
    for it in d.get("항목") or []:
        if not isinstance(it, dict) or it.get("기기") != "폰":
            continue
        rid = report_id(it)
        m = it.get("재기") if isinstance(it.get("재기"), dict) else {}
        how = "server" if rid in SERVER_IDS else ("app" if "앱" in m else "screen")
        out.append({"id": rid, "name": it.get("짧은 이름") or it.get("이름"), "need": bool(it.get("필수")), "how": how,
                    "guide": it.get("폰 안내") or (it.get("안내") or [""])[0], "icon": it.get("그림") or ""})
    return out


def store(state, device, body, now=None):
    """기기 보고 하나를 담는다 → {ok}. 꼴이 틀리면 ValueError."""
    now = now or time.time()
    if not isinstance(body, dict):
        raise ValueError("꼴")
    got, human = body.get("items") or {}, body.get("human") or {}
    if not isinstance(got, dict) or not isinstance(human, dict) or len(got) > ITEM_MAX or len(human) > ITEM_MAX:
        raise ValueError("꼴")
    clean = {k: v for k, v in got.items() if isinstance(k, str) and ID.fullmatch(k) and (v is None or isinstance(v, bool))}
    hum = {k: True for k, v in human.items() if isinstance(k, str) and ID.fullmatch(k) and v is True}
    ver = body.get("ver") if isinstance(body.get("ver"), int) else None
    path = os.path.join(state, "ready.json")
    d = _read(path, {})
    d[str(device)[:40]] = {"at": now, "ver": ver, "items": clean, "human": hum}
    if len(d) > DEV_MAX:
        for k in sorted(d, key=lambda k: d[k].get("at", 0))[:len(d) - DEV_MAX]:
            d.pop(k, None)
    os.makedirs(state, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False)
    os.replace(tmp, path)
    return {"ok": True}


def report(state, now=None):
    """{보고 id: 참|거짓|null} — 7일 안 기기 보고를 합침 + 서버 기록(plugin·viewer)."""
    now = now or time.time()
    d = _read(os.path.join(state, "ready.json"), {})
    fresh = [v for v in d.values() if isinstance(v, dict) and now - v.get("at", 0) < WEEK]
    vals = {}
    for v in fresh:
        for k, x in (v.get("items") or {}).items():
            vals.setdefault(k, []).append(x)
    out = {k: (False if False in xs else (True if xs and all(x is True for x in xs) else None)) for k, xs in vals.items()}
    seen = _read(os.path.join(state, "seen.json"), {})

    def seen_kind(kind):
        return any(k.endswith("|" + kind) and isinstance(v, dict) and now - v.get("at", 0) < WEEK for k, v in seen.items())
    out["plugin"] = True if seen_kind("obsidian") else (False if fresh else None)
    out["viewer"] = True if seen_kind("viewer") else (False if fresh else None)
    return out


def main(argv):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    vault = argv[argv.index("--vault") + 1] if "--vault" in argv else None
    state = state_dir(vault)
    cmd = argv[0] if argv else "json"
    if cmd == "json":
        print(json.dumps(report(state), ensure_ascii=False))
        return 0
    if cmd == "show":
        d = _read(os.path.join(state, "ready.json"), {})
        for dev, v in d.items():
            items_ = v.get("items") or {}
            bad = [k for k, x in items_.items() if x is False]
            print(f"{dev} · {time.strftime('%m-%d %H:%M', time.localtime(v.get('at', 0)))} · 됨 {sum(1 for x in items_.values() if x)} · 안 됨 {', '.join(bad) or '0'} · 사람 확인 {len(v.get('human') or {})}")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
