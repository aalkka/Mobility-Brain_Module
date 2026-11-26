"""서버 모듈 격리 시험 — 임시 볼트에 대본 사본을 두고 돌린다(본 볼트 무관). 찾기만 본 볼트 색인을 읽기 전용으로 잰다(--search).
    py -3 -u .claude/skills/mobility/scripts/server_check.py [--search]
"""
# mf:allow-path-file — 시험 픽스처: 임시 볼트 안의 1_수집·3_시스템 자리를 만들고 잰다(본 볼트 안 건드림)
import datetime
import http.client
import hashlib
import importlib.util
import json
import os
import re
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

MOD = os.path.dirname(os.path.abspath(__file__))
SYS = os.path.normpath(os.path.join(MOD, '..', '..', '..', '..', '3_시스템'))


def src(f):
    """모듈 대본(server·alarms)은 모듈 자리 · 나머지는 볼트 3_시스템"""
    return os.path.join(MOD if f in MOD_FILES else SYS, f)


HAS_TW = os.path.isfile(os.path.join(MOD, 'tabwork.py'))     # 작업 모드 대본이 안 실린 판에서는 그 칸을 «묻기»로만 잰다
MOD_FILES = ('server.py', 'alarms.py', 'core_api.py', 'pair.py', 'ready.py', 'qr.py', 'conf.py', 'notechat_route.py') + (('tabwork.py',) if HAS_TW else ()) + ('vaultwatch.py', 'pdfprint.py')     # 11-17 짝짓기·준비 목록·감싸개
fails = []


def ok(name, cond, extra=''):
    print(('통과 ' if cond else '실패 ') + name + (f' — {extra}' if extra else ''), flush=True)
    if not cond:
        fails.append(name)


