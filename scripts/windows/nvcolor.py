"""Get/set NVIDIA output color format via NvAPI_Disp_ColorControl.

usage:
  py -I nvcolor.py get
  py -I nvcolor.py set <rgb|yuv422|yuv444|yuv420> <bpc 8|10|12> [hold_seconds]   (restores the previous state after hold)
  py -I nvcolor.py auto                                                          (driver default selection)
"""
import ctypes as C
import sys
import time

nv = C.WinDLL('nvapi64.dll')
nv.nvapi_QueryInterface.restype = C.c_void_p
nv.nvapi_QueryInterface.argtypes = [C.c_uint]


def fn(fid, *argtypes):
    p = nv.nvapi_QueryInterface(fid)
    if not p:
        raise SystemExit(f'nvapi function 0x{fid:08X} not available')
    return C.WINFUNCTYPE(C.c_int, *argtypes)(p)


class COLOR_DATA(C.Structure):
    _fields_ = [('version', C.c_uint32), ('size', C.c_uint16), ('cmd', C.c_uint8),
                ('colorFormat', C.c_uint8), ('colorimetry', C.c_uint8), ('dynamicRange', C.c_uint8),
                ('bpc', C.c_int), ('colorSelectionPolicy', C.c_int), ('depth', C.c_int)]


FMT = {'rgb': 0, 'yuv422': 1, 'yuv444': 2, 'yuv420': 3}
FMT_NAME = {v: k for k, v in FMT.items()} | {0xFE: 'default', 0xFF: 'auto'}
BPC = {8: 2, 10: 3, 12: 4}
BPC_NAME = {0: 'default', 1: '6', 2: '8', 3: '10', 4: '12', 5: '16'}

init = fn(0x0150E828)
get_id = fn(0xAE457190, C.c_char_p, C.POINTER(C.c_uint32))
ctl = fn(0x92F9D80D, C.c_uint32, C.POINTER(COLOR_DATA))


class DISPLAY_DEVICE(C.Structure):
    _fields_ = [('cb', C.c_uint32), ('DeviceName', C.c_wchar * 32), ('DeviceString', C.c_wchar * 128),
                ('StateFlags', C.c_uint32), ('DeviceID', C.c_wchar * 128), ('DeviceKey', C.c_wchar * 128)]


def primary_display_name():
    i = 0
    while True:
        dd = DISPLAY_DEVICE(cb=C.sizeof(DISPLAY_DEVICE))
        if not C.windll.user32.EnumDisplayDevicesW(None, i, C.byref(dd), 0):
            raise SystemExit('no primary display found')
        if dd.StateFlags & 0x4:   # DISPLAY_DEVICE_PRIMARY_DEVICE
            return dd.DeviceName
        i += 1


def call(did, cmd, **kw):
    d = COLOR_DATA(cmd=cmd, **kw)
    d.version = C.sizeof(COLOR_DATA) | (5 << 16)
    d.size = C.sizeof(COLOR_DATA)
    rc = ctl(did, C.byref(d))
    return rc, d


def show(tag, rc, d):
    print(f'{time.strftime("%H:%M:%S")} {tag} rc={rc} format={FMT_NAME.get(d.colorFormat, d.colorFormat)} '
          f'colorimetry={d.colorimetry} range={d.dynamicRange} bpc={BPC_NAME.get(d.bpc, d.bpc)} '
          f'policy={d.colorSelectionPolicy} depth={d.depth}')


def main():
    init()
    did = C.c_uint32()
    get_id(primary_display_name().encode(), C.byref(did))
    did = did.value
    rc, cur = call(did, 1)  # GET
    show('current', rc, cur)
    if sys.argv[1] == 'get':
        return
    if sys.argv[1] == 'auto':
        rc, d = call(did, 2, colorFormat=0xFE, colorimetry=0xFE, dynamicRange=2, bpc=0, colorSelectionPolicy=1, depth=0)
        show('set auto', rc, d)
        return
    fmt, bpc = FMT[sys.argv[2]], BPC[int(sys.argv[3])]
    hold = float(sys.argv[4]) if len(sys.argv) > 4 else 15
    keep = '--keep' in sys.argv
    # colorimetry 0 / range 0 is the combination the driver reports via IS_SUPPORTED_COLOR
    rc, d = call(did, 2, colorFormat=fmt, colorimetry=0, dynamicRange=0, bpc=bpc,
                 colorSelectionPolicy=0, depth=0)
    show('set', rc, d)
    if rc == 0 and keep:
        return
    try:
        if rc == 0:
            time.sleep(hold)
    finally:
        rc, d = call(did, 2, colorFormat=cur.colorFormat, colorimetry=cur.colorimetry, dynamicRange=cur.dynamicRange,
                     bpc=cur.bpc, colorSelectionPolicy=cur.colorSelectionPolicy, depth=cur.depth)
        show('restored', rc, d)


main()
