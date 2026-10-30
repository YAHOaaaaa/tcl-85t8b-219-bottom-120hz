# Run elevated. For an A/B test without the EDID override: removes the TV's Windows EDID override (Windows then uses
# the TV's own EDID, Max FRL 12G x4 on the tested TV), restarts the GPU driver, waits until edid_tempremove_done.flag
# appears in this folder or $Timeout seconds pass, and then ALWAYS writes edid_override.bin (the 8G x4 override) back
# and restarts the GPU driver again.
# Tip: switch the PC to a standard mode the TV's own EDID lists (e.g. 3840x1600@60) first, so there is a picture.
param([int]$Timeout = 300, [string]$MonitorId = 'TOL9653')
$dir = $PSScriptRoot
$log = Join-Path $dir 'edid_apply.log'
$good = Join-Path $dir 'edid_override.bin'
$flag = Join-Path $dir 'edid_tempremove_done.flag'
function L($m) { "$(Get-Date -Format 'HH:mm:ss') $m" | Tee-Object -FilePath $log -Append }
$mon = Get-PnpDevice -Class Monitor -PresentOnly | Where-Object { $_.InstanceId -like "DISPLAY\$MonitorId\*" } | Select-Object -First 1
if (-not $mon) { L "monitor $MonitorId not present - nothing changed"; return }
if (-not (Test-Path $good)) { L "edid_override.bin missing - nothing changed"; return }
$regPath = "SYSTEM\CurrentControlSet\Enum\$($mon.InstanceId)\Device Parameters"
$ovr = "HKLM:\$regPath\EDID_OVERRIDE"
$gpu = (Get-PnpDevice -Class Display -PresentOnly | Where-Object { $_.InstanceId -like 'PCI\VEN_10DE*' } | Select-Object -First 1).InstanceId
function Restart-Gpu { L 'restarting GPU driver'; $o = pnputil /restart-device "$gpu" 2>&1; L ($o -join ' / '); Start-Sleep 8 }
function Restore-Good {
    [byte[]]$e = [IO.File]::ReadAllBytes($good)
    New-Item -Path $ovr -Force | Out-Null
    for ($b = 0; $b * 128 -lt $e.Length; $b++) {
        New-ItemProperty -Path $ovr -Name "$b" -PropertyType Binary -Value ([byte[]]$e[($b * 128)..($b * 128 + 127)]) -Force | Out-Null
    }
    L "override written back from edid_override.bin ($($e.Length) bytes)"
    Restart-Gpu
}
Remove-Item $flag -ErrorAction SilentlyContinue
try {
    reg export "HKLM\$regPath" (Join-Path $dir 'edid_devparams_backup.reg') /y | Out-Null
    L 'backup exported'
    if (Test-Path $ovr) { Remove-Item $ovr -Recurse -Force; L 'override removed (temporary)' } else { L 'no override was present' }
    Restart-Gpu
    L "waiting up to $Timeout s for edid_tempremove_done.flag"
    $end = (Get-Date).AddSeconds($Timeout)
    while ((Get-Date) -lt $end -and -not (Test-Path $flag)) { Start-Sleep 2 }
    L $(if (Test-Path $flag) { 'done flag found' } else { 'timeout' })
} catch { L "ERROR $_" }
finally { Restore-Good; Remove-Item $flag -ErrorAction SilentlyContinue }
