# Builds an EDID override from the TV's current EDID with the HF-VSDB Max_FRL_Rate lowered
# (6 = 12 Gbps x4 -> 4 = 8 Gbps x4) and fixes the block checksum.
# The TV must be in its 21:9 mode (Game Bar) when this runs, so the 21:9 EDID is the source.
param([int]$MaxFrl = 4, [string]$MonitorId = 'TOL9653')
$inst = Get-PnpDevice -Class Monitor -PresentOnly | Where-Object { $_.InstanceId -like "DISPLAY\$MonitorId\*" } | Select-Object -First 1
if (-not $inst) { throw "monitor $MonitorId not present" }
$key = "HKLM:\SYSTEM\CurrentControlSet\Enum\$($inst.InstanceId)\Device Parameters"
[byte[]]$e = (Get-ItemProperty -Path $key -Name EDID).EDID
"source: $($inst.InstanceId) ($($e.Length) bytes)"
$changed = 0
for ($b = 1; $b * 128 -lt $e.Length; $b++) {
    $x = $b * 128
    if ($e[$x] -ne 0x02) { continue }
    $d = $e[$x + 2]; $i = $x + 4
    while ($i -lt $x + $d) {
        $tag = $e[$i] -shr 5; $len = $e[$i] -band 31
        if ($tag -eq 3 -and $len -ge 7 -and $e[$i + 1] -eq 0xD8 -and $e[$i + 2] -eq 0x5D -and $e[$i + 3] -eq 0xC4) {
            $o = $i + 7   # byte after OUI, version, Max_TMDS, flags
            $old = $e[$o]
            $e[$o] = [byte](($MaxFrl -shl 4) -bor ($e[$o] -band 0x0F))
            "HF-VSDB FRL/DC byte 0x{0:X2} -> 0x{1:X2}" -f $old, $e[$o]
            $changed++
        }
        $i += $len + 1
    }
    $sum = 0; for ($k = $x; $k -lt $x + 127; $k++) { $sum += $e[$k] }
    $e[$x + 127] = [byte]((256 - ($sum % 256)) % 256)
}
if ($changed -ne 1) { throw "HF-VSDB not found exactly once ($changed)" }
[IO.File]::WriteAllBytes((Join-Path $PSScriptRoot 'edid_override.bin'), $e)
"edid_override.bin written ($($e.Length) bytes)"
