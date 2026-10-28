# Dumps the TV's current UI hierarchy (uiautomator) and prints a compact node list.
# Optional -Keys: space-separated keyevents to send first (e.g. "DPAD_DOWN DPAD_CENTER").
param([string]$Keys = '', [string]$Tag = 'ui', [int]$Wait = 1500)
. "$PSScriptRoot\tvserial.ps1"
$s = Get-TvSerial
foreach ($k in ($Keys -split ' ' | Where-Object { $_ })) {
    adb -s $s shell input keyevent "KEYCODE_$k"
    Start-Sleep -Milliseconds 400
}
Start-Sleep -Milliseconds $Wait
$dir = Join-Path $PSScriptRoot 'ui'
New-Item -ItemType Directory -Force $dir | Out-Null
$f = Join-Path $dir ("{0}_{1}.xml" -f (Get-Date -Format HHmmss), $Tag)
adb -s $s shell "uiautomator dump /sdcard/ui.xml >/dev/null 2>&1; cat /sdcard/ui.xml; rm -f /sdcard/ui.xml" | Out-File -Encoding utf8 $f
[xml]$x = Get-Content $f -Raw
$x.SelectNodes('//node') | ForEach-Object {
    $t = $_.text; $id = ($_.'resource-id' -replace '^.*:id/', '')
    if ($t -or $_.focused -eq 'true' -or $_.selected -eq 'true') {
        '{0}{1}{2} [{3}] {4}' -f $(if ($_.focused -eq 'true') { '>F ' } else { '   ' }), $(if ($_.selected -eq 'true') { 'S ' } else { '' }), $t, $id, $_.bounds
    }
}
