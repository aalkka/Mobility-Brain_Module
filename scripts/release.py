#!/usr/bin/env python3
"""폰 출시물 깔기 — 폰 앱·폰 플러그인·폰 캘린더·폰 보기를 서버 출시 자리(<볼트>/3_시스템/_index/server/{app,plugin}/)에 둔다(LLM 0 · 창 없음).

  py -3 .claude/skills/mobility/scripts/release.py check [--vault V]            # 종료 0 = 넷 다 있음 · 1 = 빠짐(까닭 한 줄)
  py -3 .claude/skills/mobility/scripts/release.py install [--from 자리] [--dry] [--vault V]
  py -3 .claude/skills/mobility/scripts/release.py pack <출시 자리> <묶음.zip>    # 만드는 사람 몫 — 출시 자리 → 묶음(release.json 포함)

왜: 서버는 짝 쪽(/pair)·갱신기(/v1/plugin·/v1/app)로 이 자리의 파일만 내준다. 새로 깐 볼트는 자리가 비어 폰이 받을 것이 없다.
받는 길(차례): --from(폴더 또는 zip) → 모듈 안 release/ 폴더 → 모듈 저장소의 최신 출시 첨부 mobility-release.zip(공개 · 인증 없음).
묶음 = zip 안 release.json {"items": {"plugin/brain-server": "0.7.48", "app/brain-phone": 44, …}, "files": {"<자리>/<파일>": sha256}} + 그 파일들.
깔기 규칙: 파일마다 sha256 을 맞춘 뒤 · 깐 판이 묶음 판보다 같거나 새로우면 그 항목은 건너뜀(낮추지 않음 · 만드는 사람 볼트는 빌더가 올린 판이 이김) ·
  항목 폴더를 통째로 바꿈(옛 파일이 남지 않게 · 새 폴더를 다 쓴 뒤 바꿈).
"""
import hashlib
import io
import json
import os
import re
import shutil
import sys
import tempfile
import time
import urllib.request
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
MODULE = os.path.dirname(HERE)
ITEMS = ("app/brain-phone", "plugin/brain-server", "plugin/brain-calendar", "plugin/brain-source-mobile")
NAMES = {"app/brain-phone": "폰 앱", "plugin/brain-server": "폰 플러그인", "plugin/brain-calendar": "폰 캘린더", "plugin/brain-source-mobile": "폰 보기"}
URL = os.environ.get("BRAIN_MOBILITY_RELEASE", "https://github.com/aalkka/Mobility-Brain_Module/releases/latest/download/mobility-release.zip")
SAFE = re.compile(r"^(app|plugin)/[a-z0-9-]+/(?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+$")


def vault_of(argv):
    if "--vault" in argv:
        return os.path.abspath(argv[argv.index("--vault") + 1])
    return os.path.abspath(os.path.join(MODULE, "..", "..", ".."))


def state(vault):
    return os.path.join(vault, "3_시스템", "_index", "server")


def sha(b):
    return hashlib.sha256(b).hexdigest()


def ver_key(v):
    """판 비교 열쇠 — 앱 = 정수 · 플러그인 = «0.7.48» · 모르면 None"""
    if isinstance(v, int):
        return (v,)
    if isinstance(v, str) and re.fullmatch(r"\d+(\.\d+)*", v):
        return tuple(int(x) for x in v.split("."))
    return None


def viewer_off(vault):
    """기능 단계 «폰 보기 받기»(mobility.viewer · 기본 켬) — 끔이면 폰 보기를 안 깔고 check 에서도 뺀다. 못 읽으면 켬."""
    try:
        sysdir = os.path.join(vault, "3_시스템")
        if sysdir not in sys.path:
            sys.path.insert(0, sysdir)
        import options
        return options.level("mobility.viewer", vault) == "off"
    except Exception:  # noqa: BLE001
        return False


def wanted(vault):
    off = viewer_off(vault)
    return [i for i in ITEMS if not (off and i == "plugin/brain-source-mobile")]


def installed(vault, item):
    p = os.path.join(state(vault), *item.split("/"), "version.json")
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f).get("version")
    except (OSError, ValueError):
        return None


# ───────── 묶음 읽기 ─────────
def from_dir(d):
    rj = os.path.join(d, "release.json")
    with open(rj, encoding="utf-8") as f:
        man = json.load(f)
    files = {}
    for rel in man.get("files", {}):
        with open(os.path.join(d, *rel.split("/")), "rb") as f:
            files[rel] = f.read()
    return man, files


