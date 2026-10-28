# Dot-source helper: resolves the TV's adb serial.
# Uses $env:TV_SERIAL when set, otherwise the single attached device whose model is Smart_TV_Pro (TCL Google TV).
function Get-TvSerial {
    if ($env:TV_SERIAL) { return $env:TV_SERIAL }
    $lines = adb devices -l | Where-Object { $_ -match '\sdevice\s.*model:Smart_TV_Pro' }
    if (@($lines).Count -ne 1) { throw 'TV not found uniquely; set $env:TV_SERIAL (e.g. 192.168.x.x:5555)' }
    return ($lines -split '\s+')[0]
}
