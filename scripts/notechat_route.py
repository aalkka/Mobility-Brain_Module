"""탭 곁창(볼트 클로드 · 노트 특화) 서버 길 — server.py 가 부른다(11-21).

탭(폰 보기 brain-source)은 requestUrl 로만 부를 수 있어(흘려받기 없음) «시작 → 조각 묻기»로 나눈다:
  POST /v1/notechat {note?, chip?, text?, resume?, kind?, view?, panes?}  → {job}   (panes = 보는 화면 칸들 · 11-22)   (모델 호출 = 이때만 · 사용량 = 누를 때만)
  POST /v1/notechat {note, chips: true}                         → {kind, why, chips}  (종류 짐작만 · 모델 없음 · 곁창이 열릴 때)
  GET  /v1/notechat?job=&from=N                                 → {events: [...], next, done}  (실행기 한 줄 JSON 그대로)
  POST /v1/notechat/stop {job}                                  → {ok}
  GET  /v1/notechat/past[?id=]                                  → 지난 대화 목록(엔진 대화 = PC 대화창과 같은 기록) · id 면 그 대화의 말들
실행기 = 볼트 3_시스템/ink/notechat.cjs(brain-base 가지 notechat 빌드 · 엔진 = 볼트 클로드 engine.ts 그대로).
도구 권한·기록 규칙은 실행기가 정한다(PC 대화창 묻기 모드보다 좁음 · 작업.md §3-2).
"""
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import threading
import time

try:
    import tabwork  # 탭 곁창 작업 모드(폰 지문 승인 · 11-22)
except ImportError:                 # 작업 모드 대본이 안 실린 판 = 늘 묻기
    tabwork = None

KINDS = ("풀이", "강의 필기", "그림", "실험 기록", "메모")
MAX_RUN = 2                 # 동시에 도는 대화(엔진) 수 — 탭 하나 + 여유
KEEP = 15 * 60              # 끝난 일 기록을 이만큼 들고 있음(탭이 늦게 물어도)
_NOWIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)
_LOCK = threading.Lock()
JOBS = {}
_MODE = {}                  # 대화 id → 지난 턴의 모드(바뀐 첫 턴에 앞머리 · 서버를 다시 켜면 비어 묻기로 봄)


class NoteChatError(Exception):
    def __init__(self, code, msg):
        super().__init__(msg)
        self.code, self.msg = code, msg


def _runner(vault):
    p = os.path.join(vault, "3_시스템", "ink", "notechat.cjs")
    if not os.path.isfile(p):
        raise NoteChatError(503, "노트 대화 실행기 없음")
    return p


def _node():
    return shutil.which("node") or "node"


def _env():
    """실행기 환경 — 대역 서버 시험은 CLAUDE_CONFIG_DIR 을 임시 자리로 두므로 BRAIN_NOTECHAT_CLAUDE_CONFIG 로 진짜 로그인 자리를 줄 수 있다(빈 값 = 기본 자리)."""
    env = dict(os.environ)
    if "BRAIN_NOTECHAT_CLAUDE_CONFIG" in env:
        v = env.pop("BRAIN_NOTECHAT_CLAUDE_CONFIG")
        if v:
            env["CLAUDE_CONFIG_DIR"] = v
        else:
            env.pop("CLAUDE_CONFIG_DIR", None)
    return env