def from_zip(data):
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        man = json.loads(z.read("release.json").decode("utf-8"))
        files = {rel: z.read(rel) for rel in man.get("files", {})}
    return man, files


def fetch(src):
    """(묶음 설명, {자리: 바이트}, 어디서) — 못 받으면 예외"""
    if src:
        if os.path.isdir(src):
            return (*from_dir(src), src)
        with open(src, "rb") as f:
            return (*from_zip(f.read()), src)
    local = os.path.join(MODULE, "release")
    if os.path.isfile(os.path.join(local, "release.json")):
        return (*from_dir(local), "모듈 release/")
    req = urllib.request.Request(URL, headers={"User-Agent": "brain-mobility-release"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return (*from_zip(r.read()), URL)


def verify(man, files):
    bad = []
    items = man.get("items") or {}
    for rel, want in (man.get("files") or {}).items():
        if not SAFE.match(rel) or ".." in rel.split("/"):
            bad.append("자리 꼴이 아님: " + rel)
        elif not any(rel.startswith(i + "/") for i in items):
            bad.append("항목 밖 파일: " + rel)
        elif sha(files.get(rel, b"")) != want:
            bad.append("sha256 다름: " + rel)
    for i in items:
        if i not in ITEMS:
            bad.append("모르는 항목: " + i)
        elif ver_key(items[i]) is None:
            bad.append("판 꼴이 아님: %s %r" % (i, items[i]))
    return bad


# ───────── 깔기 ─────────
def install(vault, src=None, dry=False):
    man, files, where = fetch(src)
    bad = verify(man, files)
    if bad:
        return {"ok": False, "어디서": where, "틀림": bad[:10]}
    done, skip = [], []
    want = wanted(vault)
    for item, v in sorted((man.get("items") or {}).items()):
        if item not in want:
            skip.append("%s(기능 단계 끔)" % NAMES[item])
            continue
        have = installed(vault, item)
        if have is not None and ver_key(have) is not None and ver_key(have) >= ver_key(v):
            skip.append("%s %s(깐 판 %s)" % (NAMES[item], v, have))
            continue
        done.append("%s %s%s" % (NAMES[item], v, "" if have is None else "(옛 판 %s)" % have))
        if dry:
            continue
        dest = os.path.join(state(vault), *item.split("/"))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        tmp = tempfile.mkdtemp(prefix=".new-", dir=os.path.dirname(dest))
        for rel, b in files.items():
            if rel.startswith(item + "/"):
                p = os.path.join(tmp, *rel[len(item) + 1:].split("/"))
                os.makedirs(os.path.dirname(p), exist_ok=True)
                with open(p, "wb") as f:
                    f.write(b)
        old = None
        if os.path.isdir(dest):
            old = dest + ".old-%d" % int(time.time())
            os.replace(dest, old)
        os.replace(tmp, dest)
        if old:
            shutil.rmtree(old, ignore_errors=True)
    return {"ok": True, "어디서": where, "깜": done, "건너뜀": skip, "dry": dry}


def check(vault):
    want = wanted(vault)
    miss = [NAMES[i] for i in want if installed(vault, i) is None]
    off = "" if len(want) == len(ITEMS) else " · 폰 보기 = 기능 단계 끔"
    if miss:
        return 1, "출시 자리에 없음: " + " · ".join(miss) + " — «release.py install» 로 깐다" + off
    return 0, "출시물 %d 다 있음 — " % len(want) + " · ".join("%s %s" % (NAMES[i], installed(vault, i)) for i in want) + off


# ───────── 묶기(만드는 사람) ─────────
CSS_NOTE = re.compile(rb"/\*(?!!).*?\*/", re.S)     # /*! 알림(라이선스)은 남김


def pairs_of(path):
    """바꿈 짝(«찾을 글<TAB>바꿀 글» · 만드는 사람 볼트의 git 밖 파일) — js 안 \\uXXXX 꼴도 함께 바꾼다. 없으면 빈 목록."""
    out = []
    if path and os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            for ln in f:
                ln = ln.rstrip("\n")
                if ln.strip() and not ln.startswith("#"):
                    a, _, b = ln.partition("\t")
                    out.append((a.encode("utf-8"), b.encode("utf-8")))
                    esc = lambda s, up: "".join(("\\u%04X" if up else "\\u%04x") % ord(c) if ord(c) > 127 else c for c in s).encode()  # noqa: E731
                    for up in (False, True):
                        out.append((esc(a, up), esc(b, up)))
    return out


def scrub(data, name, pairs):
    if name.endswith(".css"):
        data = CSS_NOTE.sub(b"", data)
    if name.endswith((".css", ".js", ".json", ".html")):
        for a, b in pairs:
            data = data.replace(a, b)
    return data


def strip_css(files, pairs=()):
    """css 주석을 걷고 바꿈 짝을 적용한다(만든 사람의 메모·호칭이 출시물에 실리지 않게 · 11-21) — 바뀐 파일의 sha·크기를 같은 항목
    version.json(files·big)과 플러그인 설치 묶음 zip 안 파일에 맞춰 고친다. 폰 갱신기는 version.json 의 sha 로 받은 파일을 잰다."""
    out = dict(files)
    changed = {}
    for rel, b in files.items():
        if not rel.endswith(("version.json", ".zip")):
            nb = scrub(b, rel, pairs)
            if nb != b:
                out[rel] = nb
                changed[rel] = nb
    for rel in list(out):
        d, name = rel.rsplit("/", 1)
        if name == "version.json":
            vj = json.loads(out[rel].decode("utf-8"))
            hit = False
            for c, nb in changed.items():
                cd, cn = c.rsplit("/", 1)
                if cd != d:
                    continue
                if cn in (vj.get("files") or {}):
                    vj["files"][cn] = sha(nb)
                    hit = True
                if cn in (vj.get("big") or {}):
                    vj["big"][cn].update(sha256=sha(nb), size=len(nb))
                    hit = True
            if hit:
                out[rel] = json.dumps(vj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        elif name.endswith(".zip"):
            src = zipfile.ZipFile(io.BytesIO(out[rel]))
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
                for info in src.infolist():
                    z.writestr(info, scrub(src.read(info), info.filename, pairs))
            out[rel] = buf.getvalue()
    return out


def pack(src_state, out, pairs_file=None):
    items, files = {}, {}
    if pairs_file is None:      # 만드는 사람 볼트의 익명화 짝(dist-sync 자리 · git 밖) — 출시 자리가 그 볼트 안일 때
        pairs_file = os.path.join(src_state, "..", "dist-sync", "anon-pairs.txt")
    for item in ITEMS:
        d = os.path.join(src_state, *item.split("/"))
        try:
            with open(os.path.join(d, "version.json"), encoding="utf-8") as f:
                v = json.load(f).get("version")
        except (OSError, ValueError):
            print("빠짐: " + item, file=sys.stderr)
            return 1
        items[item] = v
        for dp, _dns, fns in os.walk(d):
            for fn in fns:
                p = os.path.join(dp, fn)
                rel = item + "/" + os.path.relpath(p, d).replace(os.sep, "/")
                with open(p, "rb") as f:
                    files[rel] = f.read()
    files = strip_css(files, pairs_of(pairs_file))
    man = {"items": items, "files": {r: sha(b) for r, b in sorted(files.items())}, "made": time.strftime("%Y-%m-%d")}
    bad = verify(man, files)
    if bad:
        print("\n".join(bad), file=sys.stderr)
        return 1
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("release.json", json.dumps(man, ensure_ascii=False, indent=1) + "\n")
        for r, b in sorted(files.items()):
            z.writestr(r, b)
    print("묶음 %s — %s · 파일 %d" % (out, " · ".join("%s %s" % (NAMES[i], items[i]) for i in ITEMS), len(files)))
    return 0


def main(argv):
    cmd = argv[0] if argv else "check"
    vault = vault_of(argv)
    if cmd == "check":
        code, line = check(vault)
        print(line)
        return code
    if cmd == "install":
        src = argv[argv.index("--from") + 1] if "--from" in argv else None
        try:
            r = install(vault, src, "--dry" in argv)
        except Exception as e:  # noqa: BLE001 — 받기·읽기 실패는 한 줄로
            print("못 깖 — %s: %s" % (type(e).__name__, e))
            return 2
        if not r["ok"]:
            print("못 깖(%s) — %s" % (r["어디서"], " · ".join(r["틀림"])))
            return 1
        print("%s(%s) — 깜: %s · 건너뜀: %s" % ("미리 보기" if r["dry"] else "깖", r["어디서"], " · ".join(r["깜"]) or "없음", " · ".join(r["건너뜀"]) or "없음"))
        return 0
    if cmd == "pack" and len(argv) >= 3:
        return pack(argv[1], argv[2])
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
