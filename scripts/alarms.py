"""알림 모듈 — 일정 줄과 수집 상태에서 폰이 울릴 목록을 만든다(LLM 0). 서버가 /v1/alarms 로 내준다.

  py -3 .claude/skills/mobility/scripts/alarms.py [--days N]     # 앞으로 울릴 것을 시각 순으로(상태를 바꾸지 않는다)
  py -3 .claude/skills/mobility/scripts/alarms.py --check        # 알림 설정에 틀린 칸이 있나
  py -3 .claude/skills/mobility/scripts/alarms.py --report       # 폰이 보고한 늦음·놓침(_index/alarms/fired.jsonl)
  py -3 .claude/skills/mobility/scripts/alarms.py --push-report [--days N]   # 즉시 알림 왕복·잃음·배터리(_index/alarms/push.jsonl · 11-18 시험판)

무엇을 언제 울릴지는 사용자 설정 = 노트 [[알림-설정]] 의 json 블록(칸 설명은 그 노트). 요청 때마다 읽어 재시작 없이 반영한다.
일정 하나만 다르게 = 노트 [[일정별-알림]] 의 json 블록(캘린더 종이 씀 · ADR-052) — 줄 열쇠(블록 id) 하나에 «울림» 목록. 있으면 그 줄은 그것만 따른다.
틀린 값은 그 칸만 기본값으로 울리고, 틀린 칸을 «알림 설정 틀림» 한 번으로 알린다 — 잘못 고쳐 알림이 조용히 사라지면 안 된다.
알림 항목에는 줄의 날짜·열쇠와 누름 주소(open = obsidian://brain-calendar?date=…&key=…)를 싣는다 — 폰 앱이 알림 누름에 붙인다.
바로 알릴 것 = 시각 예약이 아니라 폰이 당겨 올 때 울린다(지난 시각으로 받은 알람은 바로 울린다). 잘 시간이면 아침으로.
쓰는 곳은 _index/alarms 뿐이다(상태·보고 장부 · 폰 «넘김» 장부 skips.json · 두 기기 울림 판정 rings.json). 볼트 노트는 쓰지 않는다 — 넘김도 노트가 아니라 장부에 써서
캘린더(데스크톱)와 같은 파일을 쓰는 일이 없다. 같은 회차를 두 쪽이 말하면 늘 데스크톱(일정별-알림의 «열쇠@날짜» 칸)이 이긴다(사용자 11-13 «무조건 데스크탑 우선»).
"""
import datetime as dt
import glob
import hashlib
import json
import os
import re
import sys
import threading
import time
import urllib.parse

MOD = os.path.dirname(os.path.abspath(__file__))     # mobility 모듈 scripts(11-16 · 옛 자리 3_시스템/alarms.py)
# HERE = 볼트의 3_시스템 — 시험 사본은 임시 볼트의 3_시스템 안(옆에 schedule.py)에 두므로 그 자리
HERE = MOD if os.path.isfile(os.path.join(MOD, 'schedule.py')) else os.path.normpath(os.path.join(MOD, '..', '..', '..', '..', '3_시스템'))
sys.path.insert(0, HERE)
import schedule  # noqa: E402 — 일정 줄 문법은 한 곳

DEFAULTS = {
    '켬': True,
    '기본': {'며칠_전': [3, 1], '시각': ['20:00']},        # 사용자 11-05 · 조리법 setup.json «alarm_default» 와 같게
    '파일': {},     # 개인 값은 노트에만(11-17 범용화) — 노트의 «파일»이 깨지면 마지막으로 맞았던 «파일»(last-good.json) → 없으면 '*'(일정 폴더 전부). 조용해지지 않게
    '과목': {},
    '글자': [],
    '잘_시간': {'켬': True, '부터': '23:00', '까지': '08:00'},     # 방해 금지(잘 시간) · 켬 false = 부터=까지(11-19)
    '바로': {'막힘': True, '옮겨짐': True, '늦게_앎': True, '새_공지': True},     # 새 공지 = 사용자 승인 11-05
    '당겨_오기_분': 30,                                     # 폰이 몇 분마다 당겨 오나(사용자 합격선: «바로» 60분 이내)
}
PENDING = '(판정 대기)'
MAX_ITEMS = 400                         # 안드로이드는 앱당 알람 500개에서 예외를 낸다
EVENT_DAYS = 7                          # 폰이 이만큼 못 당기면 사건은 사라진다
NOTICE_DAYS = 7                         # 게시일이 이보다 오래된 공지는 새 공지로 안 친다(새 출처 첫 수집이 몰아 울리지 않게)
PROBE_AT = dt.time(3, 17)               # 재기: 폰이 깊이 잠들어 있을 때
PROBE_NIGHTS = 3                        # 며칠 PC 가 잠들어도 이어지게
WD = '월화수목금토일'
ALL_FILES = '*'                         # «파일» 칸의 '*' = 일정 폴더의 모든 파일(설정이 깨졌고 맞았던 적도 없을 때의 기본)
# 설정 노트 둘(알림-설정 · 일정별-알림 — 일정 폴더 밖이라 폰에서도 고침 · 일정별은 캘린더가 쓴다)의 자리 = 모듈 선언(module.json contributes.notes).
# 선언 자리에 없으면 이름(basename · 볼트에 하나)으로 찾는다 — 옛 자리·사람이 옮긴 자리도 따라간다. 둘 다 없으면 선언 자리(처음 설정이 틀로 만든다).
# alarms.SETTINGS·PER_LINE 은 읽을 때마다 다시 찾는다(아래 __getattr__ · 서버가 켠 뒤 노트가 생기거나 옮겨져도 따라감).
MODULE_JSON = os.path.join(os.path.dirname(MOD), 'module.json')
NOTE_NAMES = {'alarm-settings': '알림-설정', 'alarm-per-line': '일정별-알림'}     # 선언을 못 읽을 때(시험 사본)의 이름
NOTE_HOME = '2_지식/modules/mobility'     # 모듈 홈(touches) — 선언을 못 읽을 때의 자리
_NOTE_HIT = {}
# 울림 한 칸 — «3일 전 20:00» · «당일 09:00» · «90분 전» · «2시간 전»(캘린더 repeat.ts 옆 alarm.ts 와 같은 글)
RING = re.compile(r'^(?:(당일)|(\d{1,3})일 전) ([01]?\d|2[0-3]):([0-5]\d)$|^(\d{1,5})(분|시간) 전$')
KEY = re.compile(r'^[A-Za-z0-9-]{1,64}(?:@(\d{4}-\d{2}-\d{2}))?$')     # «열쇠@날짜» = 그 회차만(캘린더가 넘김을 풀거나 회차를 따로 정할 때)
REP_SERIES = re.compile(r'^(rep-[0-9a-f]{8})-\d{8}$')    # 반복 회차 id → 그 반복 전체(schedule.py repeat · 캘린더 repeat.ts)
OPEN = 'obsidian://brain-calendar?date={date}&key={key}'
OPEN_HOME = 'obsidian://brain-server'   # 폰 brain-server 0.7.6~ — file 을 주면 그 노트(폰에 없으면 PC 에서 받음) · 없으면 홈
VAULT = os.path.dirname(HERE)
STATE = os.path.join(HERE, '_index', 'alarms')
FIRED = os.path.join(STATE, 'fired.jsonl')
SEEN = os.path.join(STATE, 'seen.json')
SKIPS = os.path.join(STATE, 'skips.json')     # 폰 «넘김» — {"열쇠@날짜": {"글", "at"}} · 서버만 쓴다 · 캘린더는 읽기만
QUEUE = os.path.join(HERE, '_index', '수집-대기열.md')
QUEUE_LINE = None                       # 사람 줄 «(호칭)» — 호칭은 프로필에서(blocked_lines 가 처음 부를 때 짓는다)
HHMM = re.compile(r'^([01]?\d|2[0-3]):([0-5]\d)$')
JSON_BLOCK = re.compile(r'^```json[ \t]*\r?\n(.*?)^```', re.M | re.S)
LOCK = threading.Lock()
LAST_GOOD = os.path.join(STATE, 'last-good.json')     # 마지막으로 맞았던 «파일» 칸 — 노트가 깨지면 이것으로 울린다
SAVE_LAST = True                        # 명령줄(읽기 행위)에서는 끈다 — 맞았던 설정은 서버가 요청 때 적는다
# 다른 대본이 낸 «바로» 사건(11-18 · 범용 도구 셋 S9) — 내는 쪽마다 파일 하나 in/<kind>.json = [{id «ev-<kind>-…», at, title, text, made, open?}].
# 지금 내는 쪽 = 알림 도구 alert.py(이 모듈 · 11-18 옛 자리 3_시스템 · kind «sort» · 분류 알림). 서버는 요청 때 읽어 사건 뒤에 싣는다(build) · 이 모듈은 그 파일을 쓰지 않는다(inbox_put 은 내는 쪽이 부름).
# 폰 앱(판 32)은 id 머리로 가르지 않는다 — ev-config-·ev-blocked- 만 상태 알림 · 나머지 ev-* 는 새 공지처럼 카드 한 장의 울린 항목(넘김·다시).
INBOX = os.path.join(STATE, 'in')
INBOX_KIND = re.compile(r'^[a-z][a-z0-9]{1,15}$')
INBOX_OWN = ('notice', 'moved', 'late', 'blocked', 'config')     # 이 모듈이 내는 kind — 밖에서 못 씀(폰이 상태 알림으로 가르는 것도 여기)
INBOX_KEYS = ('id', 'at', 'title', 'text', 'made', 'open', 'buttons', 'clear_on_open')
EXTRA_KEYS = ('buttons', 'clear_on_open')       # 폰 앱 판 35~(11-19): 알림 자체 단추 글 1~3개(누름 = 그 글이 답 · act pick) · 누르면 사라지기(act open) — 옛 앱은 모르는 칸이라 무시


