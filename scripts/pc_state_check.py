"""바깥 설정 PC 항목 시험 — 항목마다 «된» 자료와 «안 된» 자료에서 0·1(·2)이 갈리는가 + 이 PC 에서 진짜로 한 번(읽기만).
    py -3 .claude/skills/mobility/scripts/pc_state_check.py
진짜 PC 설정(예약·serve·덮개)은 바꾸지 않는다 — 안 된 쪽은 가짜 자료와 빈 문·다른 볼트 자리로 만든다.
"""
# mf:allow-path-file — 시험 픽스처: 임시 볼트 자리를 만들고 잰다(본 볼트 안 건드림)
import http.server
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading

MOD = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, MOD)
import conf  # noqa: E402
import pc_state as P  # noqa: E402

fails = []


def ok(name, cond, extra=""):
    print(("통과 " if cond else "실패 ") + name + (" — %s" % extra if extra else ""), flush=True)
    if not cond:
        fails.append(name)


def split(name, done, not_done, unknown=None):
    """된 자료 = 0 · 안 된 자료 = 1 · (있으면) 못 읽음 = 2"""
    got = (done[0], not_done[0]) + ((unknown[0],) if unknown else ())
    want = (0, 1) + ((2,) if unknown else ())
    ok("%s 0·1%s 갈림" % (name, "·2" if unknown else ""), got == want, "%s · %s" % (got, not_done[1]))


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


class H401(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(401)
        self.end_headers()

    def log_message(self, *a):
        pass


class HSlow(H401):
    def do_GET(self):
        import time
        time.sleep(1.5)
        H401.do_GET(self)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    run = {"BackendState": "Running", "CurrentTailnet": {"MagicDNSEnabled": True}, "CertDomains": ["pc.example.ts.net"]}
    off = {"BackendState": "NeedsLogin", "CurrentTailnet": {"MagicDNSEnabled": False}, "CertDomains": None}
    split("로그인", P.judge_login(run), P.judge_login(off), P.judge_login(None))
    split("MagicDNS", P.judge_magicdns(run), P.judge_magicdns(off), P.judge_magicdns({"BackendState": "Running"}))
    split("HTTPS", P.judge_https(run), P.judge_https(off), P.judge_https(None))
    sv = lambda p: {"TCP": {"443": {"HTTPS": True}}, "Web": {"pc.example.ts.net:443": {"Handlers": {"/": {"Proxy": "http://127.0.0.1:%d" % p}}}}}  # noqa: E731
    split("serve", P.judge_serve(sv(8377), 8377), P.judge_serve(sv(8399), 8377), P.judge_serve(None, 8377))
    ok("serve 없음 = 안 됨", P.judge_serve({}, 8377)[0] == 1)
    ok("serve 다른 문 = 그 문을 까닭에", "8399" in P.judge_serve(sv(8399), 8377)[1])
    tmp = tempfile.mkdtemp(prefix="pcstate-")
    mine = os.path.join(tmp, "v1")
    other = os.path.join(tmp, "v2")
    act = lambda v: [{"Execute": "pyw.exe", "Arguments": '-3 "%s"' % os.path.join(v, ".claude", "skills", "mobility", "scripts", "server.py"), "WorkingDirectory": v}]  # noqa: E731
    split("예약", P.judge_task(act(mine), mine), P.judge_task(act(other), mine), P.judge_task(None, mine))
    ok("예약 없음 = 안 됨", P.judge_task([], mine)[0] == 1)
    ok("로그온 트리거 없음(옛 등록) = 안 됨 · 있음 = 됨", P.judge_task(act(mine), mine, False)[0] == 1 and "로그온" in P.judge_task(act(mine), mine, False)[1]
       and P.judge_task(act(mine), mine, True)[0] == 0)
    port = free_port()
    srv = http.server.HTTPServer(("127.0.0.1", port), H401)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    split("서버 답함", P.judge_alive(port), P.judge_alive(free_port()))
    srv.shutdown()
    slow = http.server.ThreadingHTTPServer(("127.0.0.1", free_port()), HSlow)
    threading.Thread(target=slow.serve_forever, daemon=True).start()
    ok("서버가 늦음 = 모름(2) · 닫힌 문과 갈림", P.judge_alive(slow.server_address[1], timeout=0.3)[0] == 2, P.judge_alive(slow.server_address[1], timeout=0.3)[1])
    slow.shutdown()
    ko = "    현재 AC 전원 설정 색인: 0x%08x\n    현재 DC 전원 설정 색인: 0x00000002\n"
    en = "    Current AC Power Setting Index: 0x%08x\n"
    split("덮개(한국어)", P.judge_power(ko % 0), P.judge_power(ko % 1), P.judge_power("전원 구성표 GUID: x\n"))
    split("덮개(영어)", P.judge_power(en % 0), P.judge_power(en % 2))
    # 문 번호 한 곳 — config «port» → 없으면 조리법 기본값 · 틀린 값은 기본값
    os.makedirs(os.path.join(mine, "3_시스템", "_index", "server"))
    cfg = conf.config_path(mine)
    ok("문 번호 — config 없음 = 조리법 기본값", conf.port(mine) == conf.default("port"))
    with open(cfg, "w", encoding="utf-8") as f:
        json.dump({"port": 8399}, f)
    ok("문 번호 — config 값", conf.port(mine) == 8399)
    with open(cfg, "w", encoding="utf-8") as f:
        json.dump({"port": "8399"}, f)
    ok("문 번호 — 글자 값 = 기본값", conf.port(mine) == conf.default("port"))
    # 이 PC 에서 진짜(읽기만) — 대본 종료 코드가 0·1·2 안이고 · 다른 볼트 자리면 예약은 1
    real = {}
    for i in P.ITEMS:
        r = subprocess.run([sys.executable, os.path.join(MOD, "pc_state.py"), i], capture_output=True, timeout=60,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        real[i] = r.returncode
    ok("이 PC 진짜 재기 — 종료 0·1·2 안", set(real.values()) <= {0, 1, 2}, json.dumps(real))
    r = subprocess.run([sys.executable, os.path.join(MOD, "pc_state.py"), "task", "--vault", other], capture_output=True, timeout=60,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    ok("이 PC 진짜 재기 — 다른 볼트 자리 = 예약 1", r.returncode == 1, r.stdout.decode("utf-8", "replace").strip())
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)
    print("== 실패 %d건" % len(fails))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
