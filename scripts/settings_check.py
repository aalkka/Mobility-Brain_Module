"""앱 안 볼트 설정(GET·POST /v1/settings · 11-27) 격리 시험 — 임시 볼트에 대본 사본을 두고 서버를 띄워 잰다(본 볼트 무관).
    py -3 -u .claude/skills/mobility/scripts/settings_check.py
잼: 칸마다 POST → 노트 블록·config 가 바뀜(블록 밖 글은 그대로 · 같은 꼴) → 다음 서버 동작(/v1/alarms 의 잘 시간·당김·울림 시각·울릴 파일 · 민감 노트 읽기 · 일정 쓰기)에 반영 · 장부 줄.
"""
# mf:allow-path-file — 시험 픽스처: 임시 볼트 안의 3_시스템 자리를 만들고 잰다(본 볼트 안 건드림)
import datetime
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.parse

MOD = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, MOD)
import server_check as sc  # noqa: E402 — call · src · MOD_FILES 를 같이 씀

fails = []


def ok(name, cond, extra=''):
    print(('통과 ' if cond else '실패 ') + name + (f' — {extra}' if extra else ''), flush=True)
    if not cond:
        fails.append(name)


NOTE = '2_지식/modules/mobility/알림-설정.md'
HEAD = '---\ntitle: 알림 설정\n---\n# 알림 설정\n\n'
TAIL = '\n\n| 칸 | 뜻 |\n|---|---|\n| 켬 | 다 끔 |\n'
BLOCK = ('{\n "켬": true,\n "기본": {"며칠_전": [3, 1], "시각": ["20:00"]},\n "파일": {\n  "가-마감.md": {},\n  "나-일정.md": {"며칠_전": [1]}\n },\n'
         ' "과목": {},\n "글자": [],\n "잘_시간": {"켬": false, "부터": "23:00", "까지": "08:00"},\n'
         ' "바로": {"막힘": true, "옮겨짐": true, "늦게_앎": true, "새_공지": true},\n "당겨_오기_분": 45\n}')