def declared_notes():
    """module.json contributes.notes → {id: {name, path, template}} · 못 읽으면 {}."""
    try:
        with open(MODULE_JSON, encoding='utf-8') as f:
            notes = (json.load(f).get('contributes') or {}).get('notes') or []
    except (OSError, ValueError, AttributeError):
        notes = []
    return {n['id']: n for n in notes if isinstance(n, dict) and n.get('id')}


def note_path(nid):
    """설정 노트의 절대 자리 — 선언 자리에 있으면 그것 · 없으면 이름으로 찾은 자리 · 둘 다 없으면 선언 자리. 있는 자리만 기억한다."""
    hit = _NOTE_HIT.get(nid)
    if hit and os.path.isfile(hit):
        return hit
    d = declared_notes().get(nid) or {}
    name = d.get('name') or NOTE_NAMES[nid]
    p = os.path.join(VAULT, *(d.get('path') or f'{NOTE_HOME}/{name}.md').split('/'))
    if not os.path.isfile(p):
        import roles
        found = roles.find_note(name, vault=VAULT)
        if found:
            p = os.path.join(VAULT, *found.split('/'))
    if os.path.isfile(p):
        _NOTE_HIT[nid] = p
    return p


def note_rel(nid):
    return os.path.relpath(note_path(nid), VAULT).replace(os.sep, '/')


def __getattr__(name):
    """alarms.SETTINGS · alarms.PER_LINE — 부를 때마다 note_path(서버·캘린더 짝 대본이 이 이름으로 읽는다)."""
    if name == 'SETTINGS':
        return note_path('alarm-settings')
    if name == 'PER_LINE':
        return note_path('alarm-per-line')
    raise AttributeError(name)


def load_last_good(path=None):
    try:
        with open(path or LAST_GOOD, encoding='utf-8') as f:
            d = json.load(f)
        return d if isinstance(d, dict) and isinstance(d.get('파일'), dict) and d['파일'] else None
    except (OSError, ValueError):
        return None


def save_last_good(files, path=None):
    """맞았던 «파일»을 적는다(바뀌었을 때만 · 상태 자리 _index/alarms · 볼트 노트 아님)."""
    path = path or LAST_GOOD
    if (load_last_good(path) or {}).get('파일') == files:
        return
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + '.tmp'
        with open(tmp, 'w', encoding='utf-8', newline='\n') as f:
            json.dump({'파일': files, 'at': time.time()}, f, ensure_ascii=False)
        os.replace(tmp, path)
    except OSError:
        pass


# ───────── 설정 ─────────
def rule_of(raw, where, problems):
    """규칙 칸 하나 → 맞는 값만 담은 사전. 틀린 값은 빼고 문제에 적는다(위 단계 값이 그대로 쓰인다)."""
    out = {}
    if not isinstance(raw, dict):
        problems.append(f'{where}: {{}} 꼴이어야 함')
        return out
    for k, v in raw.items():
        if k == '며칠_전':
            if isinstance(v, list) and v and all(type(x) is int and 0 <= x <= 365 for x in v):
                out[k] = sorted(set(v), reverse=True)
            else:
                problems.append(f'{where}.며칠_전: 0~365 숫자 목록이어야 함 ({json.dumps(v, ensure_ascii=False)})')
        elif k == '시각':
            if isinstance(v, list) and v and all(isinstance(x, str) and HHMM.match(x) for x in v):
                out[k] = sorted({f'{int(x.split(":")[0]):02d}:{x.split(":")[1]}' for x in v})
            else:
                problems.append(f'{where}.시각: "20:00" 꼴의 목록이어야 함 ({json.dumps(v, ensure_ascii=False)})')
        elif k == '끔':
            if isinstance(v, bool):
                out[k] = v
            else:
                problems.append(f'{where}.끔: true 나 false 여야 함 ({json.dumps(v, ensure_ascii=False)})')
        elif k != '포함':
            problems.append(f'{where}.{k}: 모르는 칸')
    return out


def fallback_files(last=None):
    """«파일»이 없거나 깨졌을 때 — 마지막으로 맞았던 «파일» → 없으면 일정 폴더 전부('*')."""
    return json.loads(json.dumps(last['파일'])) if last and isinstance(last.get('파일'), dict) and last['파일'] else {ALL_FILES: {}}


def parse_settings(text, last=None, meta=None):
    """노트 글 → (설정, 문제들). 없는 칸은 기본값, 틀린 칸은 기본값 + 문제.
    «파일»이 없거나 깨지면 last(마지막으로 맞았던 설정 · load_last_good) → 없으면 '*'. meta 를 주면 {'files_ok': «파일»이 맞았나}."""
    problems = []
    s = json.loads(json.dumps(DEFAULTS))
    s['기본'] = dict(DEFAULTS['기본'])
    meta = meta if meta is not None else {}
    meta['files_ok'] = False

    def done():
        if not meta['files_ok']:
            s['파일'] = fallback_files(last)
        return s, problems
    if text is None:
        return done()
    m = JSON_BLOCK.search(text)
    if not m:
        problems.append('json 블록을 못 찾음 — 전부 기본값')
        return done()
    try:
        raw = json.loads(m.group(1))
    except ValueError as e:
        problems.append(f'json 오류({e}) — 전부 기본값')
        return done()
    if not isinstance(raw, dict):
        problems.append('맨 바깥이 { } 가 아님 — 전부 기본값')
        return done()
    for k, v in raw.items():
        if k == '켬':
            if isinstance(v, bool):
                s[k] = v
            else:
                problems.append(f'켬: true 나 false 여야 함 ({json.dumps(v, ensure_ascii=False)})')
        elif k == '기본':
            s[k] = {**s[k], **{a: b for a, b in rule_of(v, '기본', problems).items() if a != '끔'}}
        elif k == '파일':
            files = {}
            if isinstance(v, dict) and v:
                for name, r in v.items():
                    name = name if name == ALL_FILES or name.endswith('.md') else name + '.md'
                    files[name] = rule_of(r, f'파일.{name}', problems)
                    if name != ALL_FILES and not os.path.exists(os.path.join(schedule.SCHED_DIR, name)):
                        problems.append(f'파일.{name}: 일정 폴더에 없는 파일')
                # 이름을 잘못 적어 울릴 파일이 하나도 없으면 조용히 다 꺼진다
                if not any((n == ALL_FILES or os.path.exists(os.path.join(schedule.SCHED_DIR, n))) and not r.get('끔') for n, r in files.items()):
                    if not all(r.get('끔') for r in files.values()):
                        problems.append('파일: 울릴 파일이 하나도 없음 — 마지막으로 맞았던 파일로 울림')
                        continue
                s[k] = files
                meta['files_ok'] = True
            else:
                problems.append('파일: 비었거나 { } 꼴이 아님 — 마지막으로 맞았던 파일로 울림(다 끄려면 «켬»)')
        elif k == '과목':
            if isinstance(v, dict):
                s[k] = {name: rule_of(r, f'과목.{name}', problems) for name, r in v.items()}
            else:
                problems.append('과목: { } 꼴이어야 함')
        elif k == '글자':
            if isinstance(v, list):
                rules = []
                for i, r in enumerate(v):
                    if isinstance(r, dict) and isinstance(r.get('포함'), str) and r['포함'].strip():
                        rules.append({'포함': r['포함'], **rule_of(r, f'글자[{i}]', problems)})
                    else:
                        problems.append(f'글자[{i}]: "포함" 글자가 있어야 함')
                s[k] = rules
            else:
                problems.append('글자: [ ] 꼴이어야 함')
        elif k == '잘_시간':          # 보이는 이름 = «방해 금지(잘 시간)» · «켬» 칸(없으면 true · 11-19 사용자 «폰을 늘 무음으로 두니 안 씀»)
            if isinstance(v, dict):
                for a, b in v.items():
                    if a == '켬':
                        if isinstance(b, bool):
                            s[k]['켬'] = b
                        else:
                            problems.append(f'잘_시간.켬: true 나 false 여야 함 ({json.dumps(b, ensure_ascii=False)})')
                    elif a not in ('부터', '까지'):
                        problems.append(f'잘_시간.{a}: 모르는 칸')
                    elif isinstance(b, str) and HHMM.match(b):
                        s[k][a] = b
                    else:
                        problems.append(f'잘_시간.{a}: "23:00" 꼴이어야 함 ({json.dumps(b, ensure_ascii=False)})')
                if s[k].get('켬') is False:     # 끔 = 부터=까지(잘 시간 없음) — 읽는 쪽(서버 probe·awake·quiet_of·알림 도구·폰)이 한 규칙으로 «없음»을 본다
                    s[k]['까지'] = s[k]['부터']
            else:
                problems.append('잘_시간: { } 꼴이어야 함')
        elif k == '바로':
            if isinstance(v, dict):
                for a, b in v.items():
                    if a not in DEFAULTS['바로']:
                        problems.append(f'바로.{a}: 모르는 칸')
                    elif isinstance(b, bool):
                        s[k][a] = b
                    else:
                        problems.append(f'바로.{a}: true 나 false 여야 함 ({json.dumps(b, ensure_ascii=False)})')
            else:
                problems.append('바로: { } 꼴이어야 함')
        elif k == '당겨_오기_분':
            if type(v) is int and 15 <= v <= 1440:     # 15분 = 안드로이드 주기 작업의 하한
                s[k] = v
            else:
                problems.append(f'당겨_오기_분: 15~1440 숫자여야 함 ({json.dumps(v, ensure_ascii=False)})')
        else:
            problems.append(f'{k}: 모르는 칸')
    return done()


