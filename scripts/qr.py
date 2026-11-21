"""QR 부호기 — 짝짓기 주소 한 줄을 QR 그림(SVG)으로(바이트 꼴 · 오류 고침 M · 판 1~40 · 가림 8가지 중 벌점 낮은 것).

자체 제작(11-17 · 계획서 §9.1 의 «바깥 MIT 한 파일» 대신 — 규격 ISO/IEC 18004 의 공개 알고리즘을 따라 썼다 · 바깥 코드 없음 · NOTICE 필요 없음).
  py -3 .claude/skills/mobility/scripts/qr.py "<글>"        # SVG 를 표준 출력으로
  import qr; m = qr.encode("https://…"); qr.svg(m)          # m = 줄마다 참(검은 칸) 목록
검사 = qr_check.py(판별 용량표 · 형식 BCH · RS 증후군 0 · 다시 읽은 글 = 넣은 글).
"""
import sys

# 판마다 오류 고침 덩이 하나의 코드워드 수 · 덩이 수 — [L, M, Q, H][판] (판 0 은 안 씀)
ECC_PER_BLOCK = (
    (-1, 7, 10, 15, 20, 26, 18, 20, 24, 30, 18, 20, 24, 26, 30, 22, 24, 28, 30, 28, 28, 28, 28, 30, 30, 26, 28, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30),
    (-1, 10, 16, 26, 18, 24, 16, 18, 22, 22, 26, 30, 22, 22, 24, 24, 28, 28, 26, 26, 26, 26, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28),
    (-1, 13, 22, 18, 26, 18, 24, 18, 22, 20, 24, 28, 26, 24, 20, 30, 24, 28, 28, 26, 30, 28, 30, 30, 30, 30, 28, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30),
    (-1, 17, 28, 22, 16, 22, 28, 26, 26, 24, 28, 24, 28, 22, 24, 24, 30, 28, 28, 26, 28, 30, 24, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30),
)
NUM_BLOCKS = (
    (-1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 4, 4, 4, 4, 4, 6, 6, 6, 6, 7, 8, 8, 9, 9, 10, 12, 12, 12, 13, 14, 15, 16, 17, 18, 19, 19, 20, 21, 22, 24, 25),
    (-1, 1, 1, 1, 2, 2, 4, 4, 4, 5, 5, 5, 8, 9, 9, 10, 10, 11, 13, 14, 16, 17, 17, 18, 20, 21, 23, 25, 26, 28, 29, 31, 33, 35, 37, 38, 40, 43, 45, 47, 49),
    (-1, 1, 1, 2, 2, 4, 4, 6, 6, 8, 8, 8, 10, 12, 16, 12, 17, 16, 18, 21, 20, 23, 23, 25, 27, 29, 34, 34, 35, 38, 40, 43, 45, 48, 51, 53, 56, 59, 62, 65, 68),
    (-1, 1, 1, 2, 4, 4, 4, 5, 6, 8, 8, 11, 11, 16, 16, 18, 16, 19, 21, 25, 25, 25, 34, 30, 32, 35, 37, 40, 42, 45, 48, 51, 54, 57, 60, 63, 66, 70, 74, 77, 81),
)
ECL = {"L": (0, 1), "M": (1, 0), "Q": (2, 3), "H": (3, 2)}     # 이름 → (표 자리, 형식 비트)
MASKS = (
    lambda x, y: (x + y) % 2 == 0,
    lambda x, y: y % 2 == 0,
    lambda x, y: x % 3 == 0,
    lambda x, y: (x + y) % 3 == 0,
    lambda x, y: (x // 3 + y // 2) % 2 == 0,
    lambda x, y: x * y % 2 + x * y % 3 == 0,
    lambda x, y: (x * y % 2 + x * y % 3) % 2 == 0,
    lambda x, y: ((x + y) % 2 + x * y % 3) % 2 == 0,
)


def raw_modules(ver):
    """판의 자료 칸 수(기능 무늬 빼고)."""
    n = (16 * ver + 128) * ver + 64
    if ver >= 2:
        k = ver // 7 + 2
        n -= (25 * k - 10) * k - 55
        if ver >= 7:
            n -= 36
    return n


def data_codewords(ver, ecl="M"):
    i = ECL[ecl][0]
    return raw_modules(ver) // 8 - ECC_PER_BLOCK[i][ver] * NUM_BLOCKS[i][ver]


def align_positions(ver):
    if ver == 1:
        return []
    k = ver // 7 + 2
    size = ver * 4 + 17
    step = (ver * 8 + k * 3 + 5) // (k * 4 - 4) * 2
    return sorted([size - 7 - i * step for i in range(k - 1)] + [6])


def gf_mul(x, y):
    z = 0
    for i in reversed(range(8)):
        z = (z << 1) ^ ((z >> 7) * 0x11D)
        z ^= ((y >> i) & 1) * x
    return z


def rs_divisor(degree):
    out = [0] * (degree - 1) + [1]
    root = 1
    for _ in range(degree):
        for j in range(degree):
            out[j] = gf_mul(out[j], root)
            if j + 1 < degree:
                out[j] ^= out[j + 1]
        root = gf_mul(root, 0x02)
    return out


def rs_remainder(data, div):
    out = [0] * len(div)
    for b in data:
        f = b ^ out.pop(0)
        out.append(0)
        for i, c in enumerate(div):
            out[i] ^= gf_mul(c, f)
    return out


def interleave(data, ver, ecl):
    i = ECL[ecl][0]
    nb, eccl = NUM_BLOCKS[i][ver], ECC_PER_BLOCK[i][ver]
    raw = raw_modules(ver) // 8
    short_n, short_len = nb - raw % nb, raw // nb
    div = rs_divisor(eccl)
    blocks, k = [], 0
    for b in range(nb):
        dat = list(data[k:k + short_len - eccl + (0 if b < short_n else 1)])
        k += len(dat)
        ecc = rs_remainder(dat, div)
        if b < short_n:
            dat.append(0)
        blocks.append(dat + ecc)
    out = []
    for c in range(len(blocks[0])):
        for b, blk in enumerate(blocks):
            if c != short_len - eccl or b >= short_n:
                out.append(blk[c])
    return out


class _M:
    def __init__(self, ver):
        self.ver, self.size = ver, ver * 4 + 17
        self.dark = [[False] * self.size for _ in range(self.size)]
        self.fn = [[False] * self.size for _ in range(self.size)]

    def setf(self, x, y, d):
        self.dark[y][x] = d
        self.fn[y][x] = True

    def functions(self):
        s = self.size
        for i in range(s):
            self.setf(6, i, i % 2 == 0)
            self.setf(i, 6, i % 2 == 0)
        for cx, cy in ((3, 3), (s - 4, 3), (3, s - 4)):
            for dy in range(-4, 5):
                for dx in range(-4, 5):
                    x, y = cx + dx, cy + dy
                    if 0 <= x < s and 0 <= y < s:
                        self.setf(x, y, max(abs(dx), abs(dy)) not in (2, 4))
        pos = align_positions(self.ver)
        last = len(pos) - 1
        for a, px in enumerate(pos):
            for b, py in enumerate(pos):
                if (a, b) in ((0, 0), (0, last), (last, 0)):
                    continue
                for dy in range(-2, 3):
                    for dx in range(-2, 3):
                        self.setf(px + dx, py + dy, max(abs(dx), abs(dy)) != 1)
        self.format_bits(0, 0)
        if self.ver >= 7:
            rem = self.ver
            for _ in range(12):
                rem = (rem << 1) ^ ((rem >> 11) * 0x1F25)
            bits = self.ver << 12 | rem
            for i in range(18):
                d = (bits >> i) & 1 == 1
                a, b = s - 11 + i % 3, i // 3
                self.setf(a, b, d)
                self.setf(b, a, d)

    def format_bits(self, fbits, mask):
        s = self.size
        data = fbits << 3 | mask
        rem = data
        for _ in range(10):
            rem = (rem << 1) ^ ((rem >> 9) * 0x537)
        bits = (data << 10 | rem) ^ 0x5412
        g = lambda i: (bits >> i) & 1 == 1
        for i in range(6):
            self.setf(8, i, g(i))
        self.setf(8, 7, g(6))
        self.setf(8, 8, g(7))
        self.setf(7, 8, g(8))
        for i in range(9, 15):
            self.setf(14 - i, 8, g(i))
        for i in range(8):
            self.setf(s - 1 - i, 8, g(i))
        for i in range(8, 15):
            self.setf(8, s - 15 + i, g(i))
        self.setf(8, s - 8, True)

    def codewords(self, cw):
        s, i, n = self.size, 0, len(cw) * 8
        right = s - 1
        while right >= 1:
            if right == 6:
                right = 5
            for v in range(s):
                for j in range(2):
                    x = right - j
                    y = s - 1 - v if ((right + 1) & 2) == 0 else v
                    if not self.fn[y][x] and i < n:
                        self.dark[y][x] = (cw[i >> 3] >> (7 - (i & 7))) & 1 == 1
                        i += 1
            right -= 2

    def apply_mask(self, m):
        f = MASKS[m]
        for y in range(self.size):
            for x in range(self.size):
                if not self.fn[y][x] and f(x, y):
                    self.dark[y][x] = not self.dark[y][x]

    def penalty(self):
        s, d, p = self.size, self.dark, 0
        lines = [d[y] for y in range(s)] + [[d[y][x] for y in range(s)] for x in range(s)]
        pat = (True, False, True, True, True, False, True)
        for ln in lines:
            run, prev = 0, None
            for c in ln:
                if c == prev:
                    run += 1
                else:
                    if run >= 5:
                        p += 3 + run - 5
                    run, prev = 1, c
            if run >= 5:
                p += 3 + run - 5
            padded = [False] * 4 + list(ln) + [False] * 4
            for k in range(len(padded) - 6):
                if tuple(padded[k:k + 7]) == pat and (not any(padded[max(0, k - 4):k]) and k >= 4 or not any(padded[k + 7:k + 11]) and k + 11 <= len(padded)):
                    p += 40
        for y in range(s - 1):
            for x in range(s - 1):
                if d[y][x] == d[y][x + 1] == d[y + 1][x] == d[y + 1][x + 1]:
                    p += 3
        dark = sum(sum(r) for r in d)
        total = s * s
        p += ((abs(dark * 20 - total * 10) + total - 1) // total - 1) * 10
        return p


def encode(text, ecl="M", mask=None):
    """글 → 칸 목록(줄 = y · 칸 = x · 참 = 검은 칸)."""
    data = text.encode("utf-8") if isinstance(text, str) else bytes(text)
    for ver in range(1, 41):
        cap = data_codewords(ver, ecl) * 8
        need = 4 + (8 if ver < 10 else 16) + len(data) * 8
        if need <= cap:
            break
    else:
        raise ValueError("너무 김")
    bits = []

    def put(v, n):
        bits.extend((v >> i) & 1 for i in reversed(range(n)))
    put(0b0100, 4)
    put(len(data), 8 if ver < 10 else 16)
    for b in data:
        put(b, 8)
    put(0, min(4, cap - len(bits)))
    put(0, (-len(bits)) % 8)
    pad = 0xEC
    while len(bits) < cap:
        put(pad, 8)
        pad ^= 0xEC ^ 0x11
    cw = [int("".join(map(str, bits[i:i + 8])), 2) for i in range(0, len(bits), 8)]
    m = _M(ver)
    m.functions()
    m.codewords(interleave(cw, ver, ecl))
    fb = ECL[ecl][1]
    best = None
    for k in (range(8) if mask is None else (mask,)):
        m.apply_mask(k)
        m.format_bits(fb, k)
        p = m.penalty()
        if best is None or p < best[0]:
            best = (p, k)
        m.apply_mask(k)                         # 되돌림(가림은 제 짝)
    m.apply_mask(best[1])
    m.format_bits(fb, best[1])
    return m.dark


def svg(mods, border=4, px=None):
    """검은 칸 = 검정 · 바탕 = 흰색(어두운 테마에서도 찍히게 색을 바꾸지 않는다)."""
    n = len(mods) + border * 2
    d = "".join(f"M{x + border},{y + border}h1v1h-1z" for y, row in enumerate(mods) for x, c in enumerate(row) if c)
    size = f' width="{px}" height="{px}"' if px else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {n} {n}"{size} shape-rendering="crispEdges">'
            f'<rect width="{n}" height="{n}" fill="#fff"/><path d="{d}" fill="#000"/></svg>')


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(svg(encode(sys.argv[1] if len(sys.argv) > 1 else "")))
