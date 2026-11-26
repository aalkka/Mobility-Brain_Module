"""탭 곁창 작업 모드 — 폰 지문 승인으로 그 대화 하나만 켠다(11-22 · 설계 제작자 작업 노트).

server.py 가 부른다:
  POST /v1/tabwork/ask {session, why}  → 명령 승인 요청 하나(run «tabwork») · {state: waiting, expires}
  GET  /v1/tabwork?session=            → {state: ask|waiting|work|rejected|expired|failed, until?, expires?, why?}
  POST /v1/tabwork/end {session}       → 그 대화의 표를 거둠(대기 중이면 명령 요청도 닫아 폰 알림을 걷음)
notechat_route 는 mode(vault, session) 만 본다(work 면 실행기에 --work).

믿음: 켜는 근거는 적용기 장부(3_시스템/_index/approve/ledger.jsonl)의 run-start 한 줄뿐이다 — 적용기(게이트 코어 approve.py)가
폰 Keystore 서명을 잰 뒤에만 적는다. 이 파일·서버·탭이 쓰는 기록(_index/tabwork)은 «무엇을 물었나»일 뿐 켜는 근거가 아니다.
서명된 명령 = 아무것도 안 하는 한 줄(Write-Output) — 명령 글에 대화 id·nonce 가 들어 서명 글이 그 대화 하나를 덮는다.
시한: 대기 10분(넘으면 만료 · 명령 요청도 닫음) · 켠 뒤 30분 또는 end 까지. 승인 시각이 대기 10분 밖이면(폰이 늦게 서명) 안 켬.
"""
import json
import os
import re
import secrets
import subprocess
import sys
import threading
import time
import unicodedata

RUN = 'tabwork'
ASK_TTL = 10 * 60          # 폰 승인 대기 상한(초)
WORK_TTL = 30 * 60         # 켠 뒤 상한(초)
MAX_WAIT = 3               # 함께 기다리는 요청 수 상한(폰 알림 쌓임 막기)
PURPOSE = '탭 대화 작업 모드'
SID = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
_NOWIN = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
_LOCK = threading.Lock()


class TabWorkError(Exception):
    def __init__(self, code, msg):
        super().__init__(msg)
        self.code, self.msg = code, msg


def _sys(vault):
    return os.path.join(vault, '3_시스템')


def _bb(vault):
    return os.environ.get('BIGBOSS_STATE') or os.path.join(_sys(vault), '_index', 'bigboss')


def _cmd_dir(vault):
    return os.path.join(_bb(vault), RUN, 'commands')


def _approve_ledger(vault):
    return os.path.join(os.environ.get('APPROVE_STATE') or os.path.join(_sys(vault), '_index', 'approve'), 'ledger.jsonl')


def _approver(vault):
    return os.path.join(_sys(vault), 'hooks', 'approve', 'approve.py')


def _tw(vault):
    return os.path.join(_sys(vault), '_index', 'tabwork')


def _approve(vault, *args):
    p = _approver(vault)
    if not os.path.isfile(p):
        return {'ok': False, 'why': '적용기 없음'}
    try:
        r = subprocess.run([sys.executable, p, *args], capture_output=True, timeout=60, creationflags=_NOWIN, cwd=vault, stdin=subprocess.DEVNULL)
        return json.loads(r.stdout.decode('utf-8', 'replace').strip().splitlines()[-1])
    except (OSError, subprocess.TimeoutExpired, ValueError, IndexError) as e:
        return {'ok': False, 'why': f'적용기를 못 돌림 ({type(e).__name__})'}