def load_settings(path=None, last_good=None):
    """노트를 읽어 설정으로 — «파일»이 맞으면 마지막으로 맞았던 설정으로 적어 두고, 깨졌으면 그것으로 울린다."""
    path = path or note_path('alarm-settings')
    try:
        with open(path, encoding='utf-8') as f:
            text = f.read()
    except OSError:
        text = None
    meta = {}
    s, problems = parse_settings(text, load_last_good(last_good), meta)
    if meta['files_ok'] and SAVE_LAST:
        save_last_good(s['파일'], last_good)
    return s, problems


def ring_of(text):
    """울림 한 칸 글 → ('d', 며칠 전, 'HH:MM') · ('m', 분 전) · 틀리면 None."""
    m = RING.match(text.strip()) if isinstance(text, str) else None
    if not m:
        return None
    if m.group(5):
        n = int(m.group(5)) * (60 if m.group(6) == '시간' else 1)
        return ('m', n) if 1 <= n <= 7 * 1440 else None
    n = 0 if m.group(1) else int(m.group(2))
    return ('d', n, f'{int(m.group(3)):02d}:{m.group(4)}') if n <= 365 else None


def parse_per_line(text):
    """일정별-알림 노트 글 → ({열쇠: [울릴 칸…]}, 문제들). 틀린 칸은 빼고(그 줄은 기본 규칙으로) 문제에 적는다. «울림»: [] = 그 일정은 안 울림.
    «끔»: [칸…] = 정해 둔 칸은 남기고 그 칸만 안 울림(캘린더 상자의 종 · 사용자 11-13 «삭제가 아닌 끄기») — 울릴 칸 = 울림 − 끔."""
    problems, out = [], {}
    if text is None:
        return out, problems
    m = JSON_BLOCK.search(text)
    if not m:
        return out, ['일정별-알림: json 블록을 못 찾음 — 모든 일정이 기본 규칙']
    try:
        raw = json.loads(m.group(1))
    except ValueError as e:
        return out, [f'일정별-알림: json 오류({e}) — 모든 일정이 기본 규칙']
    if not isinstance(raw, dict):
        return out, ['일정별-알림: 맨 바깥이 { } 가 아님 — 모든 일정이 기본 규칙']
    for k, v in raw.items():
        where = f'일정별-알림.{k}'
        if not KEY.match(k):
            problems.append(f'{where}: 열쇠는 블록 id 꼴(영문·숫자·-)이어야 함')
            continue
        if not isinstance(v, dict) or not isinstance(v.get('울림'), list):
            problems.append(f'{where}: {{"울림": [...]}} 꼴이어야 함 — 기본 규칙으로')
            continue
        extra = [a for a in v if a not in ('울림', '글', '끔')]
        if extra:
            problems.append(f'{where}.{extra[0]}: 모르는 칸')
        off = set()
        if '끔' in v:
            if isinstance(v['끔'], list) and all(ring_of(x) for x in v['끔']):
                off = {ring_of(x) for x in v['끔']}
            else:       # 틀린 «끔»은 무시 = 울림 그대로 울린다(조용해지는 쪽으로 틀리지 않게)
                problems.append(f'{where}.끔: «울림»과 같은 꼴의 목록이어야 함 ({json.dumps(v["끔"], ensure_ascii=False)})')
        rings, bad = [], []
        for x in v['울림']:
            r = ring_of(x)
            (rings if r else bad).append(r or x)
        if bad:
            problems.append(f'{where}.울림: "3일 전 20:00"·"당일 09:00"·"90분 전"·"2시간 전" 꼴이어야 함 ({json.dumps(bad[0], ensure_ascii=False)})')
            if not rings:           # 다 틀렸으면 그 줄을 조용히 끄지 않고 기본 규칙으로
                continue
        out[k] = [r for r in dict.fromkeys(rings) if r not in off]     # 같은 칸 두 번은 한 번 · 끈 칸 뺌(다 끄면 [] = 안 울림)
    return out, problems


def load_per_line(path=None):
    path = path or note_path('alarm-per-line')
    try:
        with open(path, encoding='utf-8') as f:
            text = f.read()
    except OSError:
        text = None
    return parse_per_line(text)


def per_of(per, key, date=None, skips=()):
    """그 줄의 일정별 울림 — 차례: 데스크톱 그 회차(열쇠@날짜) > 폰 넘김(장부) > 데스크톱 열쇠 > 반복 전체(rep-<8>). 없으면 None(기본 규칙).
    데스크톱 회차 칸이 넘김보다 앞 = 같은 회차를 두 쪽이 말하면 늘 데스크톱(캘린더 종으로 넘김을 풀 때 쓴다)."""
    occ = f'{key}@{date}' if date else None
    if occ and occ in per:
        return per[occ]
    if occ and occ in skips:
        return []
    if key in per:
        return per[key]
    m = REP_SERIES.match(key)
    return per.get(m.group(1)) if m else None


def load_skips(path=None, today=None):
    """폰 «넘김» 장부 → 오늘 이후 회차 열쇠들(«열쇠@날짜»). 못 읽으면 빈 것 — 넘김이 빠지면 한 번 더 울릴 뿐 조용해지지 않는다."""
    today = today or dt.datetime.now(schedule.KST).date().isoformat()
    try:
        with open(path or SKIPS, encoding='utf-8') as f:
            raw = json.load(f)
    except (OSError, ValueError):
        return set()
    return {k for k in raw if isinstance(raw, dict) and (m := KEY.match(k)) and m.group(1) and m.group(1) >= today} if isinstance(raw, dict) else set()


