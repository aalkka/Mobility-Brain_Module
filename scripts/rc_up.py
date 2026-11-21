#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RC(Remote Control) 켜기를 볼트 서버에 부탁한다 — 폰 «Claude 켜기» 단추와 같은 길(POST /v1/rc · 창 없음 · 서버 몫 RC 로 남아 새벽 다시 켜기가 앎).
자동 재시작 뒤 다시 세팅(after_restart.json «mobility.rc»)이 부른다. 터미널 탭으로 띄우면 창이 뜨고 서버가 제 몫으로 모르므로 이 길을 쓴다.

  py -3 .claude/skills/mobility/scripts/rc_up.py [--vault V]   종료 0 = 켰거나 이미 돎 · 1 = 서버가 거절(까닭 한 줄) · 2 = 서버 없음·열쇠 없음
"""
import json
import os
import sys
import urllib.error
import urllib.request

MOD = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, MOD)
import conf  # noqa: E402


def main(argv):
    vault = argv[argv.index("--vault") + 1] if "--vault" in argv else os.path.normpath(os.path.join(MOD, "..", "..", "..", ".."))
    try:
        with open(os.path.join(vault, "3_시스템", "_index", "server", "token"), encoding="utf-8") as h:
            tok = h.read().strip()
    except OSError:
        print("열쇠 없음")
        return 2
    req = urllib.request.Request("http://127.0.0.1:%d/v1/rc" % conf.port(vault), data=b"{}", method="POST",
                                 headers={"Authorization": "Bearer " + tok, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            d = json.loads(r.read().decode("utf-8") or "{}")
        print("켬" if d.get("started") else "이미 돎")
        return 0
    except urllib.error.HTTPError as e:
        try:
            why = json.loads(e.read().decode("utf-8")).get("error") or e.reason
        except Exception:  # noqa: BLE001
            why = e.reason
        print("거절 %d %s" % (e.code, why))
        return 1
    except (urllib.error.URLError, OSError) as e:
        print("서버 없음 %s" % getattr(e, "reason", e))
        return 2


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
