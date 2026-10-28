# Read-only: reads EDID blobs stored by Windows for the TV (PnP id TOL9653 by default) and prints the mode list.
param([string]$MonitorId = 'TOL9653')
$base = "HKLM:\SYSTEM\CurrentControlSet\Enum\DISPLAY\$MonitorId"
function Show-DTD($e, $o, $tag) {
    $pclk = ($e[$o] + 256 * $e[$o + 1]) * 10000
    if ($pclk -eq 0) { return }
    $ha = $e[$o + 2] + (($e[$o + 4] -shr 4) * 256); $hb = $e[$o + 3] + (($e[$o + 4] -band 15) * 256)
    $va = $e[$o + 5] + (($e[$o + 7] -shr 4) * 256); $vb = $e[$o + 6] + (($e[$o + 7] -band 15) * 256)
    $hz = $pclk / (($ha + $hb) * ($va + $vb))
    "  [$tag] DTD ${ha}x${va} @ {0:N2}Hz  pclk={1:N2}MHz" -f $hz, ($pclk / 1e6)
}
Get-ChildItem $base | ForEach-Object {
    $p = Join-Path $_.PSPath 'Device Parameters'
    $e = (Get-ItemProperty -Path $p -Name EDID -ErrorAction SilentlyContinue).EDID
    if (-not $e) { return }
    "=== $($_.PSChildName)  bytes=$($e.Length)  ext=$($e[126])"
    foreach ($o in 54, 72, 90, 108) {
        if ($e[$o] -eq 0 -and $e[$o + 1] -eq 0) {
            $t = $e[$o + 3]
            if ($t -in 0xFC, 0xFE) { "  name/text: " + (-join ($e[($o + 5)..($o + 17)] | ForEach-Object { [char]$_ })).Trim() }
            if ($t -eq 0xFD) { "  range: V {0}-{1}Hz  H {2}-{3}kHz  maxPclk {4}MHz" -f $e[$o + 5], $e[$o + 6], $e[$o + 7], $e[$o + 8], ($e[$o + 9] * 10) }
        } else { Show-DTD $e $o 'base' }
    }
    for ($b = 1; $b -le $e[126] -and ($b * 128) -lt $e.Length; $b++) {
        $x = $b * 128
        "  -- ext block $b tag=0x{0:X2}" -f $e[$x]
        if ($e[$x] -ne 0x02) { continue }
        $d = $e[$x + 2]; $i = $x + 4
        while ($i -lt $x + $d) {
            $tagc = $e[$i] -shr 5; $len = $e[$i] -band 31
            $pl = if ($len) { $e[($i + 1)..($i + $len)] } else { @() }
            if ($tagc -eq 2) { "  VICs: " + (($pl | ForEach-Object { $_ -band 0x7F }) -join ',') }
            elseif ($tagc -eq 3) { "  VSDB OUI {0:X2}{1:X2}{2:X2} len={3} bytes={4}" -f $pl[2], $pl[1], $pl[0], $len, (($pl | ForEach-Object { '{0:X2}' -f $_ }) -join ' ') }
            elseif ($tagc -eq 7) { "  Ext tag {0} len={1} bytes={2}" -f $pl[0], $len, (($pl | ForEach-Object { '{0:X2}' -f $_ }) -join ' ') }
            $i += $len + 1
        }
        for ($o = $x + $d; $o + 18 -le $x + 127; $o += 18) { Show-DTD $e $o "ext$b" }
    }
}