def _args(vault, b, clean, hidden):
    a = ["--vault", vault]
    note = b.get("note")
    if note:
        rel, ab = clean(note)
        if os.path.splitext(rel)[1].lower() not in (".note", ".sdocx", ".md", ".pdf"):
            raise NoteChatError(400, "노트 형식 아님")
        if not os.path.isfile(ab) or hidden(ab):
            raise NoteChatError(404, "노트 없음")
        if os.path.splitext(rel)[1].lower() in (".note", ".sdocx"):
            a += ["--note", rel]
        else:
            a += ["--text-file-hint", rel]   # md·pdf 를 보며 부른 볼트 대화 — 실행기는 노트 특화 없이(아래 text 머리로 넘김)
    for k, rx, n in (("chip", r"^[^\x00-\x1f]{1,20}$", "chip"), ("kind", "^(" + "|".join(KINDS) + ")$", "kind"),
                     ("view", r"^\d{1,4}(,-?\d{1,6}(\.\d+)?,-?\d{1,6}(\.\d+)?)?$", "view"), ("resume", r"^[0-9a-f-]{36}$", "resume")):
        v = b.get(k)
        if v in (None, ""):
            continue
        if not isinstance(v, str) or not re.match(rx, v):
            raise NoteChatError(400, f"{k} 꼴이 잘못됨")
        a += ["--" + n, v]
    ps = b.get("panes")   # 보는 화면(분할 칸 · 11-22) — [{path, pos, cur, view}] · 실행기 --panes(머리 «보는 화면» + look)
    if ps:
        if not isinstance(ps, list) or len(ps) > 6:
            raise NoteChatError(400, "panes 꼴이 잘못됨")
        keep = []
        for q in ps:
            if not isinstance(q, dict) or not isinstance(q.get("path"), str) or not re.match(r"^[^\x00-\x1f]{1,16}$", str(q.get("pos", ""))):
                raise NoteChatError(400, "panes 꼴이 잘못됨")
            v = q.get("view") or ""
            if not isinstance(v, str) or not re.match(r"^[^\x00-\x1f]{0,80}$", v):
                raise NoteChatError(400, "panes view 꼴이 잘못됨")
            prel, pab = clean(q["path"])
            if not os.path.isfile(pab) or hidden(pab):
                continue                 # 없는 칸·숨김 칸은 뺌(머리에 안 실음)
            keep.append({"path": prel, "pos": q["pos"], "cur": bool(q.get("cur")), "view": v})
        if keep:
            a += ["--panes", json.dumps(keep, ensure_ascii=False)]
    t = b.get("text")
    if t:
        if not isinstance(t, str) or len(t) > 8000:
            raise NoteChatError(400, "글이 너무 김")
        a += ["--text", t]
    return a


def _warm_docs(vault, a):
    """곁창이 열릴 때 보이는 칸 중 PDF 의 문항 표를 미리(11-22 docitems --no-wait · 캐시 있으면 즉시 · 없으면 뒤에서) — 기다리지 않음."""
    if "--panes" not in a:
        return
    script = os.path.join(vault, "3_시스템", "ink", "docitems.py")
    if not os.path.isfile(script):
        return
    try:
        panes = json.loads(a[a.index("--panes") + 1])
    except (ValueError, IndexError):
        return
    for q in panes[:6]:
        if str(q.get("path", "")).lower().endswith(".pdf"):
            try:
                subprocess.Popen([sys.executable, script, os.path.join(vault, q["path"]), "--no-wait"], cwd=vault, stdin=subprocess.DEVNULL,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=_NOWIN)
            except OSError:
                pass


def chips(vault, b, clean, hidden):
    """곁창이 열릴 때 — 종류 짐작 + 칩(모델 호출 없음 · 0.3~2초)."""
    a = _args(vault, {**b, "chip": None, "text": None, "resume": None}, clean, hidden)
    _warm_docs(vault, a)
    if "--note" not in a:
        return {"kind": None, "chips": [], "why": "노트 아님"}
    r = subprocess.run([_node(), _runner(vault), *a, "--chips"], capture_output=True, timeout=60, cwd=vault, creationflags=_NOWIN, env=_env())
    out = {"kind": None, "chips": [], "why": ""}
    for ln in r.stdout.decode("utf-8", "replace").splitlines():
        try:
            j = json.loads(ln)
        except ValueError:
            continue
        if j.get("t") == "kind":
            out.update(kind=j.get("kind"), why=j.get("why"))
        if j.get("t") == "chips":
            out["chips"] = j.get("chips") or []
    return out


