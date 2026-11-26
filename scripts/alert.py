"""알림 도구 alert — 분류가 정한 «알림» 동작을 알림 사건으로 낸다(범용 도구 셋 S9 · 2026-11-18 · 설계 = 제작자 작업 노트 §7 · §8.6 · §11).
mobility 모듈 몫(사용자 11-18 «알림도구를 mobility 주관으로, 나머지는 본체» · 옛 자리 3_시스템/alert.py). 본체는 분류·태그·판정 기록·넘김 장부까지 —
분류(sort.alert_now)와 15분 확인(collect-tick act_tick)은 mobility 가 켜져 있을 때만 이 대본을 부른다. 수집 창 «일어난 일»은 넘김 장부를 직접 읽는다
(collect_desk sort_alert_rows · 이 도구의 장부 알림.jsonl 이 있으면 때·폰 칸을 더함) — mobility 가 없어도 데스크톱에 보인다.

울릴지·급한지는 분류가 정한다(판정 기록의 동작 {"알림": {"때", "급함"}} · 기록의 «급함» 칸 · Claude 가 같은 호출에서 채울 수 있음).
이 도구는 때·중복·전달만 한다.
  읽는 것 = 넘김 장부(_index/sort/넘김.jsonl)의 알림 줄(분류는 갈래가 바뀔 때만 넘긴다) · 커서·울린 것 = _index/sort/알림.json.
  때: 바로 = 지금 · 아침 = 다음 잘_시간 끝(기본 08:00) · 묶음 HH:MM = 다음 그 시각. 잘 시간(노트 알림-설정 «잘_시간» · 기본 23:00~08:00)이면
      mobility alarms.awake() 로 아침 — 급함이면 건너뛰고 지금.
  중복: 같은 대상·같은 갈래는 한 번 · 갈래가 오르면 다시(순위 = 어댑터 rank · 없으면 태그 사전 가족 차례) · 내리면 안 울림 ·
        순위가 없는 체계는 처음 보는 갈래만 · 대상이 분류 상태에서 사라지면 잊음(다시 나오면 새것 — 매진 뒤 다시 나온 표).
  한 번 돌림에 같은 체계 알림이 여럿 = 같은 때에 1초씩 차례(순위 높은 것부터) → 폰은 카드 한 장에 넘겨 본다(점 7개까지 · 넘으면 «k / n» · 11-15 꼴).
  전달: ① mobility 알림 사건 kind «sort»(id ev-sort-…) — mobility 모듈이 켜져 있을 때만 · alarms.inbox_put → 서버가 /v1/alarms 에 싣고 폰이 당겨 온다(45분 · 알림-설정 «당겨_오기_분» · 잘 시간엔 안 당김 = Beat.java)
        ①' 즉시(11-18 시험판) — ① 뒤에 서버(127.0.0.1 /v1/push/emit)에 같은 사건을 넘긴다 → 폰이 붙잡아 둔 물음에 바로 실림(폰은 같은 id 로 거름 · 서버가 없으면 ①만 · 장부 줄 «즉시»).
           분류(sort.run)가 알림 동작을 넘기면 그 자리에서 run 을 부른다(sort.alert_now) — 15분 확인은 그물로 남음.
        ② 수집 창 «일어난 일» — 알림 장부 _index/sort/알림.jsonl 의 그 자리(출처) 줄. mobility 가 꺼져 있으면 ②만.
  알림 글: 어댑터 alert_event(가격줄 = sort_price · 티어·2인가·편)가 있으면 그 폰 꼴 · 없으면 «체계 이름 · 갈래» + 대상 제목(없으면 근거).
  누름: 폰 앱(판 32)은 obsidian:// 주소만 바로 연다(그 밖은 옵시디언 홈) → 체계 «보기.moa» 가 있으면 그 모아보기 · 없으면 홈.

  py -3 .claude/skills/mobility/scripts/alert.py run [--dry] [--from-start]     # 넘김의 새 알림 → 때·중복 → 전달
  py -3 .claude/skills/mobility/scripts/alert.py tick                           # 15분 확인 끝(collect-tick act_tick) — run 하고 낸 것이 있을 때만 한 줄
  py -3 .claude/skills/mobility/scripts/alert.py list [--json]                  # 알림 동작이 있는 체계 · 앞으로 울릴 것(폰 사건) · 최근 낸 것 · 아직 안 읽은 알림 줄
  py -3 .claude/skills/mobility/scripts/alert.py now <제목> [--text <글>] [--urgent] [--system <체계>] [--target <대상>] [--place <자리>] [--open <볼트 경로|obsidian://>] [--buttons "네,아니오"] [--clear-on-open] [--dry]   # 대화 Claude 가 지금 하나
      --buttons = 카드 단추 글 1~3개(쉼표로 · 폰 앱 판 35~ · 누름 = 그 글이 답 · 옛 판은 넘김·다시) · 앞에 ✎ = 입력 단추(누르면 알림 안 긴 입력창 · 쓴 글이 답 ·
                  예 "네,아니오,✎답 쓰기") · --clear-on-open = 본문 누름 = 열고 카드에서 지움
  py -3 .claude/skills/mobility/scripts/alert.py answer <id> [--json]           # 그 알림의 답(단추 글 · 열어 봄) · 시각 · 기기 — 없으면 «아직»
  py -3 .claude/skills/mobility/scripts/alert.py wait <id> [--minutes 120]      # 질문 알림 대기(고를 때만) — 답이 오면 한 줄 내고 끝 · now --wait [분] = 보내고 바로 기다림 · 대화 Claude 는 run_in_background 로(끝나는 순간 대화가 깨어나 답을 옮김)
"""
import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import os
import sys
import urllib.parse
from collections import Counter

