#!/usr/bin/env python3
"""폰 쪽 속도 줄 — 본체 3_시스템/speed.py 가 module.json contributes.speed 로 부른다(읽기만 · 창 없음 · LLM 0).

  py -3 .claude/skills/mobility/scripts/speed_rows.py [--days 7] [--vault V]

출력 = JSON 목록 [{name, median_ms, p90_ms, n, limit_ms}] — 기록이 없으면 [].
폰 홈 = 서버 로그(_index/server/server.log)의 «GET /v1/home … 200 <ms>ms» 줄 · 한계 3초(11-16 실측 근거 · 옛 speed.py 값).
"""
import datetime as dt
import json
import os
import re
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LIMIT_HOME = 3000


def vault_of(argv):
    if "--vault" in argv:
        return argv[argv.index("--vault") + 1]
    return os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))


def q(v, p):
    v = sorted(v)
    return v[min(len(v) - 1, max(0, int(round(p * (len(v) - 1)))))]


def phone_home(vault, days):
    p = os.path.join(vault, "3_시스템", "_index", "server", "server.log")
    if not os.path.exists(p):
        return []
    since = (dt.datetime.now() - dt.timedelta(days=days)).strftime("%Y-%m-%d")
    v = []
    with open(p, "rb") as fh:
        fh.seek(max(0, os.path.getsize(p) - 8 * 2**20))      # 큰 파일 — 끝 8MB 만
        for ln in fh:
            if b"/v1/home" not in ln:
                continue
            m = re.match(rb"(\d{4}-\d\d-\d\d) [\d:]+ GET /v1/home\S* 200 (\d+)ms", ln)
            if m and m.group(1).decode() >= since:
                v.append(int(m.group(2)))
    return v


def rows(vault, days):
    ph = phone_home(vault, days)
    if not ph:
        return []
    return [{"name": "폰 홈(/v1/home)", "median_ms": st.median(ph), "p90_ms": q(ph, .9), "n": len(ph), "limit_ms": LIMIT_HOME}]


def main(argv):
    days = float(argv[argv.index("--days") + 1]) if "--days" in argv else 7
    print(json.dumps(rows(vault_of(argv), days), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
