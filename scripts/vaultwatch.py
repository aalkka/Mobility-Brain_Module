# -*- coding: utf-8 -*-
"""볼트 바뀜 버스(11-23) — PC 에서 누가 바꿨든(옵시디언·탐색기·Claude·대본·fileops) 폰이 몇 초 안에 알게 한다.

왜: 폰은 폴더 목록을 5분 믿고(explorer) 링크 이름 지도·홈은 서버가 1분 기억했다. PC 쪽 바뀜을 알리는 길이 없어
    폴더 만들기·옮기기가 폰 나무에 안 뜨고, 옮긴 파일을 옛 경로로 열면 «PC 에 없음»으로 캐시까지 지웠다(11-23 사용자).
어떻게: 윈도 ReadDirectoryChangesW(볼트 뿌리 · 아래 전부 · 막는 호출을 스레드 하나로)가 바뀐 경로를 바로 준다.
    안 되면(윈도 아님·핸들 실패) 폴더 시각 훑기로 대신한다(POLL 초 · 폴더만 stat).
    장부(3_시스템/ledger/ops.jsonl)에 새 줄이 붙으면 옮김(mv·rename)을 «옮김» 사건으로 싣는다 — 탐색기 옮김은 같은 묶음 안의
    지움 + 생김(끝 이름이 같음)을 옮김으로 맞춘다.
사건 = {seq, k: add|rm|mod|mv, p, src?, dst?} · 폰은 POST /v1/changes {since, wait} 로 붙잡고 있다가 묶음으로 받는다.
경로·이름은 로그에 안 적는다.
"""
import collections
import json
import os
import threading
import time

SETTLE = 0.3            # 첫 사건 뒤 이만큼 더 모아 한 묶음으로(옮김 = 지움 + 생김이 따로 온다)
KEEP = 4000             # 기억하는 사건 수 — since 가 이보다 오래면 reset(폰이 기억을 다 버리고 다시 받는다)
WAIT_MAX = 25           # 붙잡는 초 상한(/v1/watch 와 같음)
POLL = 2.0              # 대신 길(폴더 시각 훑기) 간격
FRESH_MAX = 500         # 찾기 보탬 — 서버가 켜진 뒤 생기거나 고친 md(색인이 아직 모르는 것)


