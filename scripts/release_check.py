#!/usr/bin/env python3
"""release.py 시험 — 가짜 출시 자리로 묶고 빈 볼트에 깐다(네트워크 없음 · 진짜 볼트 안 건드림).

  py -3 .claude/skills/mobility/scripts/release_check.py
"""
import hashlib
import io
import json
import os
import sys
import tempfile
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import release as R  # noqa: E402

fails = []


def ok(name, cond, why=""):
    print(("통과 " if cond else "실패 ") + name + ("" if cond else " — " + str(why)[:160]))
    if not cond:
        fails.append(name)


def put(p, b):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb") as f:
        f.write(b)


def fake_state(root, app=3, plug="0.1.2"):
    css = b"/* note by maker */\n.a{b:c}\n/*! license */\n"
    h = lambda b: hashlib.sha256(b).hexdigest()  # noqa: E731
    put(os.path.join(root, "app", "brain-phone", "brain-phone.apk"), b"apk")
    put(os.path.join(root, "app", "brain-phone", "version.json"), json.dumps({"version": app, "sha256": h(b"apk"), "size": 3}).encode())
    for pid in ("brain-server", "brain-calendar", "brain-source-mobile"):
        d = os.path.join(root, "plugin", pid)
        put(os.path.join(d, "core.js"), b"js")
        put(os.path.join(d, "styles.css"), css)
        vj = {"version": plug, "files": {"core.js": h(b"js"), "styles.css": h(css)}}
        if pid == "brain-source-mobile":
            put(os.path.join(d, "edit.css"), css)
            vj["big"] = {"edit.css": {"sha256": h(css), "size": len(css)}}
        if pid == "brain-server":
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w") as z:
                z.writestr("brain-server/versions/%s/styles.css" % plug, css)
            put(os.path.join(d, "brain-server.zip"), buf.getvalue())
        put(os.path.join(d, "version.json"), json.dumps(vj).encode())


with tempfile.TemporaryDirectory() as t:
    st = os.path.join(t, "maker", "3_시스템", "_index", "server")
    fake_state(st)
    zp = os.path.join(t, "r.zip")
    ok("묶기 종료 0", R.pack(st, zp) == 0)
    v = os.path.join(t, "vault")
    os.makedirs(os.path.join(v, "3_시스템"))
    ok("빈 볼트 = check 1", R.check(v)[0] == 1)
    r = R.install(v, zp)
    ok("깔기 = 넷 다", r["ok"] and len(r["깜"]) == 4, r)
    ok("깐 뒤 check 0", R.check(v)[0] == 0)
    srv = os.path.join(v, "3_시스템", "_index", "server", "plugin")
    css = open(os.path.join(srv, "brain-server", "styles.css"), "rb").read()
    ok("css 메모 주석 걷힘 · /*! 남음", b"maker" not in css and b"/*! license */" in css, css)
    vj = json.load(open(os.path.join(srv, "brain-source-mobile", "version.json"), encoding="utf-8"))
    ec = open(os.path.join(srv, "brain-source-mobile", "edit.css"), "rb").read()
    ok("version.json sha·big 이 걷은 css 와 맞음", vj["files"]["styles.css"] == hashlib.sha256(css).hexdigest()
       and vj["big"]["edit.css"]["sha256"] == hashlib.sha256(ec).hexdigest() and vj["big"]["edit.css"]["size"] == len(ec), vj)
    with zipfile.ZipFile(os.path.join(srv, "brain-server", "brain-server.zip")) as z:
        ok("설치 묶음 zip 안 css 도 걷힘", all(b"maker" not in z.read(n) for n in z.namelist()))
    r = R.install(v, zp)
    ok("같은 판 다시 = 다 건너뜀", r["ok"] and not r["깜"] and len(r["건너뜀"]) == 4, r)
    old = os.path.join(t, "old")
    fake_state(os.path.join(old, "s"), app=2, plug="0.1.1")
    zo = os.path.join(t, "old.zip")
    R.pack(os.path.join(old, "s"), zo)
    r = R.install(v, zo)
    ok("옛 판 = 낮추지 않음", r["ok"] and not r["깜"], r)
    # 고친 묶음 — sha 다름 · 위로 나가는 자리
    data = open(zp, "rb").read()
    zin = zipfile.ZipFile(io.BytesIO(data))
    man = json.loads(zin.read("release.json"))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zz:
        zz.writestr("release.json", json.dumps(man))
        for n in man["files"]:
            zz.writestr(n, b"evil" if n.endswith("core.js") else zin.read(n))
    bad = os.path.join(t, "bad.zip")
    put(bad, buf.getvalue())
    v2 = os.path.join(t, "v2")
    os.makedirs(os.path.join(v2, "3_시스템"))
    r = R.install(v2, bad)
    ok("sha 다름 = 안 깖", not r["ok"] and R.check(v2)[0] == 1, r)
    man2 = dict(man, files=dict(man["files"], **{"plugin/brain-server/../../../x.py": "0" * 64}))
    ok("위로 나가는 자리 = 틀림", any("자리 꼴" in x for x in R.verify(man2, {})), R.verify(man2, {}))
    man3 = dict(man, items=dict(man["items"], **{"plugin/evil": "1.0"}))
    ok("모르는 항목 = 틀림", any("모르는 항목" in x for x in R.verify(man3, {})))

print("== 실패 %d건" % len(fails))
sys.exit(1 if fails else 0)
