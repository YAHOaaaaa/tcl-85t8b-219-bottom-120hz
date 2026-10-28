"""Tiny DEX flow lister (no external deps).

usage: py -I dexflow.py <regex> <apk|jar> [more files]
Prints every method whose name/class, string constants or call targets match <regex>,
as a linear list of const / const-string / field / invoke operations.
"""
import re
import struct
import sys
import zipfile

SIZES = {}
for op in range(256):
    SIZES[op] = 1
for op, n in [(0x02, 2), (0x03, 3), (0x05, 2), (0x06, 3), (0x08, 2), (0x09, 3), (0x13, 2), (0x14, 3), (0x15, 2),
              (0x16, 2), (0x17, 3), (0x18, 5), (0x19, 2), (0x1a, 2), (0x1b, 3), (0x1c, 2), (0x1f, 2), (0x20, 2),
              (0x22, 2), (0x23, 2), (0x24, 3), (0x25, 3), (0x26, 3), (0x29, 2), (0x2a, 3), (0x2b, 3), (0x2c, 3),
              (0xfa, 4), (0xfb, 4), (0xfc, 3), (0xfd, 3), (0xfe, 2), (0xff, 2)]:
    SIZES[op] = n
for lo, hi, n in [(0x2d, 0x3d, 2), (0x44, 0x6d, 2), (0x6e, 0x72, 3), (0x74, 0x78, 3), (0x90, 0xaf, 2), (0xd0, 0xe2, 2)]:
    for op in range(lo, hi + 1):
        SIZES[op] = n

IF_NAMES = {0x32: 'if-eq', 0x33: 'if-ne', 0x34: 'if-lt', 0x35: 'if-ge', 0x36: 'if-gt', 0x37: 'if-le',
            0x38: 'if-eqz', 0x39: 'if-nez', 0x3a: 'if-ltz', 0x3b: 'if-gez', 0x3c: 'if-gtz', 0x3d: 'if-lez'}


def uleb(b, o):
    r = s = 0
    while True:
        x = b[o]
        o += 1
        r |= (x & 0x7F) << s
        if x < 0x80:
            return r, o
        s += 7


class Dex:
    def __init__(self, d):
        self.d = d
        u = lambda off: struct.unpack_from('<II', d, off)
        sz, so = u(0x38)
        tz, to = u(0x40)
        fz, fo = u(0x50)
        mz, mo = u(0x58)
        self.cz, self.co = u(0x60)
        self.strs = []
        for i in range(sz):
            off = struct.unpack_from('<I', d, so + 4 * i)[0]
            _, p = uleb(d, off)
            self.strs.append(d[p:d.index(b'\0', p)].decode('utf-8', 'replace'))
        self.types = [self.strs[struct.unpack_from('<I', d, to + 4 * i)[0]] for i in range(tz)]
        self.fields = []
        for i in range(fz):
            c, t, n = struct.unpack_from('<HHI', d, fo + 8 * i)
            self.fields.append(f'{self.types[c]}->{self.strs[n]}')
        self.meths = []
        for i in range(mz):
            c, _p, n = struct.unpack_from('<HHI', d, mo + 8 * i)
            self.meths.append(f'{self.types[c]}->{self.strs[n]}')

    def methods(self):
        d = self.d
        for i in range(self.cz):
            cdo = struct.unpack_from('<8I', d, self.co + 32 * i)[6]
            if not cdo:
                continue
            o = cdo
            sf, o = uleb(d, o)
            inf, o = uleb(d, o)
            dm, o = uleb(d, o)
            vm, o = uleb(d, o)
            for _ in range(sf + inf):
                _, o = uleb(d, o)
                _, o = uleb(d, o)
            for cnt in (dm, vm):
                idx = 0
                for _ in range(cnt):
                    diff, o = uleb(d, o)
                    _, o = uleb(d, o)
                    code, o = uleb(d, o)
                    idx += diff
                    if code:
                        yield self.meths[idx], code

    def ops(self, code):
        d = self.d
        n = struct.unpack_from('<I', d, code + 12)[0]
        base = code + 16
        pc = 0
        out = []
        while pc < n:
            w = struct.unpack_from('<H', d, base + 2 * pc)[0]
            op = w & 0xFF
            if op == 0 and w in (0x100, 0x200, 0x300):
                if w == 0x100:
                    size = struct.unpack_from('<H', d, base + 2 * pc + 2)[0]
                    pc += size * 2 + 4
                elif w == 0x200:
                    size = struct.unpack_from('<H', d, base + 2 * pc + 2)[0]
                    pc += size * 4 + 2
                else:
                    width = struct.unpack_from('<H', d, base + 2 * pc + 2)[0]
                    size = struct.unpack_from('<I', d, base + 2 * pc + 4)[0]
                    pc += (size * width + 1) // 2 + 4
                continue
            a1 = struct.unpack_from('<H', d, base + 2 * pc + 2)[0] if SIZES[op] > 1 else 0
            if op == 0x12:
                v = (w >> 12)
                out.append(f'const v{(w >> 8) & 15}={v - 16 if v > 7 else v}')
            elif op == 0x13:
                out.append(f'const v{w >> 8}={struct.unpack("<h", struct.pack("<H", a1))[0]}')
            elif op == 0x14:
                out.append(f'const v{w >> 8}={struct.unpack_from("<i", d, base + 2 * pc + 2)[0]}')
            elif op == 0x1a:
                out.append(f'str v{w >> 8}={self.strs[a1]!r}')
            elif op == 0x1b:
                out.append(f'str v{w >> 8}={self.strs[struct.unpack_from("<I", d, base + 2 * pc + 2)[0]]!r}')
            elif 0x52 <= op <= 0x6d:
                kind = 'get' if (op - 0x52) % 14 < 7 else 'put'
                out.append(f'field-{kind} {self.fields[a1]}')
            elif 0x6e <= op <= 0x78 and op != 0x73:
                out.append(f'call {self.meths[a1]}')
            elif op in IF_NAMES:
                out.append(IF_NAMES[op])
            elif 0xd8 <= op <= 0xe2 or 0xd0 <= op <= 0xd7:
                pass
            pc += SIZES[op]
        return out


def main():
    rx = re.compile(sys.argv[1])
    for f in sys.argv[2:]:
        z = zipfile.ZipFile(f)
        for name in z.namelist():
            if not re.match(r'classes\d*\.dex$', name):
                continue
            dx = Dex(z.read(name))
            for m, code in dx.methods():
                try:
                    ops = dx.ops(code)
                except Exception as e:  # noqa: BLE001
                    ops = [f'<decode error {e}>']
                if rx.search(m) or any(rx.search(o) for o in ops if o.startswith(('str', 'call'))):
                    print(f'### {m}  [{name}]')
                    for o in ops:
                        print('   ', o[:220])


main()
