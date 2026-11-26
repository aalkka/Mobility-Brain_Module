#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""로그인 전 서버(세션 0 · S4U 예약) ↔ 사용자 서버 바꾸기 — 자동 재시작 대비책 C(설계 제작자 작업 노트 §12).

왜: 재시작 뒤 자동 로그인(ARSO)이 안 된 날에도 폰이 닿도록 «외부뇌 서버(로그인 전)»을 S4U(로그온 여부 무관 · 비밀번호 저장 안 함)로
부팅 때 띄운다(11-20 사용자 관리자 시험: 세션 0 에서 열쇠 파일·Claude 로그인 파일 읽힘 · 127.0.0.1 문 열림 · api.anthropic.com 닿음).
로그인하면 그 서버가 문을 쥐고 있어 «로그온 때» 예약의 사용자 서버가 안 뜬다 → 세션 0 서버는 화면 일(창·알림 띄우기)을 못 하므로
로그인 뒤에는 사용자 세션 서버로 바꾼다. 자동 재시작 뒤 다시 세팅(after_restart.json «mobility.server»)이 부른다.

  py -3 .claude/skills/mobility/scripts/server_swap.py check     종료 0 = 사용자 세션에서 돎 · 1 = 세션 0 에서만 돎 · 2 = 안 돎
  py -3 .claude/skills/mobility/scripts/server_swap.py swap      예약 «외부뇌 서버»를 바로 돌림 → 뜬 서버가 시작할 때 세션 0 서버를 넘겨받음(take_over)
넘겨받기 길은 둘이다(재시작 기록 유무와 무관): ① server.py 가 시작할 때 take_over() — 사용자 세션이면 세션 0 서버를 끄고 문을 엶
② 예약 «외부뇌 서버»의 로그온 트리거(server-setup.ps1 -Task) — ARSO 든 손 로그인이든 로그온하면 사용자 세션 서버가 뜸(15분 반복도 그물).
  py -3 .claude/skills/mobility/scripts/server_swap.py task-xml  S4U 예약 «외부뇌 서버(로그인 전)» XML 을 보임(등록은 관리자 PowerShell 에서 한 번 · 사용자)
"""
import ctypes
import os
import re
import subprocess
import sys
import time

NOWIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)
MOD = os.path.dirname(os.path.abspath(__file__))
VAULT = os.path.normpath(os.path.join(MOD, "..", "..", ".."))
SERVER = re.compile(r"mobility[\\/]+scripts[\\/]+server\.py", re.I)
TASK, TASK_S4U = "외부뇌 서버", "외부뇌 서버(로그인 전)"


def session_of(pid):
    s = ctypes.c_uint()
    return s.value if ctypes.windll.kernel32.ProcessIdToSessionId(pid, ctypes.byref(s)) else None


def servers():
    """[(pid, 세션)] 이 볼트 서버 프로세스(pyw/python · 명령 줄에 mobility/scripts/server.py)"""
    import psutil
    out = []
    for p in psutil.process_iter(["name", "cmdline"]):
        try:
            if (p.info["name"] or "").lower() in ("pyw.exe", "pythonw.exe", "python.exe", "py.exe") and SERVER.search(" ".join(p.info["cmdline"] or [])):
                out.append((p.pid, session_of(p.pid)))
        except Exception:  # noqa: BLE001
            pass
    return out


def decide(rows, me):
    """순수 판정 — rows = [(pid, 세션)] · me = 지금 세션 → (종료 코드, 세션 0 pid 목록)"""
    zero = [pid for pid, s in rows if s == 0]
    mine = [pid for pid, s in rows if s == me and s != 0]
    if mine:
        return 0, zero
    if zero:
        return 1, zero
    return 2, []


def victims(rows, me):
    """순수 판정 — 넘겨받을 세션 0 서버 pid · 나도 세션 0(로그인 전 서버 자신)이거나 세션을 모르면 []"""
    if not me:
        return []
    return [pid for pid, s in rows if s == 0]


def take_over(timeout=15):
    """server.py 가 문을 열기 전에 부름 — 사용자 세션이면 세션 0 서버를 끄고 끝나길 기다림 · 끈 pid 목록"""
    import psutil
    me = session_of(os.getpid())
    vs = [p for p in victims(servers(), me) if p != os.getpid()]
    procs = []
    for pid in vs:
        try:
            q = psutil.Process(pid)
            q.terminate()
            procs.append(q)
        except Exception:  # noqa: BLE001
            pass
    if procs:
        psutil.wait_procs(procs, timeout=timeout)
    return vs


def check():
    rc, zero = decide(servers(), session_of(os.getpid()))
    print({0: "사용자 세션에서 돎", 1: "세션 0(로그인 전 서버)에서만 돎", 2: "안 돎"}[rc] + (" · 세션 0 %d개" % len(zero) if zero and rc == 0 else ""))
    return rc


def swap():
    """예약 «외부뇌 서버»를 바로 돌림 → 그 서버가 take_over 로 세션 0 서버를 넘겨받음 · 60초 안 사용자 세션에서 뜨나 잼"""
    rc, _zero = decide(servers(), session_of(os.getpid()))
    if rc == 0:
        print("바꿀 것 없음")
        return 0
    subprocess.run(["schtasks", "/run", "/tn", TASK], capture_output=True, timeout=30, creationflags=NOWIN)
    end = time.time() + 60
    while time.time() < end:
        if decide(servers(), session_of(os.getpid()))[0] == 0:
            print("바꿈")
            return 0
        time.sleep(3)
    print("사용자 서버가 안 뜸")
    return 1


def task_xml():
    py = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "pyw.exe")
    me = os.environ.get("USERDOMAIN", "") + "\\" + os.environ.get("USERNAME", "")
    return ('<?xml version="1.0" encoding="UTF-16"?><Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">'
            "<Triggers><BootTrigger><Delay>PT30S</Delay></BootTrigger></Triggers>"
            "<Principals><Principal id=\"Author\"><UserId>%s</UserId><LogonType>S4U</LogonType><RunLevel>LeastPrivilege</RunLevel></Principal></Principals>"
            "<Settings><MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy><DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>"
            "<StopIfGoingOnBatteries>false</StopIfGoingOnBatteries><ExecutionTimeLimit>PT0S</ExecutionTimeLimit></Settings>"
            "<Actions Context=\"Author\"><Exec><Command>%s</Command><Arguments>-3 \"%s\"</Arguments><WorkingDirectory>%s</WorkingDirectory></Exec></Actions></Task>"
            ) % (me, py, os.path.join(MOD, "server.py"), VAULT)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    a = sys.argv[1:2] or ["check"]
    if a[0] == "selftest":
        T = [([], 1, 2), ([(10, 1)], 1, 0), ([(10, 0)], 1, 1), ([(10, 0), (11, 1)], 1, 0), ([(10, 2)], 1, 2)]
        bad = [t for t in T if decide(t[0], t[1])[0] != t[2]]
        V = [([(10, 0)], 1, [10]), ([(10, 0)], 0, []), ([(10, 0)], None, []), ([(10, 1), (11, 0), (12, 0)], 1, [11, 12]), ([(10, 1)], 1, [])]
        bad += [v for v in V if victims(v[0], v[1]) != v[2]]
        print("selftest %d/%d" % (len(T) + len(V) - len(bad), len(T) + len(V)))
        sys.exit(1 if bad else 0)
    sys.exit({"check": check, "swap": swap, "task-xml": lambda: print(task_xml()) or 0}[a[0]]())
