"""모바일 연결 — 짝짓기(QR) · 붙은 기기 · 열쇠 바꾸기 (M2 · 계획서 §5.1 · 11-17)

  py -3 .claude/skills/mobility/scripts/pair.py new [--open]   # 짝 코드 하나(10분 · 4번) → «모바일 연결» 화면이 QR 로 보인다 · --open = 옵시디언 없이 기본 브라우저(_index/server/pair.html · 10분 뒤 지움)
  py -3 .claude/skills/mobility/scripts/pair.py view [--reason R]   # «모바일 연결» 화면 자료(마지막 줄 JSON · brain-base 모듈 화면이 부른다)
  py -3 .claude/skills/mobility/scripts/pair.py rotate         # 열쇠 바꾸기 — 새 열쇠 · 옛 열쇠는 바로 죽음(서버는 열쇠 파일 판이 바뀌면 다시 읽음) · 기기는 QR 을 다시 찍는다
  py -3 .claude/skills/mobility/scripts/pair.py status         # 붙은 기기 · 코드 남은 시간(값 없이)
  py -3 .claude/skills/mobility/scripts/pair.py doctor         # 건강 한 줄(module.json contributes.doctor)

짝 코드는 HTTP 로 만들지 않는다 — tailscale serve 가 넘긴 요청도 127.0.0.1 에서 와서 «PC 안»과 못 가른다. 만드는 길 = 이 대본(PC 화면 단추 · Claude)뿐.
코드 = 무작위 128비트(QR 주소 안) + 짧은 코드 8자(카메라 없는 기기가 주소와 함께 친다) · 10분 · 4번(폰 앱·폰 옵시디언·탭 앱·탭 옵시디언) · 틀림 10번이면 모든 코드 무효.
pair.json = 해시만. 화면이 그릴 글(QR 주소·짧은 코드)은 pair-show.json 에 만료까지만 둔다 — 서버는 그 파일을 읽지도 내보내지도 않는다. 열쇠는 QR·쪽 어디에도 안 든다.
붙은 기기 = 짝 기록(pair.json) + 서버가 본 기기(seen.json · 앱 당김 phone-app.json) — 열쇠를 바꾼 뒤 아직 안 닿은 기기는 «다시 찍기».
주소 = Tailscale 이 아는 이 PC 이름(https://<이름>.ts.net) · 시험은 BRAIN_PAIR_BASE 로 준다(에뮬레이터 http://10.0.2.2:<문>).
"""
import hashlib
import html
import json
import os
import secrets
import subprocess
import sys
import time

MOD = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, MOD)
import conf  # noqa: E402
import qr  # noqa: E402

TTL = 10 * 60
USES = 4
BAD_MAX = 10
SHORT_ABC = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"      # 헷갈리는 I·L·O·0·1 뺌
KINDS = {"app": "앱", "obsidian": "옵시디언"}
NOWIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)
SEEN_DAYS = 30                                    # 이보다 오래 안 닿은 기기는 목록에서 뺀다


class PairError(Exception):
    def __init__(self, code, msg):
        super().__init__(msg)
        self.code, self.msg = code, msg


def state_dir(vault=None):
    return os.path.join(conf.vault_of(vault), "3_시스템", "_index", "server")


def _p(state, name):
    return os.path.join(state, name)


def _read(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, type(default)) else default
    except (OSError, ValueError):
        return default


def _write(path, d):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False)
    os.replace(tmp, path)