def skip(key, date, label='', path=None, today=None, now=None):
    """폰 알림 «넘김» — 그 회차만 앞으로 안 울린다(장부 skips.json 에 «열쇠@날짜»). 반복의 다른 회차·다른 날로 옮겨진 줄은 그대로 울린다.
    볼트 노트(일정별-알림)는 건드리지 않는다 — 캘린더와 같은 파일을 쓰지 않으니 겹쳐 쓸 일이 없다. 지난 회차는 쓸 때 정리한다."""
    if not re.match(r'^[A-Za-z0-9-]{1,64}$', key or '') or not re.match(r'^\d{4}-\d{2}-\d{2}$', date or ''):
        return {'ok': False, 'why': '열쇠·날짜 꼴이 아님'}
    path = path or SKIPS
    today = today or dt.datetime.now(schedule.KST).date().isoformat()
    with LOCK:
        try:
            with open(path, encoding='utf-8') as f:
                raw = json.load(f)
            raw = raw if isinstance(raw, dict) else {}
        except (OSError, ValueError):
            raw = {}
        raw = {k: v for k, v in raw.items() if (m := KEY.match(k)) and m.group(1) and m.group(1) >= today}
        raw[f'{key}@{date}'] = {'글': str(label)[:40], 'at': ms(now or dt.datetime.now(schedule.KST))}
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + '.tmp'
        with open(tmp, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(raw, f, ensure_ascii=False, indent=0)
        os.replace(tmp, path)
    return {'ok': True}


# ───────── 울림 판정 — 두 기기(사용자 11-16 «두 알림 모두 받게 하고 알림 결과는 더 먼저 선택한 쪽을 우선으로») ─────────
# 폰·탭이 같은 목록을 받아 같은 울림(같은 id)을 따로 울린다. 단추(넘김·완료·다시)가 처음 서버에 닿은 쪽이 그 울림의 판정이고,
# 다른 기기가 뒤에 보낸 단추는 하지 않고 «이미 판정됨»으로 답한다(그 기기는 카드에서 빼기만). 같은 기기가 다시 보낸 것(답을 못 받음)은 그대로 한다.
# 완료·넘김은 그 줄(열쇠@날짜) 전체의 판정도 남긴다 — 그 때까지 울린 그 줄의 다른 울림도 판정된 것(위젯 체크 = 그 줄 완료).
# 다시 = 새 울림 하나(snz-…)를 두 기기가 같이 받는다(목록에 실림). 판정된 울림은 목록에서 빠진다(아직 안 울린 기기는 안 울림).
RINGS = os.path.join(STATE, 'rings.json')     # {"rings": {울림 id: {act, by, at}}, "lines": {열쇠@날짜: {act, by, at}}, "snoozes": {id: 항목}}
RING_DAYS = 8                                 # 사건(7일)보다 하루 더 — 그 뒤 판정은 지움
RING_WAIT_MAX = 25                            # 기다리는 물음(초) 상한 — 폰은 카드가 떠 있는 동안만 묻는다
RING_COND = threading.Condition()             # 판정이 새로 생기면 기다리는 물음을 깨운다
ACT_KO = {'done': '완료', 'skip': '넘김', 'again': '다시', 'pick': '답', 'open': '열어 봄'}
SNOOZE_KEYS = ('id', 'at', 'title', 'text', 'date', 'key', 'open')


def ring_line(rid, key='', date=''):
    """울림의 줄(열쇠@날짜) — 항목 칸이 있으면 그것 · 없으면 id(«열쇠@날짜@종류», «snz-<때>|<본 id>»)에서 · 사건이면 None."""
    if key and re.fullmatch(r'\d{4}-\d{2}-\d{2}', date or ''):
        return f'{key}@{date}'
    rid = str(rid or '')
    if rid.startswith('snz-') and '|' in rid:
        rid = rid.split('|', 1)[1]
    p = rid.split('@')
    return f'{p[0]}@{p[1]}' if len(p) >= 3 and p[0] and re.fullmatch(r'\d{4}-\d{2}-\d{2}', p[1]) else None


def load_rings(path=None, now_ms=None):
    """판정 장부(없거나 깨졌으면 빈 것 — 판정이 빠지면 그 카드가 다른 기기에 남을 뿐) · RING_DAYS 지난 것은 뺀다."""
    try:
        with open(path or RINGS, encoding='utf-8') as f:
            st = json.load(f)
        st = st if isinstance(st, dict) else {}
    except (OSError, ValueError):
        st = {}
    old = (now_ms or ms(dt.datetime.now(schedule.KST))) - RING_DAYS * 86400000
    out = {}
    for k in ('rings', 'lines', 'snoozes'):
        v = st.get(k) if isinstance(st.get(k), dict) else {}
        out[k] = {i: r for i, r in v.items() if isinstance(r, dict) and isinstance(r.get('at'), int) and r['at'] >= old}
    return out


def _save_rings(st, path=None):
    path = path or RINGS
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(st, f, ensure_ascii=False, separators=(',', ':'))
    os.replace(tmp, path)


def ring_verdict(st, rid, ring_at=None):
    """그 울림의 판정(없으면 None) — 울림 id 의 판정 · 아니면 그 줄의 완료·넘김이 그 울림 뒤에 났으면 그것(울린 때를 모르면 줄 판정은 안 봄)."""
    r = st['rings'].get(rid)
    if r:
        return r
    line = ring_line(rid)
    lr = st['lines'].get(line) if line else None
    return lr if lr and isinstance(ring_at, int) and ring_at <= lr['at'] else None


def ring_claim(rid, act, by, line=None, ring_at=None, snooze=None, now_ms=None, path=None):
    """단추 하나 → (처음인가, 판정). 처음 = 이 판정을 남김(완료·넘김은 줄 판정도 · 다시는 새 울림도). 다른 기기가 먼저 했으면 (False, 그 판정).
    같은 기기의 되풀이(답을 못 받고 또 보냄)는 처음으로 친다 — 할 일(줄 닫기·넘김 장부)은 다시 해도 같다."""
    now_ms = now_ms or ms(dt.datetime.now(schedule.KST))
    with RING_COND:
        st = load_rings(path, now_ms)
        r = ring_verdict(st, rid, ring_at)
        if r and r.get('by') != by:
            return False, r
        if r:
            return True, r
        r = {'act': act, 'by': by, 'at': now_ms}
        if act == 'again' and isinstance(snooze, dict):
            s = {k: snooze[k] for k in SNOOZE_KEYS if k in snooze}
            if str(s.get('id', '')).startswith('snz-') and len(str(s['id'])) <= 300 and isinstance(s.get('at'), int):
                st['snoozes'][s['id']] = {**{k: str(v)[:300] if isinstance(v, str) else v for k, v in s.items()}, 'by': by, 'made': now_ms}
                r['snooze'] = s['id']
        st['rings'][rid] = r
        if line and act in ('done', 'skip'):
            st['lines'][line] = {'act': act, 'by': by, 'at': now_ms}
        _save_rings(st, path)
        RING_COND.notify_all()
        return True, r


def ring_answer(rid, r, st):
    """판정 하나를 폰이 쓰는 꼴로 — 다시였으면 그 새 울림 항목도(다른 기기가 바로 건다)."""
    by = r.get('by') or '기기 미상'
    out = {'id': rid, 'act': r['act'], 'by': by, 'at': r['at'], 'text': f"이미 판정됨 · {by} · {ACT_KO.get(r['act'], r['act'])}"}
    s = st['snoozes'].get(r.get('snooze') or '')
    if s:
        out['snooze'] = {k: s[k] for k in SNOOZE_KEYS if k in s}
    return out


def rings_wait(asked, wait=0, path=None):
    """카드에 떠 있는 울림들 [(id, 울린 때 ms)] 가운데 판정된 것. 없으면 wait 초까지 기다렸다가(그사이 판정이 나면 바로) 답한다."""
    wait = max(0, min(int(wait or 0), RING_WAIT_MAX))
    end = time.monotonic() + wait
    with RING_COND:
        while True:
            st = load_rings(path)
            got = [ring_answer(i, r, st) for i, a in asked if (r := ring_verdict(st, i, a))]
            left = end - time.monotonic()
            if got or left <= 0:
                return got
            RING_COND.wait(left)


# ───────── 즉시 알림(11-18 · 시험판 · 연구 = 제작자 연구 노트 · 제작 = 알림-즉시-제작.md) ─────────
# 폰이 붙잡아 둔 물음(서버 POST /v1/push {since, wait})에 PC 가 사건을 바로 싣는다. 싣는 것:
#   alert = 알림 도구 알림(분류 · alert.now) 내용째(item = 목록 항목 꼴 · 폰은 바로 울리고 같은 id 로 목록에도) ·
#   list  = 일정이 바뀌어 울릴 목록이 바뀜(신호만 · 폰이 /v1/alarms 를 당김) ·
#   ping  = 승인 대기가 늘어남(approve·modules 칸 · 폰 승인 모듈이 그 자리에서 알림) ·
#   probe = 시험(소리 없음 · 폰이 받자마자 POST /v1/push/ack · PC 가 자기 시계로 왕복을 잰다).
# 잃은 것은 45분 당기기가 같은 id 로 다시 가져온다(폰이 id 로 거름 = 두 번 안 울림). 버스는 서버 메모리 — 번호(seq)는 ms 라 재시작 뒤에도 커진다.
# 장부 = PUSH_LOG 한 곳(send · deliver · ack · beat · cut) · 요약 = alarms.py --push-report.
PUSH_LOG = os.path.join(STATE, 'push.jsonl')
PUSH_LOG_MAX = 8 * 2 ** 20                     # 넘으면 push.jsonl.1 로 밀고 새로
PUSH_KEEP_N, PUSH_KEEP_MS = 300, 86400000      # 버스에 남기는 사건(폰이 끊겼다 다시 물을 때 since 뒤를 준다)
PUSH_WAIT_MAX = 1800                          # 붙잡는 물음 상한(초) — 기본은 서버 설정 push.wait(300)
PUSH_KINDS = ('alert', 'list', 'probe', 'ping')
PUSH_LOST_MS = 10 * 60000                      # probe 를 보낸 뒤 이만큼 ack 가 없으면 «잃음»
PUSH_COND = threading.Condition()
_PUSH = {'seq': int(time.time() * 1000), 'ev': [], 'held': {}, 'gen': 0, 'sent': {}}     # seq 는 켠 때(ms)부터 — 0 은 «처음 물음» 뜻 · held = {기기: 붙잡힌 물음 수} · gen = 깨우기(정책 바뀜) · sent = {id: 보낸 때}
_PUSH_LOG_LOCK = threading.Lock()


def push_log(row, path=None):
    """즉시 알림 장부 한 줄(PC 시계 ms 'pc' 칸을 붙임)."""
    p = path or PUSH_LOG
    row = {'pc': int(time.time() * 1000), **row}
    try:
        with _PUSH_LOG_LOCK:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            if os.path.exists(p) and os.path.getsize(p) > PUSH_LOG_MAX:
                os.replace(p, p + '.1')
            with open(p, 'a', encoding='utf-8', newline='\n') as f:
                f.write(json.dumps(row, ensure_ascii=False, separators=(',', ':')) + '\n')
    except OSError:
        pass


def push_seq():
    with PUSH_COND:
        return _PUSH['seq']


def push_held():
    """지금 붙잡힌 물음 {기기: 수}."""
    with PUSH_COND:
        return {k: v for k, v in _PUSH['held'].items() if v > 0}


def push_emit(kind, body=None, now_ms=None, path=None):
    """사건 하나를 버스에 — 붙잡힌 물음이 바로 깬다. alert 는 body = {'item': 목록 항목} · ping 은 {'approve', 'modules'} · list·probe 는 없음.
    돌려줌 = 사건(id · seq · kind · at = PC ms)."""
    if kind not in PUSH_KINDS:
        raise ValueError(f'kind «{kind}» 는 {"·".join(PUSH_KINDS)}')
    now_ms = now_ms or int(time.time() * 1000)
    with PUSH_COND:
        seq = max(_PUSH['seq'] + 1, now_ms)
        _PUSH['seq'] = seq
        item = (body or {}).get('item') if kind == 'alert' else None
        eid = item['id'] if item else f'{kind[:2]}-{seq}'
        ev = {'id': eid, 'seq': seq, 'kind': kind, 'at': now_ms, **(body or {})}
        _PUSH['ev'] = [e for e in _PUSH['ev'] if now_ms - e['at'] < PUSH_KEEP_MS][-(PUSH_KEEP_N - 1):] + [ev]
        _PUSH['sent'][eid] = now_ms
        if len(_PUSH['sent']) > 4 * PUSH_KEEP_N:
            for k in sorted(_PUSH['sent'], key=_PUSH['sent'].get)[:len(_PUSH['sent']) - 2 * PUSH_KEEP_N]:
                _PUSH['sent'].pop(k, None)
        held = sorted(k for k, v in _PUSH['held'].items() if v > 0)
        PUSH_COND.notify_all()
    push_log({'t': 'send', 'id': eid, 'seq': seq, 'kind': kind, 'held': held}, path)
    return ev


def push_kick():
    """붙잡힌 물음을 사건 없이 깨운다(붙잡기 정책이 바뀜 — 폰이 새 hold 를 바로 받게)."""
    with PUSH_COND:
        _PUSH['gen'] += 1
        PUSH_COND.notify_all()


def push_since(since):
    with PUSH_COND:
        return [e for e in _PUSH['ev'] if e['seq'] > since], _PUSH['seq']


def push_wait(since, wait, device, path=None):
    """since 뒤의 사건 — 없으면 wait 초(상한 PUSH_WAIT_MAX)까지 붙잡고 있다가 사건이 나면 바로 · 정책이 바뀌면(push_kick) 빈 답.
    돌려줌 = (사건들, 지금 seq). 건넨 사건은 장부에 deliver 로."""
    wait = max(0, min(int(wait or 0), PUSH_WAIT_MAX))
    end = time.monotonic() + wait
    dev = device or '기기 미상'
    with PUSH_COND:
        gen = _PUSH['gen']
        _PUSH['held'][dev] = _PUSH['held'].get(dev, 0) + 1
        try:
            while True:
                got = [e for e in _PUSH['ev'] if e['seq'] > since]
                left = end - time.monotonic()
                if got or left <= 0 or _PUSH['gen'] != gen:
                    seq = _PUSH['seq']
                    break
                PUSH_COND.wait(left)
        finally:
            _PUSH['held'][dev] -= 1
    for e in got:
        push_log({'t': 'deliver', 'id': e['id'], 'seq': e['seq'], 'kind': e['kind'], 'device': dev, 'age': int(time.time() * 1000) - e['at']}, path)
    return got, seq


PUSH_ACK_KEYS = ('recv_ms', 'post_ms', 'idle', 'light', 'screen', 'off_min', 'net', 'blocked', 'batt', 'charge', 'plugged', 'holder', 'held_s', 'hold_age_s',
                 'exempt', 'bucket', 'via', 'cut_s', 'fails', 'ver', 'why')


def _st(b):
    """폰이 실은 상태 칸만(폰 시계 시각은 안 받음 — 차이(ms)만)."""
    out = {}
    for k in PUSH_ACK_KEYS:
        v = b.get(k)
        if isinstance(v, bool) or (isinstance(v, (int, float)) and abs(v) < 1e12) or (isinstance(v, str) and len(v) <= 40):
            out[k] = v
    return out


def push_ack(b, device, path=None):
    """POST /v1/push/ack — kind ack(사건을 받음 · id · rtt = PC 가 보낸 때부터 ack 가 닿은 때까지 · PC 시계) · beat(박마다 배터리·상태) · cut(붙잡던 물음이 끊김 · cut_s)."""
    t = b.get('kind') if b.get('kind') in ('ack', 'beat', 'cut') else 'ack'
    row = {'t': t, 'device': device or '기기 미상', **_st(b)}
    if t == 'ack':
        eid = str(b.get('id') or '')[:300]
        with PUSH_COND:
            sent = _PUSH['sent'].get(eid)
            kind = next((e['kind'] for e in reversed(_PUSH['ev']) if e['id'] == eid), None)
        row.update(id=eid, kind=b.get('ev') if isinstance(b.get('ev'), str) else kind)
        if sent:
            row['rtt'] = int(time.time() * 1000) - sent
    push_log(row, path)
    return {'ok': True, **({'rtt': row['rtt']} if 'rtt' in row else {})}


def _pct(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(q * len(xs)))] if xs else None