def fixture(port=None):
    """임시 볼트 + 서버 — (서버 프로세스, 열쇠, 볼트, 임시 폴더, 문 번호). 에뮬 시험(손발 앱 tests/appset_test.py)도 이것을 부른다(서버는 127.0.0.1 · 에뮬은 10.0.2.2)."""
    tmp = tempfile.mkdtemp(prefix='set-')
    v = os.path.join(tmp, 'vault')
    s = os.path.join(v, '3_시스템')
    os.makedirs(s)
    for f in ('server.py', 'alarms.py', 'fileops.py', 'roles.py', 'roles.json', 'schedule.py', 'nowin.py') + sc.MOD_FILES[2:]:
        shutil.copy2(sc.src(f), s)
    os.makedirs(os.path.join(v, '.claude', 'skills', 'mobility'))
    shutil.copy2(os.path.join(MOD, '..', 'outside.json'), os.path.join(v, '.claude', 'skills', 'mobility', 'outside.json'))
    for d in ('2_지식/일정', '2_지식/일', '1_수집/받은함', '0_작업', '.obsidian', '3_시스템/ledger'):
        os.makedirs(os.path.join(v, *d.split('/')), exist_ok=True)

    def put(rel, text):
        p = os.path.join(v, *rel.split('/'))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w', encoding='utf-8', newline='') as f:
            f.write(text)

    def read(rel):
        with open(os.path.join(v, *rel.split('/')), encoding='utf-8', newline='') as f:
            return f.read()

    day = datetime.date.today() + datetime.timedelta(days=6)
    put('2_지식/일정/가-마감.md', f'# 가\n\n- [ ] {day.isoformat()} 가 과제 마감\n')
    put('2_지식/일정/나-일정.md', f'# 나\n\n- [ ] {day.isoformat()} 나 약속\n')
    put('2_지식/일정/내-일정.md', '# 내 일정\n')
    put('2_지식/일/비밀.md', '---\ntitle: 비밀\nsensitive: true\n---\n카드\n')
    put(NOTE, HEAD + '```json\n' + BLOCK + '\n```' + TAIL)
    cfgp = os.path.join(s, '_index', 'server', 'config.json')
    os.makedirs(os.path.dirname(cfgp))
    with open(cfgp, 'w', encoding='utf-8') as f:
        json.dump({'port': 1, 'home_wifi': ['옛-와이파이'], 'phone_sensitive': 'show', 'push': {'hold': 'off'}}, f, ensure_ascii=False)
    port = str(port or os.environ.get('SETTINGS_CHECK_PORT') or '18391')
    cfg = os.path.join(tmp, 'claude')
    os.makedirs(cfg)
    env = dict(os.environ, BRAIN_SERVER_PORT=port, PYTHONIOENCODING='utf-8', CLAUDE_CONFIG_DIR=cfg, CLAUDECODE='1',
               BRAIN_RC_BIN=json.dumps([sys.executable, '-c', 'import time; time.sleep(1)']))
    pr = subprocess.Popen([sys.executable, os.path.join(s, 'server.py')], env=env, cwd=v, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                          creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    tok = None
    if True:
        for _ in range(100):
            time.sleep(0.2)
            p = os.path.join(s, '_index', 'server', 'token')
            if os.path.exists(p) and open(p, encoding='utf-8').read().strip():
                tok = open(p, encoding='utf-8').read().strip()
                try:
                    sc.call(port, tok, 'GET', '/v1/ping')
                    break
                except OSError:
                    pass
    return pr, tok, v, tmp, port


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    pr, tok, v, tmp, port = fixture()
    s = os.path.join(v, '3_시스템')
    cfgp = os.path.join(s, '_index', 'server', 'config.json')
    day = datetime.date.today() + datetime.timedelta(days=6)

    def read(rel):
        with open(os.path.join(v, *rel.split('/')), encoding='utf-8', newline='') as f:
            return f.read()
    try:
        ok('서버 뜸', bool(tok))

        def get():
            c, _, b = sc.call(port, tok, 'GET', '/v1/settings')
            return c, json.loads(b)

        def post(k, val):
            c, _, b = sc.call(port, tok, 'POST', '/v1/settings', {'set': k, 'value': val})
            try:
                return c, json.loads(b)
            except ValueError:
                return c, {}

        def alarms_now():
            c, _, b = sc.call(port, tok, 'GET', '/v1/alarms')
            return json.loads(b)

        def block():
            t = read(NOTE)
            ok_out = t.startswith(HEAD + '```json\n') and t.endswith('\n```' + TAIL)
            return json.loads(t[len(HEAD) + 8:-len('\n```' + TAIL)]), ok_out

        def ledger_n():
            n = 0
            for r, _, fs in os.walk(os.path.join(s, 'ledger')):
                for f in fs:
                    with open(os.path.join(r, f), encoding='utf-8', errors='replace') as fh:
                        n += sum(1 for ln in fh if '폰 설정' in ln)
            return n

        c, g = get()
        ok('GET 값', c == 200 and g['ok'] and g['quiet'] == {'on': False, 'from': '23:00', 'to': '08:00'} and g['pull'] == 45
           and g['before'] == {'days': [3, 1], 'times': ['20:00']} and [f['name'] for f in g['files'] if f['on']] == ['가-마감.md', '나-일정.md']
           and g['sensitive'] == 'show' and g['write'] == '내-일정.md' and g['wifi']['list'] == ['옛-와이파이'], json.dumps(g, ensure_ascii=False)[:300])
        a0 = alarms_now()
        n0 = ledger_n()

        # 잘 시간
        c, g = post('quiet', {'on': True, 'from': '22:30', 'to': '07:10'})
        d, same = block()
        a = alarms_now()
        ok('잘 시간 → 노트', c == 200 and d['잘_시간'] == {'켬': True, '부터': '22:30', '까지': '07:10'} and same, str(d.get('잘_시간')))
        ok('잘 시간 → /v1/alarms quiet', json.dumps(a['quiet']) != json.dumps(a0['quiet']) and '22:30' in json.dumps(a['quiet']) and '07:10' in json.dumps(a['quiet']), json.dumps(a['quiet']))
        c, g = post('quiet', {'on': False})
        ok('잘 시간 끔 → 부터·까지 남김', c == 200 and block()[0]['잘_시간'] == {'켬': False, '부터': '22:30', '까지': '07:10'} and g['quiet']['to'] == '07:10')
        ok('잘 시간 틀린 값 400', post('quiet', {'from': '25:00'})[0] == 400 and block()[0]['잘_시간']['부터'] == '22:30')

        # 당김
        c, g = post('pull', 60)
        ok('당김 → 노트·/v1/alarms', c == 200 and block()[0]['당겨_오기_분'] == 60 and alarms_now()['pull_minutes'] == 60)
        ok('당김 범위 밖 400', post('pull', 5)[0] == 400)

        # 미리 알림
        def ring_days(a):
            out = set()
            for it in a['items']:
                if it.get('date') == day.isoformat() and isinstance(it.get('at'), int):
                    t = datetime.datetime.fromtimestamp(it['at'] / 1000)
                    out.add(((day - t.date()).days, t.strftime('%H:%M')))
            return out
        before0 = ring_days(alarms_now())
        c, g = post('before', {'days': [2], 'times': ['09:30']})
        r1 = ring_days(alarms_now())
        ok('미리 알림 → 노트', c == 200 and block()[0]['기본'] == {'며칠_전': [2], '시각': ['09:30']})
        ok('미리 알림 → 울림 시각', (2, '09:30') in r1 and (3, '20:00') not in r1 and (3, '20:00') in before0, f'{sorted(before0)} → {sorted(r1)}')

        # 울릴 일정
        def titles(a):
            return {it.get('title', '') + it.get('text', '') for it in a['items']}
        c, g = post('file', {'name': '가-마감.md', 'on': False})
        t1 = ' '.join(titles(alarms_now()))
        ok('울릴 일정 끔 → 노트', c == 200 and block()[0]['파일']['가-마감.md'] == {'끔': True} and block()[0]['파일']['나-일정.md'] == {'며칠_전': [1]})
        ok('울릴 일정 끔 → 울림에서 빠짐', '가 과제' not in t1 and '나 약속' in t1, t1[:120])
        c, g = post('file', {'name': '가-마감.md', 'on': True})
        ok('울릴 일정 켬 → 돌아옴', c == 200 and block()[0]['파일']['가-마감.md'] == {} and '가 과제' in ' '.join(titles(alarms_now())))
        ok('없는 일정 파일 400', post('file', {'name': '../x.md', 'on': True})[0] == 400)

        # 바로 알림
        c, g = post('now', {'새_공지': False})
        ok('바로 알림 → 노트·GET', c == 200 and block()[0]['바로']['새_공지'] is False and g['now']['새_공지'] is False and g['now']['막힘'] is True)
        sys.path.insert(0, s)
        ok('블록 밖 글·꼴 그대로', block()[1])

        # 집 Wi-Fi
        c, g = post('wifi', {'remove': '옛-와이파이'})
        cf = json.load(open(cfgp, encoding='utf-8'))
        ok('집 Wi-Fi 빼기 → config', c == 200 and cf['home_wifi'] == [] and cf['push'] == {'hold': 'off'} and cf['port'] == 1)
        c, g = post('wifi', 'here')
        ok('집 Wi-Fi 지금 것 더하기(PC Wi-Fi 없으면 409)', (c == 200 and len(json.load(open(cfgp, encoding='utf-8'))['home_wifi']) == 1) or c == 409, str(c))

        # 민감 노트
        q = '/v1/file?path=' + urllib.parse.quote('2_지식/일/비밀.md')
        before_read = sc.call(port, tok, 'GET', q)[0]
        ok('민감 보이기는 403', post('sensitive', 'show')[0] == 403)
        c, g = post('sensitive', 'hide')
        after_read = sc.call(port, tok, 'GET', q)[0]
        ok('민감 숨김 → config·읽기 막힘', c == 200 and g['sensitive'] == 'hide' and before_read == 200 and after_read in (403, 404), f'{before_read}→{after_read}')

        # 일정 쓸 곳
        c, g = post('write', '나-일정.md')
        c2, _, _ = sc.call(port, tok, 'POST', '/v1/schedule', {'date': day.isoformat(), 'text': '앱에서 쓴 일정'})
        ok('일정 쓸 곳 → config·다음 쓰기', c == 200 and g['write'] == '나-일정.md' and c2 == 200 and '앱에서 쓴 일정' in read('2_지식/일정/나-일정.md') and '앱에서 쓴 일정' not in read('2_지식/일정/내-일정.md'))
        ok('없는 파일 400', post('write', '없는.md')[0] == 400)
        ok('모르는 칸 400 · 켬(전부 끄기)은 안 받음', post('켬', False)[0] == 400 and block()[0]['켬'] is True)

        n1 = ledger_n()
        ok('장부에 남음(폰 설정 줄)', n1 - n0 >= 8, f'{n0}→{n1}')
    finally:
        pr.terminate()
        try:
            pr.wait(10)
        except subprocess.TimeoutExpired:
            pr.kill()
        shutil.rmtree(tmp, ignore_errors=True)
    print(f'\n{"실패 " + str(len(fails)) + ": " + ", ".join(fails) if fails else "전부 통과"}')
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
