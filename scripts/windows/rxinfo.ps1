# Prints the TV's HDMI RX link state for the active port from the MediaTek debug node (read-only).
# On the tested TV, "Port 3" in HDMI_INFO is the HDMI 1 connector; the last column is used.
param([string]$Tag = '')
. "$PSScriptRoot\tvserial.ps1"
$s = Get-TvSerial
$raw = adb -s $s shell cat /sys/devices/platform/mtk_srccap0/mtk_dbg/hdmirx/HDMI_INFO 2>&1
$keys = '5V', 'DE Stable', 'Source Version', 'Width', 'Height', 'Htotal', 'Vtotal', 'Pixel Freq\(KHz\)', 'Refresh Rate\(mHz\)',
        'Color Space\(1\)', 'Color Depth', 'TMDS Clock Ratio', 'FRL Rate', 'Lane Cnt', 'Dsc FSM'
$out = foreach ($k in $keys) {
    $line = $raw | Where-Object { $_ -match "^$k\s" } | Select-Object -First 1
    if ($line) { '{0}={1}' -f ($k -replace '\\', ''), (($line.Trim() -split '\s+') | Select-Object -Last 1) }
}
"$(Get-Date -Format HH:mm:ss) $Tag | " + ($out -join ' | ')
