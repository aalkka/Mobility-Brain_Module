"""조리법 시험 — 임시 볼트에 모듈을 복사해 plan → apply(시험 답) → 다시 → 틀린 답을 잰다(본 볼트 무관 · 읽기만).
    py -3 .claude/skills/mobility/scripts/setup_check.py
더: 만든 설정(config·노트)에 이 PC 의 개인 값(집 Wi-Fi·tailnet 이름·폰 기기 이름)이 0 인가 · 모듈 파일에 남은 개인 값(자리만 · 값은 안 보임) ·
    server.py 의 문 번호 기본(설정 전 예비)이 조리법 기본값과 같은가(문 번호 한 곳의 드리프트 막기).
"""
# mf:allow-path-file — 시험 픽스처: 임시 볼트 안의 2_지식·3_시스템 자리를 만들고 잰다(본 볼트 안 건드림)
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

MOD = os.path.dirname(os.path.abspath(__file__))
MODULE = os.path.dirname(MOD)
VAULT = os.path.abspath(os.path.join(MOD, "..", "..", "..", ".."))
NOWIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)
fails = []


def ok(name, cond, extra=""):
    print(("통과 " if cond else "실패 ") + name + (" — %s" % (extra,) if extra else ""), flush=True)
    if not cond:
        fails.append(name)


def run(v, *args):
    r = subprocess.run([sys.executable, os.path.join(v, ".claude", "skills", "mobility", "scripts", "setup.py"), *args],
                       capture_output=True, timeout=60, creationflags=NOWIN)
    return r.returncode, r.stdout.decode("utf-8", "replace")


def personal_values():
    """이 PC 의 개인 값 — 집 Wi-Fi(진짜 config) · tailnet 이름 · 폰 기기 이름(서버 기록). 값은 출력하지 않는다."""
    vals = set()
    st = os.path.join(VAULT, "3_시스템", "_index", "server")
    try:
        vals |= {x for x in json.load(open(os.path.join(st, "config.json"), encoding="utf-8")).get("home_wifi") or [] if len(x) >= 3}
    except (OSError, ValueError):
        pass
    try:
        d = json.load(open(os.path.join(st, "phone-app.json"), encoding="utf-8"))
        vals |= {k for k in list((d.get("devices") or {}).keys()) + [d.get("device") or ""] if len(k) >= 4 and k != "기기 미상"}
    except (OSError, ValueError, AttributeError):
        pass
    sys.path.insert(0, MOD)
    import pc_state
    s = pc_state.ts_json("status") or {}
    dns = ((s.get("Self") or {}).get("DNSName") or "").rstrip(".")
    vals |= {x for x in dns.split(".") if len(x) >= 6 and x not in ("ts", "net")}
    return vals