MOD = os.path.dirname(os.path.abspath(__file__))     # mobility 모듈 scripts(11-18 · 옛 자리 3_시스템/alert.py)
# SYS = 볼트의 3_시스템(분류 엔진 sort.py) — 시험 사본이 3_시스템 안(옆에 sort.py)에 두면 그 자리
SYS = MOD if os.path.isfile(os.path.join(MOD, 'sort.py')) else os.path.normpath(os.path.join(MOD, '..', '..', '..', '..', '3_시스템'))
VAULT = os.path.dirname(SYS)
if SYS not in sys.path:
    sys.path.insert(0, SYS)
import sort  # noqa: E402

STATE = '알림.json'          # 넘김 커서 + 울린 것 {체계: {대상: {순위, 갈래들, 마지막, 시각}}}
LOG = '알림.jsonl'           # 낸 알림 한 줄씩 — 수집 창 «일어난 일»이 자리(출처)로 읽는다
KIND = 'sort'                # mobility 사건 kind(폰 id «ev-sort-…»)
ALARMS = os.path.join(MOD, 'alarms.py')                 # 같은 모듈 자리
SLEEP = {'부터': '23:00', '까지': '08:00'}     # mobility 를 못 읽을 때(알림-설정 기본과 같음)
OPEN_HOME = 'obsidian://brain-server'          # 폰 brain-server — file 을 주면 그 노트(alarms.open_note 와 같은 꼴)
_al = []


def ix(*p):
    return os.path.join(sort.INDEX, *p)


def now_local():
    return dt.datetime.now().astimezone().replace(microsecond=0)


def ms(t):
    return int(t.timestamp() * 1000)


# ───────── mobility ─────────
def alarms():
    """mobility 알림 모듈(.claude/skills/mobility/scripts/alarms.py) — 없거나 못 읽으면 None. 읽기만(맞았던 설정 적기는 서버 몫)."""
    if not _al:
        m = None
        if os.path.isfile(ALARMS):
            try:
                spec = importlib.util.spec_from_file_location('alarms_for_alert', ALARMS)
                m = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(m)
                m.SAVE_LAST = False
            except Exception:
                m = None
        _al.append(m)
    return _al[0]


def mobility_on():
    """mobility 모듈이 있고 켜져 있나(roles.module_on — 기본 켬 · enabledPlugins 가 false 면 꺼짐)."""
    if alarms() is None:
        return False
    import roles
    return roles.module_on('mobility')


