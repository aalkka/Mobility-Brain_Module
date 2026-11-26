"""tabwork.py 시험(11-22) — 가짜 볼트(임시 · 한글 경로) + 진짜 적용기 사본(approve.py) + 시험 키(소프트웨어 P-256).
진짜 볼트·진짜 장부·진짜 키 목록은 안 건드린다. 폰 앱(Keystore)·탭 화면은 에뮬레이터 끝-끝이 잰다.

  py -3 .claude/skills/mobility/scripts/tabwork_check.py

길: 승인(폰 서명 → 적용기 run-start → work · 30분 시한) · 끝(end → ask) · 거절(reject-cmd → rejected) · 대기 만료(명령 요청도 닫힘) ·
늦은 서명(대기 시한 뒤 = 안 켬) · 위조(기록·요청 파일만 고침 = 안 켬) · 다른 대화 id 는 못 씀 · 대기 상한.
"""
import base64
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

HERE = os.path.dirname(os.path.abspath(__file__))
VAULT_REAL = os.path.normpath(os.path.join(HERE, '..', '..', '..', '..'))
AP_SRC = os.path.join(VAULT_REAL, '3_시스템', 'hooks', 'approve', 'approve.py')
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
for k in ('BIGBOSS_STATE', 'APPROVE_STATE'):
    os.environ.pop(k, None)
os.environ['APPROVE_NO_ALERT'] = '1'
fails, count = [], 0


def ok(name, cond, extra=''):
    global count
    count += 1
    print(('통과: ' if cond else '실패: ') + name, '' if cond else str(extra)[:400], flush=True)
    if not cond:
        fails.append(name)


tmp = tempfile.mkdtemp(prefix='탭작업-')
V = os.path.join(tmp, '볼트')
HOOK = os.path.join(V, '3_시스템', 'hooks', 'approve')
os.makedirs(os.path.join(HOOK, 'used'))       # 쓴 도전값 자리(진짜 적용기 폴더처럼 · 없으면 적용기가 실행 안 함)
shutil.copy2(AP_SRC, HOOK)
shutil.copy2(os.path.join(os.path.dirname(AP_SRC), 'used', '.gitignore'), os.path.join(HOOK, 'used'))  # mf:allow-path — 승인 폴더 안의 제 파일(볼트 뿌리의 것이 아님)
priv = ec.generate_private_key(ec.SECP256R1())
spki = priv.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
KID = hashlib.sha256(spki).hexdigest()[:16]
with open(os.path.join(HOOK, 'keys.txt'), 'w', encoding='utf-8', newline='\n') as f:
    f.write(f'# 시험 키\n{KID} {base64.b64encode(spki).decode()} 2026-11-22T00:00:00 시험폰\n')

spec = importlib.util.spec_from_file_location('ap', os.path.join(HOOK, 'approve.py'))
AP = importlib.util.module_from_spec(spec)
spec.loader.exec_module(AP)
sys.path.insert(0, HERE)
import tabwork as TW  # noqa: E402

S1, S2, S3, S4 = ('11111111-1111-4111-8111-111111111111', '22222222-2222-4222-8222-222222222222',
                  '33333333-3333-4333-8333-333333333333', '44444444-4444-4444-8444-444444444444')


def cli(*args, data=None):
    r = subprocess.run([sys.executable, os.path.join(HOOK, 'approve.py'), *args], input=data, capture_output=True, cwd=V)
    try:
        return json.loads(r.stdout.decode('utf-8', 'replace').strip().splitlines()[-1])
    except (ValueError, IndexError):
        return {'ok': False, 'raw': r.stdout.decode('utf-8', 'replace')[-300:] + r.stderr.decode('utf-8', 'replace')[-300:]}


def nn_of(session):
    return TW._records(V, session)[-1]['nn']