class _Lock:
    """pair.json 읽고 고치기를 하나씩(대본과 서버) — msvcrt 바이트 잠금 · 죽으면 OS 가 풂."""

    def __init__(self, state):
        self.path, self.f = _p(state, "pair.lock"), None

    def __enter__(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self.f = open(self.path, "a+b")
        try:
            import msvcrt
        except ImportError:
            return self
        for _ in range(100):
            try:
                self.f.seek(0)
                msvcrt.locking(self.f.fileno(), msvcrt.LK_NBLCK, 1)
                return self
            except OSError:
                time.sleep(0.05)
        return self                               # 5초 넘게 못 잡으면 그냥 간다(짝짓기는 드물다)

    def __exit__(self, *a):
        try:
            import msvcrt
            self.f.seek(0)
            msvcrt.locking(self.f.fileno(), msvcrt.LK_UNLCK, 1)
        except (ImportError, OSError):
            pass
        self.f.close()


def _h(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def norm_short(s):
    return "".join(c for c in str(s or "").upper() if c.isalnum())


def load(state):
    d = _read(_p(state, "pair.json"), {})
    d.setdefault("codes", [])
    d.setdefault("bad", 0)
    d.setdefault("devices", {})
    return d


def live_codes(d, now):
    return [c for c in d.get("codes") or [] if isinstance(c, dict) and c.get("exp", 0) > now and c.get("left", 0) > 0]


# ───────── 주소 ─────────

def ts_exe():
    import shutil
    p = shutil.which("tailscale")
    dflt = os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "Tailscale", "tailscale.exe")
    return p or (dflt if os.path.isfile(dflt) else None)


def base_url():
    """짝 주소의 앞 — BRAIN_PAIR_BASE(시험) → Tailscale 이 아는 이 PC 이름 · 모르면 None."""
    env = os.environ.get("BRAIN_PAIR_BASE")
    if env:
        return env.rstrip("/")
    exe = ts_exe()
    if not exe:
        return None
    try:
        r = subprocess.run([exe, "status", "--json"], capture_output=True, timeout=10, creationflags=NOWIN)
        name = (json.loads(r.stdout.decode("utf-8", "replace")).get("Self") or {}).get("DNSName") or ""
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return None
    name = name.rstrip(".")
    return "https://" + name if name.endswith(".ts.net") else None


# ───────── 코드 ─────────

def new(state, base, now=None):
    """새 짝 코드 → {url, short, exp, left} · 옛 코드는 그대로 둔다(10분 안 · 남은 번)."""
    now = now or time.time()
    code = secrets.token_urlsafe(16)
    short = "".join(secrets.choice(SHORT_ABC) for _ in range(8))
    with _Lock(state):
        d = load(state)
        d["codes"] = live_codes(d, now)[-3:] + [{"h": _h(code), "s": _h(short), "exp": now + TTL, "left": USES, "at": now, "base": base}]
        d["bad"] = 0
        _write(_p(state, "pair.json"), d)
    show = {"url": f"{base}/pair?c={code}" if base else None, "base": base, "short": short[:4] + "-" + short[4:], "exp": now + TTL, "h": _h(code)}
    _write(_p(state, "pair-show.json"), show)
    return show


def _find(d, code, now):
    raw = str(code or "").strip()
    if not raw or len(raw) > 64:
        return None
    hs = {_h(raw), _h(norm_short(raw))}
    for c in live_codes(d, now):
        if c.get("h") in hs or c.get("s") in hs:
            return c
    return None


def active(state, now=None):
    return bool(live_codes(load(state), now or time.time()))


def check(state, code, now=None):
    """코드가 지금 맞나(쓰지 않음) → 그 코드 칸(base = 이 PC 주소 · 비밀 아님) · 틀리면 None + 틀림을 센다(살아 있는 코드가 있을 때만)."""
    now = now or time.time()
    with _Lock(state):
        d = load(state)
        if not live_codes(d, now):
            return None
        c = _find(d, code, now)
        if c:
            return dict(c)
        _bad(d, now)
        _write(_p(state, "pair.json"), d)
        return None


def _bad(d, now):
    d["bad"] = int(d.get("bad") or 0) + 1
    if d["bad"] >= BAD_MAX:                       # 틀림 10번 — 모든 코드 무효(화면 QR 도 지운다)
        d["codes"] = []
        d["bad"] = 0
        d["wiped"] = now


def use(state, code, name, kind, ip="", now=None):
    """짝짓기 — 코드 한 번 씀 · 기기를 적음 → 참. 틀리면 PairError(404 = 코드 없음·틀림 · 400 = 칸 틀림)."""
    now = now or time.time()
    if kind not in KINDS:
        raise PairError(400, "종류가 잘못됨")
    name = " ".join(str(name or "").split())[:40] or "이름 없는 기기"
    with _Lock(state):
        d = load(state)
        if not live_codes(d, now):
            raise PairError(404, "없는 길")
        c = _find(d, code, now)
        if not c:
            _bad(d, now)
            _write(_p(state, "pair.json"), d)
            raise PairError(404, "없는 길")
        c["left"] = int(c.get("left") or 0) - 1
        d["devices"][f"{name}|{kind}"] = {"name": name, "kind": kind, "ip": ip, "at": now, "paired": now}
        d["last_pair"] = now
        _write(_p(state, "pair.json"), d)
    show = _read(_p(state, "pair-show.json"), {})
    if show and c["left"] <= 0 and show.get("h") == c.get("h"):
        _rm(_p(state, "pair-show.json"))
    return True


def _rm(path):
    try:
        os.remove(path)
    except OSError:
        pass


def sweep(state, now=None):
    """만료된 화면 글·브라우저 쪽을 지운다(서버 5분 순찰 · 화면 자료가 부름)."""
    now = now or time.time()
    show = _read(_p(state, "pair-show.json"), {})
    if show and (show.get("exp", 0) <= now or not active(state, now)):
        _rm(_p(state, "pair-show.json"))
    page = _p(state, "pair.html")
    try:
        if now - os.path.getmtime(page) > TTL:
            _rm(page)
    except OSError:
        pass


def rotate(state, now=None):
    """새 열쇠 — 옛 열쇠는 바로 죽는다(서버가 파일 판을 보고 다시 읽음) · 살아 있는 코드도 지운다."""
    now = now or time.time()
    tok = _p(state, "token")
    tmp = tok + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(secrets.token_urlsafe(32))
    os.replace(tmp, tok)
    with _Lock(state):
        d = load(state)
        d["codes"] = []
        d["rotated"] = now
        _write(_p(state, "pair.json"), d)
    _rm(_p(state, "pair-show.json"))
    return now


# ───────── 붙은 기기 ─────────

def devices(state, now=None):
    """[{name, kind, at, new, again}] — 짝 기록 + 서버가 본 기기 + 앱 당김. 최근부터."""
    now = now or time.time()
    d = load(state)
    rot = d.get("rotated") or 0
    by = {}

    def put(name, kind, at, ip=""):
        if not at or kind not in KINDS:
            return
        name = name or None
        key = (name or ("ip:" + (ip or "?")), kind)
        cur = by.get(key)
        if cur is None or at > cur["at"]:
            by[key] = {"name": name, "kind": kind, "at": at, "ip": ip}
    for v in (d.get("devices") or {}).values():
        if isinstance(v, dict):
            put(v.get("name"), v.get("kind"), v.get("at"), v.get("ip", ""))
    app = _read(_p(state, "phone-app.json"), {})
    for name, v in (app.get("devices") or {}).items():
        if isinstance(v, dict) and name != "기기 미상":
            put(name, "app", (v.get("at") or 0) / 1000, v.get("ip", ""))
    seen = _read(_p(state, "seen.json"), {})
    names_by_ip = {v["ip"]: v["name"] for v in by.values() if v.get("ip") and v.get("name")}
    for k, v in seen.items():
        if isinstance(v, dict):
            ip, _, kind = k.rpartition("|")
            put(v.get("name") or names_by_ip.get(ip), kind, v.get("at"), ip)
    named_ips = {(v["ip"], v["kind"]) for v in by.values() if v.get("name")}
    out = []
    for v in by.values():
        if not v["name"] and (v["ip"], v["kind"]) in named_ips:
            continue                               # 이름 없는 줄이 같은 주소의 이름 있는 줄과 같은 기기
        if now - v["at"] > SEEN_DAYS * 86400:
            continue
        out.append({"name": v["name"] or "이름 모름", "kind": v["kind"], "at": v["at"],
                    "new": now - (d.get("devices", {}).get(f"{v['name']}|{v['kind']}", {}).get("paired") or 0) < TTL,
                    "again": bool(rot) and v["at"] < rot})
    return sorted(out, key=lambda x: -x["at"])


def ago(t, now=None):
    s = max(0, int((now or time.time()) - t))
    if s < 90:
        return "방금"
    if s < 3600:
        return f"{s // 60}분 전"
    if s < 86400:
        return f"{s // 3600}시간 전"
    return f"{s // 86400}일 전"


# ───────── PC 준비(바깥 설정 PC 필수 항목 · 10분 담아 둠) ─────────
PC_ITEMS = ("tailscale", "login", "magicdns", "https", "serve", "task", "alive")
PC_NAMES = {"tailscale": "Tailscale 설치", "login": "Tailscale 로그인", "magicdns": "MagicDNS", "https": "HTTPS 인증서",
            "serve": "serve", "task": "예약 «외부뇌 서버»", "alive": "서버 답함"}


def pc_ready(state, vault=None, fresh=False, now=None):
    now = now or time.time()
    cache = _read(_p(state, "pc-ready.json"), {})
    if not fresh and now - cache.get("at", 0) < 600 and isinstance(cache.get("items"), dict):
        return cache["items"]
    import pc_state
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=len(PC_ITEMS)) as ex:
        got = list(ex.map(lambda i: pc_state.measure(i, vault)[0], PC_ITEMS))
    items = {i: {0: True, 1: False}.get(c) for i, c in zip(PC_ITEMS, got)}
    _write(_p(state, "pc-ready.json"), {"at": now, "items": items})
    return items


