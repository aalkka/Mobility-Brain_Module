"""바깥 설정 PC 항목 재기 — 모듈 outside.json 의 «재기 명령»이 부른다(읽기만 · 창 없음 · LLM 0).

  py -3 .claude/skills/mobility/scripts/pc_state.py <id> [--vault V]   # 종료 0 됨 · 1 안 됨 · 2 모름(못 잼) · 까닭 한 줄
  py -3 .claude/skills/mobility/scripts/pc_state.py all [--vault V]    # 다 재서 한 줄씩(사람이 볼 때)

id = tailscale(설치) · login(로그인 = BackendState Running) · magicdns · https(CertDomains) ·
     serve(`/` → 127.0.0.1:<이 볼트 문>) · task(예약 «외부뇌 서버»가 이 볼트 server.py) · alive(서버가 401·200 으로 답함) ·
     power(전원 연결 때 덮개를 닫아도 아무 것도 안 함 · 선택)
값은 출력하지 않는다(tailnet 이름·주소·SSID 는 이 PC 개인 값) — 됨·안 됨과 까닭만.
문 번호는 conf.py 한 곳(config «port» → 조리법 기본값). 판정 함수(judge_*)는 시험(pc_state_check)이 가짜 자료로 0·1·2 를 가른다.
"""
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import urllib.error
import urllib.request

MOD = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, MOD)
import conf  # noqa: E402

NOWIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)
TS_DEFAULT = os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "Tailscale", "tailscale.exe")
TASK = "외부뇌 서버"
DONE, NOT, UNKNOWN = 0, 1, 2


def ts_exe():
    p = shutil.which("tailscale")
    return p or (TS_DEFAULT if os.path.isfile(TS_DEFAULT) else None)


def ts_json(*args):
    exe = ts_exe()
    if not exe:
        return None
    try:
        r = subprocess.run([exe, *args, "--json"], capture_output=True, timeout=10, creationflags=NOWIN)
        return json.loads(r.stdout.decode("utf-8", "replace")) if r.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return None


def judge_login(st):
    if st is None:
        return UNKNOWN, "tailscale status 를 못 읽음"
    s = st.get("BackendState")
    return (DONE, "로그인됨") if s == "Running" else (NOT, "로그인 안 됨(%s)" % (s or "없음"))


def judge_magicdns(st):
    if st is None:
        return UNKNOWN, "tailscale status 를 못 읽음"
    v = (st.get("CurrentTailnet") or {}).get("MagicDNSEnabled")
    if v is None:
        return UNKNOWN, "MagicDNSEnabled 칸 없음(로그인 전이거나 판이 다름)"
    return (DONE, "MagicDNS 켬") if v else (NOT, "MagicDNS 꺼짐")


def judge_https(st):
    if st is None:
        return UNKNOWN, "tailscale status 를 못 읽음"
    return (DONE, "HTTPS 인증서 이름 있음") if st.get("CertDomains") else (NOT, "HTTPS 인증서 안 켬(CertDomains 비었음)")


PROXY = re.compile(r"^https?://(?:127\.0\.0\.1|localhost):(\d+)/?$")


def judge_serve(sv, port):
    """`/` 처리기가 이 볼트 문으로 가나 — 다른 문(다른 볼트 서버)이 맡았으면 안 됨(그 설정은 건드리지 않는다)."""
    if sv is None:
        return UNKNOWN, "tailscale serve status 를 못 읽음"
    others = []
    for host, h in (sv.get("Web") or {}).items():
        if not str(host).endswith(":443"):
            continue
        prox = ((h.get("Handlers") or {}).get("/") or {}).get("Proxy") or ""
        m = PROXY.match(prox)
        if m and int(m.group(1)) == port:
            return DONE, "serve / → 이 볼트 문"
        others.append(m.group(1) if m else "다른 곳")
    if others:
        return NOT, "serve / 를 다른 문(%s)이 맡음 — 다른 볼트 서버면 그대로 둔다" % others[0]
    return NOT, "serve 없음"


def task_info():
    """예약 «외부뇌 서버»의 (동작 [{Execute, Arguments, WorkingDirectory}], 켜진 로그온 트리거가 있나) · 예약 없으면 ([], False) · 못 읽으면 (None, None)."""
    cmd = ("$t = Get-ScheduledTask -TaskName '%s' -ErrorAction SilentlyContinue; "
           "if ($t) { $l = @($t.Triggers | Where-Object { $_.Enabled -and $_.CimClass.CimClassName -eq 'MSFT_TaskLogonTrigger' }).Count -gt 0; "
           "@{a = @($t.Actions | Select-Object Execute,Arguments,WorkingDirectory); l = $l} | ConvertTo-Json -Compress -Depth 4 } "
           "else { '{\"a\":[],\"l\":false}' }" % TASK)
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd], capture_output=True, timeout=15, creationflags=NOWIN)
        d = json.loads(r.stdout.decode("utf-8", "replace").strip() or "{}")
        a = d["a"]
    except (OSError, subprocess.TimeoutExpired, ValueError, KeyError, TypeError):
        return None, None
    return (a if isinstance(a, list) else [a]), bool(d.get("l"))