def call(port, tok, method, path, body=None, headers=None):
    data = json.dumps(body).encode('utf-8') if body is not None else None
    h = {'Authorization': 'Bearer ' + tok, **(headers or {})} if tok is not None else (headers or {})
    req = urllib.request.Request(f'http://127.0.0.1:{port}{path}', data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        try:
            return e.code, dict(e.headers), e.read()
        except OSError:                             # 서버가 본문을 안 읽고 닫았다(413)
            return e.code, dict(e.headers), b''


def main():
    tmp = tempfile.mkdtemp(prefix='srv-')
    v = os.path.join(tmp, 'vault')
    s = os.path.join(v, '3_시스템')
    os.makedirs(s)
    for f in ('server.py', 'alarms.py', 'fileops.py', 'roles.py', 'roles.json', 'schedule.py', 'nowin.py') + MOD_FILES[2:]:     # nowin = 11-17 server.main 이 부름
        shutil.copy2(src(f), s)
    os.makedirs(os.path.join(v, '.claude', 'skills', 'mobility'))
    shutil.copy2(os.path.join(MOD, '..', 'outside.json'), os.path.join(v, '.claude', 'skills', 'mobility', 'outside.json'))     # 준비 목록 원본(서버가 이 볼트 모듈 자리에서 읽음)
    for d in ('2_지식/일정', '2_지식/일', '2_지식/일/외부뇌', '1_수집/받은함', '1_수집/_lms', '1_수집/배움', '0_작업', '.obsidian'):
        os.makedirs(os.path.join(v, *d.split('/')))

    def put(rel, text):
        os.makedirs(os.path.dirname(os.path.join(v, *rel.split("/"))), exist_ok=True)
        with open(os.path.join(v, *rel.split('/')), 'w', encoding='utf-8', newline='') as f:
            f.write(text)
    put('2_지식/일/보통.md', '---\ntitle: 보통\n---\n본문\n')
    put('2_지식/일/비밀.md', '---\ntitle: 비밀\nsensitive: true\n---\n카드\n')
    put('2_지식/일/산문.md', '---\ntitle: 산문\n---\nsensitive: true 라고 적은 글\n')
    put('2_지식/일/Mixed Case.md', '대소문자\n')
    put('1_수집/배움/원본.md', '원본\n')
    blob = bytes(range(256)) * 12000              # 3,072,000 바이트 — 위치마다 값이 달라 어긋나면 잡힌다 · 이름 표(1분 캐시)가 만들어지기 전에 둔다
    for name in ('강의 원본.pdf', '과제 #1.pdf'):
        with open(os.path.join(v, '1_수집', '배움', name), 'wb') as f:
            f.write(blob)
    put('1_수집/_lms/raw.json', '{}')
    put('2_지식/일정/내-일정.md', '---\ntitle: 내 일정\n---\n# 내 일정\n\n- [ ] 2099-01-10 (토) 10:00 앞\n- [ ] 2099-01-20 (화) 뒤\n\n## 메모\n- 일정 아님\n')
    put('2_지식/장부.md', '# 장부\n')
    port = os.environ.get('SERVER_CHECK_PORT') or '18377'     # 시험을 여럿 함께 돌릴 때 문이 겹치지 않게
    cfg = os.path.join(tmp, 'claude')
    pointer = os.path.join(cfg, 'projects', re.sub(r'[^A-Za-z0-9]', '-', v), 'bridge-pointer.json')
    os.makedirs(os.path.dirname(pointer))
    fake_rc = os.path.join(tmp, 'fake_rc.py')
    argv_out = os.path.join(tmp, 'rc_argv.json')
    with open(fake_rc, 'w', encoding='utf-8') as f:       # 진짜 RC 대신 — 받은 인자·작업 폴더를 남기고 기록을 쓴 뒤 잠든다
        f.write('import json, os, sys, time\n'
                f'json.dump({{"argv": sys.argv[1:], "cwd": os.getcwd(), "code": [k for k in os.environ if k.startswith("CLAUDECODE")]}}, open({argv_out!r}, "w", encoding="utf-8"))\n'
                f'json.dump({{"environmentId": "env_01Fake", "pid": os.getpid()}}, open({pointer!r}, "w", encoding="utf-8"))\n'
                'time.sleep(120)\n')
    env = dict(os.environ, BRAIN_SERVER_PORT=port, PYTHONIOENCODING='utf-8', CLAUDE_CONFIG_DIR=cfg, BRAIN_RC_BIN=json.dumps([sys.executable, fake_rc]), CLAUDECODE='1')
    srv_cfg = os.path.join(s, '_index', 'server', 'config.json')
    os.makedirs(os.path.dirname(srv_cfg))

    def set_cfg(d):                                 # 서버는 설정 파일이 바뀌면 다시 읽는다(재시작 없음)
        with open(srv_cfg, 'w', encoding='utf-8') as f:
            json.dump(d, f)
    set_cfg({'phone_sensitive': 'hide'})            # 아래 옛 시험(민감 = 폰에 안 보임)은 «hide» 로 · «show»(기본)는 «민감 노트 보기 스위치» 칸
    pr = subprocess.Popen([sys.executable, os.path.join(s, 'server.py')], env=env, cwd=v)
    try:
        tok = None
        for _ in range(50):
            time.sleep(0.2)
            p = os.path.join(s, '_index', 'server', 'token')
            if os.path.exists(p) and open(p, encoding='utf-8').read().strip():
                tok = open(p, encoding='utf-8').read().strip()
                try:
                    call(port, tok, 'GET', '/v1/ping')
                    break
                except OSError:
                    pass
        ok('뜬다 · 열쇠 만듦', bool(tok))
        ok('열쇠 없으면 401', call(port, None, 'GET', '/v1/ping')[0] == 401)
        ok('열쇠 틀리면 401', call(port, 'x', 'GET', '/v1/ping')[0] == 401)
        c, _, b = call(port, tok, 'GET', '/v1/ping')
        ok('ping', c == 200 and json.loads(b)['ok'], b.decode()[:120])

        # ── 책갈피(11-18) — 앞뒤 시험의 c·b·j 를 안 건드리게 이름은 k 로 시작 · 기기마다 파일 · 합치기 · 지운 표 · 장부 옮김 · 민감·범위 · 꼴 ──
        kmk = os.path.join(s, '_index', 'work', '책갈피')
        os.makedirs(os.path.join(s, 'ledger'), exist_ok=True)
        os.makedirs(kmk, exist_ok=True)
        know = int(time.time() * 1000)
        with open(os.path.join(kmk, 'pc.json'), 'w', encoding='utf-8') as kf:
            json.dump({'v': 1, 'dev': 'pc', 'marks': [{'id': 'pc1', 'path': '2_지식/일/보통.md', 'at': know - 5000, 'name': 'PC 책갈피', 'pos': {'k': 'scroll', 'line': 3, 'frac': 0.5}},
                                                     {'id': 'pc2', 'path': '2_지식/일/옛이름.md', 'at': know - 9000, 'name': '옛 이름에 꽂음', 'pos': {'k': 'scroll', 'frac': 0.1}}],
                       'gone': [], 'last': {'2_지식/일/보통.md': {'at': know - 4000, 'name': '', 'pos': {'k': 'scroll', 'frac': 0.9}}}}, kf, ensure_ascii=False)
        with open(os.path.join(s, 'ledger', 'ops.jsonl'), 'a', encoding='utf-8') as kf:
            kf.write(json.dumps({'id': 'mv1', 'ts': datetime.datetime.now().astimezone().isoformat(timespec='seconds'), 'op': 'mv', 'by': 'claude', 'src': '2_지식/일/옛이름.md', 'dst': '2_지식/일/보통.md', 'kind': 'file'}, ensure_ascii=False) + '\n')
        kq = '/v1/marks?path=' + urllib.parse.quote('2_지식/일/보통.md') + '&dev=phone'
        kc, _, kb = call(port, tok, 'POST', '/v1/marks', {'dev': 'phone', 'op': 'add', 'path': '2_지식/일/보통.md', 'name': '폰 책갈피', 'pos': {'k': 'scroll', 'frac': 0.3, 'q': '본문'}})
        kmid = json.loads(kb).get('id') if kc == 200 else None
        ok('K1 폰 꽂기 = 그 기기 파일(phone.json)에만', kc == 200 and kmid and os.path.exists(os.path.join(kmk, 'phone.json')) and 'phone1' not in open(os.path.join(kmk, 'pc.json'), encoding='utf-8').read(), kb.decode()[:160])
        kc, _, kb = call(port, tok, 'GET', kq)
        kj = json.loads(kb) if kc == 200 else {}
        knames = sorted(m['name'] for m in kj.get('marks', []))
        ok('K2 문서 하나 = PC·폰 책갈피 합 + 장부 mv 따라감(옛이름 → 보통)', kc == 200 and knames == sorted(['PC 책갈피', '옛 이름에 꽂음', '폰 책갈피']), kb.decode()[:240])
        call(port, tok, 'POST', '/v1/marks', {'dev': 'phone', 'op': 'last', 'path': '2_지식/일/보통.md', 'name': '', 'pos': {'k': 'scroll', 'frac': 0.7}})
        kj = json.loads(call(port, tok, 'GET', kq)[2])
        ok('K3 마지막 본 곳 = 기기마다 칸 · 새것부터 · 이 기기 표시', [(x['dev'], x['mine']) for x in kj['last']] == [('phone', True), ('pc', False)], kj['last'])
        kc, _, kb = call(port, tok, 'POST', '/v1/marks', {'dev': 'phone', 'op': 'del', 'path': '2_지식/일/보통.md', 'id': 'pc1'})
        kj = json.loads(call(port, tok, 'GET', kq)[2])
        ok('K4 폰에서 PC 책갈피 지움 = 폰 파일 지운 표 · PC 파일 그대로 · 합에서 빠짐', kc == 200 and 'pc1' not in [m['id'] for m in kj['marks']]
           and '"pc1"' in open(os.path.join(kmk, 'pc.json'), encoding='utf-8').read(), kb.decode()[:120])
        ok('K5 PC 이름(pc)으로는 못 씀 = 400', call(port, tok, 'POST', '/v1/marks', {'dev': 'pc', 'op': 'add', 'path': '2_지식/일/보통.md', 'pos': {'k': 'none'}})[0] == 400)
        ok('K5 기기 이름 꼴 틀림 = 400', call(port, tok, 'GET', '/v1/marks?path=' + urllib.parse.quote('2_지식/일/보통.md') + '&dev=' + urllib.parse.quote('../x'))[0] == 400)
        ok('K5 자리 꼴 틀림 = 400', call(port, tok, 'POST', '/v1/marks', {'dev': 'phone', 'op': 'add', 'path': '2_지식/일/보통.md', 'pos': 'x'})[0] == 400)
        ok('K5 op 틀림 = 400', call(port, tok, 'POST', '/v1/marks', {'dev': 'phone', 'op': 'zap', 'path': '2_지식/일/보통.md'})[0] == 400)
        ok('K6 민감 노트(숨김 설정) = 403', call(port, tok, 'GET', '/v1/marks?path=' + urllib.parse.quote('2_지식/일/비밀.md') + '&dev=phone')[0] == 403)
        ok('K6 폰 범위 밖(3_시스템) = 403', call(port, tok, 'GET', '/v1/marks?path=' + urllib.parse.quote('3_시스템/roles.json') + '&dev=phone')[0] == 403)
        ok('K7 반쯤 쓴 파일 없음(.tmp 안 남음)', not [n for n in os.listdir(kmk) if n.endswith('.tmp')], os.listdir(kmk))

        # 폰 승인(11-17): 대기 셈은 서버가 · 나머지는 적용기(게이트 코어)가 · 적용기 없으면 ok:false
        ok('ping 에 승인 대기 칸', json.loads(b).get('approve') == {'n': 0, 'oldest': 0, 'frozen': False}, b.decode()[-160:])
        c, _, b = call(port, tok, 'GET', '/v1/approve')
        j = json.loads(b)
        ok('승인 상태: 0 · 적용기 없음', c == 200 and j['ok'] and j['waiting'] == 0 and j['approver'] is False, j)
        c, _, b = call(port, tok, 'GET', '/v1/approve/bundle?run=x')
        ok('적용기 없으면 묶음 길 ok:false', c == 200 and json.loads(b)['ok'] is False and '적용기 없음' in json.loads(b)['why'], b)
        ok('승인 run 꼴 막음', call(port, tok, 'GET', '/v1/approve/bundle?run=' + urllib.parse.quote('../x'))[0] == 400)
        pd = os.path.join(s, '_index', 'bigboss', 'r1', 'pending')
        os.makedirs(pd)
        with open(os.path.join(pd, '01-x.json'), 'w', encoding='utf-8') as f:
            json.dump({'state': 'pending', 'added': (datetime.datetime.now() - datetime.timedelta(minutes=75)).strftime('%Y-%m-%d %H:%M:%S'), 'sha256': 'ab'}, f)
        with open(os.path.join(pd, '02-y.json'), 'w', encoding='utf-8') as f:
            json.dump({'state': 'applied', 'added': '2026-01-01 00:00:00'}, f)
        j = json.loads(call(port, tok, 'GET', '/v1/approve')[2])
        ok('승인 대기 셈(pending 만 · 분)', j['waiting'] == 1 and j['runs'] == [{'run': 'r1', 'n': 1, 'bundles': 1, 'oldest_min': 75, 'cmds': []}], j)
        cd = os.path.join(s, '_index', 'bigboss', 'r1', 'commands')     # 명령 승인(11-20) — 대기·시효 안 것만 셈
        os.makedirs(cd)
        for nm, st, age in (('01-c.json', 'pending', 120), ('02-old.json', 'pending', 13 * 3600), ('03-done.json', 'done', 60)):
            with open(os.path.join(cd, nm), 'w', encoding='utf-8') as f:
                json.dump({'purpose': '시험 명령', 'reason': '분류기가 막음', 'shell': 'powershell', 'cwd': v, 'cmd': 'Write-Output hi', 'timeout': 600,
                           'added_at': int(time.time()) - age, 'state': st}, f, ensure_ascii=False)
        j = json.loads(call(port, tok, 'GET', '/v1/approve')[2])
        ok('명령 승인 대기 셈(pending · 12시간 안만)', j['waiting'] == 2 and j['runs'][0]['bundles'] == 1
           and j['runs'][0]['cmds'] == [{'id': 1, 'purpose': '시험 명령', 'age_min': 2}], j)
        cd2 = os.path.join(s, '_index', 'bigboss', 'r2', 'commands')    # pending/ 없이 명령만 올린 run 도 센다(11-21 · 옛 판은 통째로 건너뜀)
        os.makedirs(cd2)
        with open(os.path.join(cd2, '01-c.json'), 'w', encoding='utf-8') as f:
            json.dump({'purpose': '명령만', 'reason': 'x', 'shell': 'powershell', 'cwd': v, 'cmd': 'Write-Output hi', 'timeout': 600,
                       'added_at': int(time.time()) - 60, 'state': 'pending'}, f, ensure_ascii=False)
        j = json.loads(call(port, tok, 'GET', '/v1/approve')[2])
        ok('명령만 올린 run 도 셈(pending/ 없음)', j['waiting'] == 3 and [r['run'] for r in j['runs']] == ['r1', 'r2'] and j['runs'][1]['bundles'] == 0, j)
        shutil.rmtree(os.path.join(s, '_index', 'bigboss', 'r2'))
        ok('명령 끝점 run·id 꼴 막음', call(port, tok, 'GET', '/v1/approve/command?run=' + urllib.parse.quote('../x') + '&id=1')[0] == 400
           and call(port, tok, 'GET', '/v1/approve/command?run=r1&id=x')[0] == 400 and call(port, tok, 'GET', '/v1/approve/result?run=r1')[0] == 400)
        ap_src = os.path.join(SYS, 'hooks', 'approve', 'approve.py') if os.path.isfile(os.path.join(SYS, 'hooks', 'approve', 'approve.py')) else os.environ.get('APPROVE_SRC')
        if ap_src and os.path.isfile(ap_src):
            os.makedirs(os.path.join(s, 'hooks', 'approve'))
            shutil.copy2(ap_src, os.path.join(s, 'hooks', 'approve', 'approve.py'))
            c, _, b = call(port, tok, 'GET', '/v1/approve/command?run=r1&id=1')
            cj = json.loads(b) if c == 200 else {}
            ok('명령 승인: 요청 바이트 + 도전값(적용기 challenge-cmd)', cj.get('ok') and cj.get('purpose') == 'brain-approve/1 run' and cj.get('req')
               and re.fullmatch(r'[0-9a-f]{64}', cj.get('challenge') or ''), b[:200])
            c, _, b = call(port, tok, 'GET', '/v1/approve/command?run=r1&id=2')
            ok('명령 승인: 시효 지난 요청 = 적용기가 거절', c == 200 and json.loads(b)['ok'] is False and '시효' in json.loads(b).get('why', ''), b)
            c, _, b = call(port, tok, 'GET', '/v1/approve/result?run=r1&id=1')
            ok('명령 결과 = 대기', c == 200 and json.loads(b).get('state') == 'pending', b)
            c, _, b = call(port, tok, 'POST', '/v1/approve/reject', {'run': 'r1', 'id': 1, 'why': '안 시킴'})
            ok('명령 거절 = 요청 닫힘 · 대기에서 빠짐', c == 200 and json.loads(b)['ok'] and json.loads(call(port, tok, 'GET', '/v1/approve/result?run=r1&id=1')[2]).get('state') == 'rejected'
               and json.loads(call(port, tok, 'GET', '/v1/approve')[2])['waiting'] == 1, b)
            c, _, b = call(port, tok, 'POST', '/v1/approve/freeze', {'why': '시험'})
            ok('동결(적용기 장부)', c == 200 and json.loads(b).get('frozen') is True, b)
            ok('동결이 상태에 보임', json.loads(call(port, tok, 'GET', '/v1/approve')[2])['frozen'] is True)
            c, _, b = call(port, tok, 'POST', '/v1/approve/sign', {'message': 'YQ==', 'sig': 'YQ=='})
            ok('서명 길 = 적용기가 거절(서버는 나르기만)', c == 200 and json.loads(b)['ok'] is False and json.loads(b).get('why'), b)
            c, _, b = call(port, tok, 'POST', '/v1/approve/enroll', {'spki': 'eA==', 'label': '시험'})
            ok('등록 요청 = 적용기가 꼴을 잼', c == 200 and json.loads(b)['ok'] is False, b)
            ok('풀기 끝점 없음(콘솔만)', call(port, tok, 'POST', '/v1/approve/unfreeze', {})[0] == 404)
        else:
            print('  (적용기 소스 없음 - 승인 적용기 길 시험 건너뜀 · APPROVE_SRC 로 줄 수 있음)')

        c, _, b = call(port, tok, 'GET', '/v1/list?dir=' + urllib.parse.quote('2_지식/일'))
        names = [x['name'] for x in json.loads(b)['items']]
        ok('목록에 민감 노트 없음', '보통.md' in names and '비밀.md' not in names and '산문.md' in names, str(names))
        c, _, b = call(port, tok, 'GET', '/v1/list?dir=' + urllib.parse.quote('1_수집'))
        names = [x['name'] for x in json.loads(b)['items']]
        ok('원시 JSON 폴더 안 보임', '_lms' not in names and '배움' in names, str(names))

        c, _, b = call(port, tok, 'GET', '/v1/resolve?name=' + urllib.parse.quote('보통'))
        ok('이름 → 경로', c == 200 and json.loads(b)['path'] == '2_지식/일/보통.md', b.decode()[:80])
        res = lambda n: call(port, tok, 'GET', '/v1/resolve?name=' + urllib.parse.quote(n))
        c, _, b = res('비밀')
        ok('민감 노트 이름 = 403(볼트에는 있는데 폰에 안 줌) · 응답에 경로·내용 없음', c == 403 and json.loads(b) == {'error': 'PC에서만'} and not re.search('2_지식|카드|비밀', b.decode()), f'{c} {b.decode()[:80]}')
        c, _, b = res('1_수집/배움/원본|원본')
        ok('경로 꼴 링크', c == 200 and json.loads(b)['path'] == '1_수집/배움/원본.md', b.decode()[:80])
        c, _, b = res('다른/폴더/보통#머리')
        ok('경로가 어긋나면 끝 이름으로', c == 200 and json.loads(b)['path'] == '2_지식/일/보통.md', b.decode()[:80])
        c, _, b = res('2_지식/일/비밀')
        ok('경로 꼴 민감 노트 = 403 · 응답에 경로·내용 없음', c == 403 and json.loads(b) == {'error': 'PC에서만'} and not re.search('2_지식|카드', b.decode()), f'{c} {b.decode()[:80]}')
        rs = [res(n) for n in ('2_지식/일/비밀.md', '2_지식/일/비밀.MD', '2_지식/일/비밀.md#머리', '2_지식/일/비밀.md|별칭')]
        ok('경로째 민감 노트(.md·.MD·#머리·|별칭 · 폰 링크가 경로째 묻는 길 11-20) = 403 · 경로·내용 없음',
           all(c == 403 and json.loads(b) == {'error': 'PC에서만'} and not re.search('2_지식|카드', b.decode()) for c, _, b in rs), [(c, b.decode()[:40]) for c, _, b in rs])
        ok('볼트 밖·시스템 경로 404', res('3_시스템/server')[0] == 404 and res('../../x')[0] == 404)
        c, _, b = res('mixed case')
        ok('대소문자 안 가림', c == 200 and json.loads(b)['path'] == '2_지식/일/Mixed Case.md', b.decode()[:80])
        q = lambda p: '/v1/file?path=' + urllib.parse.quote(p)
        ok('민감 노트 읽기 404', call(port, tok, 'GET', q('2_지식/일/비밀.md'))[0] == 404)
        for bad in ('../secret.txt', '2_지식/../../x', '3_시스템/server.py', '.obsidian/app.json', '2_지식/일/보통.md:s', '2_지식/일/보통.md.', 'C:/Windows/win.ini', '2_지식/일/.x'):
            c = call(port, tok, 'GET', q(bad))[0]
            ok(f'막힘 {bad}', c in (400, 403), str(c))
        c, h, b = call(port, tok, 'GET', q('2_지식/일/보통.md'))
        tag = h.get('ETag')
        ok('읽기 · ETag', c == 200 and tag and '본문' in b.decode())
        ok('If-None-Match → 304', call(port, tok, 'GET', q('2_지식/일/보통.md'), headers={'If-None-Match': tag})[0] == 304)

        # ── 원본(M7): Range · 흘려 보내기 · 이름 찾기 ──
        size = len(blob)
        pdf = q('1_수집/배움/강의 원본.pdf')
        c, h, b = call(port, tok, 'GET', pdf)
        tag2 = h.get('ETag')
        ok('원본 전체 = 200 · 바이트 그대로', c == 200 and b == blob and h.get('Accept-Ranges') == 'bytes' and h.get('Content-Type') == 'application/pdf' and int(h.get('Content-Length')) == size, str(c))

        def rng(spec, **extra):
            return call(port, tok, 'GET', pdf, headers={'Range': spec, **extra})
        c, h, b = rng('bytes=10-19')
        ok('구간 = 206 · Content-Range', c == 206 and b == blob[10:20] and h.get('Content-Range') == f'bytes 10-19/{size}' and h.get('ETag') == tag2, f'{c} {h.get("Content-Range")}')
        c, h, b = rng(f'bytes={size - 5}-')
        ok('끝 열린 구간', c == 206 and b == blob[-5:], str(c))
        c, h, b = rng('bytes=-7')
        ok('끝에서 N', c == 206 and b == blob[-7:] and h.get('Content-Range') == f'bytes {size - 7}-{size - 1}/{size}', str(c))
        c, h, b = rng(f'bytes={size - 3}-{size + 100}')
        ok('끝을 넘긴 구간 = 파일 끝까지', c == 206 and b == blob[-3:] and h.get('Content-Range') == f'bytes {size - 3}-{size - 1}/{size}', str(c))
        ok('파일 밖 시작 = 416', rng(f'bytes={size}-')[0] == 416)
        ok('끝에서 0 = 416', rng('bytes=-0')[0] == 416)
        for odd in ('bytes=abc', 'bytes=0-1,3-4', 'bytes=5-1', 'items=0-1', 'bytes=-'):
            c, _, b = rng(odd)
            ok(f'못 읽는 Range = 전체 200 ({odd})', c == 200 and b == blob, str(c))
        ok('판 확인(1바이트 + If-None-Match) 같음 = 304', rng('bytes=0-0', **{'If-None-Match': tag2})[0] == 304)
        c, h, b = rng('bytes=0-0', **{'If-None-Match': 'old-tag'})
        ok('판 확인 다름 = 206 + 새 판', c == 206 and b == blob[:1] and h.get('ETag') == tag2, str(c))
        with open(os.path.join(v, '1_수집', '배움', '빈.pdf'), 'wb'):
            pass
        c, h, b = call(port, tok, 'GET', q('1_수집/배움/빈.pdf'), headers={'Range': 'bytes=0-'})
        ok('빈 원본 + Range = 200 · 빈 본문', c == 200 and b == b'', str(c))
        c, h, b = call(port, tok, 'GET', q('2_지식/일/Mixed Case.md'), headers={'Range': 'bytes=0-2'})
        ok('md 도 구간', c == 206 and len(b) == 3, str(c))
        ok('민감 노트는 구간도 404', call(port, tok, 'GET', q('2_지식/일/비밀.md'), headers={'Range': 'bytes=0-2'})[0] == 404)
        c, _, b = res('1_수집/배움/강의 원본.pdf|이름')
        ok('경로 꼴 원본 링크', c == 200 and json.loads(b)['path'] == '1_수집/배움/강의 원본.pdf', b.decode()[:90])
        c, _, b = res('다른/자리/강의 원본.pdf')
        ok('원본 경로가 어긋나면 끝 이름으로', c == 200 and json.loads(b)['path'] == '1_수집/배움/강의 원본.pdf', b.decode()[:90])
        c, _, b = res('강의 원본.PDF')
        ok('원본 이름 · 대소문자 안 가림', c == 200 and json.loads(b)['path'] == '1_수집/배움/강의 원본.pdf', b.decode()[:90])
        c, _, b = res('1_수집/배움/과제 #1.pdf')
        ok('이름에 # 이 든 원본 = 온전한 경로로 찾음', c == 200 and json.loads(b)['path'] == '1_수집/배움/과제 #1.pdf', b.decode()[:90])
        c, _, b = res('1_수집/배움/강의 원본.pdf#page=3')
        ok('쪽 표시가 붙은 링크 = 쪽을 떼고 찾음', c == 200 and json.loads(b)['path'] == '1_수집/배움/강의 원본.pdf', b.decode()[:90])
        ok('확장자 없는 이름은 md 만', res('강의 원본')[0] == 404)
        c, _, b = res('raw.json')
        ok('원시 JSON 은 이름으로 안 줌 = 403(볼트에는 있음) · 경로 없음', c == 403 and json.loads(b) == {'error': 'PC에서만'}, f'{c} {b.decode()[:80]}')
        c, _, b = res('비밀.md')
        ok('민감 노트 이름 그대로 = 403 · 경로·내용 없음', c == 403 and json.loads(b) == {'error': 'PC에서만'} and not re.search('2_지식|카드', b.decode()), f'{c} {b.decode()[:80]}')

        # ── 11-06 못 찾는 링크: 403(볼트에는 있는데 폰에 안 줌) / 404(볼트에도 없음 · 이름을 로그에 한 줄) ──
        slog0 = os.path.join(s, '_index', 'server', 'server.log')
        lg = lambda: open(slog0, encoding='utf-8').read()
        sec = {n: res(n) for n in ('3_시스템/server.py', 'alarms.py')}
        ok('폰 범위 밖 3_시스템의 파일 이름 = 403 · 본문은 «PC에서만» 뿐', all(r[0] == 403 and json.loads(r[2]) == {'error': 'PC에서만'} for r in sec.values()), str({n: r[0] for n, r in sec.items()}))
        n0 = lg().count('링크 없음')
        gone, gone_long = res('없는 노트 시험용'), res('긴' + '이' * 300)
        new = [x for x in lg().splitlines() if '링크 없음' in x][-2:]
        ok('볼트에도 없는 이름 = 404 · 본문은 «없음» 뿐', gone[0] == 404 and gone_long[0] == 404 and json.loads(gone[2]) == {'error': '없음'}, f'{gone[0]} {gone_long[0]}')
        ok('404 만 이름을 서버 로그에 한 줄씩(긴 이름은 잘라 씀) · 403 이름은 안 남김', lg().count('링크 없음') == n0 + 2 and new[0].endswith('링크 없음 없는 노트 시험용') and len(new[1]) < 200 and not re.search(r'링크 없음 (비밀|raw|alarms|3_시스템/server\.py)', lg()), str(new)[:160])

        def peak():                               # 서버 프로세스 최고 사용 메모리(Windows)
            import ctypes
            import ctypes.wintypes as w

            class PMC(ctypes.Structure):
                _fields_ = [('cb', w.DWORD), ('faults', w.DWORD), ('peak', ctypes.c_size_t), ('now', ctypes.c_size_t)] + [(f'x{i}', ctypes.c_size_t) for i in range(6)]
            k = ctypes.WinDLL('kernel32', use_last_error=True)
            k.OpenProcess.restype = w.HANDLE
            k.K32GetProcessMemoryInfo.argtypes = (w.HANDLE, ctypes.POINTER(PMC), w.DWORD)
            k.CloseHandle.argtypes = (w.HANDLE,)
            hp = k.OpenProcess(0x1000 | 0x0010, False, pr.pid)
            m = PMC()
            m.cb = ctypes.sizeof(m)
            k.K32GetProcessMemoryInfo(hp, ctypes.byref(m), m.cb)
            k.CloseHandle(hp)
            return m.peak
        big = os.path.join(v, '1_수집', '배움', '큰 원본.pdf')
        with open(big, 'wb') as f:
            f.truncate(120 * 2 ** 20)
        before = peak()
        c, h, b = call(port, tok, 'GET', q('1_수집/배움/큰 원본.pdf'), headers={'Range': f'bytes={60 * 2 ** 20}-{64 * 2 ** 20 - 1}'})
        ok('큰 원본 구간 4MB', c == 206 and len(b) == 4 * 2 ** 20, str(c))
        conn = http.client.HTTPConnection('127.0.0.1', int(port), timeout=120)
        conn.request('GET', q('1_수집/배움/큰 원본.pdf'), headers={'Authorization': 'Bearer ' + tok})
        got = 0
        with conn.getresponse() as r:
            while True:
                chunk = r.read(2 ** 20)
                if not chunk:
                    break
                got += len(chunk)
        conn.close()
        grew = (peak() - before) / 2 ** 20
        ok('큰 원본 전체 120MB = 서버 메모리 20MB 안쪽으로 늘어남', got == 120 * 2 ** 20 and grew < 20, f'받음 {got / 2 ** 20:.0f}MB · 최고값 증가 {grew:.1f}MB')

        c, _, b = call(port, tok, 'POST', '/v1/note', {'path': '2_지식/일/보통.md', 'base': tag, 'text': '---\ntitle: 보통\n---\n폰에서\n'})
        ok('노트 고치기', c == 200, b.decode()[:100])
        ok('고친 내용', '폰에서' in open(os.path.join(v, '2_지식', '일', '보통.md'), encoding='utf-8').read())
        c, _, b = call(port, tok, 'POST', '/v1/note', {'path': '2_지식/일/보통.md', 'base': tag, 'text': '옛 판 위에서 쓴 글'})
        ok('옛 판 위 수정 = 409(PC 우선)', c == 409 and '폰에서' in open(os.path.join(v, '2_지식', '일', '보통.md'), encoding='utf-8').read(), b.decode()[:100])
        ok('원본 층 수정 막힘', call(port, tok, 'POST', '/v1/note', {'path': '1_수집/배움/원본.md', 'base': 'x', 'text': 'y'})[0] == 403)
        ok('민감 노트 수정 막힘', call(port, tok, 'POST', '/v1/note', {'path': '2_지식/일/비밀.md', 'base': 'x', 'text': 'y'})[0] == 403)
        ok('생성 일정 파일 수정 막힘', call(port, tok, 'POST', '/v1/note', {'path': '2_지식/일정/내-일정.md', 'base': 'x', 'text': 'y'})[0] == 403)
        with open(os.path.join(v, '2_지식', '일', '옛글.md'), 'wb') as f:
            f.write('옛 글자'.encode('cp949'))
        c, h, _ = call(port, tok, 'GET', q('2_지식/일/옛글.md'))
        ok('UTF-8 아닌 노트는 폰에서 안 고침', call(port, tok, 'POST', '/v1/note', {'path': '2_지식/일/옛글.md', 'base': h.get('ETag'), 'text': '깨진 글'})[0] == 403)
        ok('md 아닌 쓰기 막힘', call(port, tok, 'POST', '/v1/new', {'path': '2_지식/일/a.exe', 'text': 'y'})[0] == 400)
        ok('새 노트', call(port, tok, 'POST', '/v1/new', {'path': '2_지식/일/새것.md', 'text': '새 글\n'})[0] == 200)
        ok('새 노트 겹침 409', call(port, tok, 'POST', '/v1/new', {'path': '2_지식/일/새것.md', 'text': 'y'})[0] == 409)

        c, _, b = call(port, tok, 'POST', '/v1/memo', {'text': '폰 메모 시험'})
        ok('메모 → 받은함', c == 200 and json.loads(b)['path'].startswith('1_수집/받은함/'), b.decode()[:120])
        memo = lambda text: json.loads(call(port, tok, 'POST', '/v1/memo', {'text': text, 'at': '2026-11-04 120000'})[2])['path']
        p1, p2, p3 = memo('같은 때 하나'), memo('같은 때 둘'), memo('같은 때 하나')
        ok('메모 = 적은 때 이름 · 같은 초에 겹치지 않음 · 다시 보내도 한 벌', p1 == p3 and p1 != p2 and '2026-11-04 120000' in p1, f'{p1} · {p2}')
        ops = open(os.path.join(s, 'ledger', 'ops.jsonl'), encoding='utf-8').read()
        ok('장부에 phone', '"by": "phone"' in ops and ops.count('\n') >= 3, str(ops.count('\n')))

        c, _, b = call(port, tok, 'POST', '/v1/schedule', {'date': '2099-01-15', 'time': '09:00', 'end': '10:00', 'text': '가운데 · 시험'})
        ok('일정 더하기', c == 200, b.decode()[:120])
        lines = open(os.path.join(v, '2_지식', '일정', '내-일정.md'), encoding='utf-8').read().split('\n')
        i = [n for n, x in enumerate(lines) if '2099' in x]
        ok('날짜 순 자리', '앞' in lines[i[0]] and '가운데' in lines[i[1]] and '뒤' in lines[i[2]], str(lines[i[0]:i[-1] + 1]))
        call(port, tok, 'POST', '/v1/schedule', {'date': '2099-01-15', 'time': '09:00', 'end': '10:00', 'text': '가운데 · 시험'})
        ok('같은 일정 다시 보내도 한 줄', open(os.path.join(v, '2_지식', '일정', '내-일정.md'), encoding='utf-8').read().count('가운데') == 1)
        ok('일정 잘못된 날짜 400', call(port, tok, 'POST', '/v1/schedule', {'date': '2099-13-40', 'text': 'x'})[0] == 400)
        c, _, b = call(port, tok, 'GET', '/v1/schedule?days=400')
        ok('일정 읽기(먼 날짜는 범위 밖)', c == 200 and json.loads(b)['items'] == [])
        want = lines[i[1]]
        c, _, b = call(port, tok, 'POST', '/v1/schedule/check', {'file': '2_지식/일정/내-일정.md', 'line': want, 'done': True})
        ok('체크', c == 200 and want.replace('- [ ]', '- [x]', 1) in open(os.path.join(v, '2_지식', '일정', '내-일정.md'), encoding='utf-8').read(), b.decode()[:100])
        ok('바뀐 줄 체크 409', call(port, tok, 'POST', '/v1/schedule/check', {'file': '2_지식/일정/내-일정.md', 'line': want, 'done': True})[0] == 409)
        # 폰 캘린더 병합 — 기준 판 없이 온 글은 파일을 통째로 다시 넣지 않는다(11-24 내-일정 겹침: 머리·일정 23줄이 두 번)
        mp = os.path.join(v, '2_지식', '일정', '내-일정.md')
        pc0 = open(mp, encoding='utf-8', newline='').read()
        stale = '---\ntitle: 내 일정\nupdated: 2099-01-01\n---\n# 내 일정\n\n- [x] 2099-01-10 (토) 10:00 앞\n- [ ] 2099-01-12 (월) 폰에서 적음 ^my-a1\n- [ ] 2099-01-20 (화) 뒤\n\n## 메모\n- 일정 아님\n'
        c, _, b = call(port, tok, 'POST', '/v1/schedule/merge', {'path': '2_지식/일정/내-일정.md', 'base': '', 'text': stale})
        got = open(mp, encoding='utf-8', newline='').read()
        gl = got.split('\n')
        ok('기준 판 없는 병합 — 없는 일정 줄만 한 줄', c == 200 and json.loads(b)['took'] == 1 and len(gl) == len(pc0.split('\n')) + 1 and got.count('폰에서 적음') == 1, b.decode()[:120])
        ok('기준 판 없는 병합 — 머리·제목·일정이 안 겹침', got.count('title: 내 일정') == 1 and got.count('# 내 일정') == 1 and got.count(' 앞') == 1 and got.count('가운데') == 1 and 'updated: 2099-01-01' not in got)
        ok('기준 판 없는 병합 — 폰 글의 앞 줄 뒤에', gl.index('- [ ] 2099-01-12 (월) 폰에서 적음 ^my-a1') == [i for i, s in enumerate(gl) if s.endswith(' 앞')][0] + 1)
        ok('기준 판 없는 병합 — 체크 칸만 다르면 PC 판', json.loads(b)['dropped'] == 1 and '- [ ] 2099-01-10 (토) 10:00 앞' in gl)
        c, _, b = call(port, tok, 'POST', '/v1/schedule/merge', {'path': '2_지식/일정/내-일정.md', 'base': '', 'text': stale})
        ok('기준 판 없는 병합 — 다시 보내도 그대로', c == 200 and json.loads(b)['took'] == 0 and open(mp, encoding='utf-8', newline='').read() == got)
        edit = got.replace('폰에서 적음', '폰에서 고침')
        c, _, b = call(port, tok, 'POST', '/v1/schedule/merge', {'path': '2_지식/일정/내-일정.md', 'base': got, 'text': edit})
        ok('기준 판 있는 병합은 그대로(바꾼 줄만)', c == 200 and json.loads(b)['took'] == 1 and open(mp, encoding='utf-8', newline='').read() == edit, b.decode()[:120])
        c, _, b = call(port, tok, 'POST', '/v1/schedule/merge', {'path': '2_지식/일정/폰이-만든.md', 'base': '', 'text': '# 폰이 만든\n\n- [ ] 2099-02-01 (일) 새 파일\n'})
        ok('PC 에 없는 파일은 폰 글 그대로 만듦', c == 200 and open(os.path.join(v, '2_지식', '일정', '폰이-만든.md'), encoding='utf-8', newline='').read() == '# 폰이 만든\n\n- [ ] 2099-02-01 (일) 새 파일\n')
        os.remove(os.path.join(v, '2_지식', '일정', '폰이-만든.md'))
        with open(mp, 'w', encoding='utf-8', newline='') as f:   # 아래 알림 칸들이 보던 판으로
            f.write(pc0)
        # 알림 — 설정 노트를 요청 때마다 읽는다 · 틀린 값은 기본값으로 울리고 알린다
        app0 = json.loads(call(port, tok, 'GET', '/v1/ping')[2]).get('app')      # 앱이 아직 한 번도 안 당긴 때(아래 11-13 칸에서 봄)
        near = (datetime.date.today() + datetime.timedelta(days=20)).isoformat()
        put('2_지식/일정/LMS-마감.md', f'- [ ] {near} 23:59 물리 · 과제 ^lms-asg-1\n')
        c, h, b = call(port, tok, 'GET', '/v1/alarms')
        ids = [a['id'] for a in json.loads(b)['items']]
        ok('알림 목록 = 3일·1일 전 + 재기 3', c == 200 and sum(x.startswith('lms-asg-1@') for x in ids) == 2 and sum(x.startswith('probe-') for x in ids) == 3, str(ids)[:120])
        ok('알림 같으면 304', call(port, tok, 'GET', '/v1/alarms', headers={'If-None-Match': h['ETag']})[0] == 304)
        ok('알림 열쇠 없으면 401', call(port, None, 'GET', '/v1/alarms')[0] == 401)
        put('2_지식/modules/mobility/알림-설정.md', '```json\n{"기본": {"며칠_전": [5]}, "당겨_오기_분": 45}\n```\n')
        d = json.loads(call(port, tok, 'GET', '/v1/alarms')[2])
        ok('설정을 고치면 재시작 없이 반영', any('@d5-2000' in a['id'] for a in d['items']) and d['pull_minutes'] == 45)
        base = call(port, tok, 'GET', '/v1/file?path=' + urllib.parse.quote('2_지식/modules/mobility/알림-설정.md'))[1]['ETag']
        c, _, b = call(port, tok, 'POST', '/v1/note', {'path': '2_지식/modules/mobility/알림-설정.md', 'base': base, 'text': '```json\n{"기본": {"며칠_전": [6]}}\n```\n'})
        d = json.loads(call(port, tok, 'GET', '/v1/alarms')[2])
        ok('폰에서 설정을 고쳐도 반영(쓰기 규칙 그대로)', c == 200 and any('@d6-2000' in a['id'] for a in d['items']), b.decode()[:100])
        put('2_지식/modules/mobility/알림-설정.md', '```json\n{"기본": {"시각": ["25:00"]}}\n```\n')
        d = json.loads(call(port, tok, 'GET', '/v1/alarms')[2])
        ok('틀린 설정 = 기본값으로 울리고 알림', d['problems'] and any('@d3-2000' in a['id'] for a in d['items']) and any(a['title'] == '알림 설정 틀림' for a in d['items']), str(d['problems'])[:120])
        c, _, b = call(port, tok, 'POST', '/v1/alarms/fired', {'items': [{'id': 'probe-1', 'late_ms': 900}]})
        ok('폰 보고는 장부에', c == 200 and os.path.exists(os.path.join(s, '_index', 'alarms', 'fired.jsonl')))
        # ── 11-13: 폰 알림 앱 마지막 당김(볼트 상태 줄) · «끝냄» ──
        ok('당김 전에도 ping app 이 있었음(종은 늘 보임) · at 없음', isinstance(app0, dict) and app0.get('at') is None and app0.get('on') in (True, False) and app0.get('late') is False, str(app0))
        d = json.loads(call(port, tok, 'GET', '/v1/alarms', headers={'X-Brain-App': '4'})[2])
        app = json.loads(call(port, tok, 'GET', '/v1/ping')[2]).get('app') or {}
        ok('당김이 ping 에(판 · 늦지 않음) · 재시작 대비 파일', app.get('ver') == 4 and abs(app.get('at', 0) - time.time() * 1000) < 60000 and app.get('late') is False
           and os.path.exists(os.path.join(s, '_index', 'server', 'phone-app.json')), str(app))
        call(port, tok, 'GET', '/v1/alarms', headers={'X-Brain-App': '../x'})
        ok('판 머리가 숫자가 아니면 판 없음', json.loads(call(port, tok, 'GET', '/v1/ping')[2])['app']['ver'] is None)
        lms = os.path.join(v, '2_지식', '일정', 'LMS-마감.md')
        aid = next(a['id'] for a in d['items'] if a['id'].startswith('lms-asg-1@'))
        c, _, b = call(port, tok, 'POST', '/v1/alarms/act', {'items': [{'id': aid, 'at': 1}, {'id': 'probe-1'}, {'id': 'x@bad@d3'}]})
        got = [x['got'] for x in json.loads(b)['items']] if c == 200 else b
        ok('끝냄 = 그 줄 [x] · 꼴이 아닌 id 는 bad', got == ['done', 'bad', 'bad'] and open(lms, encoding='utf-8').read().startswith(f'- [x] {near} 23:59 물리'), str(got))
        d = json.loads(call(port, tok, 'GET', '/v1/alarms')[2])
        ok('끝낸 줄은 알림 목록에서 빠짐', not any(a['id'].startswith('lms-asg-1@') for a in d['items']))
        ok('또 보내면 gone(폰은 그만 보냄)', [x['got'] for x in json.loads(call(port, tok, 'POST', '/v1/alarms/act', {'items': [{'id': aid}]})[2])['items']] == ['gone'])
        mine = os.path.join(v, '2_지식', '일정', '내-일정.md')
        with open(mine, 'a', encoding='utf-8', newline='') as f:
            f.write(f'- [ ] {near} (월) 손 줄 · 옮김 ^my-1\r\n- [ ] {near} 같은 글\r\n- [ ] 2099-02-01 같은 글\r\n')
        c, _, b = call(port, tok, 'POST', '/v1/alarms/act', {'items': [{'id': 'my-1@2000-01-01@d3-2000'}]})
        ok('날짜가 옮겨진 줄도 열쇠가 하나면 끝냄', c == 200 and json.loads(b)['items'][0]['got'] == 'done' and f'- [x] {near} (월) 손 줄 · 옮김 ^my-1' in open(mine, encoding='utf-8').read(), b.decode()[:100])
        spec = importlib.util.spec_from_file_location('sched_t', os.path.join(s, 'schedule.py'))
        sched_t = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sched_t)
        hk = 'h-' + hashlib.sha1(sched_t.clean('같은 글').encode('utf-8')).hexdigest()[:12]
        c, _, b = call(port, tok, 'POST', '/v1/alarms/act', {'items': [{'id': f'{hk}@2099-02-01@d1-2000'}]})
        body = open(mine, encoding='utf-8', newline='').read()
        ok('손 줄(블록 id 없음)은 내용 열쇠 + 날짜로 그 줄만 · LF·CRLF 섞인 파일도 줄끝 그대로', json.loads(b)['items'][0]['got'] == 'done' and '- [x] 2099-02-01 같은 글\r\n' in body and f'- [ ] {near} 같은 글\r\n' in body, b.decode()[:100])
        with open(mine, 'a', encoding='utf-8', newline='') as f:
            f.write(f'- [ ] {near} 칸으로 ^al-2\n')
        c, _, b = call(port, tok, 'POST', '/v1/alarms/act', {'items': [{'id': 'ev-다른-꼴', 'key': 'al-2', 'date': near}]})
        ok('항목에 key·date 칸이 있으면 id 꼴과 무관하게 그것으로', json.loads(b)['items'][0]['got'] == 'done' and f'- [x] {near} 칸으로 ^al-2' in open(mine, encoding='utf-8').read(), b.decode()[:100])
        with open(mine, 'a', encoding='utf-8', newline='') as f:
            f.write(f'- [ ] {near} 넘길 것 ^al-3\n')
        before = open(mine, encoding='utf-8', newline='').read()
        c, _, b = call(port, tok, 'POST', '/v1/alarms/act', {'items': [{'id': f'al-3@{near}@d1-2000', 'act': 'skip', 'title': '넘길 것'}, {'id': f'al-3@{near}@d1-2000', 'act': 'x'}]})
        skips = os.path.join(s, '_index', 'alarms', 'skips.json')
        ok('넘김 = 줄은 그대로 · 그 회차를 알림 모듈 장부(skips.json)에 · 모르는 act 는 bad', [x['got'] for x in json.loads(b)['items']] == ['skipped', 'bad'] and open(mine, encoding='utf-8', newline='').read() == before
           and f'al-3@{near}' in (open(skips, encoding='utf-8').read() if os.path.exists(skips) else ''), b.decode()[:100])
        done_log = os.path.join(s, '_index', 'alarms', 'acts.jsonl')
        log_text = open(done_log, encoding='utf-8').read() if os.path.exists(done_log) else ''
        ok('단추는 장부에(act · 결과 · 파일)', '"act":"done","got":"done"' in log_text and '내-일정.md' in log_text and '"act":"skip","got":"skipped"' in log_text)
        # ── 11-16 두 기기(사용자 «두 알림 모두 받게 하고 … 더 먼저 선택한 쪽을 우선으로 … 다른 기기에서도 사라지게») ──
        P, T = {'X-Brain-Device': urllib.parse.quote('시험폰')}, {'X-Brain-Device': urllib.parse.quote('시험탭')}
        call(port, tok, 'GET', '/v1/alarms', headers={**P, 'X-Brain-App': '25'})
        call(port, tok, 'GET', '/v1/alarms', headers={**T, 'X-Brain-App': '24'})
        app = json.loads(call(port, tok, 'GET', '/v1/ping')[2]).get('app') or {}
        seen = json.load(open(os.path.join(s, '_index', 'server', 'phone-app.json'), encoding='utf-8'))
        ok('기기마다 당김·판(서로 안 덮음) · 맨 위 = 가장 최근 기기', app.get('devices', {}).get('시험폰', {}).get('ver') == 25 and app['devices'].get('시험탭', {}).get('ver') == 24
           and app.get('ver') == 24 and app.get('device') == '시험탭' and set(seen['devices']) >= {'시험폰', '시험탭'}, str(app)[:200])
        call(port, tok, 'POST', '/v1/alarms/fired', {'items': [{'id': 'probe-2', 'late_ms': 5}]}, headers=T)
        frows = [json.loads(x) for x in open(os.path.join(s, '_index', 'alarms', 'fired.jsonl'), encoding='utf-8') if x.strip()]
        ok('울림 보고 줄에 보낸 기기(by) · 옛 앱 줄은 그대로', frows[-1].get('by') == '시험탭' and 'by' not in frows[0], str(frows[-1]))
        call(port, tok, 'POST', '/v1/diag', {'lines': ['망 wifi 두기기']}, headers=P)
        slog_text = open(os.path.join(s, '_index', 'server', 'server.log'), encoding='utf-8').read()
        ok('진단·요청 줄 끝에 기기', '폰 망 wifi 두기기 · 시험폰' in slog_text and re.search(r'POST /v1/diag 200 \d+ms · 시험폰', slog_text) is not None)
        ok('이상한 기기 머리 = 기기 미상(제어 문자·깨진 UTF-8)', call(port, tok, 'GET', '/v1/alarms', headers={'X-Brain-Device': '%FF%FE'})[0] == 200
           and json.loads(call(port, tok, 'GET', '/v1/ping')[2])['app']['device'] == '기기 미상')
        with open(mine, 'a', encoding='utf-8', newline='') as f:
            f.write(f'- [ ] {near} 23:59 두 기기 시험 ^dv-1\n')
        ids = [a['id'] for a in json.loads(call(port, tok, 'GET', '/v1/alarms', headers=P)[2])['items']]
        r1, r2 = f'dv-1@{near}@d3-2000', f'dv-1@{near}@d1-2000'
        ok('두 기기가 같은 울림 id 를 받음', r1 in ids and r2 in ids, str([x for x in ids if x.startswith('dv-')]))
        rings = lambda h, items, wait=0: call(port, tok, 'POST', '/v1/rings', {'items': items, 'wait': wait}, headers=h)
        c, _, b = rings(T, [{'id': r1, 'at': 1}])
        ok('판정 전 물음 = 빈 답', c == 200 and json.loads(b)['items'] == [], b.decode()[:100])
        import threading
        held = {}

        def hold():
            t0 = time.time()
            held['r'] = rings(T, [{'id': r1, 'at': 1}], 10)
            held['s'] = time.time() - t0
        th = threading.Thread(target=hold)
        th.start()
        time.sleep(1.5)
        snz = {'id': f'snz-1|{r1}', 'at': int(time.time() * 1000) + 3600000, 'title': '두 기기 시험', 'text': '다시', 'key': 'dv-1', 'date': near}
        c, _, b = call(port, tok, 'POST', '/v1/alarms/act', {'items': [{'id': r1, 'ring': r1, 'ring_at': 1, 'act': 'again', 'at': 2, 'key': 'dv-1', 'date': near, 'snooze': snz}]}, headers=P)
        ok('다시(먼저) = again', c == 200 and json.loads(b)['items'][0]['got'] == 'again', b.decode()[:120])
        th.join(15)
        hb = json.loads(held['r'][2])['items'] if 'r' in held else []
        ok('붙잡은 물음은 다른 기기 판정 즉시 답(1.5초 뒤 판정 → 3초 안) · 다시면 새 울림도', 'r' in held and held['s'] < 3 and bool(hb) and hb[0]['by'] == '시험폰' and hb[0]['act'] == 'again'
           and hb[0]['snooze']['id'] == snz['id'], f"{held.get('s', 0):.2f}s {hb}")
        t0 = time.time()
        rings(T, [{'id': 'nothing-here'}], 2)
        ok('판정 없으면 wait 초 뒤 빈 답', 1.8 < time.time() - t0 < 4, f'{time.time() - t0:.2f}s')
        before_skips = open(skips, encoding='utf-8').read() if os.path.exists(skips) else ''
        c, _, b = call(port, tok, 'POST', '/v1/alarms/act', {'items': [{'id': r1, 'ring': r1, 'ring_at': 1, 'act': 'skip', 'at': 3, 'key': 'dv-1', 'date': near}]}, headers=T)
        a2 = json.loads(b)['items'][0]
        ok('뒤에 온 다른 기기 단추 = already · 하지 않음(넘김 장부 그대로) · «이미 판정됨 · 기기 · 결과» · 새 울림', a2['got'] == 'already' and a2['by'] == '시험폰' and a2['act'] == 'again'
           and a2['text'] == '이미 판정됨 · 시험폰 · 다시' and a2['snooze']['id'] == snz['id'] and (open(skips, encoding='utf-8').read() if os.path.exists(skips) else '') == before_skips, str(a2))
        ok('같은 기기가 또 보냄 = 처음 것 그대로(already 아님)', json.loads(call(port, tok, 'POST', '/v1/alarms/act', {'items': [{'id': r1, 'ring': r1, 'act': 'again', 'snooze': snz}]}, headers=P)[2])['items'][0]['got'] == 'again')
        ok('옛 앱(기기 머리 없음)도 다른 기기 = already · 줄 그대로', json.loads(call(port, tok, 'POST', '/v1/alarms/act', {'items': [{'id': r1, 'act': 'done'}]})[2])['items'][0]['got'] == 'already'
           and f'- [ ] {near} 23:59 두 기기 시험 ^dv-1' in open(mine, encoding='utf-8').read())
        items = json.loads(call(port, tok, 'GET', '/v1/alarms', headers=T)[2])['items']
        got_ids = [a['id'] for a in items]
        ok('목록: 판정된 울림 빠짐 · 다시의 새 울림 실림(두 기기 같은 id)', r1 not in got_ids and snz['id'] in got_ids and r2 in got_ids
           and next(a for a in items if a['id'] == snz['id'])['key'] == 'dv-1', str([x for x in got_ids if 'dv-' in x]))
        c, _, b = call(port, tok, 'POST', '/v1/alarms/act', {'items': [{'id': r1, 'ring': snz['id'], 'ring_at': snz['at'], 'act': 'done', 'key': 'dv-1', 'date': near}]}, headers=T)
        ok('새 울림을 탭이 완료 = 그 줄 [x]', json.loads(b)['items'][0]['got'] == 'done' and f'- [x] {near} 23:59 두 기기 시험 ^dv-1' in open(mine, encoding='utf-8').read(), b.decode()[:120])
        early, late_ms = int(time.time() * 1000) - 60000, int(time.time() * 1000) + 60000
        got = json.loads(rings(P, [{'id': r2, 'at': early}, {'id': f'dv-1@{near}@last', 'at': late_ms}, {'id': snz['id'], 'at': snz['at']}])[2])['items']
        ok('줄 완료 = 그 전에 울린 그 줄의 다른 울림도 판정 · 뒤에 울린 것은 아님', sorted(x['id'] for x in got) == sorted([r2, snz['id']]) and all(x['by'] == '시험탭' and x['act'] == 'done' for x in got), str(got))
        c, _, b = call(port, tok, 'POST', '/v1/alarms/act', {'items': [{'id': 'ev-notice-dv1', 'act': 'skip', 'ring_at': 5}, {'id': 'ev-notice-dv1', 'act': 'again'}, {'act': 'again'}]}, headers=P)
        ok('사건 울림 넘김 = noted(줄 없음) · 같은 기기 되풀이 그대로 · id 없으면 bad', [x['got'] for x in json.loads(b)['items']] == ['noted', 'noted', 'bad']
           and json.loads(call(port, tok, 'POST', '/v1/alarms/act', {'items': [{'id': 'ev-notice-dv1', 'act': 'again'}]}, headers=T)[2])['items'][0]['got'] == 'already', b.decode()[:160])
        acts_rows = [json.loads(x) for x in open(done_log, encoding='utf-8') if x.strip()]
        ok('단추 장부에 기기 · already 는 먼저 한 기기', any(r.get('device') == '시험탭' and r['got'] == 'already' and r.get('first') == '시험폰' for r in acts_rows), str(acts_rows[-1]))
        # ── 11-18 즉시 알림(시험판 · /v1/push 붙잡기 · PC 가 붙잡을 때 정함 · alert 내용째 · list 신호 · probe·ack) ──
        pj = lambda h=None: json.loads(call(port, tok, 'GET', '/v1/alarms', headers=h or P)[2])
        push = lambda body, h=None: call(port, tok, 'POST', '/v1/push', body, headers=h or P)
        a0 = pj()
        ok('U1 목록에 push 칸 = 설정 없으면 끔(hold false · fgs · 300초 · seq)', a0.get('push', {}).get('hold') is False and a0['push'].get('holder') == 'fgs'
           and a0['push'].get('wait') == 300 and isinstance(a0['push'].get('seq'), int) and a0['push'].get('why') == '끔', str(a0.get('push')))
        tag0 = call(port, tok, 'GET', '/v1/alarms', headers=P)[1].get('ETag')
        set_cfg({'phone_sensitive': 'hide', 'push': {'hold': 'always', 'wait': 4, 'tick': 0.5, 'holder': {'시험탭': 'nls', '*': 'fgs'}}})
        a1 = pj()
        tag1 = call(port, tok, 'GET', '/v1/alarms', headers=P)[1].get('ETag')
        ok('U2 늘 붙잡기 = hold true · 기기마다 방식(탭 nls) · 정책이 바뀌면 ETag 도(304 로 못 받는 일 없음)', a1['push']['hold'] is True and a1['push']['wait'] == 4
           and pj(T)['push']['holder'] == 'nls' and a1['push']['holder'] == 'fgs' and tag0 != tag1
           and call(port, tok, 'GET', '/v1/alarms', headers={**P, 'If-None-Match': tag0})[0] == 200
           and call(port, tok, 'GET', '/v1/alarms', headers={**P, 'If-None-Match': tag1})[0] == 304, f'{tag0} {tag1}')
        c, _, b = push({'since': 0})
        h0 = json.loads(b)
        ok('U3 since 없음 = 지금 seq 만 바로(사건 없음)', c == 200 and h0['events'] == [] and h0['seq'] == a1['push']['seq'] and h0['hold'] is True, b.decode()[:160])
        got = {}

        def held_push(key, since, wait=4, h=None):
            t0 = time.time()
            got[key] = (push({'since': since, 'wait': wait, 'holder': 'fgs'}, h), time.time() - t0)
        th = threading.Thread(target=held_push, args=('a', h0['seq']))
        th.start()
        time.sleep(1.0)
        ev = {'id': 'ev-sort-push1', 'at': int(time.time() * 1000), 'title': '즉시 시험', 'text': '내용째', 'open': 'obsidian://brain-server', 'made': 1}
        t_emit = time.time()
        c, _, b = call(port, tok, 'POST', '/v1/push/emit', {'kind': 'alert', 'events': [ev]})
        th.join(10)
        ra = json.loads(got['a'][0][2]) if 'a' in got else {}
        e0 = (ra.get('events') or [{}])[0]
        ok('U4 붙잡힌 물음 = alert 내놓은 즉시 답(1초 뒤 냄 → 1.5초 안) · 내용째(item) · made 는 안 실음', c == 200 and json.loads(b)['held'] == {'시험폰': 1}
           and got['a'][1] < 1.5 and e0.get('kind') == 'alert' and e0.get('id') == 'ev-sort-push1' and e0.get('item', {}).get('title') == '즉시 시험'
           and 'made' not in e0.get('item', {}) and ra.get('seq') == e0.get('seq'), f"{got.get('a', (0, 0))[1]:.2f}s {ra}")
        lat_ms = (time.time() - t_emit) * 1000
        c, _, b = call(port, tok, 'POST', '/v1/push/ack', {'id': 'ev-sort-push1', 'recv_ms': 3, 'post_ms': 40, 'idle': True, 'net': 'wifi', 'batt': 77, 'holder': 'fgs'})
        ok('U5 ack = PC 시계 왕복(rtt)', c == 200 and isinstance(json.loads(b).get('rtt'), int) and json.loads(b)['rtt'] >= 0, b.decode()[:100])
        t0 = time.time()
        c, _, b = push({'since': ra['seq'], 'wait': 60})
        ok('U6 사건 없으면 정책 wait(4초) 뒤 빈 답 · 폰이 더 길게 달라 해도 정책이 상한', c == 200 and json.loads(b)['events'] == [] and 3.5 < time.time() - t0 < 6, f'{time.time() - t0:.2f}s')
        c, _, b = push({'since': h0['seq']})
        ok('U7 끊겼다 다시 물으면(옛 since) 그 뒤 사건을 다시 줌 — 폰이 id 로 거름', c == 200 and [x['id'] for x in json.loads(b)['events']] == ['ev-sort-push1'], b.decode()[:120])
        bad = [{'id': 'x-1', 'at': 1, 'title': 't'}], [{'id': 'ev-sort-x', 'at': 'nope', 'title': 't'}]
        ok('U8 emit 꼴 틀림 = 400 · 모르는 kind = 400 · tailnet 에서 = 403', all(call(port, tok, 'POST', '/v1/push/emit', {'kind': 'alert', 'events': e})[0] == 400 for e in bad)
           and call(port, tok, 'POST', '/v1/push/emit', {'kind': 'boom'})[0] == 400
           and call(port, tok, 'POST', '/v1/push/emit', {'kind': 'probe'}, headers={'X-Forwarded-For': '100.64.0.9'})[0] == 403
           and call(port, tok, 'GET', '/v1/push/state', headers={'X-Forwarded-For': '100.64.0.9'})[0] == 403)
        seq1 = json.loads(push({'since': 0})[2])['seq']
        th = threading.Thread(target=held_push, args=('l', seq1, 30))
        th.start()
        time.sleep(1.2)                               # 살피기가 첫 지문을 잼(붙잡는 기기가 있을 때만)
        t_line = time.time()
        with open(mine, 'a', encoding='utf-8', newline='') as f:
            f.write(f'- [ ] {near} 10:00 즉시 목록 시험 ^ps-1\n')
        th.join(15)
        rl = json.loads(got['l'][0][2]) if 'l' in got else {}
        ok('U9 일정 줄이 늘어 울릴 목록이 바뀜 = list 신호(내용 없음) · 2.5초 안', [x['kind'] for x in rl.get('events') or []] == ['list'] and 'item' not in (rl.get('events') or [{}])[0]
           and time.time() - t_line < 2.5 + 0.5, f'{time.time() - t_line:.2f}s {rl}')
        th = threading.Thread(target=held_push, args=('k', rl.get('seq', seq1), 30))
        th.start()
        time.sleep(1.0)
        t_off = time.time()
        set_cfg({'phone_sensitive': 'hide', 'push': {'hold': 'off'}})
        th.join(10)
        rk = json.loads(got['k'][0][2]) if 'k' in got else {}
        ok('U10 정책이 끔으로 바뀌면 붙잡힌 물음이 바로 hold false 로 답(살피기가 깨움)', rk.get('hold') is False and rk.get('events') == [] and time.time() - t_off < 3, f'{time.time() - t_off:.2f}s {rk}')
        os.makedirs(os.path.join(s, 'sort'), exist_ok=True)
        sysf = os.path.join(s, 'sort', '급한.json')
        with open(sysf, 'w', encoding='utf-8') as f:
            json.dump({'id': '급한', '켬': True, '갈래': {'예': {'동작': [{'알림': {'때': '바로', '급함': True}}]}}}, f, ensure_ascii=False)
        set_cfg({'phone_sensitive': 'hide', 'push': {'hold': 'auto'}})
        pa = pj()['push']
        with open(sysf, 'w', encoding='utf-8') as f:
            json.dump({'id': '급한', '켬': False, '갈래': {'예': {'동작': [{'알림': {'때': '바로', '급함': True}}]}}}, f, ensure_ascii=False)
        os.utime(sysf, ns=(time.time_ns(), time.time_ns() + 10 ** 9))
        pb = pj()['push']
        ok('U11 auto = 급함 쓰는 체계가 켜졌을 때만 붙잡음(끄면 바로 놓음)', pa['hold'] is True and '급한' in pa['why'] and pb['hold'] is False, f'{pa} {pb}')
        os.remove(sysf)
        set_cfg({'phone_sensitive': 'hide', 'push': {'hold': 'always', 'wait': 4, 'tick': 0.5, 'holder': 'alt'}})
        hp = json.loads(push({'since': 0})[2])
        ok('U12 alt = 날짜로 fgs·nls 번갈아', hp['holder'] == ('fgs' if datetime.date.today().toordinal() % 2 == 0 else 'nls'), str(hp))
        th = threading.Thread(target=held_push, args=('p', hp['seq'], 4, T))
        th.start()
        time.sleep(0.8)
        pid = json.loads(call(port, tok, 'POST', '/v1/push/emit', {'kind': 'probe'})[2])['ids'][0]
        th.join(10)
        rp = json.loads(got['p'][0][2]) if 'p' in got else {}
        call(port, tok, 'POST', '/v1/push/ack', {'id': pid, 'recv_ms': 2, 'post_ms': 30, 'idle': True, 'net': 'wifi', 'holder': 'nls', 'batt': 80}, headers=T)
        call(port, tok, 'POST', '/v1/push/ack', {'kind': 'beat', 'batt': 80, 'charge': 3000000, 'idle': False, 'plugged': False, 'holder': 'nls'}, headers=T)
        call(port, tok, 'POST', '/v1/push/ack', {'kind': 'cut', 'cut_s': 61, 'holder': 'nls'}, headers=T)
        plog = [json.loads(x) for x in open(os.path.join(s, '_index', 'alarms', 'push.jsonl'), encoding='utf-8') if x.strip()]
        kinds = {(r['t'], r.get('kind')) for r in plog}
        ok('U13 probe = 붙잡힌 탭에 바로 · 장부 한 곳(send·deliver·ack·beat·cut · send 에 붙잡힌 기기)', [x['kind'] for x in rp.get('events') or []] == ['probe']
           and {('send', 'probe'), ('deliver', 'probe'), ('ack', 'probe'), ('beat', None), ('cut', None), ('send', 'alert'), ('ack', 'alert')} <= kinds
           and next(r for r in plog if r['t'] == 'send' and r['id'] == pid)['held'] == ['시험탭'], str(sorted(kinds, key=str))[:240])
        spec = importlib.util.spec_from_file_location('alarms_push_t', os.path.join(s, 'alarms.py'))
        al_t = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(al_t)
        rep = al_t.push_report(os.path.join(s, '_index', 'alarms', 'push.jsonl'))
        ok('U14 --push-report = 기기마다 probe 왕복·깊은 Doze·방식·망·밤낮·끊김', any(x.startswith('[시험탭] probe 보냄(붙잡힌 때) 1 · 받음 1 · 잃음 0') for x in rep)
           and any('깊은 Doze 1' in x for x in rep) and any('방식 nls 1' in x for x in rep) and any('끊김 1번' in x for x in rep), ' | '.join(rep)[:300])
        spec = importlib.util.spec_from_file_location('alert_push_t', os.path.join(MOD, 'alert.py') if os.path.isfile(os.path.join(MOD, 'alert.py')) else os.path.join(SYS, 'alert.py'))   # 11-18 alert.py 가 모듈 자리로 옮겨짐
        alert_t = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(alert_t)
        alert_t._al[:] = [al_t]                          # 시험 서버 사본의 alarms(이 볼트 자리) — 진짜 서버에 안 감
        th = threading.Thread(target=held_push, args=('t', json.loads(push({'since': 0})[2])['seq'], 4))
        th.start()
        time.sleep(0.8)
        r_alert = alert_t.push_server([{'id': 'ev-sort-tool1', 'at': 1, 'title': '도구에서', 'text': '', 'made': 1}], here=s, port=int(port))
        th.join(10)
        rt = json.loads(got['t'][0][2]) if 't' in got else {}
        al_t.INBOX = os.path.join(tmp, 'other-in')
        ok('U15 알림 도구 push_server → 서버 → 붙잡힌 물음(내용째) · 사건 자리를 바꾼 시험은 안 보냄 · 서버 없음 = False', r_alert is True
           and [x.get('id') for x in rt.get('events') or []] == ['ev-sort-tool1'] and alert_t.push_server([ev]) is False
           and alert_t.push_server([ev], here=s, port=1) is False, f'{r_alert} {rt}')
        set_cfg({'phone_sensitive': 'hide'})
        # 상태 줄 종(사용자 11-13 안 A) — 알림-설정 «켬»
        settings = os.path.join(v, '2_지식', 'modules', 'mobility', '알림-설정.md')
        put('2_지식/modules/mobility/알림-설정.md', '---\ntitle: 알림 설정\n---\n# 알림 설정\n\n```json\n{\n "켬": true,\n "파일": {"LMS-마감.md": {}},\n "당겨_오기_분": 45\n}\n```\n\n| 칸 | 뜻 |\n')
        put('2_지식/일정/LMS-마감.md', f'- [ ] {near} 23:59 물리 · 과제 둘 ^lms-asg-2\n')
        c, _, b = call(port, tok, 'POST', '/v1/alarms/power', {'on': False})
        st = open(settings, encoding='utf-8').read()
        d = json.loads(call(port, tok, 'GET', '/v1/alarms')[2])
        pa = json.loads(call(port, tok, 'GET', '/v1/ping')[2])['app']
        ok('종 끔 = 설정 «켬» false(나머지 그대로) · 목록 빔 + off · ping on=false', c == 200 and '"켬": false' in st and '"당겨_오기_분": 45' in st and '| 칸 | 뜻 |' in st
           and d['items'] == [] and d.get('off') is True and pa['on'] is False, f'{b.decode()[:60]} {str(d)[:80]} {pa}')
        c, _, b = call(port, tok, 'POST', '/v1/alarms/power', {'on': True})
        d = json.loads(call(port, tok, 'GET', '/v1/alarms')[2])
        ok('종 켬 = 되돌림 · off 없음 · 마감 다시 옴', c == 200 and '"켬": true' in open(settings, encoding='utf-8').read() and 'off' not in d and any(a['id'].startswith('lms-asg-2@') for a in d['items']), str(d)[:120])
        ok('on 이 참거짓 아니면 400', call(port, tok, 'POST', '/v1/alarms/power', {'on': 'no'})[0] == 400)
        put('2_지식/modules/mobility/알림-설정.md', '```json\n{"당겨_오기_분": 45}\n```\n')
        c, _, b = call(port, tok, 'POST', '/v1/alarms/power', {'on': False})
        ok('«켬» 칸이 없으면 넣어서 끔', c == 200 and json.loads(b)['on'] is False and json.loads(call(port, tok, 'GET', '/v1/alarms')[2]).get('off') is True, b.decode()[:80])
        call(port, tok, 'POST', '/v1/alarms/power', {'on': True})
        # «이 기기만 끄기»(11-17 Q7) — 기기별 · 폰 종(머리 없음 = 같은 주소의 앱)과 앱 스위치가 같은 값 · 알림-설정 «켬»은 안 건드림
        call(port, tok, 'GET', '/v1/alarms', headers={**T, 'X-Brain-App': '30'})
        on_before = open(settings, encoding='utf-8').read()
        c0, h0, _ = call(port, tok, 'GET', '/v1/alarms', headers=T)
        c, _, b = call(port, tok, 'POST', '/v1/alarms/mute', {'mute': True}, headers=T)
        dT = call(port, tok, 'GET', '/v1/alarms', headers=T)
        dP = json.loads(call(port, tok, 'GET', '/v1/alarms', headers=P)[2])
        mf = json.load(open(os.path.join(s, '_index', 'server', 'mute.json'), encoding='utf-8'))
        ok('M1 앱 머리로 끔 = 그 기기만(mute.json) · 그 기기 목록 mute=true·태그 바뀜 · 다른 기기 mute=false · «켬» 그대로',
           c == 200 and json.loads(b)['device'] == '시험탭' and mf.get('시험탭', {}).get('mute') is True and json.loads(dT[2]).get('mute') is True
           and dT[1]['ETag'] != h0['ETag'] and dP.get('mute') is False and open(settings, encoding='utf-8').read() == on_before, f'{b.decode()[:80]} {mf}')
        call(port, tok, 'GET', '/v1/alarms', headers={**T, 'X-Brain-App': '30'})
        pa = json.loads(call(port, tok, 'GET', '/v1/ping')[2])['app']
        ok('M2 플러그인(머리 없음) = 같은 주소에서 마지막 당긴 앱의 기기 · ping app 에 here·mute·me(그 기기 판)', pa.get('here') == '시험탭' and pa.get('mute') is True
           and (pa.get('me') or {}).get('ver') == 30 and pa.get('on') is True, str(pa)[:200])
        X1, X2 = {'X-Forwarded-For': '100.64.0.7'}, {'X-Forwarded-For': '100.64.0.9'}
        call(port, tok, 'GET', '/v1/alarms', headers={**P, **X1, 'X-Brain-App': '29'})
        px = json.loads(call(port, tok, 'GET', '/v1/ping', headers=X1)[2])['app']
        c, _, b = call(port, tok, 'POST', '/v1/alarms/mute', {'mute': True}, headers=X1)
        mf = json.load(open(os.path.join(s, '_index', 'server', 'mute.json'), encoding='utf-8'))
        ok('M3 tailscale serve 주소(X-Forwarded-For) = 그 주소의 앱 기기 · 플러그인이 끄면 그 기기만', px.get('here') == '시험폰' and px.get('mute') is False and (px.get('me') or {}).get('ver') == 29
           and c == 200 and json.loads(b)['device'] == '시험폰' and mf['시험폰']['mute'] is True and mf['시험탭']['mute'] is True, f'{px} {b.decode()[:80]}')
        ok('M4 모르는 주소·머리 없음 = 409 · 참거짓 아님 = 400', call(port, tok, 'POST', '/v1/alarms/mute', {'mute': True}, headers=X2)[0] == 409
           and json.loads(call(port, tok, 'GET', '/v1/ping', headers=X2)[2])['app'].get('here') is None and call(port, tok, 'POST', '/v1/alarms/mute', {'mute': 'no'}, headers=T)[0] == 400)
        call(port, tok, 'POST', '/v1/alarms/mute', {'mute': False}, headers=T)
        call(port, tok, 'POST', '/v1/alarms/mute', {'mute': False}, headers=P)
        ok('M5 다시 켬 = mute=false · 304 태그는 끈 때와 다름', json.loads(call(port, tok, 'GET', '/v1/alarms', headers=T)[2]).get('mute') is False
           and call(port, tok, 'GET', '/v1/alarms', headers={**T, 'If-None-Match': dT[1]['ETag']})[0] == 200)
        log = open(os.path.join(s, '_index', 'server', 'server.log'), encoding='utf-8').read()
        ok('로그에 찾는 말·경로 쿼리 없음', '보통' not in log and 'path=' not in log)

        # ── 11-14 모바일볼트 ①: 홈 수집 칸 · 받은함 제안대로 · 작업 끝냄 · 되돌리기(폰이 받은 묶음만) ──
        for f in ('topic.py', 'work.py', 'brain.py', 'inbox.py', 'actions.json'):
            shutil.copy2(src(f), s)
        os.makedirs(os.path.join(s, 'ledger'), exist_ok=True)
        with open(os.path.join(s, 'ledger', 'actions.jsonl'), 'a', encoding='utf-8') as f:
            f.write(json.dumps({'ts': '2026-11-13T18:25:03', 'action': 'collect.lms', 'code': 0}) + '\n')
        os.makedirs(os.path.join(v, '1_수집', '받은함', '빈 폴더 시험'))
        put('1_수집/받은함/비밀 메모.md', '---\nsensitive: true\n---\n비밀\n')
        os.makedirs(os.path.join(v, '0_작업', '일', '시험주제', '시험작업'))
        put('0_작업/일/시험주제/시험작업/작업.md', '---\ntitle: 시험작업\n---\n# 시험작업\n')
        srv_home = lambda: json.loads(call(port, tok, 'GET', '/v1/home')[2])
        hm = srv_home()
        it = {x['name']: x for x in hm['inbox']['items']}
        ok('홈 = 수집 칸(출처별 마지막 실행) · 받은함 제안(빈 폴더 = 지움) · 민감 받은함 없음',
           any(x.get('ts') == '2026-11-13T18:25:03' for x in hm.get('collect') or []) and it.get('빈 폴더 시험', {}).get('act') == '지움' and '비밀 메모.md' not in it, str(hm.get('collect'))[:120] + ' ' + str(list(it))[:120])
        c, _, b = call(port, tok, 'POST', '/v1/inbox/do', {'name': '빈 폴더 시험'})
        ok('받은함 제안대로 = 그 항목만(빈 폴더 치움) · 홈 캐시 새로', c == 200 and json.loads(b)['ok'] and not os.path.exists(os.path.join(v, '1_수집', '받은함', '빈 폴더 시험'))
           and '빈 폴더 시험' not in [x['name'] for x in srv_home()['inbox']['items']], b.decode()[:120])
        ok('받은함에 없는 이름·민감·위로 나가기 = 404', all(call(port, tok, 'POST', '/v1/inbox/do', {'name': n})[0] == 404 for n in ('없음.md', '비밀 메모.md', '../2_지식/일/보통.md', 3)))
        c, _, b = call(port, tok, 'POST', '/v1/work/finish', {'path': '0_작업/일/시험주제/시험작업'})
        batch = json.loads(b).get('batch') if c == 200 else None
        ok('작업 끝냄 = 비움(묶음 id) · 장부 by = phone', bool(batch) and not os.path.exists(os.path.join(v, '0_작업', '일', '시험주제', '시험작업', '작업.md'))
           and '"by": "phone"' in open(os.path.join(s, 'ledger', 'ops.jsonl'), encoding='utf-8').read().replace('"by":"phone"', '"by": "phone"'), b.decode()[:160])
        ok('작업 끝냄 = 0_작업 밖 403 · 위로 나가기 400', call(port, tok, 'POST', '/v1/work/finish', {'path': '2_지식/일/보통.md'})[0] == 403
           and call(port, tok, 'POST', '/v1/work/finish', {'path': '0_작업/../2_지식'})[0] == 400)
        ok('되돌리기 = 폰이 받지 않은 묶음 404', call(port, tok, 'POST', '/v1/undo', {'batch': 'b000000-000000-0000'})[0] == 404)
        c, _, b = call(port, tok, 'POST', '/v1/undo', {'batch': batch})
        ok('되돌리기 = 되살림 · 같은 묶음 두 번째는 404', c == 200 and os.path.exists(os.path.join(v, '0_작업', '일', '시험주제', '시험작업', '작업.md'))
           and call(port, tok, 'POST', '/v1/undo', {'batch': batch})[0] == 404, b.decode()[:120])

        # ── 11-17 화면 쓰기(Q3 «C»): 형식 화면 내 칸·칸 너비 = 그 파일에(brain-base setMine·setCols 규칙) · 모듈 화면 행위 = 그 모듈 것만 ──
        put('3_시스템/views.json', json.dumps({'schema': 1, 'views': [{'owner': 'tmod', 'id': 'main', 'name': '시험', 'html': '3_시스템/tv.html', 'data': ['{py}', '3_시스템/tv.py']}],
                                               'formats': [{'ext': 'tmoa', 'name': '시험 모아', 'html': '3_시스템/tv.html', 'data': ['{py}', '3_시스템/tv.py', '{file}']}]}))
        put('3_시스템/tv.html', '<!doctype html><p>시험</p>')
        put('3_시스템/tv.py', 'import json, sys\nprint(json.dumps({"mine": json.load(open(sys.argv[1], encoding="utf-8")).get("mine") if len(sys.argv) > 1 else None}))\n')
        put('2_지식/일/장학.tmoa', json.dumps({'fields': {'상태': {'mine': ['관심', '냄']}}, 'columns': ['제목', '마감', '상태']}, ensure_ascii=False))
        put('1_수집/배움/밖.tmoa', '{}')
        fp = os.path.join(v, '2_지식', '일', '장학.tmoa')
        fmt = lambda: json.loads(call(port, tok, 'GET', '/v1/format?path=' + urllib.parse.quote('2_지식/일/장학.tmoa'))[2])['data']['mine']
        fmt()                                       # 20초 캐시를 채워 둔다 — 적으면 비워져야 한다
        c, _, b = call(port, tok, 'POST', '/v1/format/set', {'path': '2_지식/일/장학.tmoa', 'field': '상태', 'id': 'src:001', 'value': '관심'})
        d1 = json.load(open(fp, encoding='utf-8'))
        ok('W1 내 칸 = 파일 mine 에 · 바로 다시 받으면 새 값(캐시 비움)', c == 200 and json.loads(b)['ok'] and d1['mine'] == {'상태': {'src:001': '관심'}} and fmt() == {'상태': {'src:001': '관심'}}, b.decode()[:80])
        r_bad = [call(port, tok, 'POST', '/v1/format/set', x)[2] for x in ({'path': '2_지식/일/장학.tmoa', 'field': '상태', 'id': 'src:001', 'value': '준비'},
                                                                          {'path': '2_지식/일/장학.tmoa', 'field': '마감', 'id': 'src:001', 'value': '관심'})]
        c2 = call(port, tok, 'POST', '/v1/format/set', {'path': '2_지식/일/장학.tmoa', 'field': '상태', 'id': '../x', 'value': '관심'})[0]
        ok('W2 목록 밖 값·내 칸 아닌 칸 = 안 적음 · 이상한 줄 id = 400', all(json.loads(x)['ok'] is False for x in r_bad) and c2 == 400
           and json.load(open(fp, encoding='utf-8'))['mine'] == {'상태': {'src:001': '관심'}}, str(r_bad))
        call(port, tok, 'POST', '/v1/format/set', {'path': '2_지식/일/장학.tmoa', 'field': '상태', 'id': 'src:001', 'value': ''})
        c, _, b = call(port, tok, 'POST', '/v1/format/set', {'path': '2_지식/일/장학.tmoa', 'cols': {'제목': 250.5, '마감': 10, '금액': 99, '상태': True}})
        d2 = json.load(open(fp, encoding='utf-8'))
        ok('W3 빈 값 = 지움 · 칸 너비 = 그 파일 칸만 40~2000 정수(반올림 = JS 와 같게)', d2['mine'] == {'상태': {}} and d2['widths'] == {'제목': 251, '마감': 40} and c == 200, str(d2)[:160])
        call(port, tok, 'POST', '/v1/format/set', {'path': '2_지식/일/장학.tmoa', 'cols': {}})
        ok('W4 칸 너비 빈 값 = widths 지움', 'widths' not in json.load(open(fp, encoding='utf-8')))
        ok('W5 쓰기 자리 밖(1_수집)·형식 아님(md)·민감 = 거절', call(port, tok, 'POST', '/v1/format/set', {'path': '1_수집/배움/밖.tmoa', 'cols': {}})[0] == 403
           and call(port, tok, 'POST', '/v1/format/set', {'path': '2_지식/일/보통.md', 'cols': {}})[0] == 404
           and call(port, tok, 'POST', '/v1/format/set', {'path': '2_지식/일/비밀.md', 'cols': {}})[0] == 404)
        c, _, b = call(port, tok, 'POST', '/v1/view/act', {'module': 'tmod', 'id': 'main', 'act': 'collect.tick', 'args': {}})
        c3, _, b3 = call(port, tok, 'POST', '/v1/view/act', {'module': 'tmod', 'id': 'main', 'act': 'tmod.nothing', 'args': {}})
        c4 = call(port, tok, 'POST', '/v1/view/act', {'module': 'tmod', 'id': 'main', 'act': 'tmod.x', 'args': {'a b': '1'}})[0]
        c5 = call(port, tok, 'POST', '/v1/view/act', {'module': '없음', 'id': 'main', 'act': '없음.x'})[0]
        ok('W6 행위 = 그 화면 모듈 것만(남의 것 403) · 없는 행위 = ok false · 인자 이름 틀림 400 · 없는 화면 404', c == 403 and c3 == 200 and json.loads(b3)['ok'] is False
           and c4 == 400 and c5 == 404, f'{c} {b3.decode()[:120]}')

        # ── 11-14 모바일볼트 1-9: 폰 이름 바꾸기·옮기기·휴지통(fileops) · 바뀐 파일 409 · 금지 자리 · 되돌리기 ──
        A = lambda *p: os.path.join(v, *p)
        os.makedirs(A('2_지식', '일', '옮길곳'))
        put('2_지식/일/폰이름.md', '---\ntitle: 폰이름\n---\n본문\n')
        put('2_지식/일/링크건.md', '[[폰이름]] 을 가리킴\n')
        fo = lambda body: call(port, tok, 'POST', '/v1/fileop', body)
        et = call(port, tok, 'GET', '/v1/file?path=' + urllib.parse.quote('2_지식/일/폰이름.md'))[1].get('ETag')
        c, _, b = fo({'op': 'mv', 'src': '2_지식/일/폰이름.md', 'dst': '2_지식/일/새이름.md', 'base': et})
        r1 = json.loads(b) if c == 200 else {}
        ok('이름 바꾸기 = fileops mv(장부 by=phone) · 링크 고침 · 옛 이름 없음', c == 200 and os.path.exists(A('2_지식', '일', '새이름.md')) and not os.path.exists(A('2_지식', '일', '폰이름.md'))
           and '새이름' in open(A('2_지식', '일', '링크건.md'), encoding='utf-8').read() and r1.get('batch') and r1.get('dst') == '2_지식/일/새이름.md', b.decode()[:160])
        c, _, b = fo({'op': 'mv', 'src': '2_지식/일/새이름.md', 'dst': '2_지식/일/옮길곳'})
        ok('옮기기(폴더를 주면 그 안으로)', c == 200 and os.path.exists(A('2_지식', '일', '옮길곳', '새이름.md')) and json.loads(b).get('dst') == '2_지식/일/옮길곳/새이름.md', b.decode()[:160])
        b2 = json.loads(b).get('batch')
        c, _, b = call(port, tok, 'POST', '/v1/undo', {'batch': b2})
        ok('옮기기 되돌리기 = 제자리', c == 200 and os.path.exists(A('2_지식', '일', '새이름.md')) and not os.path.exists(A('2_지식', '일', '옮길곳', '새이름.md')), b.decode()[:120])
        old = call(port, tok, 'GET', '/v1/file?path=' + urllib.parse.quote('2_지식/일/새이름.md'))[1].get('ETag')
        time.sleep(1.1)
        put('2_지식/일/새이름.md', '---\ntitle: 폰이름\n---\nPC 에서 고침\n')
        c, _, b = fo({'op': 'rm', 'src': '2_지식/일/새이름.md', 'base': old})
        ok('폰이 본 뒤 PC 가 고친 파일 = 409 · 안 지움', c == 409 and os.path.exists(A('2_지식', '일', '새이름.md')), b.decode()[:120])
        c, _, b = fo({'op': 'rm', 'src': '2_지식/일/새이름.md'})
        rb = json.loads(b).get('batch') if c == 200 else None
        trash = [os.path.join(d, f) for d, _, fs in os.walk(A('.trash')) for f in fs if f == '새이름.md'] if os.path.isdir(A('.trash')) else []
        ok('휴지통으로 = 볼트 .trash 로(영구 삭제 아님) · 장부 by=phone', c == 200 and not os.path.exists(A('2_지식', '일', '새이름.md')) and len(trash) == 1
           and '"phone"' in open(os.path.join(s, 'ledger', 'ops.jsonl'), encoding='utf-8').read(), b.decode()[:120] + ' ' + str(trash)[:120])
        c, _, b = call(port, tok, 'POST', '/v1/undo', {'batch': rb})
        ok('휴지통 되돌리기 = 되살림', c == 200 and os.path.exists(A('2_지식', '일', '새이름.md')), b.decode()[:120])
        bad = [fo({'op': 'rm', 'src': x})[0] for x in ('3_시스템/server.py', '../x.md', '2_지식', '1_수집/_lms/raw.json', '.obsidian/app.json', '2_지식/일/비밀.md')]
        bad += [fo({'op': 'mv', 'src': '2_지식/일/보통.md', 'dst': x})[0] for x in ('3_시스템/보통.md', '.obsidian/보통.md', '../보통.md')]
        bad += [fo({'op': 'zap', 'src': '2_지식/일/보통.md'})[0]]
        ok('금지 = 3_시스템·위로·범위 뿌리·숨김(_lms)·점 자리·민감·모르는 일 → 4xx · 보통.md 그대로', all(400 <= x < 500 for x in bad) and os.path.exists(A('2_지식', '일', '보통.md')), str(bad))
        fl = json.loads(call(port, tok, 'GET', '/v1/folders')[2])['items']
        ok('옮길 자리 = 범위 안 폴더(숨김 _lms·점 자리 없음)', '2_지식/일/옮길곳' in fl and not any('_lms' in x or '/.' in x or x.startswith(('3_시스템', '.')) for x in fl), str(fl)[:160])

        # ── 11-23 폰 «새 폴더»(op=mkdir) · 이름 바꾸기 확장자 지킴 ──
        c, _, b = fo({'op': 'mkdir', 'dst': '2_지식/일/폰새폴더'})
        mb = json.loads(b).get('batch') if c == 200 else None
        led = open(os.path.join(s, 'ledger', 'ops.jsonl'), encoding='utf-8').read().splitlines()
        ok('새 폴더 = fileops mkdir(장부 by=phone) · 묶음 · /v1/folders 에 보임', c == 200 and os.path.isdir(A('2_지식', '일', '폰새폴더')) and mb and json.loads(b).get('dst') == '2_지식/일/폰새폴더'
           and any('"mkdir"' in x and '"phone"' in x and '폰새폴더' in x for x in led) and '2_지식/일/폰새폴더' in json.loads(call(port, tok, 'GET', '/v1/folders')[2])['items'], b.decode()[:160])
        c2 = fo({'op': 'mkdir', 'dst': '2_지식/일/폰새폴더'})[0]
        c4 = fo({'op': 'mkdir', 'dst': '2_지식/일/보통.md'})[0]
        ok('이미 있음 = 409(같은 폴더 · 같은 이름 파일)', c2 == 409 and c4 == 409, f'{c2} {c4}')
        far = [fo({'op': 'mkdir', 'dst': x})[0] for x in ('3_시스템/새', '새폴더', '2_지식', '1_수집/_lms/새', '2_지식/_색인/새', '.obsidian/새', '../새', '2_지식/없는곳/새')]
        ok('범위 밖 = 3_시스템·볼트 뿌리·범위 뿌리 자체·숨김·점 자리·위로 → 403/400 · 없는 부모 = 404 · 안 만듦', far[:7] and all(x in (400, 403) for x in far[:7]) and far[7] == 404
           and not os.path.exists(A('3_시스템', '새')) and not os.path.exists(A('새폴더')) and not os.path.exists(A('2_지식', '없는곳')), str(far))
        names = ('', ' ', '.숨김', '..', 'a\\b', 'a:b', 'a?b', 'a*b', 'a|b', 'a"b', 'a<b', '끝점.', '끝공백 ', ' 앞공백', 'CON', 'nul.txt', 'x' * 121)
        before = sorted(os.listdir(A('2_지식', '일')))
        nb = [fo({'op': 'mkdir', 'dst': '2_지식/일/' + x})[0] for x in names] + [fo({'op': 'mkdir', 'dst': None})[0], fo({'op': 'mkdir', 'dst': '2_지식/일/'})[0]]
        ok('이름 거절 = 빈 이름·점 시작·..·역슬래시·윈도 금지 글자·끝 점/공백·장치 이름·너무 김 → 400 · 안 만듦', all(x == 400 for x in nb)
           and sorted(os.listdir(A('2_지식', '일'))) == before, str(nb))
        c, _, b = call(port, tok, 'POST', '/v1/undo', {'batch': mb})
        ok('새 폴더 되돌리기 = 빈 폴더 치움', c == 200 and not os.path.exists(A('2_지식', '일', '폰새폴더')), b.decode()[:120])
        c, _, b = fo({'op': 'mkdir', 'dst': '1_수집/폰폴더'})
        ok('1_수집 안 새 폴더도 됨(폰 범위 = /v1/folders 와 같음)', c == 200 and os.path.isdir(A('1_수집', '폰폴더')), f'{c} {b.decode()[:120]}')
        with open(A('1_수집', '폰폴더', 'Notes_1.sdocx'), 'wb') as f:
            f.write(b'PK\x03\x04sdocx')
        c, _, b = fo({'op': 'mv', 'src': '1_수집/폰폴더/Notes_1.sdocx', 'dst': '1_수집/폰폴더/Hw4'})
        c2, _, b2 = fo({'op': 'mv', 'src': '1_수집/폰폴더/Hw4.sdocx', 'dst': '1_수집/폰폴더/Hw5.pdf'})
        c3, _, b3 = fo({'op': 'mv', 'src': '1_수집/폰폴더/Hw5.pdf.sdocx', 'dst': '1_수집/폰폴더/Hw6.SDOCX'})
        ok('.sdocx 이름 바꾸기 → 확장자 유지(빠지면 붙임 · 바꾸면 원래 것을 덧붙임 · 대소문자도 원래 글자로)', c == 200 and json.loads(b).get('dst') == '1_수집/폰폴더/Hw4.sdocx'
           and c2 == 200 and json.loads(b2).get('dst') == '1_수집/폰폴더/Hw5.pdf.sdocx' and c3 == 200 and json.loads(b3).get('dst') == '1_수집/폰폴더/Hw6.sdocx'
           and not os.path.exists(A('1_수집', '폰폴더', 'Hw4')), f'{b.decode()[:100]} {b2.decode()[:100]} {b3.decode()[:100]}')
        os.makedirs(A('2_지식', '일', '옮길곳2'), exist_ok=True)
        c, _, b = fo({'op': 'mv', 'src': '1_수집/폰폴더/Hw6.sdocx', 'dst': '2_지식/일/옮길곳2'})
        c2, _, b2 = fo({'op': 'mv', 'src': '2_지식/일/옮길곳2', 'dst': '2_지식/일/옮길곳3'})
        ok('옮기기·폴더 이름 바꾸기는 확장자 손대지 않음', c == 200 and json.loads(b).get('dst') == '2_지식/일/옮길곳2/Hw6.sdocx' and c2 == 200 and os.path.isdir(A('2_지식', '일', '옮길곳3')), f'{b.decode()[:100]} {b2.decode()[:100]}')

        # ── 11-16 민감 노트 보기 스위치(config phone_sensitive · 없으면 «show» = 사용자 C선택 · «hide» = 옛 동작 · 모르는 값 = 숨김) ──
        spec = importlib.util.spec_from_file_location('srv_ps', os.path.join(s, 'server.py'))
        srv_ps = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(srv_ps)

        class FakeIndex:                            # 찾기 = 색인이 낸 줄을 서버가 거르는 자리만 잰다(색인·모형 없이)
            def ranked(self, *_a):
                return [(0.9, '2_지식/일/비밀.md'), (0.8, '2_지식/일/보통.md')]

            def notes(self, _idx):
                return {}
        srv_ps.FIND.mod, srv_ps.FIND.load = FakeIndex(), lambda: None
        found = lambda: [x['path'] for x in srv_ps.FIND.search('카드', 8, 'lexical')]
        lst = lambda: {x['name']: x for x in json.loads(call(port, tok, 'GET', '/v1/list?dir=' + urllib.parse.quote('2_지식/일'))[2])['items']}
        home_inbox = lambda: [x['name'] for x in srv_home()['inbox']['items']]
        secret = os.path.join(v, '2_지식', '일', '비밀.md')
        set_cfg({})
        c, h, b = call(port, tok, 'GET', q('2_지식/일/비밀.md'))
        ok('show(설정 없음 = 기본) = 민감 노트가 목록·읽기·링크·찾기·홈 받은함에 보임',
           lst().get('비밀.md', {}).get('title') == '비밀' and c == 200 and '카드' in b.decode() and res('비밀')[0] == 200
           and '2_지식/일/비밀.md' in found() and '비밀 메모.md' in home_inbox(), f'{c} {list(lst())} {found()} {home_inbox()}')
        c2, _, b2 = call(port, tok, 'POST', '/v1/note', {'path': '2_지식/일/비밀.md', 'base': h.get('ETag'), 'text': '---\ntitle: 비밀\nsensitive: true\n---\n카드 폰에서\n'})
        ok('show = 민감 노트 폰에서 고침(표시 그대로)', c2 == 200 and open(secret, encoding='utf-8').read() == '---\ntitle: 비밀\nsensitive: true\n---\n카드 폰에서\n', b2.decode()[:100])
        c3, _, b3 = call(port, tok, 'POST', '/v1/note', {'path': '2_지식/일/비밀.md', 'base': json.loads(b2).get('etag'), 'text': '---\ntitle: 비밀\n---\n카드 뗌\n'})
        ok('show = 민감 표시를 떼는 고침은 403 · 파일 그대로(git 밖에 남음)', c3 == 403 and 'sensitive: true' in open(secret, encoding='utf-8').read() and '뗌' not in open(secret, encoding='utf-8').read(), f'{c3} {b3.decode()[:80]}')
        set_cfg({'phone_sensitive': 'hide'})
        ok('hide = 목록·읽기·링크·찾기·홈 받은함에 안 보임(재시작 없이)',
           '비밀.md' not in lst() and call(port, tok, 'GET', q('2_지식/일/비밀.md'))[0] == 404 and res('비밀')[0] == 403
           and found() == ['2_지식/일/보통.md'] and '비밀 메모.md' not in home_inbox(), f'{list(lst())} {found()} {home_inbox()}')
        set_cfg({'phone_sensitive': 'yes'})
        ok('모르는 값 = 숨김(안전 쪽)', call(port, tok, 'GET', q('2_지식/일/비밀.md'))[0] == 404 and '비밀.md' not in lst())
        set_cfg({'phone_sensitive': 'hide'})

        # ── 11-15: 폰 보기가 고친 원본 = PUT /v1/file(If-Match) · PC 가 먼저 바뀌면 409 · 옛 판 휴지통 · 되돌리기 · 금지 자리 ──
        def put_bin(rel, data, tag, t=tok):
            h = {'If-Match': tag} if tag is not None else {}
            if t is not None:
                h['Authorization'] = 'Bearer ' + t
            req = urllib.request.Request(f'http://127.0.0.1:{port}/v1/file?path=' + urllib.parse.quote(rel), data=data, headers=h, method='PUT')
            try:
                with urllib.request.urlopen(req, timeout=120) as r:
                    return r.status, dict(r.headers), r.read()
            except urllib.error.HTTPError as e:
                try:
                    return e.code, dict(e.headers), e.read()
                except OSError:
                    return e.code, dict(e.headers), b''
            except OSError:                         # 서버가 본문을 다 안 받고 닫음(413 · 409) — 보내던 쪽은 끊김으로 본다
                return 0, {}, b''
        tag_of = lambda rel: call(port, tok, 'GET', '/v1/file?path=' + urllib.parse.quote(rel))[1].get('ETag')
        sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
        os.makedirs(A('0_작업', '보고'), exist_ok=True)
        blob1 = bytes(range(256)) * 400 + b'PK-old'
        blob2 = bytes(reversed(range(256))) * 500 + b'PK-new'
        for rel in ('0_작업/보고/보고서.docx', '1_수집/배움/표.xlsx', '0_작업/보고/그림.png'):
            with open(A(*rel.split('/')), 'wb') as f:
                f.write(blob1)
        rel = '0_작업/보고/보고서.docx'
        t1 = tag_of(rel)
        c, h, b = put_bin(rel, blob2, t1)
        r = json.loads(b) if c == 200 else {}
        tb = [os.path.join(d, f) for d, _, fs in os.walk(A('.trash')) for f in fs if f == '보고서.docx'] if os.path.isdir(A('.trash')) else []
        ok('원본 덮기 = 새 바이트(해시) · 새 ETag · 옛 판 휴지통 1벌 · 장부 by=phone', c == 200 and sha(A(*rel.split('/'))) == hashlib.sha256(blob2).hexdigest() and r.get('etag') == tag_of(rel) != t1
           and len(tb) == 1 and sha(tb[0]) == hashlib.sha256(blob1).hexdigest() and r.get('batch'), b.decode()[:160] + ' ' + str(tb)[:80])
        c, _, b = put_bin(rel, blob1, t1)
        ok('옛 ETag 로 덮기 = 409 · 지금 ETag 를 줌 · 안 덮음', c == 409 and json.loads(b).get('etag') == tag_of(rel) and sha(A(*rel.split('/'))) == hashlib.sha256(blob2).hexdigest(), b.decode()[:120])
        c, _, b = call(port, tok, 'POST', '/v1/undo', {'batch': r.get('batch')})
        ok('폰 고침 되돌리기 = 옛 판으로', c == 200 and sha(A(*rel.split('/'))) == hashlib.sha256(blob1).hexdigest(), b.decode()[:120])
        t2 = tag_of('1_수집/배움/표.xlsx')
        c, _, b = put_bin('1_수집/배움/표.xlsx', blob2, t2)
        ok('1_수집 원본도 덮음(사람이 보호를 푼 고침 · 옛 판 휴지통)', c == 200 and sha(A('1_수집', '배움', '표.xlsx')) == hashlib.sha256(blob2).hexdigest(), b.decode()[:120])
        os.makedirs(A('1_수집', '필기'), exist_ok=True)     # 11-23: 삼성노트 .sdocx 그 자리 필기 — 같은 길(옛 판 휴지통)
        with open(A('1_수집', '필기', '노트.sdocx'), 'wb') as f:
            f.write(blob1)
        c, _, b = put_bin('1_수집/필기/노트.sdocx', blob2, tag_of('1_수집/필기/노트.sdocx'))
        tsd = [os.path.join(d, f) for d, _, fs in os.walk(A('.trash')) for f in fs if f == '노트.sdocx'] if os.path.isdir(A('.trash')) else []
        ok('.sdocx 덮음 = 새 바이트 · 옛 판 휴지통 1벌', c == 200 and sha(A('1_수집', '필기', '노트.sdocx')) == hashlib.sha256(blob2).hexdigest() and len(tsd) == 1 and sha(tsd[0]) == hashlib.sha256(blob1).hexdigest(), b.decode()[:120])
        c, _, b = put_bin(rel, blob1, tag_of(rel))
        ok('같은 내용 = 200 · 장부 묶음 없음', c == 200 and 'batch' not in json.loads(b), b.decode()[:120])
        cur = tag_of(rel)
        bad = [put_bin(rel, b'', cur)[0], put_bin(rel, blob2, None)[0], put_bin(rel, blob2, cur, t='x')[0], put_bin('0_작업/보고/그림.png', blob2, tag_of('0_작업/보고/그림.png'))[0],
               put_bin('0_작업/보고/없음.docx', blob2, 'x')[0], put_bin('2_지식/일/보통.md', b'x', tag_of('2_지식/일/보통.md'))[0], put_bin('3_시스템/roles.json', b'{}', 'x')[0],
               put_bin('1_수집/_lms/raw.csv', b'x', 'x')[0], put_bin('../x.docx', b'x', 'x')[0]]
        ok('금지 = 빈 본문 400 · If-Match 없음 428 · 열쇠 401 · png·md 형식 · 없는 파일 · 3_시스템 · _lms · 위로 → 4xx · 파일 그대로', bad[:3] == [400, 428, 401] and all(400 <= x < 500 for x in bad)
           and sha(A(*rel.split('/'))) == hashlib.sha256(blob1).hexdigest() and sha(A('0_작업', '보고', '그림.png')) == hashlib.sha256(blob1).hexdigest(), str(bad))
        # 보스 조건 ①(11-15): 우회 — 위로(..)·절대 경로·드라이브·역슬래시·대소문자(숨은 자리 _LMS · 확장자 .MD)·숨은 스트림·끝 점
        with open(A('1_수집', '_lms', 'raw.csv'), 'wb') as f:
            f.write(blob1)
        with open(A('0_작업', '보고', '대문자.DOCX'), 'wb') as f:
            f.write(blob1)
        dodge = {
            '위로': '0_작업/../3_시스템/roles.json', '위로2': '0_작업/보고/../../3_시스템/x.docx', '절대': '/C:/Windows/win.ini', '드라이브': 'D:/Vault/0_작업/보고/보고서.docx',
            '역슬래시': '0_작업\\..\\3_시스템\\x.docx', '역슬래시 절대': '\\\\?\\C:\\x.docx', '대소문자 숨은 자리': '1_수집/_LMS/raw.csv', '대소문자 md': '2_지식/일/보통.MD',
            '숨은 스트림': '0_작업/보고/보고서.docx::$DATA', '끝 점': '0_작업/보고/보고서.docx.', '점 폴더': '.obsidian/x.docx',
        }
        got = {k: put_bin(p, blob2, tag_of(p) or 'x')[0] for k, p in dodge.items()}     # 읽을 수 있는 자리면 진짜 ETag 로(판이 맞아도 막혀야 한다)
        ok('우회 막힘(위로·절대·드라이브·역슬래시·대소문자·숨은 스트림·끝 점·점 폴더) → 4xx · _lms 파일 그대로', all(400 <= c < 500 for c in got.values()) and sha(A('1_수집', '_lms', 'raw.csv')) == hashlib.sha256(blob1).hexdigest(), str(got))
        t3 = tag_of('0_작업/보고/대문자.DOCX')
        ok('대문자 확장자(.DOCX) = 같은 형식으로 받음', put_bin('0_작업/보고/대문자.DOCX', blob2, t3)[0] == 200)
        big = b'\0' * (64 * 2 ** 20 + 1)
        ok('64MB 넘음 = 413(또는 받다 끊음) · 안 덮음', put_bin(rel, big, cur)[0] in (413, 0) and sha(A(*rel.split('/'))) == hashlib.sha256(blob1).hexdigest())

        # ── 11-15 draw: 필기 노트 덧붙이기 = POST /v1/ink · 없는 줄만 · 두 기기 합치기 · 머리 줄부터 · .note 만 · 금지 자리 ──
        inkp = '2_지식/필기/교재.note'
        head = json.dumps({'note': 1, 'id': 'n-t', 'paper': 'grid', 'size': [595, 842], 'bg': {'path': '1_수집/배움/교재.pdf', 'sha256': 'ab' * 32, 'pages': 3}}, ensure_ascii=False)
        pg = json.dumps({'page': 'p1', 'bg': 0})
        s1 = json.dumps({'s': 'd1-a', 'p': 'p1', 't': 'pen', 'c': 0, 'w': 1, 'z': 'AAAA'})
        s2 = json.dumps({'s': 'd2-b', 'p': 'p1', 't': 'hl', 'c': 4, 'w': 0, 'z': 'AAAA'})
        dl = json.dumps({'o': 'd1-x', 'del': ['d1-a']})
        inkc = lambda lines, path=inkp: call(port, tok, 'POST', '/v1/ink', {'path': path, 'lines': lines})
        c, _, b = inkc([pg, s1])
        ok('새 필기 = 머리 줄 없으면 400 · 파일 안 생김', c == 400 and not os.path.exists(A('2_지식', '필기', '교재.note')), str(c))
        c, _, b = inkc([head, pg, s1])
        j = json.loads(b) if c == 200 else {}
        ok('새 필기 = 머리 줄부터 만듦', c == 200 and j.get('lines') == 3 and j.get('took') == 3, b.decode()[:120])
        c, _, b = inkc([head, pg, s1, s2])
        j = json.loads(b) if c == 200 else {}
        ok('다른 기기 줄 = 없는 것만 덧붙임(한 벌)', c == 200 and j.get('took') == 1 and j.get('lines') == 4, b.decode()[:120])
        c, _, b = inkc([s2, dl, dl])
        j = json.loads(b) if c == 200 else {}
        body = open(A('2_지식', '필기', '교재.note'), encoding='utf-8').read().splitlines()
        ok('같은 줄 두 번 = 한 번 · 순서 그대로', c == 200 and j.get('took') == 1 and body == [head, pg, s1, s2, dl], str(body)[:200])
        g = call(port, tok, 'GET', '/v1/file?path=' + urllib.parse.quote(inkp))
        ok('받기 = GET /v1/file 그대로 · ETag 같음', g[0] == 200 and g[1].get('ETag') == j.get('etag'), str(g[1].get('ETag')))
        ok('.note 아니면 400', inkc([head], '2_지식/필기/x.md')[0] == 400)
        # 바탕 PDF 찾기(해시 → 지금 경로)
        os.makedirs(A('1_수집', '배움', '책'), exist_ok=True)
        os.makedirs(A('1_수집', '_색인', '배움', '책'), exist_ok=True)
        with open(A('1_수집', '배움', '책', '옮긴 교재.pdf'), 'wb') as fh:
            fh.write(b'%PDF-1.4 book')
        hx = hashlib.sha256(b'%PDF-1.4 book').hexdigest()
        with open(A('1_수집', '_색인', '배움', '책', '옮긴 교재.pdf.색인.md'), 'w', encoding='utf-8') as fh:
            fh.write('---\nsha256: ' + hx + '\n---\n색인\n')
        c, _, b = call(port, tok, 'GET', '/v1/find?sha256=' + hx)
        ok('해시로 원본 찾기 = 지금 경로', c == 200 and json.loads(b).get('path') == '1_수집/배움/책/옮긴 교재.pdf', b.decode()[:120])
        ok('없는 해시 = 404', call(port, tok, 'GET', '/v1/find?sha256=' + '0' * 64)[0] == 404)
        ok('해시 꼴 아님 = 400', call(port, tok, 'GET', '/v1/find?sha256=../x')[0] == 400)
        ok('1_수집(원본 층) 막힘', inkc([head], '1_수집/배움/교재.note')[0] == 403)
        # ── 11-18 필기 13차: 원본 옆 필기 짝 «<이름> (필기).note» = 1_수집 안이어도 씀(옆에 <이름>.pdf 가 있을 때만) · 원본·다른 이름·PDF 없는 짝 = 막힘 ──
        with open(A('1_수집', '배움', '책', '옮긴 교재.pdf'), 'rb') as fh:
            pdf0 = fh.read()
        pairp = '1_수집/배움/책/옮긴 교재 (필기).note'
        phead = json.dumps({'note': 1, 'id': 'n-p', 'paper': 'plain', 'size': [595, 842], 'bg': {'path': '1_수집/배움/책/옮긴 교재.pdf', 'sha256': hx, 'pages': 1}, 'pair': 1}, ensure_ascii=False)
        c, _, b = inkc([phead, pg, s1], pairp)
        pbody = open(A('1_수집', '배움', '책', '옮긴 교재 (필기).note'), encoding='utf-8').read().splitlines() if c == 200 else []
        with open(A('1_수집', '배움', '책', '옮긴 교재.pdf'), 'rb') as fh:
            pdf1 = fh.read()
        ok('필기 짝(원본 옆 «이름 (필기).note») = 1_수집 안에 만듦 · 원본 PDF 바이트 그대로', c == 200 and pbody == [phead, pg, s1] and pdf0 == pdf1, f'{c} {b.decode()[:100]}')
        ok('필기 짝 = 덧붙이기도(없는 줄만)', inkc([phead, pg, s1, s2], pairp)[0] == 200 and len(open(A('1_수집', '배움', '책', '옮긴 교재 (필기).note'), encoding='utf-8').read().splitlines()) == 4)
        ok('옆에 PDF 없는 짝 = 막힘', inkc([phead], '1_수집/배움/책/없는 책 (필기).note')[0] == 403 and not os.path.exists(A('1_수집', '배움', '책', '없는 책 (필기).note')))
        ok('짝 꼴 아닌 1_수집 .note = 막힘', inkc([phead], '1_수집/배움/책/옮긴 교재.note')[0] == 403)
        ok('원본 PDF 자리 = .note 아님 400', inkc([phead], '1_수집/배움/책/옮긴 교재.pdf')[0] in (400, 403))
        ok('짝 꼴로 위로 나가기 = 막힘', inkc([phead], '1_수집/../2_지식/x (필기).note')[0] in (400, 403))
        ok('위로 나가기 막힘', inkc([head], '2_지식/../../밖.note')[0] in (400, 403))
        ok('줄 안 줄바꿈 = 400', inkc([head + '\n' + pg])[0] == 400)
        ok('줄이 글자 목록 아니면 400', call(port, tok, 'POST', '/v1/ink', {'path': inkp, 'lines': 'x'})[0] == 400)
        ok('열쇠 없으면 막힘', call(port, None, 'POST', '/v1/ink', {'path': inkp, 'lines': [s1]})[0] in (401, 403))

        # ── 11-21 탭 곁창(작업 세션): 시작 → 조각 묻기 · 칩 짐작 · 경로·꼴 거름 — 가짜 실행기(받은 인자를 사건으로 되돌림 · 모델 없음)
        put('3_시스템/ink/notechat.cjs', 'const a=process.argv.slice(2);const o=x=>process.stdout.write(JSON.stringify(x)+"\\n");'
            'if(a.includes("--chips")){o({t:"kind",kind:"풀이",why:"가짜"});o({t:"chips",kind:"풀이",chips:["봐줘","힌트만"]});process.exit(0)}'
            'o({t:"lines",page:1,lines:[{n:1,y0:0,y1:10}]});o({t:"d",s:"L1 "});setTimeout(()=>{o({t:"d",s:"끝"});o({t:"done",session:"s",text:"L1 끝",args:a})},300);')
        put('2_지식/일/풀이.note', '{"note":1,"id":"n-t","size":[595,842],"bg":null}\n{"page":"p1"}\n')
        c, _, b = call(port, tok, 'POST', '/v1/notechat', {'note': '2_지식/일/풀이.note', 'chips': True})
        ok('곁창 칩 = 종류 짐작(모델 없음)', c == 200 and json.loads(b) == {'kind': '풀이', 'chips': ['봐줘', '힌트만'], 'why': '가짜'}, b[:200])
        c, _, b = call(port, tok, 'POST', '/v1/notechat', {'note': '2_지식/일/풀이.note', 'chip': '봐줘', 'view': '1,0,500'})
        job = json.loads(b).get('job') if c == 200 else None
        evs, nxt, t0 = [], 0, time.time()
        while job and time.time() - t0 < 10:
            j = json.loads(call(port, tok, 'GET', f'/v1/notechat?job={job}&from={nxt}')[2])
            evs += j['events']; nxt = j['next']
            if j['done']:
                break
            time.sleep(0.1)
        dn = [e for e in evs if e['t'] == 'done']
        ok('곁창 시작 → 조각 묻기 → 끝(사건 차례 그대로 · 인자 = 볼트 상대 노트·칩·보는 자리)', [e['t'] for e in evs] == ['lines', 'd', 'd', 'done'] and dn
           and dn[0]['args'][dn[0]['args'].index('--note') + 1] == '2_지식/일/풀이.note' and '--view' in dn[0]['args'], evs)
        bad = [call(port, tok, 'POST', '/v1/notechat', x)[0] for x in ({'note': '../x.note', 'chip': '봐줘'}, {'note': '2_지식/일/없음.note', 'chip': '봐줘'},
               {'note': '2_지식/일/보통.md'}, {'note': '2_지식/일/풀이.note', 'resume': 'x;y'}, {'note': '2_지식/일/풀이.note', 'view': '1;2'}, {'text': ''})]
        ok('곁창 거름: 경로·없는 노트·물을 글 없음·대화 id·보는 자리 꼴', bad == [400, 404, 400, 400, 400, 400], bad)
        ok('곁창 없는 일 = 404 · 열쇠 없으면 막힘', call(port, tok, 'GET', '/v1/notechat?job=zz')[0] == 404
           and call(port, None, 'POST', '/v1/notechat', {'text': 'x'})[0] in (401, 403))
        c, _, b = call(port, tok, 'GET', '/v1/notechat/past')
        ok('지난 대화 목록(엔진 대화만 · 없으면 빈 목록)', c == 200 and isinstance(json.loads(b).get('items'), list), b[:200])
        # ── 11-22: 탭 곁창 작업 모드 = 폰 명령 승인 요청(run tabwork) · 켜는 길(폰 서명)은 tabwork_check.py ──
        tsid = '12345678-1234-4234-8234-123456789abc'
        ok('작업 모드: 처음 = 묻기 · 대화 id 꼴 막음', json.loads(call(port, tok, 'GET', f'/v1/tabwork?session={tsid}')[2]).get('state') == 'ask'
           and (not HAS_TW or (call(port, tok, 'GET', '/v1/tabwork?session=x')[0] == 400 and call(port, tok, 'POST', '/v1/tabwork/ask', {'session': '../x'})[0] == 400)))
        if not HAS_TW:
            ok('작업 모드 대본 없는 판: 요청 = 503 · 끝 = 묻기', call(port, tok, 'POST', '/v1/tabwork/ask', {'session': tsid})[0] == 503
               and json.loads(call(port, tok, 'POST', '/v1/tabwork/end', {'session': tsid})[2]).get('state') == 'ask')
        if HAS_TW and ap_src and os.path.isfile(ap_src):
            c, _, b = call(port, tok, 'POST', '/v1/tabwork/ask', {'session': tsid, 'why': '제목 고쳐 줘'})
            ok('작업 모드 요청 = 폰 승인 대기(명령 요청 하나)', c == 200 and json.loads(b).get('state') == 'waiting'
               and any(r['run'] == 'tabwork' for r in json.loads(call(port, tok, 'GET', '/v1/approve')[2])['runs']), b[:200])
            c, _, b = call(port, tok, 'POST', '/v1/tabwork/end', {'session': tsid})
            ok('대화 끝 = 묻기 · 대기 요청 닫힘', c == 200 and json.loads(b).get('state') == 'ask'
               and not any(r['run'] == 'tabwork' for r in json.loads(call(port, tok, 'GET', '/v1/approve')[2])['runs']), b[:200])
        def nc_args(body):                          # 가짜 실행기가 받은 인자(done 사건)
            c_, _, b_ = call(port, tok, 'POST', '/v1/notechat', body)
            jb, t1 = json.loads(b_).get('job') if c_ == 200 else None, time.time()
            while jb and time.time() - t1 < 10:
                j_ = json.loads(call(port, tok, 'GET', f'/v1/notechat?job={jb}')[2])
                d_ = [e for e in j_['events'] if e['t'] == 'done']
                if d_:
                    return d_[0]['args']
                time.sleep(0.1)
            return None
        ar = nc_args({'text': '제목 고쳐 줘', 'resume': tsid})
        ok('승인 표 없는 대화 = 지금과 같음(--work·--mode-note 없음)', ar is not None and '--work' not in ar and '--mode-note' not in ar, ar)
        if HAS_TW and ap_src and os.path.isfile(ap_src):
            sys.path.insert(0, s)
            import tabwork as TWm                   # 가짜 볼트 사본 — 폰 서명 대신 적용기 장부에 run-start 한 줄(서명 길 자체는 tabwork_check.py)
            TWm.ask(v, {'session': tsid, 'why': '제목'})
            nn_ = TWm._records(v, tsid)[-1]['nn']
            with open(os.path.join(s, '_index', 'approve', 'ledger.jsonl'), 'a', encoding='utf-8') as f:
                f.write(json.dumps({'at': int(time.time()), 'ev': 'run-start', 'run': 'tabwork', 'id': nn_}) + '\n')
            ar = nc_args({'text': '이어서', 'resume': tsid})
            ok('승인된 대화 = --work + 바뀐 첫 턴 --mode-note', ar is not None and '--work' in ar and '--mode-note' in ar, ar)
            ar = nc_args({'text': '또', 'resume': tsid})
            ok('같은 모드 다음 턴 = --work 만', ar is not None and '--work' in ar and '--mode-note' not in ar, ar)
            call(port, tok, 'POST', '/v1/tabwork/end', {'session': tsid})
            ar = nc_args({'text': '끝난 뒤', 'resume': tsid})
            ok('대화 끝 뒤 = 묻기 + 바뀐 첫 턴 --mode-note', ar is not None and '--work' not in ar and '--mode-note' in ar, ar)
        ok('작업 모드 길 = 열쇠 없으면 막힘', call(port, None, 'POST', '/v1/tabwork/ask', {'session': tsid})[0] in (401, 403)
           and call(port, None, 'GET', f'/v1/tabwork?session={tsid}')[0] in (401, 403))

        # ── 11-16 sdocx: 폰·탭 공유 받기 = POST /v1/upload?name=&sha256= → 받은함 새 파일(종류 안 가림 · 덮지 않음 · «이름 (2)» · 받은 바이트 그대로 · 경로 거름) ──
        def up(name, data, want=None, t=tok):
            qs = 'name=' + urllib.parse.quote(name) + ('&sha256=' + want if want else '')
            h = {'Content-Type': 'application/octet-stream'}
            if t is not None:
                h['Authorization'] = 'Bearer ' + t
            req = urllib.request.Request(f'http://127.0.0.1:{port}/v1/upload?' + qs, data=data, headers=h, method='POST')
            try:
                with urllib.request.urlopen(req, timeout=120) as r:
                    return r.status, json.loads(r.read() or b'{}')
            except urllib.error.HTTPError as e:
                try:
                    return e.code, json.loads(e.read() or b'{}')
                except (OSError, ValueError):
                    return e.code, {}
            except OSError:
                return 0, {}
        inb = lambda *p: os.path.join(v, '1_수집', '받은함', *p)
        ub1 = b'PK\x03\x04' + bytes(range(256)) * 300
        ub2 = b'PK\x03\x04' + bytes(range(255, -1, -1)) * 300
        hx = lambda b: hashlib.sha256(b).hexdigest()
        c, j = up('견본 노트.sdocx', ub1, hx(ub1))
        ok('공유 받기 → 받은함 · 받은 바이트 그대로 · sha256', c == 200 and j.get('path') == '1_수집/받은함/견본 노트.sdocx' and j.get('sha256') == hx(ub1)
           and sha(inb('견본 노트.sdocx')) == hx(ub1), f'{c} {j}')
        c2, j2 = up('견본 노트.sdocx', ub2)
        ok('같은 이름 다른 내용 = «이름 (2)» · 앞 파일 그대로', c2 == 200 and j2.get('path') == '1_수집/받은함/견본 노트 (2).sdocx'
           and sha(inb('견본 노트.sdocx')) == hx(ub1) and sha(inb('견본 노트 (2).sdocx')) == hx(ub2), f'{c2} {j2}')
        c3, j3 = up('견본 노트.sdocx', ub1, hx(ub1))
        ok('응답 못 받고 또 보냄(같은 내용) = 한 벌', c3 == 200 and j3.get('same') and j3.get('path') == '1_수집/받은함/견본 노트.sdocx'
           and not os.path.exists(inb('견본 노트 (3).sdocx')), f'{c3} {j3}')
        c4, _ = up('한글 문서.hwp', b'HWP Document File' + b'\0' * 100)
        ok('종류 안 가림(.hwp)', c4 == 200 and os.path.isfile(inb('한글 문서.hwp')), str(c4))
        before = set(os.listdir(inb()))
        bad = {n: up(n, ub1)[0] for n in ('../밖.sdocx', '../../2_지식/밖.sdocx', 'a/b.sdocx', 'a\\b.sdocx', '.숨김', 'con.txt', 'NUL', '끝점.', 'x:y.sdocx', 'C:/w.sdocx', '', 'a' * 151)}
        ok('이름 거름(위로·폴더·역슬래시·숨김·예약·끝 점/칸·스트림·드라이브·빈·긴) = 400 · 새 파일 없음', all(x == 400 for x in bad.values()) and set(os.listdir(inb())) == before
           and not os.path.exists(os.path.join(v, '1_수집', '밖.sdocx')) and not os.path.exists(A('2_지식', '밖.sdocx')), str(bad))
        c5, _ = up('틀린 해시.sdocx', ub1, hx(ub2))
        c6, _ = up('빈 파일.sdocx', b'')
        c7, _ = up('열쇠 없음.sdocx', ub1, t=None)
        ok('sha256 다름 = 400 · 빈 파일 = 400 · 열쇠 없음 = 401/403 · 안 생김', c5 == 400 and c6 == 400 and c7 in (401, 403)
           and not any(os.path.exists(inb(n)) for n in ('틀린 해시.sdocx', '빈 파일.sdocx', '열쇠 없음.sdocx')), f'{c5} {c6} {c7}')
        # ── 11-18 필기 11차: 폰·탭 «PDF 로 볼트에 저장» = to=0_작업/필기/ · 같은 이름은 옛 판 휴지통 거쳐 덮음 · 같은 내용 = 한 벌 · 그 아래 폴더·다른 자리 = 403 ──
        def upto(name, data, to):
            qs = 'name=' + urllib.parse.quote(name) + '&sha256=' + hx(data) + '&size=' + str(len(data)) + '&offset=0&to=' + urllib.parse.quote(to)
            req = urllib.request.Request(f'http://127.0.0.1:{port}/v1/upload?' + qs, data=data, method='POST',
                                         headers={'Content-Type': 'application/octet-stream', 'Authorization': 'Bearer ' + tok})
            try:
                with urllib.request.urlopen(req, timeout=120) as r:
                    return r.status, json.loads(r.read() or b'{}')
            except urllib.error.HTTPError as e:
                return e.code, json.loads(e.read() or b'{}')
        outp = lambda *q: os.path.join(v, '0_작업', '필기', *q)
        pd1, pd2 = b'%PDF-1.7\n' + b'a' * 500, b'%PDF-1.7\n' + b'b' * 700
        c1_, j1_ = upto('내보냄.pdf', pd1, '0_작업/필기/')
        c2_, j2_ = upto('내보냄.pdf', pd2, '0_작업/필기')
        c3_, j3_ = upto('내보냄.pdf', pd2, '0_작업/필기/')
        ok('필기 PDF 로 볼트에 = 0_작업/필기/<이름> · 같은 이름 다른 내용 = 덮음(«(2)» 없음) · 같은 내용 = 한 벌',
           c1_ == 200 and j1_.get('path') == '0_작업/필기/내보냄.pdf' and c2_ == 200 and j2_.get('path') == '0_작업/필기/내보냄.pdf'
           and sha(outp('내보냄.pdf')) == hx(pd2) and not os.path.exists(outp('내보냄 (2).pdf')) and c3_ == 200 and j3_.get('same'), f'{c1_} {j1_} {c2_} {j2_} {c3_} {j3_}')
        with open(os.path.join(s, 'ledger', 'ops.jsonl'), encoding='utf-8') as f_:
            led = [json.loads(x) for x in f_ if x.strip()]
        ok('덮은 옛 판 = 휴지통(장부 rm · 그 자리)', any(e.get('op') == 'rm' and e.get('src') == '0_작업/필기/내보냄.pdf' for e in led), str(led[-3:]))
        bad_to = {to_: upto('밖.pdf', pd1, to_)[0] for to_ in ('0_작업/필기/아래/', '0_작업/', '2_지식/', '0_작업/필기/../밖/')}
        ok('필기 내보냄 자리 밖(아래 폴더·위·다른 뿌리) = 403/400 · 안 생김', all(x in (400, 403) for x in bad_to.values())
           and not os.path.exists(outp('아래', '밖.pdf')) and not os.path.exists(os.path.join(v, '0_작업', '밖.pdf')), str(bad_to))
        # ── 11-23 폰 PDF: 내보낸 PDF 자리 = 0_작업/<영역>/<주제>/… (brain-source outdir.ts) · 덮음 · 영역 밖·주제 없음·위로 = 막음 ──
        c4_, j4_ = upto('노트.pdf', pd1, '0_작업/일/주제A/PDF/')
        c5_, j5_ = upto('노트.pdf', pd2, '0_작업/일/주제A/PDF')
        ok('내보낸 PDF = 0_작업/<영역>/<주제>/…/<이름> · 같은 이름 = 덮음', c4_ == 200 and j4_.get('path') == '0_작업/일/주제A/PDF/노트.pdf' and c5_ == 200 and j5_.get('path') == '0_작업/일/주제A/PDF/노트.pdf', f'{c4_} {j4_} {c5_} {j5_}')
        bad2 = {to_: upto('밖.pdf', pd1, to_)[0] for to_ in ('0_작업/기타/주제/', '0_작업/일/', '0_작업/일/a/../../../밖/', '0_작업/일/.숨은/', '1_수집/일/a/')}
        ok('내보낸 PDF 자리 밖 = 403/400', all(x in (400, 403) for x in bad2.values()), str(bad2))
        # ── 11-23 폰 PDF 를 PC 가 만듦: POST /v1/pdf(본문 = HTML) → 헤드리스 인쇄 → 그 자리 · 바깥 주소는 CSP 가 막음 ──
        def pdf_(name, html, to):
            req = urllib.request.Request(f'http://127.0.0.1:{port}/v1/pdf?name=' + urllib.parse.quote(name) + '&to=' + urllib.parse.quote(to), data=html.encode('utf-8'), method='POST',
                                         headers={'Content-Type': 'text/html; charset=utf-8', 'Authorization': 'Bearer ' + tok})
            try:
                with urllib.request.urlopen(req, timeout=180) as r:
                    return r.status, json.loads(r.read() or b'{}')
            except urllib.error.HTTPError as e:
                return e.code, json.loads(e.read() or b'{}')
        import pdfprint as pp_
        if pp_.browser():
            doc_ = '<!doctype html><html><head><meta charset="utf-8"><style>@page{size:A4}</style></head><body><h1>한글 제목</h1><table><tr><td>가</td><td>1</td></tr></table><img src="http://127.0.0.1:1/x.png"></body></html>'
            c6_, j6_ = pdf_('노트.pdf', doc_, '0_작업/일/주제A/PDF/')
            pb_ = open(os.path.join(v, *'0_작업/일/주제A/PDF/노트.pdf'.split('/')), 'rb').read() if c6_ == 200 else b''
            ok('PC PDF = /v1/pdf HTML → 0_작업/<영역>/<주제>/…/<이름>.pdf(덮음) · %PDF · 글자 있음', c6_ == 200 and j6_.get('path') == '0_작업/일/주제A/PDF/노트.pdf' and pb_.startswith(b'%PDF') and b'/Font' in pb_, f'{c6_} {j6_} {len(pb_)}')
            bad3 = [pdf_('밖.pdf', doc_, '0_작업/기타/a/')[0], pdf_('노트.txt', doc_, '0_작업/일/주제A/PDF/')[0], pdf_('빈.pdf', '  ', '0_작업/일/주제A/PDF/')[0]]
            ok('PC PDF 막음 = 자리 밖 403 · .pdf 아님 400 · 빈 문서 400', bad3 == [403, 400, 400], str(bad3))
        else:
            ok('PC PDF — 이 PC 에 크롬·엣지 없음(건너뜀)', True)
        # ── 11-16 큰 파일(사용자 «64mb 제한 없애기»): 상한 = PC 남은 자리(2GB 남김 → 507) · 흘려 받음 · 끊기면 받은 자리부터 이어 받음 ──
        updir = os.path.join(s, '_index', 'server', 'upload')

        def raw(qs, n, send=b''):                   # 머리 + 본문 앞부분만 보내고 연결을 쥔다(폰이 망을 잃은 꼴)
            so = socket.create_connection(('127.0.0.1', port), timeout=20)
            so.sendall(('POST /v1/upload?' + qs + ' HTTP/1.1\r\nHost: x\r\nAuthorization: Bearer ' + tok
                        + '\r\nContent-Length: ' + str(n) + '\r\n\r\n').encode('utf-8') + send)
            return so

        def code_of(so):
            try:
                return so.recv(64).split(b' ')[1].decode()
            except (OSError, IndexError):
                return '0'
            finally:
                so.close()

        def ask(h_, n_, name_=None):
            c_, _, b_ = call(port, tok, 'GET', f'/v1/upload?sha256={h_}&size={n_}' + ('&name=' + urllib.parse.quote(name_) if name_ else ''))
            return c_, json.loads(b_ or b'{}')

        def upq(qs, data):
            req = urllib.request.Request(f'http://127.0.0.1:{port}/v1/upload?' + qs, data=data, method='POST',
                                         headers={'Content-Type': 'application/octet-stream', 'Authorization': 'Bearer ' + tok})
            try:
                with urllib.request.urlopen(req, timeout=120) as r:
                    return r.status, json.loads(r.read() or b'{}')
            except urllib.error.HTTPError as e:
                return e.code, json.loads(e.read() or b'{}')
        huge = 2 ** 50
        st = code_of(raw('name=' + urllib.parse.quote('큰 파일.bin'), huge, b'\0' * 1024))
        c, j = ask('0' * 64, huge)
        ok('PC 남은 자리보다 큼 = 507(본문 받기 전 · 묻기도 · 남김 2GB) · 안 생김', st == '507' and c == 507 and j.get('margin') == 2 * 2 ** 30
           and not os.path.exists(inb('큰 파일.bin')), f'{st} {c} {j}')
        big = os.urandom(64 * 2 ** 20 + 1)
        c, j = up('64MB 넘는 영상.mp4', big, hx(big))
        ok('64MB 넘어도 받음(옛 상한 없앰) · 바이트 그대로', c == 200 and sha(inb('64MB 넘는 영상.mp4')) == hx(big), f'{c} {j}')
        del big
        rb = os.urandom(5 * 2 ** 20 + 123)
        rh, cut = hx(rb), 2 * 2 ** 20 + 7
        rq = lambda o: 'name=' + urllib.parse.quote('이어 받기.mp4') + f'&sha256={rh}&size={len(rb)}&offset={o}'
        so = raw(rq(0), len(rb), rb[:cut])
        time.sleep(0.3)
        so.close()                                  # 연결이 닫힘(폰이 끊음)
        for _ in range(50):
            c, j = ask(rh, len(rb))
            if j.get('have') == cut:
                break
            time.sleep(0.1)
        have = j.get('have')
        c2, j2 = upq(rq(have or 0), rb[have or 0:])
        ok('끊긴 뒤 묻기 = 받은 자리 · 거기부터 이어 받음 · 바이트 그대로', have == cut and c2 == 200 and j2.get('path') == '1_수집/받은함/이어 받기.mp4'
           and sha(inb('이어 받기.mp4')) == rh, f'{have} {c2} {j2}')
        c, j = ask(rh, len(rb), '이어 받기.mp4')
        ok('다 받은 뒤 다시 물음(응답 잃은 폰) = 그 경로 · 다시 안 보냄', c == 200 and j.get('same') and j.get('path') == '1_수집/받은함/이어 받기.mp4', f'{c} {j}')
        tb = os.urandom(3 * 2 ** 20)
        th = hx(tb)
        tq = lambda o: 'name=' + urllib.parse.quote('갈아탐.bin') + f'&sha256={th}&size={len(tb)}&offset={o}'
        so = raw(tq(0), len(tb), tb[:2 ** 20])      # 연결은 열린 채(망이 바뀌어 폰은 끊긴 줄 앎 · 서버는 모름)
        time.sleep(0.5)
        t0 = time.time()
        for _ in range(5):
            c, j = ask(th, len(tb))
            c2, j2 = upq(tq(j.get('have', 0)), tb[j.get('have', 0):])
            if c2 == 200:
                break
        dt = time.time() - t0
        so.close()
        ok('끊긴 줄 모르는 옛 연결 = 새 연결이 끊고 이어 받음(본문 멈춤 60초를 안 기다림)', c2 == 200 and sha(inb('갈아탐.bin')) == th and dt < 20, f'{c2} {j2} {dt:.1f}s')
        pb = os.urandom(3 * 2 ** 20 + 5)
        ph = hx(pb)
        pq = lambda o: 'name=' + urllib.parse.quote('나눠 보냄.bin') + f'&sha256={ph}&size={len(pb)}&offset={o}'
        c1, j1 = upq(pq(0), pb[:2 ** 20])
        c3, j3 = upq(pq(5), pb[5:9])
        c2, j2 = upq(pq(2 ** 20), pb[2 ** 20:])
        ok('나눠 보냄 = {have} → 이어서 끝 · 자리 다름 = 409 + have', c1 == 200 and j1.get('have') == 2 ** 20 and 'path' not in j1 and c3 == 409 and j3.get('have') == 2 ** 20
           and c2 == 200 and sha(inb('나눠 보냄.bin')) == ph, f'{c1} {j1} {c3} {j3} {c2}')
        old = os.path.join(updir, 'f' * 64 + '-9.part')
        with open(old, 'wb') as f:
            f.write(b'x')
        os.utime(old, (time.time() - 4 * 86400,) * 2)
        ask('0' * 64, 10)
        ok('조각이 안 남음(다 받은 것) · 사흘 넘게 멈춘 조각은 지움', os.listdir(updir) == [], str(os.listdir(updir)))
        c8, j8 = up(' 앞뒤 칸.pdf ', ub1)
        ok('이름 앞뒤 칸은 떼고 받음', c8 == 200 and j8.get('path') == '1_수집/받은함/앞뒤 칸.pdf', f'{c8} {j8}')
        led = open(os.path.join(s, 'ledger', 'ops.jsonl'), encoding='utf-8').read()
        ok('장부에 남음(by=phone · 폰 공유 받음)', '폰 공유 받음' in led and '견본 노트 (2).sdocx' in led and '"by": "phone"' in led, str(led.count('폰 공유 받음')))

        # ── 11-14 모바일볼트 1-5·4-4: 설명서 장 = 읽기만(파일·링크) · 목록·쓰기·폰 손 = 안 됨 · 3_시스템 나머지는 그대로 막힘 ──
        os.makedirs(A('3_시스템', '설명서', '_index'), exist_ok=True)
        put('3_시스템/설명서/설명서-시험장.md', '# 시험장\n')
        put('3_시스템/설명서/_index/설명서-시험모듈.md', '# 시험모듈 장\n')
        os.makedirs(A('.claude', 'skills', 'mantest'), exist_ok=True)
        put('.claude/skills/mantest/module.json', json.dumps({'contributes': {'manual': [{'file': '.claude/skills/mantest/설명서-시험모듈.md', 'name': '시험모듈', 'gist': '줄거리'}]}}))
        put('.claude/skills/mantest/설명서-시험모듈.md', '# 원본 장\n')
        c1 = call(port, tok, 'GET', '/v1/file?path=' + urllib.parse.quote('3_시스템/설명서/설명서-시험장.md'))[0]
        c2 = call(port, tok, 'GET', '/v1/file?path=' + urllib.parse.quote('3_시스템/server.py'))[0]
        time.sleep(0.1)
        c3, _, b3 = call(port, tok, 'GET', '/v1/resolve?name=' + urllib.parse.quote('설명서-시험모듈'))
        c4 = call(port, tok, 'POST', '/v1/note', {'path': '3_시스템/설명서/설명서-시험장.md', 'base': 'x', 'text': 'y'})[0]
        c5 = fo({'op': 'rm', 'src': '3_시스템/설명서/설명서-시험장.md'})[0]
        c6 = json.loads(call(port, tok, 'GET', '/v1/manual')[2])['items']
        c7 = [x['name'] for x in json.loads(call(port, tok, 'GET', '/v1/list')[2])['items']]
        ok('설명서 = 파일 200 · 3_시스템 나머지 403 · 쓰기·폰 손 4xx · manual = 켜진 모듈 장(사본 있는 것) · 뿌리 목록엔 없음',
           c1 == 200 and c2 == 403 and 400 <= c4 < 500 and 400 <= c5 < 500 and c6 == [{'base': '설명서-시험모듈', 'name': '시험모듈', 'gist': '줄거리'}] and '3_시스템' not in c7,
           f'{c1} {c2} {c3} {b3[:80]} {c4} {c5} {c6} {c7}')

        # ── 11-05: 폰 새 노트(받은함 = 새 md 만 · 덮어쓰기 없음 · 경로 탈출 차단) ──
        inbox = os.path.join(v, '1_수집', '받은함')
        named = lambda name, text='새 글': call(port, tok, 'POST', '/v1/memo', {'text': text, 'name': name, 'at': '2026-11-05 090000'})
        c, _, b = named('폰 새 글')
        ok('새 노트 이름 = 받은함 바로 아래', c == 200 and json.loads(b)['path'] == '1_수집/받은함/폰 새 글.md', b.decode()[:120])
        c, _, b = named('폰 새 글', '다른 글')
        ok('같은 이름 다른 글 = 덮어쓰지 않고 새 파일', c == 200 and json.loads(b)['path'] == '1_수집/받은함/폰 새 글 2.md' and open(os.path.join(inbox, '폰 새 글.md'), encoding='utf-8').read() == '새 글\n', b.decode()[:120])
        c, _, b = named('폰 새 글.md')
        ok('다시 보낸 같은 글 = 한 벌 · 끝의 .md 는 이름에 안 붙음', c == 200 and json.loads(b)['path'] == '1_수집/받은함/폰 새 글.md' and not os.path.exists(os.path.join(inbox, '폰 새 글.md.md')), b.decode()[:120])
        before = {os.path.join(d, f) for d, _, fs in os.walk(v) for f in fs}
        for bad in ('../밖', '..\\밖', '../../밖', 'a/b', 'a\\b', '/절대', 'C:/x', 'C:x', '보통.md:s', '.숨김', 'con', 'NUL.txt', 'com1', '', 'x' * 121, '가<나', '가|나'):
            c = named(bad)[0]
            ok(f'새 노트 이름 막힘 {bad[:12]!r}', c in (400, 403), str(c))
        ok('막힌 이름 = 볼트에 아무것도 안 생김', {os.path.join(d, f) for d, _, fs in os.walk(v) for f in fs} - before <= {os.path.join(s, '_index', 'server', 'server.log')})
        ok('이름이 글자가 아니면 400', call(port, tok, 'POST', '/v1/memo', {'text': 'x', 'name': ['a']})[0] == 400)
        ok('민감 표시 새 노트 막힘', named('민감', '---\nsensitive: true\n---\n카드')[0] == 403)
        ok('받은함에 /v1/new 막힘', call(port, tok, 'POST', '/v1/new', {'path': '1_수집/받은함/새로.md', 'text': 'y'})[0] == 403)
        own = '1_수집/받은함/폰 새 글.md'
        c, h, _ = call(port, tok, 'GET', q(own))
        c1 = call(port, tok, 'POST', '/v1/note', {'path': own, 'base': h.get('ETag'), 'text': '폰에서 고침\n'})[0]
        ok('폰이 만든 받은함 md = 고침(판 확인)', c1 == 200 and open(os.path.join(inbox, '폰 새 글.md'), encoding='utf-8').read() == '폰에서 고침\n', str(c1))
        ok('폰이 만든 md 도 옛 판 위면 409', call(port, tok, 'POST', '/v1/note', {'path': own, 'base': h.get('ETag'), 'text': '옛 판'})[0] == 409)
        put('1_수집/받은함/손으로 넣음.md', '사용자 글\n')
        c, h2, _ = call(port, tok, 'GET', q('1_수집/받은함/손으로 넣음.md'))
        ok('다른 받은함 파일 = 읽기만', c == 200 and call(port, tok, 'POST', '/v1/note', {'path': '1_수집/받은함/손으로 넣음.md', 'base': h2.get('ETag'), 'text': '덮어쓰기'})[0] == 403 and open(os.path.join(inbox, '손으로 넣음.md'), encoding='utf-8').read() == '사용자 글\n')
        os.makedirs(os.path.join(inbox, '폴더'))
        put('1_수집/받은함/폴더/안.md', '안 글\n')
        ok('받은함 하위 폴더 막힘 · 경로 탈출 막힘', call(port, tok, 'POST', '/v1/note', {'path': '1_수집/받은함/폴더/안.md', 'base': 'x', 'text': 'y'})[0] == 403 and call(port, tok, 'POST', '/v1/note', {'path': '1_수집/받은함/../배움/원본.md', 'base': 'x', 'text': 'y'})[0] in (400, 403) and call(port, tok, 'POST', '/v1/note', {'path': '1_수집/받은함/폰 새 글.md:s', 'base': 'x', 'text': 'y'})[0] in (400, 403))
        c, h3, _ = call(port, tok, 'GET', q(own))
        os.replace(os.path.join(inbox, '폰 새 글.md'), os.path.join(v, '2_지식', '일', '옮겨진 글.md'))      # door.py 정리가 옮긴 뒤
        ok('정리가 옮긴 뒤 = 폰 404 · 옮겨진 글 그대로', call(port, tok, 'POST', '/v1/note', {'path': own, 'base': h3.get('ETag'), 'text': '늦은 고침'})[0] == 404 and call(port, tok, 'GET', q(own))[0] == 404 and open(os.path.join(v, '2_지식', '일', '옮겨진 글.md'), encoding='utf-8').read() == '폰에서 고침\n')

        # ── 폰 진단 줄 ──
        slog = os.path.join(s, '_index', 'server', 'server.log')
        diag = lambda lines: call(port, tok, 'POST', '/v1/diag', {'lines': lines})
        c, _, b = diag(['[11-05 09:00:00] 상태 up→asleep', '줄\n바꿈\x1b[31m', 'ㄱ' * 500])
        text = open(slog, encoding='utf-8').read()
        ok('진단 = 서버 로그에 · 제어 문자 지움 · 한 줄 상한', c == 200 and '폰 [11-05 09:00:00] 상태 up→asleep' in text and '줄 바꿈 [31m' in text and 'ㄱ' * 240 in text and 'ㄱ' * 241 not in text, b.decode()[:80])
        c, _, b = diag(['줄'] * 80)
        ok('진단 = 한 번 50줄', c == 200 and json.loads(b)['kept'] == 50, b.decode()[:80])
        try:
            big = call(port, tok, 'POST', '/v1/diag', {'lines': ['ㄱ' * 70000]})[0]
        except OSError:                             # 답을 읽기 전에 끊겨도 안 받은 것은 같다
            big = 413
        ok('진단 본문 상한 413', big == 413, str(big))
        ok('진단 줄 없으면 400', call(port, tok, 'POST', '/v1/diag', {'lines': 'x'})[0] == 400)
        ok('진단 열쇠 없으면 401', call(port, None, 'POST', '/v1/diag', {'lines': ['x']})[0] == 401)
        total = 0
        for _i in range(25):
            total += json.loads(diag(['하루'] * 50)[2])['kept']
        text = open(slog, encoding='utf-8').read()
        ok('진단 = 하루 1000줄 뒤 버리고 한 번 알림', json.loads(diag(['더'])[2])['kept'] == 0 and text.count('폰 진단 하루 상한') == 1 and '폰 더' not in text, str(total))

        # ── Remote Control 상태(읽기만) ──
        rc = lambda: {k: x for k, x in json.loads(call(port, tok, 'GET', '/v1/ping')[2])['rc'].items() if k in ('up', 'url')}     # can·why = 11-17 M9 칸(아래 따로)
        ok('RC 기록 없음 = 꺼짐', rc() == {'up': False}, str(rc()))
        spec = importlib.util.spec_from_file_location('srv_copy', os.path.join(s, 'server.py'))
        srv = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(srv)
        srv_log = srv.log
        me = os.getpid()
        put_rc = lambda d: json.dump(d, open(pointer, 'w', encoding='utf-8'))
        real = srv.proc_start(me)
        ok('프로세스 시작 시각을 읽음 · 없는 pid 는 None', isinstance(real, int) and real > 0 and srv.proc_start(4) != real and srv.proc_start(999999) is None, str(real))
        put_rc({'sessionId': 'session_01A', 'environmentId': 'env_01B', 'source': 'standalone', 'pid': me, 'procStart': str(real)})
        ok('RC 살아 있음 = 켜짐 · 환경 주소', rc() == {'up': True, 'url': 'https://claude.ai/code?environment=env_01B'}, str(rc()))
        put_rc({'environmentId': 'env_01B', 'pid': me, 'procStart': str(real + 1)})
        ok('pid 가 다시 쓰임(시작 시각 다름) = 꺼짐', rc() == {'up': False}, str(rc()))
        put_rc({'environmentId': 'env_01B', 'pid': 999999})
        ok('죽은 pid = 꺼짐', rc() == {'up': False}, str(rc()))
        put_rc({'environmentId': 'https://악성/?x', 'pid': me, 'procStart': str(real)})
        ok('환경 값이 이상하면 주소 안 냄', rc() == {'up': True}, str(rc()))
        with open(pointer, 'w', encoding='utf-8') as f:
            f.write('{깨짐')
        ok('RC 기록이 깨짐 = 꺼짐', rc() == {'up': False}, str(rc()))
        put_rc({'environmentId': 'env_01B', 'pid': 'x'})
        ok('pid 가 글자 = 꺼짐', rc() == {'up': False}, str(rc()))

        # ── Remote Control 켜기(가짜 실행 파일) ──
        os.remove(pointer)
        c, _, b = call(port, tok, 'POST', '/v1/rc', {'args': ['--evil'], 'cmd': 'calc.exe', 'cwd': 'C:/'})
        for _i in range(50):
            time.sleep(0.2)
            if os.path.exists(pointer) and os.path.exists(argv_out):
                break
        time.sleep(0.5)
        run = json.load(open(argv_out, encoding='utf-8'))
        ok('RC 켜기 = 고정 명령만 · 작업 폴더 = 볼트 · 폰이 준 값 안 씀 · 세션 표식 안 물림', c == 200 and json.loads(b)['started'] is True and run['argv'] == ['remote-control', '--permission-mode', 'auto'] and os.path.normcase(run['cwd']) == os.path.normcase(v) and not run['code'], str(run))
        c, _, b = call(port, tok, 'GET', '/v1/ping')
        ok('켠 뒤 ping = 켜짐 · 주소 · can ok', json.loads(b)['rc'] == {'up': True, 'url': 'https://claude.ai/code?environment=env_01Fake', 'can': 'ok'}, b.decode()[-90:])
        c, _, b = call(port, tok, 'POST', '/v1/rc', {})
        ok('이미 돌면 안 띄움', c == 200 and json.loads(b)['started'] is False, b.decode()[:80])
        fake_pid = json.load(open(pointer, encoding='utf-8'))['pid']
        subprocess.run(['taskkill', '/F', '/PID', str(fake_pid)], capture_output=True)
        time.sleep(0.3)
        ok('곧바로 다시 켜기 = 429(간격 상한)', call(port, tok, 'POST', '/v1/rc', {})[0] == 429)
        ok('RC 켜기 열쇠 없으면 401', call(port, None, 'POST', '/v1/rc', {})[0] == 401)
        text = open(slog, encoding='utf-8').read()
        ok('RC 켜기·상한이 로그에', 'RC 켬 pid=' in text and 'RC 켜기 상한' in text)
        srv.RC_LOG = os.path.join(tmp, 'rc.log')
        srv.RC_WATCH = 1
        srv.log = lambda m: seen.append(m)
        seen = []

        def spawn(code):
            with open(srv.RC_LOG, 'wb') as out:
                return subprocess.Popen([sys.executable, '-c', code], stdout=out, stderr=subprocess.STDOUT)
        srv.rc_watch(spawn('import sys; print("why-not"); sys.exit(7)'))
        ok('RC 가 일찍 끝남 = 코드가 로그에 · 까닭은 rc.log', any('RC 일찍 끝남 코드=7' in x for x in seen) and b'why-not' in open(srv.RC_LOG, 'rb').read(), str(seen))
        seen.clear()
        p = spawn('import time; time.sleep(5)')
        srv.rc_watch(p)
        p.kill()
        p.wait()
        ok('RC 가 살아 있음 = 기록 유무가 로그에', any('RC 1초 살아 있음 기록=' in x for x in seen), str(seen))
        srv.log = srv_log
        srv._rc.update(day=time.strftime('%Y-%m-%d'), n=srv.RC_DAY, at=0)
        try:
            srv.rc_start({})
            over = 200
        except srv.Bad as e:
            over = e.code
        ok('RC 켜기 = 하루 상한', over == 429, str(over))
        cfg0 = srv.config                            # 조리법 rc_mode(11-21) — 고른 꼴만 · 목록 밖(권한 건너뛰기)은 auto
        srv.config = lambda: {'rc_mode': 'plan'}
        a1 = srv.rc_args()
        srv.config = lambda: {'rc_mode': 'bypassPermissions'}
        a2 = srv.rc_args()
        srv.config = cfg0
        ok('RC 권한 꼴 = config rc_mode · 목록 밖은 auto', a1 == ('remote-control', '--permission-mode', 'plan') and a2 == ('remote-control', '--permission-mode', 'auto'), str((a1, a2)))

        # ── 폰 플러그인 판(자기 갱신) ──
        ok('올린 판 없음 = 404', call(port, tok, 'GET', '/v1/plugin/brain-server')[0] == 404)
        pub = os.path.join(s, '_index', 'server', 'plugin', 'brain-server')
        os.makedirs(pub)
        with open(os.path.join(pub, 'version.json'), 'w', encoding='utf-8', newline='') as f:
            f.write('{"version": "0.2.1", "files": {"core.js": "틀린 해시도 그대로"}}')
        with open(os.path.join(pub, 'core.js'), 'wb') as f:
            f.write(b'// \xed\x8c\x90\n')
        with open(os.path.join(pub, 'styles.css'), 'wb') as f:
            f.write(b'.a{}')
        with open(os.path.join(pub, 'secret.py'), 'wb') as f:
            f.write(b'x')
        c, _, b = call(port, tok, 'GET', '/v1/plugin/brain-server')
        ok('판 = version.json 그대로(서버가 다시 계산하지 않음)', c == 200 and '틀린 해시도 그대로' in b.decode(), b.decode()[:80])
        c, _, b = call(port, tok, 'GET', '/v1/plugin/brain-server/core.js')
        c2, _, b2 = call(port, tok, 'GET', '/v1/plugin/brain-server/styles.css')
        ok('판 파일 = 바이트 그대로', c == 200 and b == b'// \xed\x8c\x90\n' and c2 == 200 and b2 == b'.a{}')
        for bad in ('/v1/plugin/brain-server/secret.py', '/v1/plugin/brain-server/version.json', '/v1/plugin/brain-server/../../token', '/v1/plugin/..%2f..%2ftoken', '/v1/plugin/BAD', '/v1/plugin/brain-server/core.js/x', '/v1/plugin/brain_server'):
            ok(f'판 길 막힘 {bad}', call(port, tok, 'GET', bad)[0] == 404)
        ok('판 열쇠 없으면 401', call(port, None, 'GET', '/v1/plugin/brain-server')[0] == 401)
        ok('처음 설치 묶음 없음 = 404', call(port, tok, 'GET', '/v1/plugin/brain-server/brain-server.zip')[0] == 404)
        with open(os.path.join(pub, 'brain-server.zip'), 'wb') as f:
            f.write(b'PK-zip-test')
        c, h, b = call(port, tok, 'GET', '/v1/plugin/brain-server/brain-server.zip')
        ok('처음 설치 묶음(손발 앱 «볼트 만들기» · M2) = 열쇠로 바이트 그대로 · zip · 열쇠 없으면 401', c == 200 and b == b'PK-zip-test' and h.get('Content-Type') == 'application/zip'
           and call(port, None, 'GET', '/v1/plugin/brain-server/brain-server.zip')[0] == 401, str(c))
        os.remove(os.path.join(pub, 'brain-server.zip'))         # 뒤 시험 P11(묶음 없음)이 같은 자리를 본다

        # ── 폰 보기 플러그인의 큰 묶음(그 형식을 처음 열 때 받는다) ──
        big = os.path.join(s, '_index', 'server', 'plugin', 'brain-source-mobile')
        os.makedirs(big)
        wasm = bytes(range(256)) * (3 * 2 ** 12)                # 3MB — 서버가 읽는 한 걸음(1MB)보다 크게
        for name, data in (('rhwp_bg.wasm', wasm), ('hwp.js', b'// h'), ('sheet.js', b'// s'), ('main.js', b'// m'), ('manifest.json', b'{}'), ('other.js', b'x'), ('sheet.css', b'x')):
            with open(os.path.join(big, name), 'wb') as f:
                f.write(data)
        ok('큰 묶음 없는 판 = 404', call(port, tok, 'GET', '/v1/plugin/brain-server/rhwp_bg.wasm')[0] == 404)
        c, h, b = call(port, tok, 'GET', '/v1/plugin/brain-source-mobile/rhwp_bg.wasm')
        ok('큰 묶음 = 바이트 그대로 · 길이 · 종류', c == 200 and b == wasm and h.get('Content-Length') == str(len(wasm)) and h.get('Content-Type') == 'application/wasm' and h.get('Accept-Ranges') == 'bytes' and bool(h.get('ETag')), str(dict(h))[:120])
        c, h, b = call(port, tok, 'GET', '/v1/plugin/brain-source-mobile/rhwp_bg.wasm', headers={'Range': f'bytes={2 ** 20}-{2 ** 20 + 9}'})
        ok('큰 묶음 조각 = 206 · 그 자리 바이트', c == 206 and b == wasm[2 ** 20:2 ** 20 + 10] and h.get('Content-Range') == f'bytes {2 ** 20}-{2 ** 20 + 9}/{len(wasm)}', str(c))
        tag = h.get('ETag')
        c, h, b = call(port, tok, 'GET', '/v1/plugin/brain-source-mobile/rhwp_bg.wasm', headers={'Range': f'bytes={len(wasm) - 5}-'})
        ok('이어 받기 = 끝까지 · ETag 같음', c == 206 and b == wasm[-5:] and h.get('ETag') == tag)
        ok('파일 밖 조각 = 416', call(port, tok, 'GET', '/v1/plugin/brain-source-mobile/rhwp_bg.wasm', headers={'Range': f'bytes={len(wasm)}-'})[0] == 416)
        for name, ct, want in (('hwp.js', 'text/javascript', b'// h'), ('sheet.js', 'text/javascript', b'// s'), ('main.js', 'text/javascript', b'// m'), ('manifest.json', 'application/json', b'{}')):
            c, h, b = call(port, tok, 'GET', '/v1/plugin/brain-source-mobile/' + name)
            ok(f'큰 묶음 {name}', c == 200 and b == want and (h.get('Content-Type') or '').startswith(ct))
        for bad in ('/v1/plugin/brain-source-mobile/other.js', '/v1/plugin/brain-source-mobile/sheet.css', '/v1/plugin/brain-source-mobile/hwp.js.tmp', '/v1/plugin/brain-source-mobile/rhwp_bg.wasm/x', '/v1/plugin/brain-source-mobile/..%2f..%2ftoken'):
            ok(f'큰 묶음 길 막힘 {bad}', call(port, tok, 'GET', bad)[0] == 404)
        ok('큰 묶음 열쇠 없으면 401', call(port, None, 'GET', '/v1/plugin/brain-source-mobile/hwp.js')[0] == 401)

        # ── 폰 앱 자기 갱신(APK 판) ──
        ok('올린 앱 판 없음 = 404', call(port, tok, 'GET', '/v1/app/brain-phone')[0] == 404)
        appdir = os.path.join(s, '_index', 'server', 'app', 'brain-phone')
        os.makedirs(appdir)
        apk = bytes(range(256)) * 40                    # 10,240 바이트 — 서버는 내용을 보지 않는다
        meta = '{"version": 3, "name": "0.3.0", "sha256": "올릴 때 적은 값 그대로", "size": 10240}'
        with open(os.path.join(appdir, 'version.json'), 'w', encoding='utf-8', newline='') as f:
            f.write(meta)
        ok('앱 APK 없음 = 404', call(port, tok, 'GET', '/v1/app/brain-phone/brain-phone.apk')[0] == 404)
        with open(os.path.join(appdir, 'brain-phone.apk'), 'wb') as f:
            f.write(apk)
        with open(os.path.join(appdir, 'secret.txt'), 'wb') as f:
            f.write(b'x')
        c, _, b = call(port, tok, 'GET', '/v1/app/brain-phone')
        ok('앱 판 = version.json 그대로(서버가 다시 계산하지 않음)', c == 200 and b.decode() == meta, b.decode()[:80])
        c, h, b = call(port, tok, 'GET', '/v1/app/brain-phone/brain-phone.apk')
        ok('앱 APK = 바이트 그대로 · 길이 · 종류', c == 200 and b == apk and h.get('Content-Length') == str(len(apk)) and h.get('Content-Type') == 'application/vnd.android.package-archive' and h.get('Accept-Ranges') == 'bytes', str(dict(h))[:120])
        c, h, b = call(port, tok, 'GET', '/v1/app/brain-phone/brain-phone.apk', headers={'Range': 'bytes=100-199'})
        ok('앱 APK 조각 = 206 · 그 자리 바이트', c == 206 and b == apk[100:200] and h.get('Content-Range') == f'bytes 100-199/{len(apk)}')
        for bad in ('/v1/app/brain-phone/secret.txt', '/v1/app/brain-phone/version.json', '/v1/app/brain-phone/../../token', '/v1/app/..%2f..%2ftoken', '/v1/app/other', '/v1/app/brain-phone/brain-phone.apk/x', '/v1/app/brain_phone', '/v1/app/brain-phone/'):
            ok(f'앱 판 길 막힘 {bad}', call(port, tok, 'GET', bad)[0] == 404)
        ok('앱 판 열쇠 없으면 401', call(port, None, 'GET', '/v1/app/brain-phone')[0] == 401)
        ok('앱 APK 열쇠 없으면 401', call(port, None, 'GET', '/v1/app/brain-phone/brain-phone.apk')[0] == 401)

        # ── 길이 없는 본문 · 끊긴 연결 ──
        conn = http.client.HTTPConnection('127.0.0.1', int(port), timeout=20)
        conn.request('POST', '/v1/memo', iter([json.dumps({'text': '길이 없는 ', 'at': '2026-11-05 100000'}, ensure_ascii=False)[:-2].encode('utf-8'), '"}'.encode('utf-8')]), headers={'Authorization': 'Bearer ' + tok, 'Content-Type': 'application/json'}, encode_chunked=True)
        r = conn.getresponse()
        got = r.read().decode()
        conn.close()
        ok('chunked 본문 받음', r.status == 200 and '폰메모 2026-11-05 100000' in got and '길이 없는' in open(os.path.join(inbox, '폰메모 2026-11-05 100000.md'), encoding='utf-8').read(), got[:100])

        def raw_post(body):
            with socket.create_connection(('127.0.0.1', int(port)), timeout=20) as so:
                so.sendall(b'POST /v1/memo HTTP/1.1\r\nHost: x\r\nAuthorization: Bearer ' + tok.encode() + b'\r\nTransfer-Encoding: chunked\r\n\r\n' + body)
                return so.recv(64)
        ok('chunked 길이가 글자 = 400', b' 400 ' in raw_post(b'zz\r\n'))
        ok('chunked 음수 길이 = 400', b' 400 ' in raw_post(b'-5\r\n'))
        ok('chunked 상한 = 413', b' 413 ' in raw_post(b'%x\r\n' % (5 * 2 ** 20)))
        with open(os.path.join(v, '0_작업', '큰파일.bin'), 'wb') as f:
            f.write(b'x' * (12 * 2 ** 20))
        so = socket.create_connection(('127.0.0.1', int(port)), timeout=20)
        so.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack('ii', 1, 0))    # 끊을 때 RST — 앱이 뒤로 가 연결이 사라진 경우
        so.sendall(b'GET ' + q('0_작업/큰파일.bin').encode() + b' HTTP/1.1\r\nHost: x\r\nAuthorization: Bearer ' + tok.encode() + b'\r\n\r\n')
        so.recv(4096)
        so.close()
        for _i in range(50):
            time.sleep(0.1)
            text = open(slog, encoding='utf-8').read()
            if re.search(r'GET /v1/file 499', text):
                break
        ok('끊긴 연결 = 499 · 오류·500 아님', 'GET /v1/file 499' in text and 'GET /v1/file 500' not in text and '오류 GET /v1/file' not in text, [x for x in text.splitlines() if '/v1/file' in x][-1])

        # ── Wi-Fi 이름: 못 읽어도 전 값 · ping 은 안 기다림(10분 안의 값 = 바로 · 넘으면 1.5초까지) ──
        def done():
            j = srv._net['job']
            if j is not None:
                j.join(5)
        srv._net.update(at=time.time() - 120, ssid='home-wifi-test', job=None)

        def boom():
            raise subprocess.TimeoutExpired('netsh', 5)
        srv.read_ssid = boom
        v = srv.ssid()
        done()
        ok('netsh 시간 넘김 = 전 값 유지', v == 'home-wifi-test' and srv._net['ssid'] == 'home-wifi-test' and srv._net['job'] is None)
        srv._net.update(at=time.time() - 120, job=None)

        def slow():
            time.sleep(3)
            return 'KUWIFI'
        srv.read_ssid = slow
        t0 = time.time()
        old = srv.ssid()
        took = time.time() - t0
        ok('netsh 가 느림 · 2분 된 값 = 기다리지 않고 전 값', old == 'home-wifi-test' and took < 0.2, f'{took:.2f}초')
        done()
        ok('늦은 값 = 다음 번에 새 값', srv.ssid() == 'KUWIFI')
        srv._net.update(at=time.time() - 700, job=None)
        t0 = time.time()
        old = srv.ssid()
        took = time.time() - t0
        ok('10분 넘은 값 = 1.5초까지 기다린 뒤 전 값', old == 'KUWIFI' and 1.3 < took < 2, f'{took:.2f}초')
        done()
        srv._net.update(at=time.time() - 120, job=None)
        srv.read_ssid = lambda: ''
        srv.ssid()
        done()
        ok('Wi-Fi 끊김(netsh 는 답함) = 다음 번에 빈 값', srv.ssid() == '')

        # ── 로그 상한 ──
        srv.LOG, srv.LOG_MAX = os.path.join(tmp, 'rot.log'), 200
        for _i in range(40):
            srv.log('줄' * 10)
        ok('로그 상한 = .1 로 밀고 새로 씀', os.path.exists(srv.LOG + '.1') and os.path.getsize(srv.LOG) <= 300, str(os.path.getsize(srv.LOG)))

        # ── rc.log 상한(11-17 · 115MB) — 끝에만 쓰는 손잡이를 받은 자식이 계속 써도 서버가 앞을 자른다 · 구멍(0 바이트) 없음 ──
        srv.STATE, srv.RC_LOG, srv.RC_LOG_MARK = tmp, os.path.join(tmp, 'rc.log'), os.path.join(tmp, 'rc-log.json')
        srv.RC_LOG_MAX, srv.RC_LOG_KEEP = 2 ** 20, 64 * 2 ** 10
        writer = 'import sys,time\nfor i in range(400):\n    sys.stdout.write(("line %05d " % i) + "x" * 8000 + "\\n"); sys.stdout.flush(); time.sleep(0.005)\nsys.stdout.write("END\\n")\n'
        with srv.rc_log_open() as out:
            child = subprocess.Popen([sys.executable, '-c', writer], stdout=out, stderr=subprocess.STDOUT, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        trims = 0
        while child.poll() is None:
            trims += srv.trim_rc_log()
            time.sleep(0.2)
        child.wait(30)
        trims += srv.trim_rc_log()
        data = open(srv.RC_LOG, 'rb').read()
        ok('rc.log 상한 = 끝만 남김(자식이 쓰는 중에도) · 구멍 없음 · 끝 줄 그대로', os.path.isfile(srv.RC_LOG_MARK) and trims >= 1 and len(data) <= srv.RC_LOG_MAX + 9000
           and b'\x00' not in data and data.rstrip(b'\r\n').endswith(b'END') and data.startswith('… 앞'.encode('utf-8')), f'잘림 {trims} · {len(data)}B · 구멍 {data.count(0)}')
        with open(srv.RC_LOG, 'wb') as f:
            f.write(b'y' * (2 * 2 ** 20))
        os.remove(srv.RC_LOG_MARK)
        ok('표시 파일이 없으면(옛 손잡이) 안 자름', srv.trim_rc_log() is False and os.path.getsize(srv.RC_LOG) == 2 * 2 ** 20)

        # ── RC 새벽 다시 켜기(11-18) — 가짜 RC(자식 세션 둘 · 1초에 화면 100번)로: 서버 몫 + 쉼 = 자식째 끄고 다시 띄움(새 rc.log 끝 손잡이 · 상한)
        #    손으로 띄움(부모 = 살아 있는 다른 프로세스 · 부모 죽고 기록 없음) · 활동(폰 세션 기록 · 화면 바뀜) · 일하는 중(CPU · 도구 셸) = 건너뜀 · 하루 한 번 · 5시만
        tree_rc = os.path.join(tmp, 'fake_rc_tree.py')
        with open(tree_rc, 'w', encoding='utf-8') as f:
            f.write(r"""import json, os, subprocess, sys, time
ptr, mode = sys.argv[1], sys.argv[2]
work = {'idle': 'import time; time.sleep(120)',
        'busy': 'import time\nt = time.time()\nwhile time.time() - t < 60: pass',
        'tool': 'import subprocess, time; subprocess.Popen(["cmd", "/c", "ping -n 120 127.0.0.1 >nul"]); time.sleep(120)'}[mode]
kids = [subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)']), subprocess.Popen([sys.executable, '-c', work])]
json.dump({'environmentId': 'env_01Tree', 'pid': os.getpid()}, open(ptr, 'w', encoding='utf-8'))
frame = '\x1b[3A\x1b[J* Connected * fake\n    Capacity: 2/32\n' + 'x' * 400 + '\n'
end = time.time() + 120
while time.time() < end:
    sys.stdout.write(frame); sys.stdout.flush(); time.sleep(0.01)
""")
        os.environ['CLAUDE_CONFIG_DIR'] = cfg           # 이 시험 프로세스의 srv 사본도 임시 RC 기록만 본다(진짜 ~/.claude 를 안 봄)
        os.environ.pop('BRAIN_CLAUDE_BIN', None)
        srv.STATE, srv.RC_LOG, srv.RC_LOG_MARK = tmp, os.path.join(tmp, 'rc.log'), os.path.join(tmp, 'rc-log.json')
        srv.RC_OWN, srv.RC_NIGHT = os.path.join(tmp, 'rc-own.json'), os.path.join(tmp, 'rc-night.json')
        srv.LOG, srv.LOG_MAX = os.path.join(tmp, 'night.log'), 2 ** 20
        srv.RC_BUSY_WAIT, srv.RC_LOG_MAX, srv.RC_LOG_KEEP = 1, 64 * 2 ** 10, 16 * 2 ** 10
        alive = lambda q: bool(q) and srv.proc_start(q) is not None
        kids_of = lambda q: [x for x, (pp, n) in srv.proc_tree().items() if pp == q and n.lower() != 'conhost.exe']
        fakes = []

        def wait_ptr(old=None):
            for _i in range(60):
                time.sleep(0.2)
                try:
                    q = json.load(open(pointer, encoding='utf-8'))['pid']
                except (OSError, ValueError, KeyError):
                    continue
                if q != old and alive(q) and len(kids_of(q)) >= 2:
                    fakes.append((q, srv.proc_start(q)))
                    return q
            return None

        def launch(mode):
            os.environ['BRAIN_RC_BIN'] = json.dumps([sys.executable, tree_rc, pointer, mode])
            srv.rc_launch(srv.rc_cmd(srv.rc_env()), srv.rc_env())
            return wait_ptr()
        day1 = datetime.date.today() + datetime.timedelta(days=1)
        t5 = time.mktime(day1.timetuple()) + 5 * 3600 + 600          # 내일 05:10 — 지금보다 5시간 넘게 뒤 = 쉼
        night = lambda: json.load(open(srv.RC_NIGHT, encoding='utf-8'))
        try:
            with open(os.path.join(os.path.dirname(pointer), 'desk.jsonl'), 'w', encoding='utf-8') as f:
                f.write('{"type":"queue-operation","sessionId":"x"}\n')       # 데스크톱 세션 기록(첫 줄 session-owner 아님) — 방금 썼어도 RC 활동 아님
            pid1 = launch('idle')
            kids1 = kids_of(pid1) if pid1 else []
            ok('N1 가짜 RC = 서버 몫(부모 = 이 서버) · 자식 세션 둘', alive(pid1) and srv.rc_owner(pid1, srv.proc_tree()) == ('server', '') and len(kids1) == 2, f'{pid1} {kids1}')
            ok('N2 새벽 5시가 아니면 안 함', srv.rc_nightly(now=t5 - 40 * 60) is None and not os.path.exists(srv.RC_NIGHT))
            r = srv.rc_nightly(now=t5) or {}
            pid2 = wait_ptr(pid1)
            ok('N3 서버 몫 + 2시간 쉼 + 자식 안 일함 = 자식째 끄고 다시 띄움', r.get('result') == '다시 켬' and r.get('kids') == 2 and not alive(pid1) and not any(alive(k) for k in kids1)
               and alive(pid2) and r.get('new') == pid2 and json.load(open(srv.RC_OWN, encoding='utf-8'))['pid'] == pid2 and night()['day'] == day1.isoformat(), f'{r} · 새 {pid2}')
            time.sleep(2)
            ok('N4 다시 켠 RC = 새 rc.log 끝 손잡이 · 상한이 걸림', os.path.isfile(srv.RC_LOG_MARK) and srv.trim_rc_log() is True
               and open(srv.RC_LOG, 'rb').read(len('… 앞'.encode('utf-8'))) == '… 앞'.encode('utf-8'), f'{os.path.getsize(srv.RC_LOG)}B')
            ok('N5 하루 한 번 — 같은 날 다시 순찰 = 안 함', srv.rc_nightly(now=t5 + 600) is None and alive(pid2))
            ok('N6 상태가 서버 로그에', 'RC 새벽 다시 켬: 자식 세션 2개 끔' in open(srv.LOG, encoding='utf-8').read())
            sess = os.path.join(os.path.dirname(pointer), 'phone.jsonl')
            with open(sess, 'w', encoding='utf-8') as f:
                f.write('{"type":"session-owner","sessionId":"y"}\n')
            os.utime(sess, (t5 - 30 * 60, t5 - 30 * 60))
            r = srv.rc_nightly(now=t5, force=True) or {}
            ok('N7 폰 세션 기록이 2시간 안 = 건너뜀 · 안 끔', r.get('result') == '건너뜀' and r.get('why') == 'RC 활동 30분 전' and alive(pid2), str(r))
            os.utime(sess, (t5 - 3 * 3600, t5 - 3 * 3600))
            keep = srv.RC_LOG
            srv.RC_LOG = os.path.join(tmp, 'frames.log')
            fa, fb = b'\x1b[3A\x1b[J* Connected\n    Capacity: 2/32\n', b'\x1b[3A\x1b[J* Connected\n    Capacity: 3/32\n'
            open(srv.RC_LOG, 'wb').write(fa * 5)
            t_a = srv.rc_frame_tick(now=t5 - 3 * 3600)
            t_same = srv.rc_frame_tick(now=t5 - 2 * 3600)
            open(srv.RC_LOG, 'ab').write(fb * 3)
            t_b = srv.rc_frame_tick(now=t5 - 20 * 60)
            srv.RC_LOG = keep
            r = srv.rc_nightly(now=t5, force=True) or {}
            ok('N8 rc.log 화면이 바뀐 때 = 활동(같은 화면 다시 그리기는 아님) · 20분 전 = 건너뜀', t_a and not t_same and t_b and night()['frame_at'] == int(t5 - 20 * 60)
               and r.get('why') == 'RC 활동 20분 전' and alive(pid2), f'{t_a} {t_same} {t_b} {r}')
            d = night()
            d['frame_at'] = int(t5 - 3 * 3600)
            json.dump(d, open(srv.RC_NIGHT, 'w', encoding='utf-8'))
            if pid2:
                srv.rc_kill(pid2)
            for mode, want in (('busy', '자식 세션 일하는 중 — CPU'), ('tool', '자식 세션 일하는 중 — 도구 도는 중(cmd.exe)')):
                q = launch(mode)
                time.sleep(0.5)
                r = srv.rc_nightly(now=t5, force=True) or {}
                ok(f'N9 자식 세션이 일하는 중({mode}) = 건너뜀 · 안 끔', (r.get('why') or '').startswith(want) and r.get('result') == '건너뜀' and alive(q), str(r))
                if q:
                    srv.rc_kill(q)
            holder = subprocess.Popen([sys.executable, '-c', f'import subprocess, sys, time; subprocess.Popen([sys.executable, {tree_rc!r}, {pointer!r}, "idle"], stdout=subprocess.DEVNULL); time.sleep(120)'])
            q = wait_ptr()
            r = srv.rc_nightly(now=t5, force=True) or {}
            ok('N10 손으로 띄운 RC(부모 = 살아 있는 다른 프로세스) = 건너뜀 · 안 끔', r.get('result') == '건너뜀' and r.get('own') == 'hand' and '손으로 띄운 RC' in r.get('why', '') and f'{holder.pid})' in r['why'] and alive(q), str(r))
            holder.kill()
            holder.wait(5)
            ok('N11 부모가 죽고 서버가 띄운 기록 없음 = 손 몫(안 끔)', alive(q) and srv.rc_owner(q, srv.proc_tree()) == ('hand', '부모 없음 · 서버가 띄운 기록 없음') and alive(q))
            with open(srv.LOG, 'a', encoding='utf-8') as f:
                f.write(f'{time.strftime("%Y-%m-%d %H:%M:%S")} RC 켬 pid={q}\n')
            ok('N12 부모가 죽었어도 server.log «RC 켬 pid» 가 시작 2분 안 = 서버 몫(rc-own.json 전에 켠 RC)', alive(q) and srv.rc_owner(q, srv.proc_tree()) == ('server', ''))
            if q:
                srv.rc_kill(q)
            os.remove(pointer)
            ok('N13 RC 안 돎 = 없음', (srv.rc_nightly(now=t5, force=True) or {}).get('result') == '없음')

            # ── RC 되살리기(11-27) — 서버와 함께 사라진 서버 몫 RC 만 다시 띄움 · 서버가 죽음을 봤으면(gone) 안 띄움 · 세션 0 안 함
            rw = srv.rc_resume_why
            ok('R1 판정 — 세션 0 · 돎 · 기록 없음 · gone = 안 함 · 기록 있고 안 돎 = 되살림',
               rw({'pid': 1}, False, 0).startswith('세션 0') and rw({'pid': 1}, True, 1) == 'RC 돎' and rw(None, False, 1).startswith('서버가 띄운 RC 기록 없음')
               and rw({'pid': 1, 'gone': 1}, False, 1).startswith('서버가 돌던 중에') and rw({'pid': 2 ** 31 - 1, 'start': 1}, False, None) == '')
            srv._rc_seen['pid'] = None
            json.dump({'pid': 2 ** 31 - 1, 'start': 1, 'at': 1}, open(srv.RC_OWN, 'w', encoding='utf-8'))
            ok('R2 재부팅 뒤 새 서버(살아 있는 것을 본 적 없음) = 죽었어도 gone 안 적음', srv.rc_seen_tick() is None and 'gone' not in json.load(open(srv.RC_OWN, encoding='utf-8')))
            os.environ['BRAIN_RC_BIN'] = json.dumps([sys.executable, tree_rc, pointer, 'idle'])
            why = srv.rc_resume()
            q = wait_ptr()
            ok('R3 서버와 함께 사라진 서버 몫 RC = 시작 때 다시 띄움 · 새 RC_OWN', why.startswith('다시 켬') and alive(q) and json.load(open(srv.RC_OWN, encoding='utf-8'))['pid'] == q, f'{why} {q}')
            os.replace(pointer, pointer + '.x')             # RC 기록(bridge-pointer)이 아직 없는 때 = 막 띄운 직후
            ok('R4 막 띄운 서버 몫 RC 가 돌면 폰 단추·rc_up = 새로 안 띄움', srv.rc_start({}) == {'ok': True, 'started': False} and srv.rc_resume() == 'RC 돎')
            os.replace(pointer + '.x', pointer)
            if q:
                srv.rc_kill(q)
            time.sleep(1)                                   # 켠 지 30초 안에 끝남 = rc_watch 가 gone 을 적는다
            ok('R5 켠 직후 끝난 RC = rc_watch 가 gone 을 적음 → 다음 시작 때 안 띄움', bool(json.load(open(srv.RC_OWN, encoding='utf-8')).get('gone'))
               and srv.rc_resume().startswith('서버가 돌던 중에'))
            dummy = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)'])
            time.sleep(0.3)
            json.dump({'pid': dummy.pid, 'start': srv.proc_start(dummy.pid), 'at': int(time.time())}, open(srv.RC_OWN, 'w', encoding='utf-8'))
            first = srv.rc_seen_tick()
            dummy.kill()
            dummy.wait(5)
            ok('R6 5분 순찰 = 살아 있으면 봄 · 본 RC 가 끝나면 gone(한 번만)', first == 'alive' and srv.rc_seen_tick() == 'gone' and srv.rc_seen_tick() is None
               and bool(json.load(open(srv.RC_OWN, encoding='utf-8')).get('gone')), first)
            os.environ.pop('BRAIN_RC_BIN', None)
            if os.path.exists(pointer):
                os.remove(pointer)
        finally:
            for q, st in fakes:                     # 시작 시각이 같을 때만(pid 가 다시 쓰였으면 남의 것)
                if st and srv.proc_start(q) == st:
                    srv.rc_kill(q, st)
            os.environ.pop('BRAIN_RC_BIN', None)
            os.environ.pop('CLAUDE_CONFIG_DIR', None)

        # ── 11-17 짝짓기(M2) · 준비 목록(M7) · RC 쓸 수 있나(M9) · 본 기기 · 열쇠 바꾸기 ──
        st = os.path.join(s, '_index', 'server')
        pg = srv.pairing
        base = f'http://127.0.0.1:{port}'
        nb = lambda path: call(port, None, 'GET', path)
        c404 = call(port, tok, 'GET', '/v1/nowhere')
        ok('P1 코드 없을 때 /pair = 없는 길과 같은 404 · POST /v1/pair 404', nb('/pair?c=x')[0] == 404 and nb('/pair?c=x')[2] == c404[2]
           and call(port, None, 'POST', '/v1/pair', {'code': 'x', 'name': 'n', 'kind': 'app'})[0] == 404, nb('/pair?c=x'))
        show = pg.new(st, base)
        code = show['url'].split('c=', 1)[1]
        c, h, b = nb('/pair?c=' + code)
        page = b.decode('utf-8')
        ok('P2 코드 맞음 = 짝 쪽(앱에 넣기·옵시디언에 넣기 · 열쇠 없음 · 캐시 안 함)', c == 200 and 'brainphone' in page and 'obsidian://brain-server?pair=' in page
           and tok not in page and h.get('Cache-Control') == 'no-store', page[:200])
        ok('P3 틀린 코드 = 404', nb('/pair?c=' + code[:-1] + ('A' if code[-1] != 'A' else 'B'))[0] == 404)
        c, _, b = call(port, None, 'POST', '/v1/pair', {'code': code, 'name': '시험 폰', 'kind': 'app'})
        ok('P4 짝짓기(긴 코드 · 앱) = 열쇠 · 기기 기록 · 남은 번 3', c == 200 and json.loads(b)['key'] == tok and pg.load(st)['devices'].get('시험 폰|app')
           and pg.live_codes(pg.load(st), time.time())[-1]['left'] == 3, b.decode()[:80])
        c, _, b = call(port, None, 'POST', '/v1/pair', {'code': show['short'].lower(), 'name': '시험 폰', 'kind': 'obsidian'})
        ok('P5 짧은 코드(소문자·줄표 그대로) · 옵시디언 = 열쇠', c == 200 and json.loads(b)['key'] == tok, b.decode()[:80])
        ok('P6 종류 틀림 = 400', call(port, None, 'POST', '/v1/pair', {'code': code, 'name': 'x', 'kind': 'pc'})[0] == 400)
        for kd in ('app', 'obsidian'):
            call(port, None, 'POST', '/v1/pair', {'code': code, 'name': '탭', 'kind': kd})
        ok('P7 4번 쓰면 끝 = 5번째 404 · 화면 글 지움', call(port, None, 'POST', '/v1/pair', {'code': code, 'name': 'x', 'kind': 'app'})[0] == 404
           and not os.path.exists(os.path.join(st, 'pair-show.json')))
        old = pg.new(st, base, now=time.time() - 601)
        ok('P8 10분 지난 코드 = 404', nb('/pair?c=' + old['url'].split('c=', 1)[1])[0] == 404)
        good = pg.new(st, base)['url'].split('c=', 1)[1]
        for _i in range(10):
            try:
                pg.use(st, 'WRONG-' + str(_i), 'x', 'app')
            except pg.PairError:
                pass
        ok('P9 틀림 10번 = 모든 코드 무효(맞던 코드도 404)', nb('/pair?c=' + good)[0] == 404 and not pg.live_codes(pg.load(st), time.time()))
        os.makedirs(os.path.join(st, 'app', 'brain-phone'), exist_ok=True)     # 앞 시험(자기 갱신)이 만든 자리
        with open(os.path.join(st, 'app', 'brain-phone', 'brain-phone.apk'), 'wb') as f:
            f.write(b'PK-apk-test' * 100)
        code2 = pg.new(st, base)['url'].split('c=', 1)[1]
        c, h, b = nb('/pair/app?c=' + code2)
        ok('P10 앱 받기 = 코드 맞을 때만 APK · 코드 틀리면 404 · 쪽에 «손발 앱 받기»', c == 200 and b == b'PK-apk-test' * 100 and h.get('Content-Type') == 'application/vnd.android.package-archive'
           and nb('/pair/app?c=zz')[0] == 404 and '손발 앱 받기' in nb('/pair?c=' + code2)[2].decode('utf-8'))
        ok('P11 플러그인 묶음 없음 = 404', nb('/pair/plugin?c=' + code2)[0] == 404)
        with open(os.path.join(st, 'pc-ready.json'), 'w', encoding='utf-8') as f:     # PC 준비 = 잰 값을 담아 둠(시험은 진짜 Tailscale·예약을 재지 않음)
            json.dump({'at': time.time(), 'items': {k: True for k in pg.PC_ITEMS}}, f)
        vd = pg.view(st)
        ok('P12 «폰 연결» 자료 = PC 7/7 · QR(svg) · 짧은 코드 · 붙은 기기(시험 폰 앱·옵시디언 · 탭)', vd['pc'] == {'ok': 7, 'n': 7, 'miss': [], 'unknown': []}
           and vd['qr'] and vd['qr']['svg'].startswith('<svg') and len(vd['qr']['short']) == 9 and {(x['name'], x['kind']) for x in vd['devices']} >= {('시험 폰', '앱'), ('시험 폰', '옵시디언'), ('탭', '앱')}, json.dumps(vd, ensure_ascii=False)[:300])
        with open(os.path.join(s, 'views.json'), 'w', encoding='utf-8') as f:     # v 는 위 SSID 시험이 덮었다 — 3_시스템 자리(s)로
            json.dump({'schema': 1, 'views': [{'owner': 'tmod', 'id': 'main', 'name': '시험', 'html': '3_시스템/tv.html', 'data': ['{py}', '3_시스템/tv.py']},
                                              {'owner': 'tpair', 'id': 'pair', 'name': '폰 연결', 'phone': False, 'html': '3_시스템/tv.html', 'data': ['{py}', '3_시스템/tv.py']}]}, f)
        time.sleep(0.05)
        vl = json.loads(call(port, tok, 'GET', '/v1/views')[2])
        ok('P13 PC 전용 화면(phone:false) = /v1/views 에 없음 · 열기·행위 404', not any(x['module'] == 'tpair' for x in vl['views']) and any(x['module'] == 'tmod' for x in vl['views'])
           and call(port, tok, 'GET', '/v1/view?module=tpair&id=pair')[0] == 404
           and call(port, tok, 'POST', '/v1/view/act', {'module': 'tpair', 'id': 'pair', 'act': 'tpair.x', 'args': {}})[0] == 404, str(vl)[:160])
        c, _, b = call(port, tok, 'GET', '/v1/ready/list')
        rl = {x['id']: x for x in json.loads(b)['items']} if c == 200 else {}
        ok('P14 준비 목록 = outside.json 폰 항목(앱이 잼·화면·서버 기록) · 짧은 이름', rl.get('battery', {}).get('how') == 'app' and rl.get('alwayson', {}).get('how') == 'screen'
           and rl.get('plugin', {}).get('how') == 'server' and rl['battery']['name'] == '배터리 예외' and len(rl) >= 13, b.decode()[:200])
        c, _, b = call(port, tok, 'POST', '/v1/ready', {'ver': 32, 'items': {'battery': False, 'notify': True, 'BAD id': True}, 'human': {'alwayson': True}}, {'X-Brain-Device': urllib.parse.quote('시험폰')})
        rp = srv.ready.report(st)
        rj = json.load(open(os.path.join(st, 'ready.json'), encoding='utf-8'))
        ok('P15 준비 보고 = 기기마다 · 잰 값과 사람 확인 가름 · 꼴 틀린 id 버림', c == 200 and rp.get('battery') is False and rp.get('notify') is True and 'alwayson' not in rp
           and rj['시험폰']['human'] == {'alwayson': True} and 'BAD id' not in rj['시험폰']['items'], str(rj)[:200])
        ok('P16 준비 보고 꼴 틀림 = 400', call(port, tok, 'POST', '/v1/ready', {'items': [1, 2]})[0] == 400)
        call(port, tok, 'GET', '/v1/ping', headers={'X-Forwarded-For': '100.64.0.9'})
        call(port, tok, 'GET', '/v1/ping', headers={'X-Forwarded-For': '100.64.0.9', 'X-Brain-Device': urllib.parse.quote('시험폰')})
        call(port, tok, 'GET', '/v1/plugin/brain-source-mobile', headers={'X-Forwarded-For': '100.64.0.10'})
        sj = json.load(open(os.path.join(st, 'seen.json'), encoding='utf-8'))
        ok('P17 본 기기 = tailnet 주소·종류(옵시디언·앱·보기) · PC 안(127.0.0.1) 안 적음', '100.64.0.9|obsidian' in sj and sj.get('100.64.0.9|app', {}).get('name') == '시험폰'
           and '100.64.0.10|viewer' in sj and not any(k.startswith('127.0.0.1') for k in sj) and srv.ready.report(st)['plugin'] is True, str(sj)[:200])
        r = json.loads(call(port, tok, 'GET', '/v1/ping')[2])['rc']
        ok('P18 RC 꺼짐 = can·why — 위에서 켠 가짜 RC 가 30초 안에 죽음 = «켜기 실패»(단추는 회색 + 까닭 · 10분 뒤 다시 잼)', r.get('up') is False and r.get('can') == 'failed' and r.get('why') == '켜기 실패 — PC rc.log', str(r))
        import core_api as _ca
        _ca.init(s)
        sys.modules['claude_bin'] = None            # 진짜 claude 를 띄우지 않게(불러오기 = ImportError = 모름)
        ok('P18b 구독 확인을 못 함(claude_bin 없음) = 모름 · 까닭 한 줄', _ca.rc_can({}, wait=5, force=True) == 'unknown' and _ca.CAN['unknown'], _ca._rc)
        pg.rotate(st)
        new_tok = open(os.path.join(st, 'token'), encoding='utf-8').read().strip()
        ok('P19 열쇠 바꾸기 = 옛 열쇠 401 · 새 열쇠 200 · 살아 있던 코드 무효', new_tok != tok and call(port, tok, 'GET', '/v1/ping')[0] == 401 and call(port, new_tok, 'GET', '/v1/ping')[0] == 200
           and nb('/pair?c=' + code2)[0] == 404)
        ok('P20 바꾼 뒤 안 닿은 기기 = «다시 찍기»', all(x['again'] for x in pg.view(st)['devices']), str(pg.view(st)['devices'])[:200])

        # ── 11-20 /open — Claude 앱 대화의 볼트 링크(https)를 누른 기기 옵시디언으로(열쇠 없음 · 경로만) ──
        vt = os.path.join(tmp, 'vault')             # v 는 위에서 다른 값으로 다시 쓰인다
        os.makedirs(os.path.join(vt, '2_지식'), exist_ok=True)
        with open(os.path.join(vt, '2_지식', '열기 시험.md'), 'w', encoding='utf-8') as f:
            f.write('# 열기\n')
        fq = urllib.parse.quote('2_지식/열기 시험.md', safe='')
        op = lambda q, ua: call(port, None, 'GET', '/open?' + q, headers={'User-Agent': ua})
        a1, w1 = op('file=' + fq, 'Mozilla/5.0 (Linux; Android 15)'), op('file=' + fq, 'Mozilla/5.0 (Windows NT 10.0)')
        ok('O1 안드로이드 = intent(brain-server · md.obsidian) · 윈도 = obsidian://open(볼트 이름) · 열쇠 없이 200',
           a1[0] == 200 and f'intent://brain-server?file={fq}#Intent;scheme=obsidian;package=md.obsidian;end' in a1[2].decode('utf-8')
           and w1[0] == 200 and f'obsidian://open?vault={urllib.parse.quote(os.path.basename(vt), safe="")}&file={fq}' in w1[2].decode('utf-8'), a1[0])
        ok('O2 to=phone = 윈도에서도 폰 꼴로 바로', 'location.replace("obsidian://brain-server?file=' + fq in op('file=' + fq + '&to=phone', 'Windows')[2].decode('utf-8'))
        bad = [op('file=' + urllib.parse.quote(p, safe=''), 'Windows') for p in ('../x.md', '.claude/settings.json', '2_지식/없음.md', '')]
        ok('O3 위로 나가기·점 폴더·없는 파일·빈 경로 = 404 · 넘김 없음', all(b[0] == 404 and b'location.replace' not in b[2] for b in bad), [b[0] for b in bad])
        ok('O4 /open 이 다른 길을 안 엶(열쇠 없는 /v1/file = 401)', call(port, None, 'GET', '/v1/file?path=' + fq)[0] == 401)
        # 11-20 사용자 «보던 창을 지우고 그 자리를 차지» · «크롬 창이 그대로 남음» — PC 주소 = 새 탭 · 탭 닫기 신호 = 서버가 잰 전경 창
        wb = w1[2].decode('utf-8')
        ok('O5 PC 주소 = 새 탭(paneType=tab) · 쪽이 /open/front 를 물음', f'&file={fq}&paneType=tab' in wb and '/open/front?wait=' in wb)
        # 11-21: 바깥 주소로 넘기면 크롬이 HTML 해석을 멈춰 그 뒤 <script> 를 안 읽는다 → 넘기기는 맨 끝 대본 하나 · 닫기 대본은 그 앞
        sc = re.findall(r'<script>(.*?)</script>', wb, re.S)
        ok('O5b 넘기기(location.replace)는 맨 끝 대본 · 닫기 대본(/open/front)은 그 앞 · 뒤에 대본 없음',
           len(sc) == 2 and '/open/front' in sc[0] and 'location.replace' not in sc[0] and sc[1].startswith('location.replace(')
           and wb.rindex('<script>') > wb.rindex('</a>'), [s[:30] for s in sc])
        fr = call(port, None, 'GET', '/open/front?wait=0')
        far = call(port, None, 'GET', '/open/front?wait=0', headers={'X-Forwarded-For': '100.64.0.9'})
        ok('O6 /open/front = 이 PC 요청만 참/거짓 하나(열쇠 없음) · 다른 기기 주소 = 404',
           fr[0] == 200 and set(json.loads(fr[2])) == {'front'} and isinstance(json.loads(fr[2])['front'], bool) and far[0] == 404, (fr[0], fr[2][:60], far[0]))
    finally:
        pr.terminate()
        pr.wait(5)
        shutil.rmtree(tmp, ignore_errors=True)
    print('== 실패 ' + str(len(fails)) + ('건: ' + ' · '.join(fails) if fails else '건'), flush=True)


if __name__ == '__main__':
    main()