def settings():
    """알림 설정(잘_시간 = 방해 금지 · «켬» false 면 부터=까지) — mobility 노트 알림-설정 · 못 읽으면 기본 23:00~08:00."""
    m = alarms()
    if m is not None:
        try:
            return m.load_settings()[0]
        except Exception:
            pass
    return {'잘_시간': dict(SLEEP)}


def _minutes(hhmm):
    h, m = hhmm.split(':')
    return int(h) * 60 + int(m)


def next_clock(t, hhmm):
    h, m = map(int, hhmm.split(':'))
    x = t.replace(hour=h, minute=m, second=0, microsecond=0)
    return x if x > t else x + dt.timedelta(days=1)


def awake(t, s):
    """잘 시간이면 아침 — mobility alarms.awake(t, 먼 마감, 설정) · 모듈이 없으면 같은 셈을 여기서."""
    m = alarms()
    far = t + dt.timedelta(days=30)
    if m is not None:
        return m.awake(t, far, s)
    a, b = _minutes(s['잘_시간']['부터']), _minutes(s['잘_시간']['까지'])
    x = t.hour * 60 + t.minute
    if a == b or not ((a <= x or x < b) if a > b else (a <= x < b)):
        return t
    return next_clock(t, s['잘_시간']['까지'])


def when(now, want, urgent, s):
    """(울릴 때, 때 낱말). 급함 = 지금(잘 시간·묶음 건너뜀) · 바로 = 지금 · 아침 = 다음 잘_시간 끝 · 묶음 HH:MM = 다음 그 시각 — 급함이 아니면 잘 시간이면 아침."""
    want = want or '바로'
    if urgent:
        return now, '바로(급함)'
    if want == '아침':
        t = next_clock(now, s['잘_시간']['까지'])
    elif want.startswith('묶음 '):
        t = next_clock(now, want[3:])
    else:
        t = now
    t2 = awake(t, s)
    return t2, (want if t2 == t else want + ' → 아침')


# ───────── 순위·중복 ─────────
def rank_of(s, ad, branch):
    """갈래의 높이 — 어댑터 rank(갈래)(가격줄 = 티어) · 없으면 그 갈래 태그의 사전 가족 차례 · 둘 다 없으면 None(차례 없는 체계)."""
    if ad is not None and hasattr(ad, 'rank'):
        r = ad.rank(branch)
        if r is not None:
            return r
    import tag
    D = tag.dictionary()
    acts = ((s.get('갈래') or {}).get(branch) or {}).get('동작') or []
    rs = [tag.rank(t, D) for t in sort.tags({'동작': acts})]
    rs = [r for r in rs if r is not None]
    return max(rs) if rs else None


def due(prev, branch, r):
    """울릴 차례인가 — 처음 · 순위가 지난 최고보다 높음 · (순위 없는 체계) 처음 보는 갈래."""
    if not prev:
        return True
    if r is not None and prev.get('순위') is not None:
        return r > prev['순위']
    return branch not in (prev.get('갈래들') or [])


def load_state():
    try:
        d = json.load(open(ix(STATE), encoding='utf-8'))
    except (OSError, ValueError):
        d = {}
    d = d if isinstance(d, dict) else {}
    d.setdefault('커서', 0)
    d.setdefault('울림', {})
    return d


# ───────── 글 ─────────
def open_of(s, raw):
    """폰 누름 주소 — obsidian:// 면 그대로 · 체계 «보기.moa» 가 있으면 그 모아보기 · 아니면 None(폰 = 옵시디언 홈)."""
    if isinstance(raw, str) and raw.startswith('obsidian://'):
        return raw
    moa = (s.get('보기') or {}).get('moa')
    if isinstance(moa, str) and moa.endswith('.moa') and '<' not in moa:
        return f"{OPEN_HOME}?file={urllib.parse.quote(moa, safe='')}"
    return None


