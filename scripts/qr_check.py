"""QR 부호기(qr.py) 시험 — 부호기와 따로 쓴 읽기로 다시 읽는다(규격 공개 표를 여기 따로 적음 · 바깥 해독기 없음).

  py -3 .claude/skills/mobility/scripts/qr_check.py

잰다: 바이트 용량(M·L 판 1~10 = 규격 표) · 형식 비트 BCH·두 벌 같음 · 맞춤 무늬 자리(규격 표) · 덩이마다 RS 증후군 0
· 다시 읽은 글 = 넣은 글(짝 주소 꼴 · 한글 · 판 7 이상 판 정보) · SVG 꼴.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qr  # noqa: E402

rows, fails = [], []


def ok(name, cond, got=""):
    rows.append(name)
    if not cond:
        fails.append(name)
    print(("  ✓ " if cond else "  ✗ ") + name + ("" if cond else f"  — {str(got)[:300]}"), flush=True)


# 규격(ISO/IEC 18004 표 7) 바이트 용량 — 부호기 표와 따로
CAP_M = {1: 14, 2: 26, 3: 42, 4: 62, 5: 84, 6: 106, 7: 122, 8: 152, 9: 180, 10: 213}
CAP_L = {1: 17, 2: 32, 3: 53, 4: 78, 5: 106, 6: 134, 7: 154, 8: 192, 9: 230, 10: 271}
# 규격 표 9 — M 덩이 꼴 [(덩이 수, 자료 코드워드)] · 덩이마다 고침 코드워드
BLOCKS_M = {1: ([(1, 16)], 10), 2: ([(1, 28)], 16), 3: ([(1, 44)], 26), 4: ([(2, 32)], 18), 5: ([(2, 43)], 24), 6: ([(4, 27)], 16),
            7: ([(4, 31)], 18), 8: ([(2, 38), (2, 39)], 22), 9: ([(3, 36), (2, 37)], 22), 10: ([(4, 43), (1, 44)], 26)}
# 규격 부록 E — 맞춤 무늬 가운데
ALIGN = {1: [], 2: [6, 18], 3: [6, 22], 4: [6, 26], 5: [6, 30], 6: [6, 34], 7: [6, 22, 38], 8: [6, 24, 42], 9: [6, 26, 46], 10: [6, 28, 50]}
MASK = qr.MASKS


def gf_mul(x, y):
    r = 0
    while y:
        if y & 1:
            r ^= x
        x <<= 1
        if x & 0x100:
            x ^= 0x11D
        y >>= 1
    return r


def capacity(ver, ecl):
    bits = qr.data_codewords(ver, ecl) * 8 - 4 - (8 if ver < 10 else 16)
    return bits // 8


def fmt_valid(v15):
    for d in range(32):
        rem = d
        for _ in range(10):
            rem = (rem << 1) ^ ((rem >> 9) * 0x537)
        if ((d << 10 | rem) ^ 0x5412) == v15:
            return d
    return None


def decode(m):
    s = len(m)
    ver = (s - 17) // 4
    g = lambda x, y: m[y][x]
    a = [g(8, i) for i in range(6)] + [g(8, 7), g(8, 8), g(7, 8)] + [g(14 - i, 8) for i in range(9, 15)]
    b = [g(s - 1 - i, 8) for i in range(8)] + [g(8, s - 15 + i) for i in range(8, 15)]
    v1 = sum(1 << i for i, c in enumerate(a) if c)
    v2 = sum(1 << i for i, c in enumerate(b) if c)
    d = fmt_valid(v1)
    if d is None or v1 != v2:
        return None, "형식 비트"
    ecl_bits, mask = d >> 3, d & 7
    fn = [[False] * s for _ in range(s)]

    def box(x0, y0, w, h):
        for y in range(max(0, y0), min(s, y0 + h)):
            for x in range(max(0, x0), min(s, x0 + w)):
                fn[y][x] = True
    box(0, 0, 9, 9)
    box(s - 8, 0, 8, 9)
    box(0, s - 8, 9, 8)
    box(6, 0, 1, s)
    box(0, 6, s, 1)
    pos = ALIGN[ver]
    for px in pos:
        for py in pos:
            if (px, py) in ((6, 6), (6, pos[-1]), (pos[-1], 6)):
                continue
            box(px - 2, py - 2, 5, 5)
    if ver >= 7:
        box(s - 11, 0, 3, 6)
        box(0, s - 11, 6, 3)
    bits = []
    right = s - 1
    while right >= 1:
        if right == 6:
            right = 5
        for v in range(s):
            for j in range(2):
                x = right - j
                y = s - 1 - v if ((right + 1) & 2) == 0 else v
                if not fn[y][x]:
                    bits.append(int(m[y][x] ^ MASK[mask](x, y)))
        right -= 2
    cw = [int("".join(map(str, bits[i:i + 8])), 2) for i in range(0, len(bits) - len(bits) % 8, 8)]
    groups, eccl = BLOCKS_M[ver]
    lens = [n for k, n in groups for _ in range(k)]
    blocks = [[] for _ in lens]
    k = 0
    for c in range(max(lens)):
        for i, n in enumerate(lens):
            if c < n:
                blocks[i].append(cw[k])
                k += 1
    for c in range(eccl):
        for i in range(len(lens)):
            blocks[i].append(cw[k])
            k += 1
    for blk in blocks:                           # 증후군 = 코드워드 다항식을 α^0..α^(e-1) 에서 — 모두 0 이어야
        alpha = 1
        for _ in range(eccl):
            acc = 0
            for c in blk:
                acc = gf_mul(acc, alpha) ^ c
            if acc:
                return None, "RS 증후군"
            alpha = gf_mul(alpha, 2)
    data = [c for blk, n in zip(blocks, lens) for c in blk[:n]]
    bs = "".join(f"{c:08b}" for c in data)
    if bs[:4] != "0100":
        return None, "바이트 꼴 아님"
    nlen = 8 if ver < 10 else 16
    n = int(bs[4:4 + nlen], 2)
    raw = bytes(int(bs[4 + nlen + 8 * i:12 + nlen + 8 * i], 2) for i in range(n))
    return {"ver": ver, "ecl_bits": ecl_bits, "mask": mask, "text": raw.decode("utf-8")}, ""


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ok("바이트 용량 M 판 1~10 = 규격 표", all(capacity(v, "M") == c for v, c in CAP_M.items()), {v: capacity(v, "M") for v in CAP_M})
    ok("바이트 용량 L 판 1~10 = 규격 표", all(capacity(v, "L") == c for v, c in CAP_L.items()), {v: capacity(v, "L") for v in CAP_L})
    ok("맞춤 무늬 자리 판 1~10 = 규격 부록", all(qr.align_positions(v) == p for v, p in ALIGN.items()))
    samples = [
        "https://pc-name.tail0a1b2c.ts.net/pair?c=Qm9vT2xlYW5Ub2tlbjEyMw",
        "http://10.0.2.2:8399/pair?c=AbCdEfGhIjKlMnOpQrStUv",
        "A",
        "폰 연결 — 짝짓기 한글 시험",
        "https://example-host.tailnet-name.ts.net/pair?c=" + "x" * 90,
    ]
    for t in samples:
        m = qr.encode(t)
        got, why = decode(m)
        ok(f"다시 읽기 = 넣은 글 ({len(t.encode())}바이트 · 판 {(len(m) - 17) // 4})", got is not None and got["text"] == t and got["ecl_bits"] == 0, why or got)
    for k in range(8):
        got, why = decode(qr.encode("https://a.ts.net/pair?c=mask", mask=k))
        ok(f"가림 {k} 형식·RS·글", got is not None and got["mask"] == k and got["text"].endswith("mask"), why or got)
    big = qr.encode("https://example-host.tailnet-name.ts.net/pair?c=" + "y" * 80)
    ok("판 7 이상 = 판 정보 칸 · 읽힘", (len(big) - 17) // 4 >= 7 and decode(big)[0] is not None, (len(big) - 17) // 4)
    m = qr.encode("https://a.ts.net/pair?c=svg")
    s = qr.svg(m)
    n = len(m) + 8
    ok("SVG = 흰 바탕 · 검은 칸 · 조용한 테두리 4", s.startswith("<svg") and 'fill="#fff"' in s and 'fill="#000"' in s and f'viewBox="0 0 {n} {n}"' in s, s[:120])
    print(f"\n합계 {len(rows) - len(fails)}/{len(rows)} 통과" + (f" · 실패 {fails}" if fails else ""))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
