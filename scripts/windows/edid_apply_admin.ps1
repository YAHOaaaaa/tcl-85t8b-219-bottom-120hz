# Run elevated. Applies edid_override.bin as the Windows EDID override for the TV, restarts the GPU driver,
# then waits for edid_keep.flag. Without the flag within $Timeout seconds it removes the override and restarts again.
# -Remove: just remove the override and restart the GPU driver.
param([int]$Timeout = 180, [switch]$Remove, [string]$MonitorId = 'TOL9653')
$dir = $PSScriptRoot
$log = Join-Path $dir 'edid_apply.log'
function L($m) { "$(Get-Date -Format 'HH:mm:ss') $m" | Tee-Object -FilePath $log -Append }
$mon = Get-PnpDevice -Class Monitor -PresentOnly | Where-Object { $_.InstanceId -like "DISPLAY\$MonitorId\*" } | Select-Object -First 1
if (-not $mon) { L "monitor $MonitorId not present"; return }
$regPath = "SYSTEM\CurrentControlSet\Enum\$($mon.InstanceId)\Device Parameters"
$key = "HKLM:\$regPath"
$ovr = Join-Path $key 'EDID_OVERRIDE'
$gpu = (Get-PnpDevice -Class Display -PresentOnly | Where-Object { $_.InstanceId -like 'PCI\VEN_10DE*' } | Select-Object -First 1).InstanceId
function Restart-Gpu { L 'restarting GPU driver'; $o = pnputil /restart-device "$gpu" 2>&1; L ($o -join ' / '); Start-Sleep 8 }
function Remove-Override {
    if (Test-Path $ovr) { Remove-Item $ovr -Recurse -Force; L 'override removed' } else { L 'no override present' }
    Restart-Gpu
}
try {
    if ($Remove) { Remove-Override; return }
    Remove-Item (Join-Path $dir 'edid_keep.flag') -ErrorAction SilentlyContinue
    reg export "HKLM\$regPath" (Join-Path $dir 'edid_devparams_backup.reg') /y | Out-Null
    L 'backup exported'
    [byte[]]$e = [IO.File]::ReadAllBytes((Join-Path $dir 'edid_override.bin'))
    New-Item -Path $ovr -Force | Out-Null
    for ($b = 0; $b * 128 -lt $e.Length; $b++) {
        New-ItemProperty -Path $ovr -Name "$b" -PropertyType Binary -Value ([byte[]]$e[($b * 128)..($b * 128 + 127)]) -Force | Out-Null
    }
    L "override written ($($e.Length) bytes)"
    Restart-Gpu
    L "waiting up to $Timeout s for edid_keep.flag"
    $end = (Get-Date).AddSeconds($Timeout)
    while ((Get-Date) -lt $end) {
        if (Test-Path (Join-Path $dir 'edid_keep.flag')) { L 'keep flag found - override kept'; return }
        Start-Sleep 2
    }
    L 'no keep flag - rolling back'
    Remove-Override
} catch { L "ERROR $_"; Remove-Override }