def phone_sign(nn):
    """폰이 하는 일: 도전값 받기 → 서명 글 만들기 → 지문(여기선 시험 키) → 보냄."""
    ch = cli('challenge-cmd', TW.RUN, str(nn), '--json')
    if not ch.get('ok'):
        return ch
    it = AP.cmd_item(TW.RUN, nn)
    files = AP.cmd_files(it['cmd'], it['cwd'])
    msg = AP.run_message(TW.RUN, nn, it, files, ch['challenge'], str(int(time.time() * 1000)), KID)
    sig = priv.sign(msg, ec.ECDSA(hashes.SHA256()))
    return cli('apply-signed', '-', data=json.dumps({'message': base64.b64encode(msg).decode(), 'sig': base64.b64encode(sig).decode()}).encode())


def wait_state(session, want, secs=20):
    t = time.time() + secs
    st = None
    while time.time() < t:
        st = TW.status(V, {'session': session})
        if st['state'] == want:
            return st
        time.sleep(0.3)
    return st


# ── 1 승인 길 ──
ok('처음 = 묻기', TW.status(V, {'session': S1})['state'] == 'ask' and TW.mode(V, S1) == 'ask')
r = TW.ask(V, {'session': S1, 'why': '이 노트 제목 고쳐 줘'})
ok('요청 = 대기 · 시한', r['state'] == 'waiting' and r['expires'] > time.time())
req = AP.cmd_item(TW.RUN, nn_of(S1))
ok('명령 요청 = 적용기 규칙 통과 · 목적·사유', req['state'] == 'pending' and req['purpose'] == TW.PURPOSE and S1[:8] in req['reason']
   and req['cmd'] == TW.expected_cmd(S1, TW._records(V, S1)[-1]['nonce']) and AP.req_why(req) is None, req)
ok('같은 대화 다시 = 같은 요청', TW.ask(V, {'session': S1, 'why': 'x'})['state'] == 'waiting' and len(TW._records(V, S1)) == 1)
ok('대기 중엔 작업 모드 아님', TW.mode(V, S1) == 'ask')
res = phone_sign(nn_of(S1))
ok('폰 서명 → 적용기 받음', res.get('ok') and res.get('started'), res)
st = wait_state(S1, 'work')
ok('서명 뒤 = 작업 모드 · 30분 시한', st['state'] == 'work' and abs(st['until'] - (time.time() + TW.WORK_TTL)) < 60, st)
ok('mode = work', TW.mode(V, S1) == 'work')
ok('다른 대화는 묻기 그대로', TW.mode(V, S2) == 'ask')
_r, _t = None, time.time() + 30      # 실행기가 창 없이 도는 데 바쁜 PC 에서 몇 초 걸린다(1초로는 «running» 에서 잼 · 11-27)
while time.time() < _t:
    _r = cli('result', TW.RUN, str(nn_of(S1)))
    if _r.get('state') not in ('running', 'pending', None):
        break
    time.sleep(0.5)
ok('적용기 결과 = done', (_r or {}).get('state') == 'done', _r)
ok('같은 서명 다시 = 거절', not phone_sign(nn_of(S1)).get('started'))
# 시한: 장부 시각을 31분 전으로 보면 만료
real_signed = TW._signed_at
TW._signed_at = lambda v, nn: real_signed(v, nn) - TW.WORK_TTL - 60
ok('30분 지나면 만료', TW.status(V, {'session': S1})['state'] == 'expired' and TW.mode(V, S1) == 'ask')
TW._signed_at = real_signed
r = TW.end(V, {'session': S1})
ok('대화 끝 = 묻기', r['state'] == 'ask' and TW.mode(V, S1) == 'ask' and TW.status(V, {'session': S1})['state'] == 'ask')