# ───────── 화면 자료 ─────────

def view(state, vault=None, reason="open", now=None):
    now = now or time.time()
    sweep(state, now)
    d = load(state)
    pc = pc_ready(state, vault, fresh=reason == "refresh-pc", now=now)
    show = _read(_p(state, "pair-show.json"), {})
    live = {c.get("h"): c for c in live_codes(d, now)}
    qr_out = None
    if show and show.get("h") in live:
        c = live[show["h"]]
        qr_out = {"svg": qr.svg(qr.encode(show["url"])) if show.get("url") else None, "short": show.get("short"),
                  "until": time.strftime("%H:%M", time.localtime(show["exp"])), "left": c.get("left"),
                  "used": USES - int(c.get("left") or 0), "base": show.get("base")}
    devs = devices(state, now)
    last = d.get("last_pair") or 0
    return {
        "pc": {"ok": sum(1 for v in pc.values() if v), "n": len(pc), "miss": [PC_NAMES[k] for k, v in pc.items() if v is False],
               "unknown": [PC_NAMES[k] for k, v in pc.items() if v is None]},
        "qr": qr_out,
        "paired": ago(last, now) if last and now - last < TTL else None,
        "devices": [{"name": x["name"], "kind": KINDS[x["kind"]], "ago": ago(x["at"], now), "new": x["new"], "again": x["again"],
                     "tab": "tab" in x["name"].lower() or "탭" in x["name"]} for x in devs],
        "rotated": time.strftime("%m-%d %H:%M", time.localtime(d["rotated"])) if d.get("rotated") else None,
        "wiped": bool(d.get("wiped") and now - d["wiped"] < TTL),
    }