class Bus:
    def __init__(self, vault, keep, ledger=None, on_change=None):
        """keep(rel, is_dir) = 폰에 보일 자리인가 · ledger = 장부 경로 · on_change(kinds) = 서버 기억(이름 지도·홈)을 비우는 손"""
        self.vault = os.path.abspath(vault)
        self.keep = keep
        self.ledger = ledger
        self.on_change = on_change
        self.cv = threading.Condition()
        self.seq = self.seq0 = int(time.time() * 1000)             # 켤 때의 시각에서 센다 — 서버를 다시 켜도 폰이 쥔 since 가 새 사건과 겹치지 않는다(reset 으로 간다)
        self.log = collections.deque(maxlen=KEEP)
        self.fresh = collections.OrderedDict()         # rel → 시각(md 만)
        self.mode = 'off'
        self.raw = []                                   # 모으는 중인 날 사건 [(k, rel, is_dir)]
        self.raw_at = 0.0
        self.led_at = self._ledger_size()
        self.stop_ev = threading.Event()
        self.handle = None

    # ── 켜기 ──
    def start(self):
        threading.Thread(target=self._flusher, daemon=True, name='vault-bus').start()
        if os.name == 'nt':
            try:
                self.handle = _open_dir(self.vault)
                self.mode = 'native'
                threading.Thread(target=self._native, daemon=True, name='vault-watch').start()
                return self
            except OSError:
                self.handle = None
        self.mode = 'poll'
        threading.Thread(target=self._poll, daemon=True, name='vault-poll').start()
        return self

    def close(self):
        self.stop_ev.set()
        if self.handle:
            _cancel(self.handle)

    # ── 날 사건 ──
    def _rel(self, path):
        return path.replace('\\', '/').strip('/')

    def feed(self, k, rel, is_dir=None, dst=None):
        """날 사건 하나(감시 스레드·훑기·시험) — 모았다가 _flush 가 묶는다 · k = mv 면 dst = 새 이름(같은 폴더 이름 바꾸기)"""
        rel = self._rel(rel)
        if not rel:
            return
        with self.cv:
            if not self.raw:
                self.raw_at = time.time()
            self.raw.append((k, rel, is_dir, self._rel(dst) if dst else None))
            self.cv.notify_all()

    def _flusher(self):
        while not self.stop_ev.is_set():
            with self.cv:
                while not self.raw and not self.stop_ev.is_set():
                    self.cv.wait(1.0)
                left = self.raw_at + SETTLE - time.time()
            if left > 0:
                time.sleep(left)
            with self.cv:
                raw, self.raw = self.raw, []
            if raw:
                try:
                    self._flush(raw)
                except Exception:   # noqa: BLE001 — 버스가 멈추지 않게(다음 묶음은 다시 본다)
                    pass

    def _flush(self, raw):
        out = []
        ledger = False
        for k, rel, is_dir, dst in raw:
            if self.ledger and os.path.normcase(os.path.join(self.vault, *rel.split('/'))) == os.path.normcase(self.ledger):
                ledger = True
                continue
            a = os.path.join(self.vault, *(dst or rel).split('/'))
            if is_dir is None:
                is_dir = os.path.isdir(a)
            if k == 'mv':
                if self.keep(rel, is_dir) or self.keep(dst, is_dir):
                    out.append({'k': 'mv', 'src': rel, 'dst': dst, 'dir': bool(is_dir), 'by': 'watch'})
                continue
            if not self.keep(rel, is_dir):
                continue
            if k == 'mod' and is_dir:
                continue                                # 폴더 «고침» = 안의 이름이 바뀜 — 그 이름의 사건이 따로 온다
            out.append({'k': k, 'p': rel, 'dir': bool(is_dir)})
        out = _pair_moves(out)
        if ledger:
            out += self._ledger_moves()
        if not out:
            return
        now = time.time()
        with self.cv:
            for e in out:
                self.seq += 1
                e['seq'] = self.seq
                self.log.append(e)
                for p in (e.get('p'), e.get('dst')):
                    if p and p.lower().endswith('.md') and e['k'] != 'rm':
                        self.fresh.pop(p, None)
                        self.fresh[p] = now
                        while len(self.fresh) > FRESH_MAX:
                            self.fresh.popitem(last=False)
                if e['k'] in ('rm', 'mv'):
                    self.fresh.pop(e.get('p') or e.get('src') or '', None)
            self.cv.notify_all()
        if self.on_change:
            try:
                self.on_change({e['k'] for e in out})
            except Exception:   # noqa: BLE001
                pass

    # ── 장부 ──
    def _ledger_size(self):
        try:
            return os.path.getsize(self.ledger) if self.ledger else 0
        except OSError:
            return 0

    def _ledger_moves(self):
        """장부에 새로 붙은 줄 중 옮김(mv·rename) — 폰 범위 안의 것만"""
        size = self._ledger_size()
        if size < self.led_at:
            self.led_at = 0                             # 장부를 갈았다
        if size == self.led_at:
            return []
        with open(self.ledger, 'rb') as f:
            f.seek(self.led_at)
            data = f.read(size - self.led_at)
        cut = data.rfind(b'\n') + 1                     # 쓰는 중인 끝 줄은 다음 차례에
        self.led_at += cut
        out = []
        for line in data[:cut].decode('utf-8', 'replace').splitlines():
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get('op') not in ('mv', 'rename') or not isinstance(r.get('src'), str) or not isinstance(r.get('dst'), str):
                continue
            src, dst = self._rel(r['src']), self._rel(r['dst'])
            folder = r.get('kind') in ('dir', 'folder')
            if self.keep(src, folder) or self.keep(dst, folder):
                out.append({'k': 'mv', 'src': src, 'dst': dst, 'dir': folder, 'by': 'ledger'})
        return out

    # ── 폰이 묻기 ──
    def since(self, since, wait=0, stop=None):
        """since 뒤 사건 · 없으면 wait 초까지 붙잡는다 → {seq, events, reset?, stale?}. since 0 = 지금 seq 만(처음) · stop() 이 참이면 바로 끝(stale)"""
        end = time.time() + max(0, min(int(wait or 0), WAIT_MAX))
        with self.cv:
            self.cv.notify_all()                        # 붙잡힌 다른 물음이 stop 을 다시 보게(같은 기기가 새로 걸었을 수 있다)
            if self.log and since < self.log[0]['seq'] - 1 or not self.log and since and since < self.seq0:
                return {'seq': self.seq, 'events': [], 'reset': True, 'mode': self.mode}
            if not since or since > self.seq:
                return {'seq': self.seq, 'events': [], 'mode': self.mode, **({'reset': True} if since else {})}
            while True:
                if stop and stop():
                    return {'seq': self.seq, 'events': [], 'stale': True, 'mode': self.mode}
                evs = [e for e in self.log if e['seq'] > since]
                if evs or time.time() >= end:
                    return {'seq': self.seq, 'events': evs, 'mode': self.mode}
                self.cv.wait(max(0.05, end - time.time()))

    def moved(self, rel):
        """이 버스가 본 옮김을 따라간 지금 자리(없으면 None)"""
        cur, hit = rel, False
        with self.cv:
            evs = [e for e in self.log if e['k'] == 'mv']
        for e in evs:
            s, d = e['src'], e['dst']
            if cur == s:
                cur, hit = d, True
            elif cur.startswith(s + '/'):
                cur, hit = d + cur[len(s):], True
        return cur if hit else None

    def fresh_notes(self):
        with self.cv:
            return list(self.fresh.items())

    # ── 윈도 감시 ──
    def _native(self):
        import ctypes
        buf = ctypes.create_string_buffer(64 * 1024)
        got = ctypes.c_ulong(0)
        flt = 0x1 | 0x2 | 0x8 | 0x10                    # 파일 이름 · 폴더 이름 · 크기 · 마지막 쓰기
        k32 = ctypes.windll.kernel32
        old = None                                      # 이름 바꾸기의 옛 이름(4) — 새 이름(5)이 바로 뒤에 온다
        while not self.stop_ev.is_set():
            ok = k32.ReadDirectoryChangesW(self.handle, buf, len(buf), True, flt, ctypes.byref(got), None, None)
            if not ok:
                if self.stop_ev.is_set():
                    return
                time.sleep(1)                           # 막혔다 — 대신 길로
                self.mode = 'poll'
                return self._poll()
            if got.value == 0:                          # 넘침 — 폰이 다 다시 받게
                with self.cv:
                    self.log.clear()
                    self.seq += 1
                    self.cv.notify_all()
                continue
            for act, name in _parse(buf.raw[:got.value]):
                if act == 4:
                    old = name
                elif act == 5 and old is not None:
                    self.feed('mv', old, None, name)
                    old = None
                else:
                    k = {1: 'add', 2: 'rm', 3: 'mod', 5: 'add'}.get(act)
                    if k:
                        self.feed(k, name)

    # ── 대신 길: 폴더 시각 훑기(이름이 바뀌면 그 폴더의 시각이 바뀐다) ──
    def _poll(self):
        seen = self._scan()
        while not self.stop_ev.wait(POLL):
            now = self._scan()
            for d, (mt, names) in now.items():
                old = seen.get(d)
                if old is None or old[0] == mt:
                    continue
                for n in names - old[1]:
                    self.feed('add', f'{d}/{n}' if d else n)
                for n in old[1] - names:
                    self.feed('rm', f'{d}/{n}' if d else n, False)
            for d in seen.keys() - now.keys():
                self.feed('rm', d, True)
            seen = now

    def _scan(self):
        out = {}
        for root, subs, files in os.walk(self.vault):
            rel = self._rel(os.path.relpath(root, self.vault)) if root != self.vault else ''
            subs[:] = [s for s in subs if not s.startswith('.') and self.keep(f'{rel}/{s}' if rel else s, True)]     # 폰 범위 밖(3_시스템·_색인 등)은 걷지 않는다
            try:
                out[rel] = (os.stat(root).st_mtime_ns, set(subs) | set(files))
            except OSError:
                pass
        return out