def message(s, ad, rec, item, now):
    """(제목, 글, 링크) — 어댑터 alert_event 가 있으면 그 폰 꼴(가격줄 = «SSS 항공권 · 2인 28만 …») · 없으면 «체계 · 갈래» + 대상 제목."""
    if ad is not None and hasattr(ad, 'alert_event') and item is not None:
        try:
            q = settings().get('잘_시간') or {}
            try:                                   # 어댑터의 «때» 칸도 방해 금지 설정을 따르게(끔 = 부터=까지)
                ev = ad.alert_event(rec, item['facts'], now, sleep=(q['부터'], q['까지']))
            except (TypeError, KeyError):
                ev = ad.alert_event(rec, item['facts'], now)
            if ev:
                ph = ev.get('폰') or {}
                return ph.get('title') or rec['갈래'], ph.get('text') or '', ph.get('open') or ev.get('링크')
        except Exception:
            pass
    f = (item or {}).get('facts') or {}
    text = str(f.get('제목') or rec.get('근거') or rec['대상'])
    return f'{s.get("이름") or s["id"]} · {rec["갈래"]}', text[:160], None


def event_id(*parts):
    return f'ev-{KIND}-' + hashlib.sha1('|'.join(map(str, parts)).encode('utf-8')).hexdigest()[:12]


# ───────── 전달 ─────────
def deliver(rows, now, dry=False):
    """rows = 장부 줄(폰 칸 포함) → ① mobility(켜졌을 때) ② 알림 장부. 돌려줌 = 폰에 냈나(True · False · 까닭 글)."""
    if not rows:
        return False
    phone = mobility_on()
    why = None
    instant = None
    evs = [r.pop('_폰') for r in rows]
    if phone and not dry:
        try:
            alarms().inbox_put(KIND, evs, now_ms=ms(now))
        except Exception as e:
            phone, why = False, f'{type(e).__name__}: {e}'[:160]
        else:
            instant = push_server(evs)                  # 11-18 즉시 알림 — 붙잡힌 폰 물음에 바로(서버가 없거나 옛 판이면 False · 목록 길은 그대로)
    for r in rows:
        r['폰'] = phone
        if why:
            r['폰 못 냄'] = why
        if instant is not None:
            r['즉시'] = instant
    if not dry:
        sort.append_lines(ix(LOG), rows)
    return phone if not why else why