def _save(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(obj, f, ensure_ascii=False)
    os.replace(tmp, path)


def _load(path):
    try:
        with open(path, encoding='utf-8') as f:
            j = json.load(f)
        return j if isinstance(j, dict) else None
    except (OSError, ValueError):
        return None


def _note(vault, ev, **kw):
    os.makedirs(_tw(vault), exist_ok=True)
    with open(os.path.join(_tw(vault), 'ledger.jsonl'), 'a', encoding='utf-8', newline='\n') as f:
        f.write(json.dumps({'at': int(time.time()), 'ev': ev, **kw}, ensure_ascii=False) + '\n')


def expected_cmd(session, nonce):
    """서명되는 명령 글 — 아무것도 안 함 · 대화 id·nonce 가 서명 글에 들어간다."""
    return f"Write-Output 'tab-work {session} {nonce}'"


def _one_line(t, cap):
    t = ' '.join(unicodedata.normalize('NFC', str(t or '')).split())
    t = ''.join(c for c in t if not unicodedata.category(c).startswith('C'))
    return t if len(t) <= cap else t[:cap - 1].rstrip() + '…'


def _reason(session, why):
    head = f'대화 {session[:8]} · {WORK_TTL // 60}분 또는 대화 끝까지'
    w = _one_line(why, 80 - len(head) - 3)
    return f'{head} · {w}' if w else head


def _check_sid(s):
    if not isinstance(s, str) or not SID.match(s):
        raise TabWorkError(400, 'session 꼴이 잘못됨')
    return s


def _records(vault, session=None):
    d = os.path.join(_tw(vault), 'req')
    try:
        names = os.listdir(d)
    except OSError:
        return []
    out = []
    for n in names:
        if not re.fullmatch(r'[0-9a-f]{16}\.json', n):
            continue
        j = _load(os.path.join(d, n))
        if j and (session is None or j.get('session') == session):
            j['_path'] = os.path.join(d, n)
            out.append(j)
    return sorted(out, key=lambda j: j.get('added_at') or 0)


def _req(vault, nn):
    d = _cmd_dir(vault)
    try:
        for n in os.listdir(d):
            m = re.match(r'(\d+)-.*\.json$', n)
            if m and int(m.group(1)) == nn:
                return _load(os.path.join(d, n))
    except OSError:
        pass
    return None


def _signed_at(vault, nn):
    """적용기 장부의 run-start(폰 서명을 잰 뒤에만 적힘) 시각 · 없으면 None."""
    try:
        with open(_approve_ledger(vault), encoding='utf-8') as f:
            for ln in f:
                if '"run-start"' not in ln or f'"{RUN}"' not in ln:
                    continue
                try:
                    j = json.loads(ln)
                except ValueError:
                    continue
                if j.get('ev') == 'run-start' and j.get('run') == RUN and j.get('id') == nn:
                    return int(j.get('at') or 0)
    except OSError:
        pass
    return None


def _judge(vault, rec, now):
    """기록 하나 → (state, extra) · 대기 만료면 명령 요청을 닫는다."""
    nn, added = rec.get('nn'), int(rec.get('added_at') or 0)
    if not isinstance(nn, int):
        return 'failed', {'why': '기록 꼴이 다름'}
    req = _req(vault, nn)
    signed = _signed_at(vault, nn)
    cmd_ok = bool(req) and req.get('cmd') == expected_cmd(rec.get('session', ''), rec.get('nonce', ''))
    if rec.get('state') == 'ended':
        return 'ask', {'why': '대화 끝'}
    if signed is not None and cmd_ok:
        if signed - added > ASK_TTL:
            return 'expired', {'why': '승인이 대기 시한 뒤에 옴'}
        until = signed + WORK_TTL
        if now < until:
            return 'work', {'until': until}
        return 'expired', {'why': f'작업 모드 {WORK_TTL // 60}분이 지남'}
    st = (req or {}).get('state')
    if st == 'rejected':
        return 'rejected', {'why': (req or {}).get('why_rejected') or '폰에서 거절'}
    if st == 'pending':
        if now - added > ASK_TTL:
            _approve(vault, 'reject-cmd', RUN, str(nn), '--why', '탭 작업 모드 대기 만료')
            rec['state'] = 'expired'
            _save(rec['_path'], {k: v for k, v in rec.items() if not k.startswith('_')})
            _note(vault, 'expire', session=rec.get('session'), nonce=rec.get('nonce'), nn=nn)
            return 'expired', {'why': f'폰 승인 대기 {ASK_TTL // 60}분이 지남'}
        return 'waiting', {'expires': added + ASK_TTL}
    if rec.get('state') == 'expired':
        return 'expired', {'why': f'폰 승인 대기 {ASK_TTL // 60}분이 지남'}
    return 'failed', {'why': (req or {}).get('refused') or f'승인 요청 상태 {st}'}


def status(vault, q):
    session = _check_sid(q.get('session'))
    recs = _records(vault, session)
    if not recs:
        return {'ok': True, 'state': 'ask'}
    st, extra = _judge(vault, recs[-1], time.time())
    return {'ok': True, 'state': st, **extra}


def mode(vault, session):
    """notechat_route 가 부름 — 'work' 면 그 대화를 작업 모드로 돌림 · 못 재면 'ask'(안전 쪽)."""
    try:
        return 'work' if status(vault, {'session': session})['state'] == 'work' else 'ask'
    except Exception:
        return 'ask'


def ask(vault, b):
    session = _check_sid(b.get('session'))
    with _LOCK:
        now = time.time()
        recs = _records(vault, session)
        if recs:
            st, extra = _judge(vault, recs[-1], now)
            if st in ('waiting', 'work'):
                return {'ok': True, 'state': st, **extra}
        waiting = sum(1 for r in _records(vault) if r.get('state') == 'waiting' and now - int(r.get('added_at') or 0) <= ASK_TTL
                      and _judge(vault, r, now)[0] == 'waiting')
        if waiting >= MAX_WAIT:
            raise TabWorkError(429, f'폰 승인을 기다리는 요청이 이미 {MAX_WAIT}개')
        nonce = secrets.token_hex(8)
        d = _cmd_dir(vault)
        os.makedirs(d, exist_ok=True)
        nums = [int(m.group(1)) for m in (re.match(r'(\d+)-', n) for n in os.listdir(d)) if m]
        nn = max(nums, default=0) + 1
        while True:
            path = os.path.join(d, f'{nn:02d}-tab-work.json')
            try:
                fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                break
            except FileExistsError:
                nn += 1
        req = {'purpose': PURPOSE, 'reason': _reason(session, b.get('why')), 'shell': 'powershell', 'cwd': os.path.abspath(vault),
               'cmd': expected_cmd(session, nonce), 'timeout': 60, 'by': 'tab-work', 'added': time.strftime('%Y-%m-%d %H:%M:%S'),
               'added_at': int(now), 'state': 'pending'}
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(req, f, ensure_ascii=False)
        chk = _approve(vault, 'check-cmd', RUN, str(nn))
        if not chk.get('ok'):
            try:
                os.remove(path)
            except OSError:
                pass
            raise TabWorkError(503, '승인 요청을 못 올림: ' + str(chk.get('why') or ''))
        rec = {'session': session, 'nonce': nonce, 'nn': nn, 'why': _one_line(b.get('why'), 200), 'added_at': int(now), 'state': 'waiting'}
        _save(os.path.join(_tw(vault), 'req', nonce + '.json'), rec)
        _note(vault, 'ask', session=session, nonce=nonce, nn=nn)
        return {'ok': True, 'state': 'waiting', 'expires': int(now) + ASK_TTL}


def end(vault, b):
    session = _check_sid(b.get('session'))
    with _LOCK:
        recs = _records(vault, session)
        if not recs:
            return {'ok': True, 'state': 'ask'}
        rec = recs[-1]
        st, _ = _judge(vault, rec, time.time())
        if st == 'waiting':
            _approve(vault, 'reject-cmd', RUN, str(rec['nn']), '--why', '탭 대화 끝')
        if rec.get('state') != 'ended':
            rec['state'], rec['ended_at'] = 'ended', int(time.time())
            _save(rec['_path'], {k: v for k, v in rec.items() if not k.startswith('_')})
            _note(vault, 'end', session=session, nonce=rec.get('nonce'), nn=rec.get('nn'), was=st)
        return {'ok': True, 'state': 'ask'}