def push_report(path=None, now_ms=None, days=None):
    """즉시 알림 요약 — 기기마다 probe 왕복(중앙값 · 95% · 최대 · 30초 넘음 · 잃음) · 깊은 Doze 만 · Wi-Fi/셀룰러 · 밤(23~08)/낮 · 방식(fgs·nls) · 배터리 %/시간."""
    rows = []
    try:
        with open(path or PUSH_LOG, encoding='utf-8') as f:
            for ln in f:
                try:
                    rows.append(json.loads(ln))
                except ValueError:
                    pass
    except OSError:
        pass
    now_ms = now_ms or int(time.time() * 1000)
    if days:
        rows = [r for r in rows if now_ms - r.get('pc', 0) <= days * 86400000]
    if not rows:
        return ['즉시 알림 장부 없음']
    sends = {r['id']: r for r in rows if r.get('t') == 'send' and r.get('kind') == 'probe'}
    acks = {}
    for r in rows:
        if r.get('t') == 'ack' and r.get('id') in sends and isinstance(r.get('rtt'), int):
            acks.setdefault((r['id'], r.get('device')), r)
    out = []
    devs = sorted({d for (_, d) in acks} | {d for s in sends.values() for d in s.get('held') or []})

    def line(name, xs):
        xs = [x / 1000 for x in xs]
        return (f'{name} {len(xs)} · 중앙값 {_pct(xs, .5):.2f}초 · 95% {_pct(xs, .95):.2f}초 · 최대 {max(xs):.2f}초 · 30초 넘음 {sum(x > 30 for x in xs)}'
                if xs else f'{name} 0')
    for d in devs:
        mine = [r for (i, dd), r in acks.items() if dd == d]
        held = [s for s in sends.values() if d in (s.get('held') or [])]
        lost = [s for s in held if (s['id'], d) not in acks and now_ms - s.get('pc', now_ms) > PUSH_LOST_MS]
        night = lambda r: (lambda h: h >= 23 or h < 8)(dt.datetime.fromtimestamp(r.get('pc', 0) / 1000, schedule.KST).hour)
        out.append(f'[{d}] probe 보냄(붙잡힌 때) {len(held)} · 받음 {len(mine)} · 잃음 {len(lost)}')
        out.append('  ' + line('전부', [r['rtt'] for r in mine]))
        out.append('  ' + line('깊은 Doze', [r['rtt'] for r in mine if r.get('idle') is True]))
        for h in sorted({r.get('holder') for r in mine if r.get('holder')}):
            out.append('  ' + line(f'방식 {h}', [r['rtt'] for r in mine if r.get('holder') == h]))
        for n in sorted({r.get('net') for r in mine if r.get('net')}):
            out.append('  ' + line(f'망 {n}', [r['rtt'] for r in mine if r.get('net') == n]))
        out.append('  ' + line('밤', [r['rtt'] for r in mine if night(r)]) + ' | ' + line('낮', [r['rtt'] for r in mine if not night(r)]))
        beats = sorted((r for r in rows if r.get('t') == 'beat' and r.get('device') == d and isinstance(r.get('batt'), (int, float))), key=lambda r: r['pc'])
        drops = [(b2['batt'] - b1['batt']) / ((b2['pc'] - b1['pc']) / 3600000) for b1, b2 in zip(beats, beats[1:])
                 if not b1.get('plugged') and not b2.get('plugged') and b2['pc'] > b1['pc'] and b2['batt'] <= b1['batt']]
        if drops:
            out.append(f'  배터리(충전 안 함 박 사이) {len(drops)}구간 · 중앙값 {_pct(drops, .5):.2f}%/시간')
        cuts = [r.get('cut_s') for r in rows if r.get('t') == 'cut' and r.get('device') == d and isinstance(r.get('cut_s'), (int, float))]
        if cuts:
            out.append(f'  붙잡던 물음 끊김 {len(cuts)}번 · 끊긴 길이 중앙값 {_pct(cuts, .5):.0f}초 · 최소 {min(cuts):.0f}초')
    al = [r for r in rows if r.get('t') == 'ack' and r.get('kind') == 'alert' and isinstance(r.get('rtt'), int)]
    if al:
        out.append(line('알림 도구 알림(보냄 → ack)', [r['rtt'] for r in al]))
    return out or ['probe 없음']


