"""Minimal DEX/ELF string and method scanner (no external deps).

usage: py -I dexscan.py <regex> <file> [file...]
APK/JAR: prints matching strings and Class->method names from every classes*.dex.
.so / other: prints matching printable strings.
"""
import re
import struct
import sys
import zipfile


def uleb(b, o):
    r = s = 0
    while True:
        x = b[o]
        o += 1
        r |= (x & 0x7F) << s
        if x < 0x80:
            return r, o
        s += 7


def dex_tables(d):
    sz, so = struct.unpack_from('<II', d, 0x38)
    tz, to = struct.unpack_from('<II', d, 0x40)
    pz, po = struct.unpack_from('<II', d, 0x48)
    mz, mo = struct.unpack_from('<II', d, 0x58)
    strs = []
    for i in range(sz):
        off = struct.unpack_from('<I', d, so + 4 * i)[0]
        _, p = uleb(d, off)
        e = d.index(b'\0', p)
        strs.append(d[p:e].decode('utf-8', 'replace'))
    types = [strs[struct.unpack_from('<I', d, to + 4 * i)[0]] for i in range(tz)]
    meths = []
    for i in range(mz):
        c, _p, n = struct.unpack_from('<HHI', d, mo + 8 * i)
        meths.append((types[c], strs[n]))
    return strs, meths


def main():
    rx = re.compile(sys.argv[1], re.I)
    for f in sys.argv[2:]:
        if f.endswith(('.apk', '.jar')):
            z = zipfile.ZipFile(f)
            for name in z.namelist():
                if not re.match(r'classes\d*\.dex$', name):
                    continue
                strs, meths = dex_tables(z.read(name))
                for s in sorted({s for s in strs if rx.search(s)}):
                    print(f'{f}:{name}:S: {s[:300]}')
                for c, m in sorted({(c, m) for c, m in meths if rx.search(m) or rx.search(c)}):
                    print(f'{f}:{name}:M: {c}->{m}')
        else:
            data = open(f, 'rb').read()
            for m in re.finditer(rb'[\x20-\x7e]{4,}', data):
                s = m.group().decode()
                if rx.search(s):
                    print(f'{f}:STR: {s[:300]}')


main()