def push_server(events, here=None, port=None, timeout=2.0):
    """즉시 알림(11-18 시험판) — PC 서버(127.0.0.1)에 사건을 넘겨, 폰이 붙잡아 둔 물음(/v1/push)에 바로 싣게 한다. 서버만 폰과 말한다.
    폰 목록에는 inbox_put 이 이미 넣었다(같은 id · 폰이 id 로 거름 = 두 번 안 울림). 서버가 없거나 옛 판(404)이면 False(폰은 당기기로 받음).
    시험이 사건 자리(alarms.INBOX)를 바꿨으면 진짜 서버에 보내지 않는다. here·port = 시험 서버 자리. 돌려줌 = True · False · 까닭 글."""
    m = alarms()
    if m is None or not events:
        return False
    if here is None:
        if os.path.normcase(os.path.abspath(m.INBOX)) != os.path.normcase(os.path.abspath(os.path.join(m.STATE, 'in'))):
            return False
        here = m.HERE
    st = os.path.join(here, '_index', 'server')
    try:
        with open(os.path.join(st, 'token'), encoding='utf-8') as f:
            tok = f.read().strip()
    except OSError:
        return False
    if port is None:
        try:
            with open(os.path.join(st, 'config.json'), encoding='utf-8') as f:
                port = int(json.load(f).get('port') or 8377)
        except (OSError, ValueError, TypeError, AttributeError):
            port = 8377
    import urllib.error
    import urllib.request
    body = json.dumps({'kind': 'alert', 'events': [{k: e[k] for k in ('id', 'at', 'title', 'text', 'open') + tuple(getattr(m, 'EXTRA_KEYS', ())) if k in e} for e in events]}, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(f'http://127.0.0.1:{port}/v1/push/emit', data=body, method='POST',
                                 headers={'Authorization': 'Bearer ' + tok, 'Content-Type': 'application/json; charset=utf-8'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return bool(json.loads(r.read() or b'{}').get('ok'))
    except urllib.error.HTTPError as e:
        return False if e.code == 404 else f'http {e.code}'
    except Exception:  # noqa: BLE001 — 서버가 꺼져 있음 · 시험의 망 막음
        return False


def _lock():
    """run·now 겹침 막기(15분 확인 · 대화 Claude) — 남이 쥐면 None(그 회차는 건너뜀 · 다음 번에 같은 줄을 읽는다)."""
    os.makedirs(sort.INDEX, exist_ok=True)
    f = open(ix('알림.lock'), 'a+')
    try:
        if os.name == 'nt':
            import msvcrt
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return f
    except OSError:
        f.close()
        return None


def run(dry=False, now=None, from_start=False):
    """넘김 장부의 새 알림 줄 → 지금 판정과 맞는지 · 중복 · 때 → 전달. 돌려줌 = {낸, 중복, 지난 판정, 체계 꺼짐, 잊음, 폰}."""
    now = now or now_local()
    lock = None if dry else _lock()
    if not dry and lock is None:
        return {'건너뜀': '다른 알림 돌림이 쓰는 중'}
    try:
        return _run(dry, now, from_start)
    finally:
        if lock:
            lock.close()


def _run(dry, now, from_start):
    st = load_state()
    rows, cur = sort.handoffs(st['커서'], from_start)
    S = sort.systems()
    cnt = Counter()
    cand = {}
    for e in rows:
        if isinstance(e['동작'].get('알림'), dict):
            cand[(e['체계'], e['대상'])] = e                # 한 대상에 줄이 여럿이면 마지막 것(어차피 지금 판정과 대 봄)
    sent = st['울림']
    for sid in list(sent):                                 # 분류 상태에서 사라진 대상은 잊음 — 다시 나오면 새것
        s = S.get(sid)
        if not s or s.get('_err') or s.get('켬', True) is False:
            continue
        live = set(sort.state(sid)['items']) | set(sort.state(sid)['대기'])
        for tid in [t for t in sent[sid] if t not in live]:
            del sent[sid][tid]
            cnt['잊음'] += 1
        if not sent[sid]:
            del sent[sid]
    s_cfg, items, picked = None, {}, {}
    for (sid, tid), e in sorted(cand.items()):
        s = S.get(sid)
        if not s or s.get('_err') or s.get('켬', True) is False:
            cnt['체계 꺼짐'] += 1
            continue
        rec = sort.state_item(sid, tid)
        al = next((a['알림'] for a in (rec or {}).get('동작') or [] if isinstance(a.get('알림'), dict)), None)
        if not rec or rec.get('갈래') != e.get('갈래') or al is None:
            cnt['지난 판정'] += 1                          # 그 뒤 판정이 또 바뀜 · 사라짐
            continue
        kind = (s.get('대상') or {}).get('종류')
        ad = sort.adapter(kind)
        r = rank_of(s, ad, rec['갈래'])
        if not due((sent.get(sid) or {}).get(tid), rec['갈래'], r):
            cnt['중복'] += 1
            continue
        if kind not in items:
            try:
                items[kind] = {it['id']: it for it in ad.items()} if ad is not None else {}
            except Exception:
                items[kind] = {}
        it = items[kind].get(tid)
        s_cfg = s_cfg or settings()
        at, word = when(now, al.get('때'), rec.get('급함') is True, s_cfg)
        title, text, link = message(s, ad, rec, it, now)
        key = ad.alert_key(it) if it is not None and ad is not None and hasattr(ad, 'alert_key') else 0
        picked.setdefault(sid, []).append({'rec': rec, 'r': r, 'at': at, 'word': word, 'title': title, 'text': text, 'link': link,
                                           'place': sort.place_of(s, it) if it is not None else (s.get('자리') or '홈'), 'key': key})
    out = []
    for sid, xs in picked.items():
        s = S[sid]
        xs.sort(key=lambda x: (-(x['r'] or 0), x['key'], x['rec']['대상']))
        n, step = len(xs), {}
        for k, x in enumerate(xs, 1):
            rec = x['rec']
            base = ms(x['at'])
            at = base + 1000 * step.get(base, 0)            # 같은 때 여럿 = 1초씩(폰 카드에 순위 차례로)
            step[base] = step.get(base, 0) + 1
            eid = event_id(sid, rec['대상'], rec['갈래'])
            phone = {'id': eid, 'at': at, 'title': x['title'], 'text': x['text'], 'made': ms(now)}
            op = open_of(s, x['link'])
            if op:
                phone['open'] = op
            out.append({'id': eid, '시각': now.isoformat(timespec='seconds'), '체계': sid, '대상': rec['대상'], '갈래': rec['갈래'],
                        '급함': rec.get('급함') is True, '때': x['word'], '울릴 때': dt.datetime.fromtimestamp(at / 1000, now.tzinfo).isoformat(timespec='seconds'),
                        '제목': x['title'], '글': x['text'], '자리': x['place'], '묶음': [k, n], **({'링크': x['link']} if x['link'] else {}), '_폰': phone})
            prev = (sent.get(sid) or {}).get(rec['대상']) or {}
            sent.setdefault(sid, {})[rec['대상']] = {'순위': max([v for v in (prev.get('순위'), x['r']) if v is not None], default=None),
                                                 '갈래들': sorted(set(prev.get('갈래들') or []) | {rec['갈래']}), '마지막': rec['갈래'],
                                                 '시각': now.isoformat(timespec='seconds')}
    cnt['낸'] = len(out)
    phone = deliver(out, now, dry)
    st['커서'] = cur
    if not dry:
        sort.write_if_changed(ix(STATE), st)
    res = {k: v for k, v in cnt.items() if v}
    if out:
        res['폰'] = phone
    return res


def tick():
    """15분 확인 끝(collect-tick act_tick) — 낸 것이 있을 때만 한 줄."""
    r = run()
    return '' if not r.get('낸') else f'알림 {r["낸"]} · 폰 {r.get("폰")}'


def open_link(raw):
    """--open → 폰 누름 주소. obsidian:// 면 그대로 · 아니면 볼트 안 파일 경로(없으면 오류 · 이름만 주면 .md/.pdf 둘을 가를 수 없어 경로를 받는다)."""
    raw = str(raw or '').strip()
    if not raw or raw.startswith('obsidian://'):
        return raw or None
    rel = raw.replace('\\', '/').lstrip('/')
    if not os.path.isfile(os.path.join(VAULT, rel)):
        raise ValueError(f'볼트에 없는 파일: {rel}')
    return f"{OPEN_HOME}?file={urllib.parse.quote(rel, safe='')}"


def buttons_of(raw):
    """--buttons "네,아니오,✎답 쓰기" → ['네', '아니오', {'label': '답 쓰기', 'input': True}] (1~3개 · 빈 글 뺌 · 40자까지 · ✎ = 입력 단추) · 없으면 None."""
    if raw is None:
        return None
    bs = [x.strip() for x in str(raw).split(',') if x.strip()]
    if not 1 <= len(bs) <= 3 or any(len(x.lstrip('✎').strip()) > 40 or not x.lstrip('✎').strip() for x in bs):
        raise ValueError('--buttons = 쉼표로 1~3개 · 하나에 40자까지(✎ = 입력 단추)')
    return [{'label': x.lstrip('✎').strip(), 'input': True} if x.startswith('✎') else x for x in bs]


def now_one(title, text='', urgent=False, system=None, target=None, place=None, dry=False, now=None, open_=None, buttons=None, clear_on_open=False):
    """대화 Claude 가 지금 하나(행위 alert.now) — 급함이면 잘 시간에도 지금 · 아니면 잘 시간이면 아침. 중복 막기 없음(부른 그대로).
    open_ = 누르면 열 것(open_link) · 없으면 체계 모아보기 또는 홈."""
    if not str(title or '').strip():
        raise ValueError('제목 없음')
    link = open_link(open_)
    now = now or now_local()
    at, word = when(now, '바로', urgent, settings())
    s = sort.systems().get(system) or {} if system else {}
    eid = event_id('now', now.isoformat(), title, text)
    phone = {'id': eid, 'at': ms(at), 'title': title, 'text': text or '', 'made': ms(now)}
    op = link or (open_of(s, None) if s else None)
    if op:
        phone['open'] = op
    bs = buttons_of(buttons) if isinstance(buttons, str) or buttons is None else buttons
    if bs:
        phone['buttons'] = bs
    if clear_on_open:
        phone['clear_on_open'] = True
    row = {'id': eid, '시각': now.isoformat(timespec='seconds'), '체계': system or '', '대상': target or '', '갈래': '', '급함': bool(urgent), '때': word,
           '울릴 때': at.isoformat(timespec='seconds'), '제목': title, '글': text or '', '자리': place or (s.get('자리') if s else None) or '홈',
           '묶음': [1, 1], '누가': '대화', '_폰': phone}
    lock = None if dry else _lock()
    if not dry and lock is None:
        raise RuntimeError('다른 알림 돌림이 쓰는 중 — 잠시 뒤 다시')
    try:
        got = deliver([row], now, dry)
    finally:
        if lock:
            lock.close()
    return {'id': eid, '울릴 때': row['울릴 때'], '때': word, '폰': got, **({'단추': bs} if bs else {}), **({'누르면 사라짐': True} if clear_on_open else {})}


def answer(eid, path=None):
    """폰이 그 알림에 한 것 — 서버 장부(_index/alarms/acts.jsonl)의 pick(단추 글)·open(열어 봄) 줄 가운데 처음 것(두 기기면 먼저 닿은 쪽)."""
    p = path or os.path.join(SYS, '_index', 'alarms', 'acts.jsonl')
    try:
        lines = open(p, encoding='utf-8').read().splitlines()
    except OSError:
        lines = []
    for ln in lines:
        try:
            r = json.loads(ln)
        except ValueError:
            continue
        if (r.get('id') == eid or r.get('ring') == eid) and r.get('act') in ('pick', 'open') and r.get('got') in ('picked', 'opened'):
            return {'id': eid, '답': r.get('value') if r.get('act') == 'pick' else '(열어 봄)', 'act': r.get('act'), '시각': r.get('at'), '기기': r.get('device'),
                    **({'입력': True} if r.get('input') else {})}
    return {'id': eid, '답': None, '아직': True}


def answer_line(eid, d):
    return f"아직 · {eid}" if d.get('아직') else f"{'✎ ' if d.get('입력') else ''}{d['답']} · {d['시각']} · {d['기기']}"


def wait_answer(eid, minutes=120, every=3.0):
    """답이 올 때까지 기다림(질문 알림 대기 · 고를 수 있음 = now --wait · wait <id>). 대화 Claude 가 run_in_background 로 부르면
    끝나는 순간 대화가 깨어나 답을 바로 옮긴다 — 서버는 대화를 깨우지 못하므로 이 기다림이 그 길이다. 답 = 처음 닿은 pick·open."""
    import time
    end = time.time() + max(0.0, float(minutes)) * 60
    while True:
        d = answer(eid)
        if not d.get('아직'):
            return d
        if time.time() >= end:
            return {**d, '시간 끝': True}
        time.sleep(every)


# ───────── 보기 ─────────
def listing(now=None):
    now = now or now_local()
    S = sort.systems()
    sysrows = []
    for sid, s in sorted(S.items()):
        if s.get('_err'):
            continue
        for g, b in (s.get('갈래') or {}).items():
            for a in (b or {}).get('동작') or []:
                if isinstance(a, dict) and isinstance(a.get('알림'), dict):
                    sysrows.append({'체계': sid, '켬': s.get('켬', True) is not False, '갈래': g, '때': a['알림'].get('때'), '급함': a['알림'].get('급함')})
    st = load_state()
    rows, _ = sort.handoffs(st['커서'])
    unread = sum(1 for e in rows if isinstance(e['동작'].get('알림'), dict))
    ahead = []
    m = alarms()
    if m is not None:
        try:
            ahead = [e for e in m.inbox_events(ms(now)) if e['id'].startswith(f'ev-{KIND}-') and e['at'] > ms(now)]
        except Exception:
            ahead = []
    recent = []
    try:
        recent = [json.loads(x) for x in open(ix(LOG), encoding='utf-8').read().splitlines()[-10:]]
    except (OSError, ValueError):
        pass
    return {'mobility': mobility_on(), '체계': sysrows, '안 읽은 알림 줄': unread, '앞으로 울릴 것': ahead, '최근 낸 것': recent,
            '울린 대상': sum(len(v) for v in st['울림'].values())}


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    ap = argparse.ArgumentParser(description='알림 도구 — 분류가 정한 알림을 폰·수집 창으로')
    ap.add_argument('cmd', choices=['run', 'list', 'now', 'tick', 'answer', 'wait'])
    ap.add_argument('title', nargs='?')
    ap.add_argument('--dry', action='store_true')
    ap.add_argument('--from-start', action='store_true', help='run: 넘김 장부 처음부터(중복 막기는 그대로)')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--text', default='')
    ap.add_argument('--urgent', action='store_true', help='now: 급함(잘 시간에도 지금)')
    ap.add_argument('--system')
    ap.add_argument('--target')
    ap.add_argument('--place')
    ap.add_argument('--open', help='now: 누르면 열 것 — obsidian:// 주소 또는 볼트 안 파일 경로(1_수집/…/x.pdf)')
    ap.add_argument('--buttons', help='now: 카드 단추 글 1~3개(쉼표로 · 예 "네,아니오") · 누름 = 그 글이 답(alert.py answer <id>)')
    ap.add_argument('--clear-on-open', action='store_true', help='now: 본문 누름 = 열고 카드에서 지움(PC 에 «열어 봄»)')
    ap.add_argument('--wait', nargs='?', const=120, type=float, metavar='분',
                    help='now: 보낸 뒤 답이 올 때까지 기다렸다가 답 한 줄을 냄(기본 120분 · 고를 때만 · Claude 는 run_in_background 로)')
    ap.add_argument('--minutes', type=float, default=120, help='wait: 기다릴 분(기본 120)')
    a = ap.parse_args()
    if a.cmd in ('answer', 'wait'):
        if not a.title:
            sys.exit(f'{a.cmd}: 알림 id 를 주세요(now 가 낸 id)')
        d = answer(a.title) if a.cmd == 'answer' else wait_answer(a.title, a.minutes)
        line = answer_line(a.title, d) + (' · 시간 끝' if d.get('시간 끝') else '')
        print(json.dumps(d, ensure_ascii=False) if a.json else line)
        return 0
    if a.cmd == 'run':
        print(json.dumps(run(a.dry, from_start=a.from_start), ensure_ascii=False))
        return 0
    if a.cmd == 'tick':
        out = tick()
        if out:
            print(out)
        return 0
    if a.cmd == 'now':
        try:
            sent = now_one(a.title, a.text, a.urgent, a.system, a.target, a.place, a.dry, open_=a.open, buttons=a.buttons,
                           clear_on_open=a.clear_on_open)
        except (ValueError, RuntimeError) as e:
            sys.exit(f'now: {e}')
        print(json.dumps(sent, ensure_ascii=False), flush=True)
        if a.wait and not a.dry:
            d = wait_answer(sent['id'], a.wait)
            print('답: ' + answer_line(sent['id'], d) + (' · 시간 끝' if d.get('시간 끝') else ''))
        return 0
    d = listing()
    if a.json:
        print(json.dumps(d, ensure_ascii=False, indent=1))
        return 0
    print(f'mobility {"켬 — 폰 + 수집 창" if d["mobility"] else "꺼짐 — 수집 창만"} · 안 읽은 알림 줄 {d["안 읽은 알림 줄"]} · 울린 대상 {d["울린 대상"]}')
    for r in d['체계']:
        print(f'- {r["체계"]}{"" if r["켬"] else "(끔)"} · {r["갈래"]} · 때 {r["때"]} · 급함 {r["급함"]}')
    if not d['체계']:
        print('- 알림 동작이 있는 체계 없음')
    for e in d['앞으로 울릴 것']:
        print(f'  울릴 것 {dt.datetime.fromtimestamp(e["at"] / 1000):%m-%d %H:%M} {e["title"]} · {e.get("text", "")}')
    for e in d['최근 낸 것']:
        print(f'  낸 것 {str(e.get("시각"))[5:16]} {e.get("제목")} · {e.get("글")} · 폰 {e.get("폰")}')
    return 0


if __name__ == '__main__':
    sys.modules.setdefault('alert', sys.modules['__main__'])
    sys.exit(main())