def _gc():
    now = time.time()
    for k in [k for k, j in JOBS.items() if j["done"] and now - j["end"] > KEEP]:
        JOBS.pop(k, None)


def start(vault, b, clean, hidden):
    if b.get("chips"):
        return chips(vault, b, clean, hidden)
    a = _args(vault, b, clean, hidden)
    if "--text-file-hint" in a and "--panes" in a:   # 보는 화면을 보낸 새 탭 = 머리는 실행기가(«① 보는 파일» + «② 보는 화면»)
        i = a.index("--text-file-hint")
        del a[i:i + 2]
    if "--text-file-hint" in a:          # 옛 탭 — md·pdf 보며 부름 = 볼트 대화 그대로(보는 파일 한 줄만 글 앞에)
        i = a.index("--text-file-hint")
        rel = a[i + 1]
        del a[i:i + 2]
        t = b.get("text") or ""
        if "--text" in a:
            a[a.index("--text") + 1] = f"[맥락 — 탭에서 보는 파일 · 경로는 작업 폴더(이 볼트) 안]\n① 보는 파일: {rel}\n\n{t}"
    if "--note" not in a and not b.get("text"):
        raise NoteChatError(400, "물을 글 없음")
    sid = b.get("resume") or ""          # 작업 모드(11-22) = 폰 지문 승인을 잰 대화에만 · 바뀐 첫 턴엔 PC 와 같은 앞머리
    m = tabwork.mode(vault, sid) if (sid and tabwork) else "ask"
    a += (["--work"] if m == "work" else []) + (["--mode-note"] if sid and m != _MODE.get(sid, "ask") else [])
    if sid:
        _MODE[sid] = m
    with _LOCK:
        _gc()
        if sum(1 for j in JOBS.values() if not j["done"] and not j.get("answered")) >= MAX_RUN:
            raise NoteChatError(429, "이미 묻는 중")
        jid = secrets.token_hex(8)
        p = subprocess.Popen([_node(), _runner(vault), *a], stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL,
                             cwd=vault, creationflags=_NOWIN, env=_env())
        job = {"proc": p, "events": [], "done": False, "start": time.time(), "end": 0, "err": ""}
        JOBS[jid] = job

    def pump():
        for raw in p.stdout:
            try:
                e = json.loads(raw.decode("utf-8", "replace"))
            except ValueError:
                continue
            job["events"].append(e)
            if e.get("t") in ("done", "error"):
                job["answered"] = True       # 답은 끝 — 실행기 프로세스는 몇 초 더 살 수 있다(엔진 닫기) · 탭은 여기서 끝으로 본다
        p.wait()
        job["err"] = p.stderr.read().decode("utf-8", "replace")[-400:]
        if not any(e.get("t") in ("done", "error") for e in job["events"]):
            job["events"].append({"t": "error", "why": f"실행기가 끝남({p.returncode}) {job['err'][-200:]}"})
        job["done"], job["end"] = True, time.time()

    threading.Thread(target=pump, daemon=True).start()
    return {"job": jid}


def poll(q):
    j = JOBS.get(q.get("job") or "")
    if not j:
        raise NoteChatError(404, "없는 일")
    try:
        frm = max(0, int(q.get("from") or 0))
    except ValueError:
        frm = 0
    ev = j["events"][frm:]
    return {"events": ev, "next": frm + len(ev), "done": (j["done"] or j.get("answered", False)) and frm + len(ev) >= len(j["events"])}


def stop(b):
    j = JOBS.get(b.get("job") or "")
    if j and not j["done"]:
        try:
            j["proc"].kill()
        except OSError:
            pass
    return {"ok": bool(j)}


# ───────── 지난 대화(엔진 대화 = PC 대화창 «지난 대화»와 같은 기록) ─────────
PRE = re.compile(r"^\[(맥락 — |작업 모드로 바뀜|일 모드로 바뀜|묻기 모드로 바뀜|지난 대화 색인|주제 카드 — |고른 그림|고른 상자의 글자)")