def rule_for(s, name, text):
    """기본 ← 파일 ← 과목 ← 글자 순으로 덮는다. 목록에 없는 파일은 꺼진 채 시작한다(글자 칸의 «끔: false» 로 그 줄만 켠다)."""
    own = s['파일'].get(name, s['파일'].get(ALL_FILES))      # '*' = 일정 폴더의 모든 파일(이름을 적은 파일이 먼저)
    r = {**s['기본'], '끔': own is None}
    r.update(own or {})
    r.update(s['과목'].get(text.split(' · ')[0], {}))
    for g in s['글자']:
        if g['포함'] in text:
            r.update({k: v for k, v in g.items() if k != '포함'})
    return r


# ───────── 시각 ─────────
def ms(t):
    return int(t.timestamp() * 1000)


def minutes(hhmm):
    h, m = hhmm.split(':')
    return int(h) * 60 + int(m)


def at_clock(day, hhmm, tz):
    h, m = hhmm.split(':')
    return dt.datetime(day.year, day.month, day.day, int(h), int(m), tzinfo=tz)


def awake(t, due, s):
    """잘 시간에 떨어진 울림은 아침으로. 아침이 마감에 너무 가까우면 잠들기 한 시간 전으로."""
    a, b = s['잘_시간']['부터'], s['잘_시간']['까지']
    f, to, m = minutes(a), minutes(b), t.hour * 60 + t.minute
    if f == to or not ((f <= m or m < to) if f > to else (f <= m < to)):
        return t
    wake_day = t.date() + dt.timedelta(days=1) if f > to and m >= f else t.date()
    morning = at_clock(wake_day, b, t.tzinfo)
    if due - morning >= dt.timedelta(hours=1):
        return morning
    start_day = t.date() - dt.timedelta(days=1) if f > to and m < to else t.date()
    return at_clock(start_day, a, t.tzinfo) - dt.timedelta(hours=1)


def ring_times(due, rule, s):
    """[(칸, 시각)] 이른 것부터. 규칙의 시각이 모두 마감 뒤면 마감 한 시간 전에라도 — 규칙 때문에 안 울리는 일은 없게.
    일정별 울림(rule['울림'])은 정한 그 시각에 — 잘 시간으로 미루지 않는다(사용자가 그 일정에 직접 고른 때)."""
    out = []
    if '울림' in rule:
        for r in rule['울림']:
            if r[0] == 'm':
                kind, t = f'm{r[1]}', due - dt.timedelta(minutes=r[1])
            else:
                kind, t = f'd{r[1]}-{r[2].replace(":", "")}', at_clock(due.date() - dt.timedelta(days=r[1]), r[2], due.tzinfo)
            if t < due:
                out.append((kind, t))
        return sorted(out, key=lambda x: x[1]) or [('last', due - dt.timedelta(hours=1))]
    for n in rule['며칠_전']:
        for hhmm in rule['시각']:
            t = awake(at_clock(due.date() - dt.timedelta(days=n), hhmm, due.tzinfo), due, s)
            if t < due:
                out.append((f'd{n}-{hhmm.replace(":", "")}', t))
    return sorted(out, key=lambda x: x[1]) or [('last', due - dt.timedelta(hours=1))]


def date_text(due, timed):
    day = f'{due.month}-{due.day:02d} ({WD[due.weekday()]})'
    return f'{day} {due:%H:%M}' if timed else day


def head_text(t, due):
    n = (due.date() - t.date()).days
    return {0: '오늘', 1: '내일'}.get(n, f'{n}일 뒤')


# ───────── 줄과 사건 ─────────
def key_of(m):
    """같은 일정의 열쇠 — 날짜가 바뀌어도 같아야 «옮겨짐»을 안다. 손 줄은 내용으로."""
    return m.group(6) or 'h-' + hashlib.sha1(schedule.clean(m.group(5)).encode('utf-8')).hexdigest()[:12]


def lines_of(rows, s, per=None, skips=()):
    """열린 줄 전부와 그 줄의 규칙. 꺼진 줄도 담는다 — 나중에 켜도 «새 일정»으로 몰아 울리지 않게.
    일정별 울림(또는 폰 넘김)이 있으면 그 줄은 그것만(빈 목록 = 안 울림) — 기본·파일·과목·글자 규칙은 안 본다."""
    per = per or {}
    out = []
    for f, _, _, m in rows:
        if not m or m.group(1) in 'xX':
            continue
        text = schedule.clean(m.group(5))
        if PENDING in text:
            continue
        try:
            d = dt.date.fromisoformat(m.group(2))
            h, mi = (int(x) for x in m.group(3).split(':')) if m.group(3) else (23, 59)
            due = dt.datetime(d.year, d.month, d.day, h, mi, tzinfo=schedule.KST)
        except ValueError:
            continue
        key = key_of(m)
        own = per_of(per, key, m.group(2), skips)
        rule = rule_for(s, os.path.basename(f), text) if own is None else {'울림': own, '끔': not own}
        out.append({'key': key, 'date': m.group(2), 'due': due, 'timed': bool(m.group(3)), 'text': text, 'rule': rule})
    return out


def where(ln):
    """알림 누름이 갈 곳 — 그 줄의 날짜·열쇠·캘린더 주소(폰 앱이 그대로 연다 · 볼트 이름은 앱이 붙임)."""
    return {'date': ln['date'], 'key': ln['key'], 'open': OPEN.format(date=ln['date'], key=ln['key'])}


def open_note(path):
    """알림 누름이 갈 노트 — 볼트 경로(«1_수집/…/글.md»)를 폰 brain-server 주소로."""
    return f"{OPEN_HOME}?file={urllib.parse.quote(path, safe='')}"


def blocked_lines(path=None):
    """수집-대기열에서 사용자 손이 필요한 열린 줄 [(시각, 무엇)]."""
    path = path or QUEUE
    if not os.path.exists(path):
        return []
    global QUEUE_LINE
    if QUEUE_LINE is None:
        import roles
        QUEUE_LINE = re.compile(r'^- \[ \] (\S+ \S+) `[^`]*` \(' + re.escape(roles.me()) + r'\) (.+)$')
    with open(path, encoding='utf-8') as f:
        return [m.groups() for m in map(QUEUE_LINE.match, f.read().splitlines()) if m]


def heading(path):
    """글 md 의 머리줄(# 제목) — 못 읽으면 None."""
    try:
        with open(path, encoding='utf-8') as f:
            m = re.search(r'^# (.+)$', f.read(4000), re.M)
    except (OSError, UnicodeDecodeError):
        return None
    return m.group(1).strip() if m else None


def new_notices():
    """판정을 통과해 볼트에 든 공지 글(판정 층이 있는 조리법의 폴더) [(파일 이름, 제목, 게시일, 볼트 경로)]."""
    import roles
    out = []
    for p in glob.glob(os.path.join(HERE, 'collect', '*.json')):
        try:
            with open(p, encoding='utf-8') as f:
                rc = json.load(f)
            if not rc.get('filter') or not str(rc.get('folder', '')).startswith('@'):
                continue
            role, _, sub = rc['folder'][1:].partition('/')
            for a in glob.glob(os.path.join(roles.abs(role), sub, '*.md')):
                name = os.path.basename(a)[:-3]
                if re.match(r'\d{4}-\d{2}-\d{2} ', name) and not re.search(r' \(개정\d+\)$', name):     # «(개정N)» = 수정된 글의 새 판(web-collect revise) — 새 공지가 아니다(날짜가 바뀌었으면 «옮겨짐»이 울린다)
                    title = name[11:]
                    if '_' in title or len(title) >= 120:       # 파일 이름은 «/ : * ? …» 를 «_» 로 바꾸고 120자에서 자른다 — 원제는 글의 머리줄에(제목이 다르면 일정 줄과 «새 공지 ↔ 늦게 앎» 짝이 빗나간다)
                        title = heading(a) or title
                    out.append((name, title, name[:10], os.path.relpath(a, VAULT).replace(os.sep, '/')))
        except (OSError, ValueError, KeyError):
            continue
    return out


