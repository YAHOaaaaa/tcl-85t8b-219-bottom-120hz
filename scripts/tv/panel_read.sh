d=/sys/devices/platform/mediatek-drm-tv-kms
for f in $d/mtk_dbg/output_frame_rate $d/mtk_dbg/panel_out_model $d/mtk_dbg/panel_mod_status $d/panel/vrr_min_v $d/panel/vrr_max_v $d/panel/vrr_tolerance; do
  echo "== $f"; cat "$f" 2>&1 | head -30
done
for c in /sys/class/drm/card0-LVDS-*; do echo "== $c"; cat $c/status $c/modes 2>&1 | head -6; done
ls $d/panel 2>&1