def _proj(vault):
    root = os.path.join(_env().get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude"), "projects")
    return os.path.join(root, re.sub(r"[^a-zA-Z0-9]", "-", vault))


def _typed(content):
    """사용자 말 — 앞에 붙인 맥락 머리를 떼고 쓴 글만(past.ts 와 같은 규칙) · 그림은 [그림]."""
    if isinstance(content, list):
        txt = "\n".join(c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text")
        imgs = sum(1 for c in content if isinstance(c, dict) and c.get("type") == "image")
        if not txt and not imgs:
            return None                        # 도구 결과
    else:
        txt, imgs = str(content or ""), 0
    if txt.startswith("<local-command-") or txt.startswith("<command-"):
        return None
    note = None
    if PRE.match(txt) and "\n\n" in txt:
        head, txt = txt.split("\n\n", 1)
        m = re.search(r"^[①-⑤] 보는 파일: (.+)$", head, re.M)
        note = m.group(1) if m else None
    return {"text": txt.strip(), "note": note, "images": imgs}


def past(vault, q):
    d = _proj(vault)
    sid = q.get("id")
    if sid:
        if not re.match(r"^[0-9a-f-]{36}$", sid):
            raise NoteChatError(400, "id 꼴")
        f = os.path.join(d, sid + ".jsonl")
        if not os.path.isfile(f):
            raise NoteChatError(404, "없는 대화")
        turns = []
        with open(f, encoding="utf-8", errors="replace") as h:
            for ln in h:
                try:
                    r = json.loads(ln)
                except ValueError:
                    continue
                if r.get("isSidechain") or r.get("isMeta"):
                    continue
                m = r.get("message") or {}
                if r.get("type") == "user":
                    u = _typed(m.get("content"))
                    if u and u["text"]:
                        turns.append({"role": "user", "text": u["text"][:4000], "note": u["note"]})
                elif r.get("type") == "assistant":
                    t = "".join(c.get("text", "") for c in (m.get("content") or []) if isinstance(c, dict) and c.get("type") == "text")
                    t = re.sub(r"^\s*〔[^〕]*〕\s*$", "", t, flags=re.M).strip()
                    if t:
                        if turns and turns[-1]["role"] == "assistant":
                            turns[-1]["text"] += "\n\n" + t
                        else:
                            turns.append({"role": "assistant", "text": t[:12000]})
        return {"id": sid, "turns": turns[-40:]}
    items = []
    try:
        fs = sorted((os.path.join(d, f) for f in os.listdir(d) if f.endswith(".jsonl")), key=os.path.getmtime, reverse=True)[:60]
    except OSError:
        fs = []
    for f in fs:
        ent, first, note = None, None, None
        with open(f, encoding="utf-8", errors="replace") as h:
            for i, ln in enumerate(h):
                if i > 60:
                    break
                try:
                    r = json.loads(ln)
                except ValueError:
                    continue
                if r.get("type") == "user" and first is None and not r.get("isMeta"):
                    u = _typed((r.get("message") or {}).get("content"))
                    if u and u["text"]:
                        first, note = u["text"], u["note"]
                        # 엔진 대화(PC 대화창·탭 곁창 = engine.ts sendUser)만 — 데스크톱 앱·원격·빅보스 세션(origin·clientPlatform 이 붙음 · 11-21 잼)은 뺌
                        ent = r.get("entrypoint") == "sdk-cli" and r.get("promptSource") == "sdk" and "origin" not in r and "clientPlatform" not in r
                        break
        if not ent or not first:
            continue
        items.append({"id": os.path.basename(f)[:-6], "at": int(os.path.getmtime(f)), "title": first.splitlines()[0][:80], "note": note})
        if len(items) >= 20:
            break
    return {"items": items}