def _pair_moves(evs):
    """한 묶음 안의 지움 + 생김(끝 이름이 같음 · 하나씩)을 옮김으로 — 탐색기 끌어 옮기기·잘라 붙이기"""
    rms = [e for e in evs if e['k'] == 'rm']
    adds = [e for e in evs if e['k'] == 'add']
    used = set()
    out = []
    for r in rms:
        name = r['p'].rsplit('/', 1)[-1]
        same = [a for a in adds if id(a) not in used and a['p'].rsplit('/', 1)[-1] == name and a['p'] != r['p']]
        if len(same) == 1:
            a = same[0]
            used.add(id(a))
            used.add(id(r))
            out.append({'k': 'mv', 'src': r['p'], 'dst': a['p'], 'dir': a['dir'], 'by': 'watch'})
    rest = [e for e in evs if id(e) not in used]
    seen = set()
    uniq = []
    for e in rest:                                       # 같은 경로의 같은 사건은 하나만(쓰기 한 번 = 고침 여러 번)
        key = (e['k'], e.get('p') or e.get('src'), e.get('dst'))
        if key not in seen:
            seen.add(key)
            uniq.append(e)
    return uniq + out


def _open_dir(path):
    import ctypes
    from ctypes import wintypes
    k32 = ctypes.windll.kernel32
    k32.CreateFileW.restype = wintypes.HANDLE
    k32.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    k32.ReadDirectoryChangesW.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD, wintypes.BOOL, wintypes.DWORD, ctypes.POINTER(ctypes.c_ulong), ctypes.c_void_p, ctypes.c_void_p]
    h = k32.CreateFileW(path, 0x1, 0x1 | 0x2 | 0x4, None, 3, 0x02000000, None)     # 목록 읽기 · 남이 읽기·쓰기·지우기 허용 · 있는 것 · 폴더 핸들
    if not h or h == wintypes.HANDLE(-1).value:
        raise OSError('폴더 핸들 실패')
    return h


def _cancel(h):
    import ctypes
    try:
        ctypes.windll.kernel32.CancelIoEx(h, None)
        ctypes.windll.kernel32.CloseHandle(h)
    except OSError:
        pass


def _parse(b):
    """FILE_NOTIFY_INFORMATION 묶음 → [(행위, 볼트 상대 이름)]"""
    import struct
    out = []
    at = 0
    while True:
        nxt, act, n = struct.unpack_from('<III', b, at)
        out.append((act, b[at + 12: at + 12 + n].decode('utf-16-le', 'replace')))
        if not nxt:
            return out
        at += nxt