def judge_task(actions, vault, logon=None):
    """logon = 켜진 로그온 트리거가 있나(None = 안 잼). 없으면 재부팅 뒤 로그인해도 15분 반복이 돌 때까지 서버가 없다(11-27 · 등록 대본보다 옛 예약)."""
    if actions is None:
        return UNKNOWN, "예약 작업을 못 읽음"
    if not actions:
        return NOT, "예약 «%s» 없음" % TASK
    want = os.path.normcase(os.path.join(conf.vault_of(vault), ".claude", "skills", "mobility", "scripts", "server.py"))
    for a in actions:
        if want in os.path.normcase(str((a or {}).get("Arguments") or "")):
            if logon is False:
                return NOT, "예약 «%s»에 로그온 트리거 없음(옛 등록) — 등록 대본(-Task)을 다시 돌린다" % TASK
            return DONE, "예약이 이 볼트 서버를 띄움"
    return NOT, "예약 «%s»이 다른 볼트를 가리킴 — 이 볼트로 바꾸려면 등록 대본(-Task)" % TASK


def judge_alive(port, timeout=5, tries=2):
    """문이 닫힘 = 안 됨 · 문은 열렸는데 늦음(PC 가 바쁨) = 모름 — 한 번 더 묻고 판정한다."""
    why = None
    for _ in range(tries):
        try:
            urllib.request.urlopen("http://127.0.0.1:%d/v1/ping" % port, timeout=timeout)
            return DONE, "서버 답함(200)"
        except urllib.error.HTTPError as e:
            return (DONE, "서버 답함(열쇠 없음 401)") if e.code == 401 else (NOT, "서버가 %d 로 답함" % e.code)
        except (TimeoutError, socket.timeout):
            why = (UNKNOWN, "127.0.0.1:%d 가 %g초 안에 답하지 않음(바쁨?)" % (port, timeout))
        except urllib.error.URLError as e:
            why = (UNKNOWN, "127.0.0.1:%d 가 늦음(바쁨?)" % port) if isinstance(e.reason, (TimeoutError, socket.timeout)) else (NOT, "127.0.0.1:%d 에 서버 없음" % port)
        except (OSError, ValueError):
            why = (NOT, "127.0.0.1:%d 에 서버 없음" % port)
    return why


AC = re.compile(r"\bAC\b[^:\n]*:\s*0x([0-9a-fA-F]+)")


def judge_power(text):
    """powercfg /qh SCHEME_CURRENT SUB_BUTTONS LIDACTION — AC 값 0 = 아무 것도 안 함(덮개 닫아도 서버가 돈다)."""
    m = AC.search(text or "")
    if not m:
        return UNKNOWN, "덮개 설정을 못 읽음(덮개 없는 PC 일 수 있음)"
    return (DONE, "전원 연결 때 덮개 닫아도 안 잠듦") if int(m.group(1), 16) == 0 else (NOT, "전원 연결 때 덮개를 닫으면 잠들거나 꺼짐")


def power_text():
    try:
        r = subprocess.run(["powercfg", "/qh", "SCHEME_CURRENT", "SUB_BUTTONS", "LIDACTION"], capture_output=True, timeout=10, creationflags=NOWIN)
        return r.stdout.decode("mbcs" if os.name == "nt" else "utf-8", "replace")
    except (OSError, subprocess.TimeoutExpired, LookupError):
        return ""


def measure(item, vault=None):
    if item == "tailscale":
        return (DONE, "설치됨") if ts_exe() else (NOT, "tailscale 실행 파일 없음")
    if item in ("login", "magicdns", "https"):
        if not ts_exe():
            return NOT, "Tailscale 이 없음(먼저 설치)"
        return {"login": judge_login, "magicdns": judge_magicdns, "https": judge_https}[item](ts_json("status"))
    if item == "serve":
        if not ts_exe():
            return NOT, "Tailscale 이 없음(먼저 설치)"
        return judge_serve(ts_json("serve", "status"), conf.port(vault))
    if item == "task":
        actions, logon = task_info()
        return judge_task(actions, vault, logon)
    if item == "alive":
        return judge_alive(conf.port(vault))
    if item == "power":
        return judge_power(power_text())
    return UNKNOWN, "모르는 항목 %s" % item


ITEMS = ("tailscale", "login", "magicdns", "https", "serve", "task", "alive", "power")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = sys.argv[1:]
    vault = args[args.index("--vault") + 1] if "--vault" in args else None
    if not args or args[0] not in ITEMS + ("all",):
        print(__doc__.strip())
        return UNKNOWN
    if args[0] == "all":
        for i in ITEMS:
            code, why = measure(i, vault)
            print("%s %s — %s" % ({DONE: "✓", NOT: "✗", UNKNOWN: "?"}[code], i, why))
        return 0
    code, why = measure(args[0], vault)
    print(why)
    return code


if __name__ == "__main__":
    sys.exit(main())