def grep(root, vals, skip=()):
    hits = {}
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d != "__pycache__"]
        for fn in fns:
            p = os.path.join(dp, fn)
            if any(p.endswith(s) for s in skip):
                continue
            try:
                text = open(p, encoding="utf-8").read()
            except (OSError, UnicodeDecodeError):
                continue
            n = sum(text.count(v) for v in vals)
            if n:
                hits[os.path.relpath(p, root).replace(os.sep, "/")] = n
    return hits


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    tmp = tempfile.mkdtemp(prefix="mobility-setup-")
    v = os.path.join(tmp, "v")
    try:
        shutil.copytree(MODULE, os.path.join(v, ".claude", "skills", "mobility"), ignore=shutil.ignore_patterns("__pycache__"))
        os.makedirs(os.path.join(v, "3_시스템"))
        for f in ("roles.py", "roles.json"):
            shutil.copy2(os.path.join(VAULT, "3_시스템", f), os.path.join(v, "3_시스템", f))
        sys.path.insert(0, os.path.join(VAULT, "3_시스템"))
        import roles
        sched = os.path.join(v, *roles.path("schedule").split("/"))
        os.makedirs(sched)
        for f in ("가-일정.md", "나-일정.md"):
            open(os.path.join(sched, f), "w", encoding="utf-8").write("# 일정\n")
        code, out = run(v, "status")
        ok("설정 전 — status 안 됨(종료 1)", code == 1, out.strip())
        code, out = run(v, "plan", "--json")
        rows = {r["id"]: r for r in json.loads(out)}
        ok("plan — 일정 파일 둘 = 알림 파일 추천 둘 · 쓰기 파일은 물음",
           rows["alarm_files"]["추천"] == ["가-일정.md", "나-일정.md"] and rows["write_schedule"]["묻기"] and rows["alarm_files"]["묻기"])
        ok("plan — 안 물음 칸은 안 묻고 · 비밀 칸 없음", not rows["alarm_notes"]["묻기"] and not rows["lock_ttl"]["묻기"]
           and not any(re.search("token|열쇠", k) for k in rows))
        ok("plan — 노트 자리 = 모듈 홈(만들 곳)", rows["alarm_notes"]["추천"] == {"alarm-settings": "2_지식/modules/mobility/알림-설정.md",
                                                                       "alarm-per-line": "2_지식/modules/mobility/일정별-알림.md"})
        ans = os.path.join(tmp, "답.json")
        answers = {"home_wifi": ["시험-와이파이"], "phone_sensitive": "hide", "write_schedule": "나-일정.md", "alarm_files": ["가-일정.md"],
                   "quiet": {"부터": "00:00", "까지": "07:00"}, "port": 8399}
        json.dump(answers, open(ans, "w", encoding="utf-8"), ensure_ascii=False)
        code, out = run(v, "apply", "--answers", ans, "--json")
        r = json.loads(out)
        cfg_p = os.path.join(v, "3_시스템", "_index", "server", "config.json")
        cfg = json.load(open(cfg_p, encoding="utf-8"))
        ok("apply — config 여섯 칸(rc_mode 11-21)", cfg == {"port": 8399, "home_wifi": ["시험-와이파이"], "phone_sensitive": "hide", "write_schedule": "나-일정.md", "rc_mode": "auto", "lock_ttl": 120}, cfg)
        note = os.path.join(v, "2_지식", "modules", "mobility", "알림-설정.md")
        text = open(note, encoding="utf-8").read() if os.path.isfile(note) else ""
        sys.path.insert(0, MOD)
        import alarms
        m = alarms.JSON_BLOCK.search(text)
        block = json.loads(m.group(1)) if m else {}
        bad = [p for p in alarms.parse_settings(text)[1] if "일정 폴더에 없는 파일" not in p and "울릴 파일이 하나도 없음" not in p]   # 이름 재기는 본 볼트 일정 폴더 기준이라 뺌
        ok("apply — 노트 둘 · json 칸 채움(파일·잘 시간) · 꼴 문제 0", len(r["노트"]["만듦"]) == 2 and block.get("파일") == {"가-일정.md": {}}
           and block.get("잘_시간") == {"부터": "00:00", "까지": "07:00"} and not bad and text.startswith("---\ntitle: 알림 설정") and "{{날짜}}" not in text,
           (r["노트"], bad))
        # 방해 금지 켬·끔(11-19) — 꼴 검사 셋: 없음(옛 꼴)·켬 true·끔 false 는 맞음 · 켬이 참거짓 아니거나 모르는 칸이면 틀림
        import setup as setup_mod
        q_item = next(x for x in setup_mod.recipe()["항목"] if x["id"] == "quiet")
        okq = lambda val: setup_mod.valid(q_item, val) if hasattr(setup_mod, "valid") else None
        ok("quiet 꼴 — 없음·true·false 맞음 · 문자열 켬·모르는 칸 틀림 · 기본값 = 켬 23:00~08:00",
           okq({"부터": "00:00", "까지": "07:00"}) and okq({"켬": True, "부터": "23:00", "까지": "08:00"}) and okq({"켬": False, "부터": "23:00", "까지": "08:00"})
           and okq({"켬": "no", "부터": "23:00", "까지": "08:00"}) is False and okq({"켬": True, "부터": "23:00", "까지": "08:00", "x": 1}) is False
           and q_item["기본값"] == {"켬": True, "부터": "23:00", "까지": "08:00"})
        alarms.SAVE_LAST = False
        code, out = run(v, "status")
        ok("설정 뒤 — status 됨(종료 0)", code == 0, out.strip())
        before = open(cfg_p, encoding="utf-8").read(), text
        json.dump(dict(answers, home_wifi=["다른-와이파이"]), open(ans, "w", encoding="utf-8"), ensure_ascii=False)
        code, out = run(v, "apply", "--answers", ans, "--json")
        r = json.loads(out)
        ok("다시 돌림(--again 없음) — 있는 값은 그대로 · 노트 안 고침", not r["config"]["씀"] and len(r["노트"]["있음(안 고침)"]) == 2
           and (open(cfg_p, encoding="utf-8").read(), open(note, encoding="utf-8").read()) == before)
        code, out = run(v, "apply", "--answers", ans, "--again", "--dry", "--json")
        r = json.loads(out)
        ok("재보정 미리 보기 — 바뀐 칸 diff 하나 · 안 씀", [d["칸"] for d in r["config"]["다시 바뀜"]] == ["home_wifi"] and open(cfg_p, encoding="utf-8").read() == before[0])
        code, out = run(v, "apply", "--answers", ans, "--again")
        ok("재보정 — 바뀐 칸만 씀", json.load(open(cfg_p, encoding="utf-8"))["home_wifi"] == ["다른-와이파이"], out.splitlines()[0])
        json.dump({}, open(ans, "w", encoding="utf-8"))
        code, out = run(v, "apply", "--answers", ans, "--again", "--dry", "--json")
        r = json.loads(out)
        ok("재보정(답 없음) — 여러 값 칸(집 Wi-Fi)은 지금 값을 안 버림(합침 · 11-18)", "home_wifi" not in [d["칸"] for d in r["config"]["다시 바뀜"]]
           or all(x in d["새"] for d in r["config"]["다시 바뀜"] if d["칸"] == "home_wifi" for x in ["다른-와이파이"]), json.dumps(r["config"]["다시 바뀜"], ensure_ascii=False)[:200])
        json.dump({"port": "x", "lock_ttl": 5}, open(ans, "w", encoding="utf-8"))
        snap = open(cfg_p, encoding="utf-8").read()
        code, out = run(v, "apply", "--answers", ans, "--again")
        ok("틀린 답 — 종료 2 · 아무것도 안 씀", code == 2 and open(cfg_p, encoding="utf-8").read() == snap, out.splitlines()[0])
        vals = personal_values()
        made = grep(os.path.join(v, "3_시스템", "_index"), vals)
        made.update(grep(os.path.join(v, "2_지식"), vals))
        ok("만든 설정에 이 PC 개인 값 0", not made and bool(vals), "개인 값 %d개로 잼 · 걸린 파일 %s" % (len(vals), sorted(made)))
        left = grep(MODULE, vals)
        print("알림 모듈 파일에 남은 개인 값(자리만): %s" % (sorted(left) or "없음"))
        ok("모듈 파일 개인 값 — server_check(SSID 가짜 값은 다른 일꾼 몫) 밖 0", not [f for f in left if f != "scripts/server_check.py"], sorted(left))
        src = open(os.path.join(MOD, "server.py"), encoding="utf-8").read()
        m = re.search(r"config\(\)\.get\('port'\)\s+or\s+(\d+)", src)
        ok("문 번호 — server.py 예비 기본 = 조리법 기본값", bool(m) and int(m.group(1)) == json.load(open(os.path.join(MODULE, "setup.json"), encoding="utf-8"))["항목"][0]["기본값"],
           m.group(1) if m else "server.py 에서 못 찾음")
        with open(os.path.join(MOD, "server-setup.ps1"), encoding="utf-8-sig") as f:
            ps = f.read()
        ok("문 번호 — 등록 대본에 박힌 숫자 없음(conf.py 에서 읽음)", "8377" not in ps and "conf.py" in ps)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("== 실패 %d건" % len(fails))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
