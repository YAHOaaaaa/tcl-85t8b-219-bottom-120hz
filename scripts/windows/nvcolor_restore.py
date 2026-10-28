"""Tries to put NVIDIA color output back to RGB / 8 bpc / user policy / dynamic range auto, reporting each attempt."""
import ctypes as C
import importlib.util
import pathlib
import sys

spec = importlib.util.spec_from_file_location('nvc', pathlib.Path(__file__).with_name('nvcolor.py'))
sys.argv = ['nvcolor.py', 'get']
nvc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(nvc)

did = C.c_uint32()
nvc.get_id(nvc.primary_display_name().encode(), C.byref(did))
for colorimetry, rng in [(2, 2), (0, 2), (0xFE, 2), (0, 1), (0, 0)]:
    rc, d = nvc.call(did.value, 2, colorFormat=0, colorimetry=colorimetry, dynamicRange=rng, bpc=2,
                     colorSelectionPolicy=0, depth=0)
    nvc.show(f'set rgb colorimetry={colorimetry} range={rng}', rc, d)
    if rc == 0:
        break
rc, d = nvc.call(did.value, 1)
nvc.show('now', rc, d)
