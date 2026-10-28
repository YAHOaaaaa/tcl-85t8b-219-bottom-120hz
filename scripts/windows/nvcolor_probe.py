"""Query-only: asks the driver which color formats it reports as supported (NV_COLOR_CMD_IS_SUPPORTED_COLOR)."""
import ctypes as C
import importlib.util
import pathlib
import sys

spec = importlib.util.spec_from_file_location('nvc', pathlib.Path(__file__).with_name('nvcolor.py'))
sys.argv = ['nvcolor.py', 'get']
nvc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(nvc)   # runs 'get' once and defines helpers

did = C.c_uint32()
nvc.get_id(nvc.primary_display_name().encode(), C.byref(did))
for cmd, name in [(4, 'GET_DEFAULT'), (1, 'GET')]:
    rc, d = nvc.call(did.value, cmd)
    nvc.show(name, rc, d)
for fmt in ('rgb', 'yuv422', 'yuv444', 'yuv420'):
    for colorimetry in (0, 1, 2, 0xFF):
        for rng in (0, 1, 2):
            rc, d = nvc.call(did.value, 3, colorFormat=nvc.FMT[fmt], colorimetry=colorimetry, dynamicRange=rng, bpc=2,
                             colorSelectionPolicy=0, depth=0)
            if rc == 0:
                print(f'supported: {fmt} colorimetry={colorimetry} range={rng}')
