# Counts HDMI RX "UnStable"/"NoSignal" transitions on the TV over a window (read-only).
param([int]$Seconds = 120, [string]$Tag = '')
. "$PSScriptRoot\tvserial.ps1"
$s = Get-TvSerial
$start = adb -s $s shell "date +%m-%d' '%H:%M:%S"
Start-Sleep -Seconds $Seconds
$lines = adb -s $s logcat -d -v time -T "$start.000" 2>$null | Select-String 'HDMIRX signal is (1|2)'
"$Tag window=${Seconds}s from $start  drops(UnStable/NoSignal events)=$(@($lines).Count)"
$lines | Select-Object -Last 6 | ForEach-Object { '  ' + $_.Line.Substring(0, [Math]::Min(120, $_.Line.Length)) }