# ───────── 폰이 여는 쪽(/pair) — 서버가 코드가 맞을 때만 낸다 ─────────

def page(code, base, have_app, have_plugin):
    """폰 브라우저 쪽 — 손발 앱 받기·넣기 · 옵시디언 플러그인 받기·넣기(코드 = 주소의 것 · 열쇠 없음)."""
    from urllib.parse import quote
    c, b = quote(code, safe=""), quote(base, safe="")
    host = html.escape(base.split("://", 1)[-1])
    rows = []
    if have_app:
        rows.append(f'<a class="b" href="/pair/app?c={c}">손발 앱 받기</a>')
    rows.append(f'<a class="b p" href="intent://pair?u={b}&amp;c={c}#Intent;scheme=brainphone;package=brain.phone;end">손발 앱에 넣기</a>')
    if have_plugin:
        rows.append(f'<a class="b" href="/pair/plugin?c={c}">옵시디언 플러그인 받기</a>')
    rows.append(f'<a class="b p" href="obsidian://brain-server?pair={c}&amp;u={b}">옵시디언에 넣기</a>')
    return ("<!doctype html><html lang=\"ko\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            "<meta name=\"referrer\" content=\"no-referrer\"><title>모바일 연결</title><style>"
            ":root{color-scheme:light dark;--bg:#fff;--tx:#222;--tx2:#777;--ln:#ddd;--ac:#7c5cff}"
            "@media(prefers-color-scheme:dark){:root{--bg:#1e1e1e;--tx:#ddd;--tx2:#999;--ln:#3a3a3a}}"
            "body{margin:0;background:var(--bg);color:var(--tx);font:16px/1.5 system-ui,sans-serif}"
            ".w{max-width:420px;margin:0 auto;padding:20px 16px}h1{font-size:20px;margin:0 0 4px}.h{color:var(--tx2);font-size:14px;margin-bottom:18px;word-break:break-all}"
            ".b{display:block;text-align:center;text-decoration:none;color:var(--tx);border:1px solid var(--ln);border-radius:10px;padding:12px;margin:10px 0}"
            ".b.p{background:var(--ac);border-color:var(--ac);color:#fff}</style></head><body><div class=\"w\">"
            f"<h1>모바일 연결</h1><div class=\"h\">{host}</div>{''.join(rows)}</div></body></html>")


