"""mobility → 코어 감싸개(계획서 §6.1 · 11-17) — 서버·알림이 코어의 «계약 밖»(밑줄 이름 · 게이트 코어 내부 · 바깥 도구)을 부르는 곳은 여기 한 곳뿐.

계약 이름(fileops·roles·schedule·work·inbox·brain·claude_bin 공개 이름)은 server.py·alarms.py 가 바로 부른다 — 목록 = module.json uses_core(module-forge ⑬ 이 잰다).
여기서 감싸는 것
- 주제 기억 비우기(roles.forget_topics · 11-19 공개 함수로 옮김)
- 찾기(search.py · 게이트 코어) — 불러오기 한 곳(이름 INDEX_PATH·load_index·load_query_model·ranked·notes)
- 주제(topic.py) — 불러오기 한 곳
- Remote Control 상태(claude_bin.check · Claude Code bridge-pointer.json 은 server.rc_state) — 10분 담아 둠(프로세스를 띄움)
코어가 바뀌면 dist-sync contracts.py 가 module.json update_check(server_check 등)를 돌려 여기서 깨지는지 본다.
"""
import importlib.util
import os
import shutil
import sys
import threading
import time

MOD = os.path.dirname(os.path.abspath(__file__))
HERE = os.path.normpath(os.path.join(MOD, "..", "..", "..", "..", "3_시스템"))


def init(here):
    """서버가 제 3_시스템 자리를 준다(시험 사본은 임시 볼트 안)."""
    global HERE
    HERE = here
    if here not in sys.path:
        sys.path.insert(0, here)


# ───────── 주제·찾기 ─────────

def topics_reset():
    import roles
    roles.forget_topics()


def topic():
    import topic as t
    return t


def search_module():
    """search.py(게이트 코어)를 이름 brain_search 로 불러 돌려준다(한 번)."""
    mod = sys.modules.get("brain_search")
    if mod is None:
        spec = importlib.util.spec_from_file_location("brain_search", os.path.join(HERE, "search.py"))
        mod = importlib.util.module_from_spec(spec)
        sys.modules["brain_search"] = mod
        spec.loader.exec_module(mod)
    return mod


# ───────── Remote Control 쓸 수 있나(M9) ─────────
RC_TTL = 600
_rc = {"at": 0.0, "val": None, "job": None}
_rc_lock = threading.Lock()
CAN = {  # 코드 → 폰 단추 아래 한 줄
    "ok": "",
    "lapsed": "구독 해지 — PC 에서 다시 구독",
    "login": "로그인 안 됨 — PC 에서 Claude 로그인",
    "notsub": "구독 아님 — 구독 로그인만 씀",
    "limit": "사용량 한도 — 풀릴 때까지",
    "none": "PC 에 Claude 없음",
    "failed": "켜기 실패 — PC rc.log",
    "unknown": "모름 — PC 에서 확인",
}


def _measure(env):
    import claude_bin
    exe = claude_bin.newest()
    if not (os.path.isfile(exe) or shutil.which(exe)):
        return "none"
    st = claude_bin.check(env)
    return "ok" if st.get("ok") else code_of(st.get("kind"))


def code_of(k):
    """claude_bin 의 까닭(kind) → CAN 열쇠."""
    import claude_bin
    if k == claude_bin.LAPSED:
        return "lapsed"
    if k == claude_bin.LOGIN or k == getattr(claude_bin, "NO_LOGIN", None):
        return "login"
    if k == getattr(claude_bin, "NOT_SUB", None):
        return "notsub"
    if k == getattr(claude_bin, "LIMIT", None):
        return "limit"
    return "unknown"


def _refresh(env, test=False):
    try:
        v = "ok" if test else _measure(env)     # 시험(가짜 RC · BRAIN_RC_BIN) = 서버 rc_start 도 구독을 재지 않고 띄운다 → 같은 판정
    except Exception:  # noqa: BLE001 — 상태 재기가 서버를 죽이지 않게
        v = "unknown"
    with _rc_lock:
        _rc.update(at=time.time(), val=v, job=None)


def rc_can(env, wait=0.0, force=False, test=False):
    """구독으로 RC 를 켤 수 있나 → 코드(CAN 열쇠). 10분 안에 잰 값이면 그 값 · 오래됐으면 뒤에서 다시 재고 옛 값(처음이면 wait 초 기다림 · 그래도 없으면 unknown).
    test = 서버가 가짜 RC 로 도는 시험(rc_start 와 같은 판정 = 구독 안 잼) · 켜기 실패(rc_set)는 시험에서도 10분 남는다."""
    with _rc_lock:
        stale = force or _rc["val"] is None or time.time() - _rc["at"] > RC_TTL
        if stale and _rc["job"] is None:
            _rc["job"] = threading.Thread(target=_refresh, args=(env, test), daemon=True)
            _rc["job"].start()
        job, val = _rc["job"], _rc["val"]
    if job is not None and (val is None or force) and wait:
        job.join(wait)
        val = _rc["val"]
    return val or "unknown"


def rc_set(code):
    """켜기 결과로 안 값(409 의 까닭 · 일찍 끝남)을 바로 담는다."""
    with _rc_lock:
        _rc.update(at=time.time(), val=code)
