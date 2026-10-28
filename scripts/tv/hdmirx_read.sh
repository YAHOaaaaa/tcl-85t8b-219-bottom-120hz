cd /sys/devices/platform/mtk_srccap0/mtk_dbg/hdmirx || exit 1
ls -l
for f in *; do
  if [ -f "$f" ] && [ -r "$f" ]; then
    echo "===== $f"
    head -c 4000 "$f"
    echo
  fi
done