# ───────── 브라우저(옵시디언 없이) ─────────

def open_page(state, show):
    body = (qr.svg(qr.encode(show["url"]), px=280) if show.get("url") else "<p>주소 모름 — Tailscale</p>")
    doc = ("<!doctype html><html lang=\"ko\"><head><meta charset=\"utf-8\"><title>모바일 연결</title><style>"
           "body{font:16px system-ui,sans-serif;display:flex;flex-direction:column;align-items:center;gap:12px;margin-top:40px}"
           ".c{border:1px solid #ccc;border-radius:6px;padding:2px 10px}</style></head><body>"
           f"<b>모바일 연결</b>{body}<div><span class=\"c\">{html.escape(show.get('short') or '')}</span> "
           f"{time.strftime('%H:%M', time.localtime(show['exp']))} · {USES}번</div></body></html>")
    path = _p(state, "pair.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(doc)
    os.startfile(path)                             # 기본 브라우저 — 사람이 누른 길(Claude 가 사용자에게 보일 때)
    return path


# ───────── 건강 ─────────

def doctor(state, now=None):
    now = now or time.time()
    try:
        r = subprocess.run([sys.executable, os.path.join(MOD, "setup.py"), "status"], capture_output=True, timeout=15, creationflags=NOWIN)
        done = r.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        done = None
    if done is False:
        return 1, "모바일 연결 설정 안 됨 — Claude 에게 «모바일 연결 설정»"
    devs = devices(state, now)
    fresh = [x for x in devs if now - x["at"] < 3 * 86400 and not x["again"]]
    again = [x for x in devs if x["again"]]
    if again and not fresh:
        return 1, f"열쇠를 바꾼 뒤 아무 기기도 안 붙음 — «모바일 연결» 화면 QR 을 다시 찍기({len(again)})"
    if not devs:
        return 0, "붙은 기기 없음 — «모바일 연결» 화면에서 QR"
    return 0, f"붙은 기기 {len(devs)} · 3일 안에 닿음 {len(fresh)}"


def main(argv):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    vault = argv[argv.index("--vault") + 1] if "--vault" in argv else None
    state = state_dir(vault)
    cmd = argv[0] if argv and not argv[0].startswith("-") else "view"
    if cmd == "new":
        show = new(state, base_url())
        if "--open" in argv:
            open_page(state, show)
        print(json.dumps({"ok": bool(show.get("url")), "until": time.strftime("%H:%M", time.localtime(show["exp"])),
                          **({} if show.get("url") else {"err": "주소 모름 — Tailscale 로그인·MagicDNS 확인"})}, ensure_ascii=False))
        return 0
    if cmd == "view":
        reason = argv[argv.index("--reason") + 1] if "--reason" in argv else "open"
        print(json.dumps(view(state, vault, reason), ensure_ascii=False))
        return 0
    if cmd == "rotate":
        rotate(state)
        print(json.dumps({"ok": True, "msg": "열쇠 바꿈 — 기기마다 «모바일 연결» QR 을 다시 찍는다"}, ensure_ascii=False))
        return 0
    if cmd == "status":
        d = load(state)
        now = time.time()
        live = live_codes(d, now)
        print(json.dumps({"codes": [{"left": c["left"], "min": int((c["exp"] - now) // 60)} for c in live],
                          "devices": [{k: x[k] for k in ("name", "kind", "again")} | {"ago": ago(x["at"])} for x in devices(state)]}, ensure_ascii=False))
        return 0
    if cmd == "doctor":
        code, line = doctor(state)
        print(line)
        return code
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