def refresh(st, lines, now, s, problems, queue, notices):
    """지난번과 견줘 «바로 알릴 것»을 사건으로 남긴다. 처음 한 번은 전부 본 것으로 친다(몰아 울리지 않게)."""
    first = 'known' not in st
    known = set(st.get('known', []))
    prev = st.get('current', {})
    now_ms = ms(now)
    far = now + dt.timedelta(days=30)
    cfg_id = 'ev-config-' + hashlib.sha1('\n'.join(problems).encode('utf-8')).hexdigest()[:12] if problems else ''
    events = [e for e in st.get('events', []) if now_ms - e['made'] < EVENT_DAYS * 86400000 and (not e['id'].startswith('ev-config-') or e['id'] == cfg_id)]
    on = s['바로']
    cur = {}
    for ln in lines:
        if ln['due'] > now:
            cur.setdefault(ln['key'], []).append(ln['date'])

    def add(kind, mark, title, text, due, wanted=True, ln=None, to=None):
        if not first and mark not in known and wanted:
            events.append({'id': f'ev-{kind}-{hashlib.sha1(mark.encode("utf-8")).hexdigest()[:12]}', 'at': ms(awake(now, due, s)), 'title': title, 'text': text, 'made': now_ms, **(where(ln) if ln else {'open': to} if to else {})})
        known.add(mark)

    # 공지 먼저 — 같은 글의 마감 줄이 함께 처음 보이면 공지 한 번만 울린다. 이름으로 표시해 파일을 옮겨도 다시 안 울린다.
    # 공지마다 한 줄(사용자 11-15 «알림을 누르면 해당 문서로» · 묶음 대신 낱개 고름) — 폰은 한 알림에 «k / n»·넘김으로 하나씩 보인다
    since = (now.date() - dt.timedelta(days=NOTICE_DAYS)).isoformat()
    fresh = [n for n in notices if f'n|{n[0]}' not in known and n[2] >= since] if on['새_공지'] and not first else []
    for n in fresh:
        add('notice', f'n|{n[0]}', n[1], '새 공지', far, to=open_note(n[3]) if len(n) > 3 else None)
    known.update(f'n|{n[0]}' for n in notices)
    fresh_titles = [re.sub(r'^\[[^\]]*\]\s*', '', n[1])[:50] for n in fresh]

    for ln in lines:
        if ln['due'] <= now:
            continue
        mark = f"{ln['key']}|{ln['date']}"
        ringing = not ln['rule'].get('끔')
        gone = [d for d in prev.get(ln['key'], []) if d not in cur[ln['key']]]
        if len(gone) == 1 and len(cur[ln['key']]) == 1:
            add('moved', mark, ln['text'], f"{gone[0][5:]} → {date_text(ln['due'], ln['timed'])}", ln['due'], ringing and on['옮겨짐'], ln)
        elif ring_times(ln['due'], ln['rule'], s)[0][1] <= now:
            # 일정별로 정한 줄은 «늦게 앎»이 아니다 — 사용자가 그 일정을 보고 정했다(손 줄에 열쇠를 처음 붙일 때 새 줄로 보이는 것도 이것으로 조용)
            add('late', mark, ln['text'], date_text(ln['due'], ln['timed']), ln['due'], ringing and on['늦게_앎'] and '울림' not in ln['rule'] and not any(t in ln['text'] for t in fresh_titles), ln)
        else:
            known.add(mark)
    said = set()                        # 출처 여럿이 같은 까닭(구독 아님·사용량 경고 등)을 대기열에 적어도 같은 말은 한 번만 — 폰에 같은 알림이 줄줄이 뜨지 않게
    for stamp, what in queue:
        add('blocked', f'q|{stamp}|{what}', '수집 막힘', what, far, on['막힘'] and what not in said, to=OPEN_HOME)     # 대기열 파일은 폰에 안 줌(3_시스템) — 홈 «수집»이 막힌 출처를 빨갛게 보인다
        said.add(what)
    # 설정이 틀리면 첫 실행이어도 알린다(틀린 채 설치되는 경우)
    if problems and not any(e['id'] == cfg_id for e in events) and f'c|{cfg_id}' not in known:
        extra = f' 외 {len(problems) - 1}칸' if len(problems) > 1 else ''
        events.append({'id': cfg_id, 'at': ms(awake(now, far, s)), 'title': '알림 설정 틀림', 'text': f'{problems[0][:80]}{extra} · 그 칸만 기본값으로 울림', 'made': now_ms, 'open': open_note(note_rel('alarm-settings'))})
    if problems:
        known.add(f'c|{cfg_id}')
    today = now.date().isoformat()
    st['known'] = sorted(k for k in known if k[:2] in ('q|', 'n|', 'c|') or k.rsplit('|', 1)[-1] >= today)
    st['current'] = cur
    st['events'] = events


def extras_ok(e):
    """EXTRA_KEYS 의 꼴 — buttons = 1~3개 · 하나 = 글(40자까지) 또는 {"label": 글, "input": true}(누르면 알림 안 입력창 · 쓴 글이 답) ·
    clear_on_open = 참/거짓. 없으면 통과."""
    def one(x):
        if isinstance(x, dict):
            return set(x) <= {'label', 'input'} and one(x.get('label')) and isinstance(x.get('input', False), bool)
        return isinstance(x, str) and bool(x.strip()) and len(x) <= 40
    b = e.get('buttons')
    if b is not None and not (isinstance(b, list) and 1 <= len(b) <= 3 and all(one(x) for x in b)):
        return False
    return 'clear_on_open' not in e or isinstance(e['clear_on_open'], bool)


def _inbox_ok(e, kind):
    return (isinstance(e, dict) and isinstance(e.get('id'), str) and e['id'].startswith(f'ev-{kind}-') and type(e.get('at')) is int
            and type(e.get('made')) is int and isinstance(e.get('title'), str) and isinstance(e.get('text', ''), str)
            and isinstance(e.get('open', ''), str) and extras_ok(e))


def _inbox_read(p, kind, now_ms):
    try:
        with open(p, encoding='utf-8') as f:
            rows = json.load(f)
    except (OSError, ValueError):
        return []
    return [e for e in rows if _inbox_ok(e, kind) and now_ms - e['made'] < EVENT_DAYS * 86400000] if isinstance(rows, list) else []


def inbox_events(now_ms, path=None):
    """밖에서 낸 «바로» 사건 전부 — 파일 이름이 kind · 꼴이 맞고 EVENT_DAYS 안 것만(폰이 오래 못 당기면 사라짐 · 우리 사건과 같은 셈)."""
    out = []
    for p in sorted(glob.glob(os.path.join(path or INBOX, '*.json'))):
        kind = os.path.basename(p)[:-5]
        if INBOX_KIND.match(kind) and kind not in INBOX_OWN:
            out += _inbox_read(p, kind, now_ms)
    return out


def inbox_put(kind, events, now_ms=None, path=None):
    """내는 쪽(kind)이 사건을 더한다 — 같은 id 는 새것으로 · EVENT_DAYS 지난 것은 뺌 · 꼴이 틀리면 ValueError(아무것도 안 씀).
    폰은 다음 당기기(당겨_오기_분)에 받는다. 돌려줌 = 그 파일의 사건 수."""
    if not INBOX_KIND.match(kind or '') or kind in INBOX_OWN:
        raise ValueError(f'kind «{kind}» 는 못 씀(영문 소문자·숫자 2~16자 · 이 모듈 kind 아님)')
    bad = [e for e in events if not _inbox_ok(e, kind)]
    if bad:
        raise ValueError(f'사건 꼴이 틀림(id ev-{kind}-… · at·made 정수 ms · title 글): {json.dumps(bad[0], ensure_ascii=False)[:120]}')
    now_ms = now_ms or int(time.time() * 1000)
    d = path or INBOX
    p = os.path.join(d, kind + '.json')
    keep = {e['id']: e for e in _inbox_read(p, kind, now_ms)}
    keep.update({e['id']: {k: e[k] for k in INBOX_KEYS if k in e} for e in events})
    rows = sorted(keep.values(), key=lambda e: (e['at'], e['id']))
    os.makedirs(d, exist_ok=True)
    tmp = p + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(rows, f, ensure_ascii=False)
    os.replace(tmp, p)
    return len(rows)