# ── 2 거절 길 ──
TW.ask(V, {'session': S2, 'why': '파일 지워 줘'})
n2 = nn_of(S2)
ok('폰 거절', cli('reject-cmd', TW.RUN, str(n2), '--why', '안 시킴').get('ok'))
st = TW.status(V, {'session': S2})
ok('거절 = rejected · 묻기 그대로', st['state'] == 'rejected' and TW.mode(V, S2) == 'ask', st)
ok('거절 뒤 서명 = 안 켬', not phone_sign(n2).get('started') and TW.mode(V, S2) == 'ask')
ok('거절 뒤 다시 물음 = 새 요청', TW.ask(V, {'session': S2, 'why': '다시'})['state'] == 'waiting' and nn_of(S2) != n2)
TW.end(V, {'session': S2})
ok('대기 중 끝 = 명령 요청도 닫힘(폰 알림 걷힘)', AP.cmd_item(TW.RUN, nn_of(S2))['state'] == 'rejected')

# ── 3 만료 길 ──
TW.ask(V, {'session': S3, 'why': '만료 시험'})
n3 = nn_of(S3)
TW.ASK_TTL = 1
time.sleep(2.2)
st = TW.status(V, {'session': S3})
ok('대기 시한 넘음 = expired · 명령 요청 닫힘', st['state'] == 'expired' and AP.cmd_item(TW.RUN, n3)['state'] == 'rejected', st)
ok('만료 뒤 서명 = 안 켬', not phone_sign(n3).get('started') and TW.mode(V, S3) == 'ask')
TW.ASK_TTL = 10 * 60

# ── 4 늦은 서명(탭이 안 물어 만료 처리 전에 폰이 시한 뒤에 서명) ──
TW.ask(V, {'session': S4, 'why': '늦은 서명'})
rec = TW._records(V, S4)[-1]
rec['added_at'] -= TW.ASK_TTL + 60           # 11분 전에 물은 꼴(명령 요청은 적용기 12시간 시효 안)
TW._save(rec['_path'], {k: v for k, v in rec.items() if not k.startswith('_')})
res = phone_sign(rec['nn'])
time.sleep(2)
st = TW.status(V, {'session': S4})
ok('늦은 서명 = 적용기는 돌려도 안 켬', res.get('started') and st['state'] == 'expired' and TW.mode(V, S4) == 'ask', (res, st))

# ── 5 위조 ──
S5 = '55555555-5555-4555-8555-555555555555'
TW.ask(V, {'session': S5, 'why': '위조'})
n5 = nn_of(S5)
j = AP.cmd_item(TW.RUN, n5)
AP.save_req(j, state='done', rc=0, approved_by='phone:' + KID)
ok('요청 파일을 done 으로 고쳐도 = 안 켬(장부 run-start 없음)', TW.mode(V, S5) == 'ask')
S6 = '66666666-6666-4666-8666-666666666666'
recs = TW._records(V)
signed_rec = next(r for r in recs if r['session'] == S1)
fake = {k: v for k, v in signed_rec.items() if not k.startswith('_')}
fake.update(session=S6, added_at=int(time.time()), state='waiting')
TW._save(os.path.join(TW._tw(V), 'req', 'ab' * 8 + '.json'), fake)
ok('남의 서명된 요청 번호로 기록을 만들어도 = 안 켬(명령 글의 대화 id 다름)', TW.mode(V, S6) == 'ask')
try:
    TW.ask(V, {'session': '../x'})
    ok('대화 id 꼴 막음', False)
except TW.TabWorkError as e:
    ok('대화 id 꼴 막음', e.code == 400)

# ── 6 대기 상한 ──
ids = [f'7777777{i}-7777-4777-8777-777777777777' for i in range(4)]
codes = []
for s in ids:
    try:
        TW.ask(V, {'session': s, 'why': '상한'})
        codes.append(200)
    except TW.TabWorkError as e:
        codes.append(e.code)
ok(f'함께 기다리는 요청 상한 {TW.MAX_WAIT}', codes.count(429) >= 1 and codes[0] == 200, codes)

shutil.rmtree(tmp, ignore_errors=True)
print(f'\n{count - len(fails)}/{count} 통과' + (f' · 실패 {fails}' if fails else ''))
sys.exit(1 if fails else 0)
