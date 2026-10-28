"""Trial an NVIDIA custom display timing via NVAPI, then revert.

usage: py -I nvcustom.py <width> <height> <refresh> [hold_seconds] [rb|rb2]
Uses NvAPI_DISP_TryCustomDisplay (not saved) and always calls NvAPI_DISP_RevertCustomDisplayTrial at the end.
Timing: CVT reduced blanking v1 (default) or v2, computed here.
"""
import ctypes as C
import math
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


class TIMINGEXT(C.Structure):
    _fields_ = [('flag', C.c_uint32), ('rr', C.c_uint16), ('rrx1k', C.c_uint32), ('aspect', C.c_uint32),
                ('rep', C.c_uint16), ('status', C.c_uint32), ('name', C.c_char * 40)]


class TIMING(C.Structure):
    _fields_ = [('HVisible', C.c_uint16), ('HBorder', C.c_uint16), ('HFrontPorch', C.c_uint16),
                ('HSyncWidth', C.c_uint16), ('HTotal', C.c_uint16), ('HSyncPol', C.c_uint8),
                ('VVisible', C.c_uint16), ('VBorder', C.c_uint16), ('VFrontPorch', C.c_uint16),
                ('VSyncWidth', C.c_uint16), ('VTotal', C.c_uint16), ('VSyncPol', C.c_uint8),
                ('interlaced', C.c_uint16), ('pclk', C.c_uint32), ('etc', TIMINGEXT)]


class VIEWPORTF(C.Structure):
    _fields_ = [('x', C.c_float), ('y', C.c_float), ('w', C.c_float), ('h', C.c_float)]


class CUSTOM_DISPLAY(C.Structure):
    _fields_ = [('version', C.c_uint32), ('width', C.c_uint32), ('height', C.c_uint32), ('depth', C.c_uint32),
                ('colorFormat', C.c_int), ('srcPartition', VIEWPORTF), ('xRatio', C.c_float),
                ('yRatio', C.c_float), ('timing', TIMING), ('flags', C.c_uint32)]


class DISPLAY_DEVICE(C.Structure):
    _fields_ = [('cb', C.c_uint32), ('DeviceName', C.c_wchar * 32), ('DeviceString', C.c_wchar * 128),
                ('StateFlags', C.c_uint32), ('DeviceID', C.c_wchar * 128), ('DeviceKey', C.c_wchar * 128)]


def primary_display_name():
    """The GDI name (\\\\.\\DISPLAYn) of the primary display; it changes after a GPU driver restart."""
    i = 0
    while True:
        dd = DISPLAY_DEVICE(cb=C.sizeof(DISPLAY_DEVICE))
        if not C.windll.user32.EnumDisplayDevicesW(None, i, C.byref(dd), 0):
            raise SystemExit('no primary display found')
        if dd.StateFlags & 0x4:   # DISPLAY_DEVICE_PRIMARY_DEVICE
            return dd.DeviceName
        i += 1


def cvt_rb(w, h, rr):
    """CVT-RB v1: H blank 160 (fp 48, sync 32, bp 80); V fp 3, sync 10, min vblank 460us."""
    hperiod_us = (1e6 / rr - 460.0) / h
    vbi = max(int(460.0 / hperiod_us) + 1, 3 + 10 + 6)
    htotal, vtotal = w + 160, h + vbi
    pclk_10k = int(htotal * vtotal * rr / 10000)          # 10 kHz units
    t = TIMING(HVisible=w, HFrontPorch=48, HSyncWidth=32, HTotal=htotal, HSyncPol=0,  # 0 = positive
               VVisible=h, VFrontPorch=3, VSyncWidth=10, VTotal=vtotal, VSyncPol=1,   # 1 = negative
               interlaced=0, pclk=pclk_10k)
    real = pclk_10k * 10000 / (htotal * vtotal)
    t.etc.rr = int(round(real))
    t.etc.rrx1k = int(real * 1000)
    t.etc.rep = 1
    return t, real


def cvt_rb2(w, h, rr):
    """CVT-RB v2: H blank 80 (fp 8, sync 32, bp 40); V sync 8, bp 6, fp fills the 460us minimum vblank."""
    hperiod_us = (1e6 / rr - 460.0) / h
    vbi = max(int(460.0 / hperiod_us) + 1, 1 + 8 + 6)
    htotal, vtotal = w + 80, h + vbi
    pclk_10k = int(htotal * vtotal * rr / 10000)
    t = TIMING(HVisible=w, HFrontPorch=8, HSyncWidth=32, HTotal=htotal, HSyncPol=0,
               VVisible=h, VFrontPorch=vbi - 14, VSyncWidth=8, VTotal=vtotal, VSyncPol=1,
               interlaced=0, pclk=pclk_10k)
    real = pclk_10k * 10000 / (htotal * vtotal)
    t.etc.rr = int(round(real))
    t.etc.rrx1k = int(real * 1000)
    t.etc.rep = 1
    return t, real


def main():
    w, h, rr = int(sys.argv[1]), int(sys.argv[2]), float(sys.argv[3])
    hold = float(sys.argv[4]) if len(sys.argv) > 4 else 15
    name = primary_display_name()
    timing_fn = cvt_rb2 if len(sys.argv) > 5 and sys.argv[5] == 'rb2' else cvt_rb
    init = fn(0x0150E828)
    get_id = fn(0xAE457190, C.c_char_p, C.POINTER(C.c_uint32))
    try_cd = fn(0x1F7DB630, C.POINTER(C.c_uint32), C.c_uint32, C.POINTER(CUSTOM_DISPLAY))
    revert = fn(0xCBBD40F0, C.POINTER(C.c_uint32), C.c_uint32)
    print('init', init())
    did = C.c_uint32()
    print('displayId rc', get_id(name.encode(), C.byref(did)), hex(did.value))
    t, real = timing_fn(w, h, rr)
    print(f'timing {w}x{h} htotal={t.HTotal} vtotal={t.VTotal} pclk={t.pclk / 100:.2f}MHz '
          f'hfreq={t.pclk * 10 / t.HTotal:.2f}kHz refresh={real:.3f}Hz')
    cd = CUSTOM_DISPLAY(width=w, height=h, depth=32, colorFormat=0,
                        srcPartition=VIEWPORTF(0, 0, 1, 1), xRatio=1, yRatio=1, timing=t)
    cd.version = C.sizeof(CUSTOM_DISPLAY) | (1 << 16)
    ids = (C.c_uint32 * 1)(did.value)
    rc = try_cd(ids, 1, C.byref(cd))
    print(time.strftime('%H:%M:%S'), 'TryCustomDisplay rc', rc)
    if rc == 0 and '--save' in sys.argv:
        save = fn(0x49882876, C.POINTER(C.c_uint32), C.c_uint32, C.c_uint32, C.c_uint32)
        time.sleep(hold)
        print(time.strftime('%H:%M:%S'), 'SaveCustomDisplay rc', save(ids, 1, 1, 1))  # this output + this monitor only
        return
    try:
        if rc == 0:
            time.sleep(hold)
    finally:
        print(time.strftime('%H:%M:%S'), 'RevertCustomDisplayTrial rc', revert(ids, 1))


main()