def probes(now, nights=PROBE_NIGHTS):
    """조용한 재기 — 소리도 화면도 없이 폰이 깨어 기록만 한다. 사람이 안 봐도 실제 폰이 재진다."""
    out = []
    for i in range(nights + 1):
        t = dt.datetime.combine(now.date() + dt.timedelta(days=i), PROBE_AT, now.tzinfo)
        if t > now:
            out.append({'id': f'probe-{t:%Y%m%d}', 'at': ms(t), 'title': '', 'text': '', 'probe': True})
    return out[:nights]


def quiet_of(s):
    """잘 시간 ["23:00", "08:00"] — 폰의 하트비트가 이때 깨어나지 않게 같이 보낸다(둘이 같으면 잘 시간 없음)."""
    return [s['잘_시간']['부터'], s['잘_시간']['까지']]


def build(cfg=None, now=None, days=92, rows=None, st=None, queue=None, settings=None, notices=None, per=None, skips=None, rings=None, inbox=None):
    """st 를 주면 사건을 갱신해 함께 낸다(서버). 없으면 시각 예약만(대조용). cfg = 서버 config 의 alarms(mode · probe).
    per = (일정별 울림, 문제들) · skips = 폰 넘김 회차들 · rings = 울림 판정(load_rings) — 안 주면 노트·장부를 읽는다(설정을 손으로 준 시험은 빈 것).
    inbox = 밖에서 낸 사건(inbox_events · 분류 알림 kind sort) — 안 주면 in/ 을 읽는다(설정을 손으로 준 시험은 빈 것) · st 가 있을 때만 싣는다.
    판정된 울림은 빠지고(아직 안 울린 기기도 안 울림) · «다시»가 만든 새 울림은 실린다(두 기기가 같이)."""
    cfg = cfg or {}
    now = now or dt.datetime.now(schedule.KST)
    s, problems = load_settings() if settings is None else settings
    own, more = (load_per_line() if settings is None else ({}, [])) if per is None else per
    skips = (load_skips(today=now.date().isoformat()) if settings is None else set()) if skips is None else skips
    rings = (load_rings(now_ms=ms(now)) if settings is None else {'rings': {}, 'lines': {}, 'snoozes': {}}) if rings is None else rings
    problems = list(problems) + list(more)
    if not s['켬']:                     # 다 끔 = 빈 목록이라 폰도 다음 당기기에 지운다
        return {'v': 1, 'items': [], 'problems': problems, 'pull_minutes': s['당겨_오기_분'], 'quiet': quiet_of(s)}
    until = now + dt.timedelta(days=days)
    lines = lines_of(schedule.parse_all() if rows is None else rows, s, own, skips)
    items = []
    if st is not None:
        refresh(st, lines, now, s, problems, blocked_lines() if queue is None else queue, (new_notices() if notices is None else notices))
        items += [{k: e[k] for k in ('id', 'at', 'title', 'text', 'date', 'key', 'open') if k in e} for e in st['events']]
        mine = {a['id'] for a in items}
        for e in (inbox_events(ms(now)) if settings is None else []) if inbox is None else inbox:
            if e['id'] not in mine:
                items.append({k: e[k] for k in ('id', 'at', 'title', 'text', 'open') + EXTRA_KEYS if k in e})
                mine.add(e['id'])
    for ln in lines:
        if ln['rule'].get('끔'):
            continue
        for kind, t in ring_times(ln['due'], ln['rule'], s):
            if now < t <= until:
                items.append({'id': f"{ln['key']}@{ln['date']}@{kind}", 'at': ms(t), 'title': ln['text'], 'text': f"{head_text(t, ln['due'])} · {date_text(ln['due'], ln['timed'])}", **where(ln)})
    for sid, sn in rings['snoozes'].items():           # 다시 = 새 울림 하나 — 아직 안 왔고 판정 안 난 것
        if isinstance(sn.get('at'), int) and now < dt.datetime.fromtimestamp(sn['at'] / 1000, schedule.KST) <= until and not ring_verdict(rings, sid):
            items.append({k: sn[k] for k in SNOOZE_KEYS if k in sn})
    items = [a for a in items if a['id'] not in rings['rings']]
    if cfg.get('probe', True):
        items += probes(now)
    if cfg.get('mode'):                 # 앱을 다시 설치하지 않고 예약 방식을 바꾼다(clock · idle)
        for a in items:
            a['mode'] = cfg['mode']
    items.sort(key=lambda a: (a['at'], a['id']))
    if len(items) > MAX_ITEMS:
        problems.append(f'울림이 {len(items)}개라 앞 {MAX_ITEMS}개만 예약함')
        items = items[:MAX_ITEMS]
    return {'v': 1, 'items': items, 'problems': problems, 'pull_minutes': s['당겨_오기_분'], 'quiet': quiet_of(s)}


# ───────── 저장 ─────────
def load_state():
    try:
        with open(SEEN, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_state(st):
    os.makedirs(STATE, exist_ok=True)
    tmp = SEEN + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(st, f, ensure_ascii=False)
    os.replace(tmp, SEEN)


def payload(cfg=None):
    """서버가 내줄 바이트와 ETag. 내용이 같으면 같은 태그라 폰이 304 를 받는다."""
    with LOCK:
        st = load_state()
        got = build(cfg, st=st)
        save_state(st)
    data = json.dumps(got, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    return data, '"' + hashlib.sha1(data).hexdigest()[:16] + '"'


def fired(b, by=None):
    """폰이 보고한 «몇 초 늦게 울렸나»를 장부에. by = 보낸 기기(서버가 요청 머리에서 · 옛 앱은 없음) — 줄마다 «by» 칸(두 기기 줄이 섞여도 가른다)."""
    rows = b.get('items') or []
    os.makedirs(STATE, exist_ok=True)
    with LOCK, open(FIRED, 'a', encoding='utf-8', newline='\n') as f:
        for r in rows:
            if by and isinstance(r, dict) and 'by' not in r:
                r = {**r, 'by': by}
            f.write(json.dumps(r, ensure_ascii=False, separators=(',', ':')) + '\n')
    return {'ok': True, 'n': len(rows)}


def report():
    """늦음·놓침. 놓침 = 재기 날짜 사이에 빠진 날(그날 폰이 안 깼거나 아직 보고 전)."""
    rows = []
    if os.path.exists(FIRED):
        with open(FIRED, encoding='utf-8') as f:
            rows = [json.loads(ln) for ln in f if ln.strip()]
    if not rows:
        return print('보고 없음')
    timed = [r for r in rows if not r.get('id', '').startswith('ev-')]
    late = sorted(abs(r.get('late_ms') or 0) / 1000 for r in timed) or [0]
    print(f"시각 울림 {len(timed)}회 · 늦음 중앙값 {late[len(late) // 2]:.1f}초 · 최대 {late[-1]:.1f}초 · 60초 넘음 {sum(x > 60 for x in late)}회")
    now_ones = sorted((r.get('late_ms') or 0) / 60000 for r in rows if r.get('id', '').startswith('ev-'))
    if now_ones:
        print(f'바로 알림 {len(now_ones)}회 · 생긴 뒤 울리기까지 중앙값 {now_ones[len(now_ones) // 2]:.0f}분 · 최대 {now_ones[-1]:.0f}분')
    pr = [r for r in rows if r.get('id', '').startswith('probe-')]
    days = sorted(dt.date(int(r['id'][6:10]), int(r['id'][10:12]), int(r['id'][12:14])) for r in pr)
    if days:
        want = {days[0] + dt.timedelta(days=i) for i in range((days[-1] - days[0]).days + 1)}
        print(f'재기 {len(days)}일 · 깊은 절전에서 깸 {sum(bool(r.get("deep_idle")) for r in pr)}회 · 빠진 날 {sorted(str(d) for d in want - set(days))}')
    for r in rows[-5:]:
        print(r.get('id'), 'late', round((r.get('late_ms') or 0) / 1000, 1), 'deep_idle', r.get('deep_idle'), 'exempt', r.get('exempt'), 'bucket', r.get('bucket'))


def main():
    global SAVE_LAST
    SAVE_LAST = False
    if '--report' in sys.argv:
        return report()
    if '--push-report' in sys.argv:
        days = int(sys.argv[sys.argv.index('--days') + 1]) if '--days' in sys.argv else None
        print('\n'.join(push_report(days=days)))
        return 0
    if '--check' in sys.argv:
        problems = load_settings()[1] + load_per_line()[1]
        print('\n'.join(problems) or '틀린 칸 없음')
        return 1 if problems else 0
    days = int(sys.argv[sys.argv.index('--days') + 1]) if '--days' in sys.argv else 92
    for a in build(days=days)['items']:
        print(dt.datetime.fromtimestamp(a['at'] / 1000, schedule.KST).strftime('%m-%d %H:%M'), a['id'].rsplit('@', 1)[-1].ljust(10), a['title'][:60], '|', a['text'])
    return 0


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    sys.exit(main())
