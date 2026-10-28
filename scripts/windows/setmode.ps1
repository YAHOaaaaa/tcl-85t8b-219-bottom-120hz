# Sets the TV output (\\.\DISPLAY1) to a mode, holds it, then reverts unless -Keep.
# Not saved to the registry (no CDS_UPDATEREGISTRY), so a reboot or display re-plug also restores Windows' saved mode.
param([int]$W, [int]$H, [int]$Hz, [int]$Fixed = 0, [int]$Hold = 15, [switch]$Keep, [switch]$Persist)
Add-Type -TypeDefinition @'
using System; using System.Runtime.InteropServices;
public class DMS {
  [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)] public struct DEVMODE {
    [MarshalAs(UnmanagedType.ByValTStr, SizeConst=32)] public string dmDeviceName; public short dmSpecVersion, dmDriverVersion, dmSize, dmDriverExtra; public int dmFields;
    public int dmPositionX, dmPositionY, dmDisplayOrientation, dmDisplayFixedOutput; public short dmColor, dmDuplex, dmYResolution, dmTTOption, dmCollate;
    [MarshalAs(UnmanagedType.ByValTStr, SizeConst=32)] public string dmFormName; public short dmLogPixels; public int dmBitsPerPel, dmPelsWidth, dmPelsHeight, dmDisplayFlags, dmDisplayFrequency;
    public int dmICMMethod, dmICMIntent, dmMediaType, dmDitherType, dmReserved1, dmReserved2, dmPanningWidth, dmPanningHeight; }
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern bool EnumDisplaySettingsEx(string dev, int mode, ref DEVMODE dm, int flags);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int ChangeDisplaySettingsEx(string dev, ref DEVMODE dm, IntPtr hwnd, int flags, IntPtr p);
  public static DEVMODE Cur(string dev) { var d = new DEVMODE(); d.dmSize=(short)Marshal.SizeOf(d); EnumDisplaySettingsEx(dev, -1, ref d, 0); return d; }
  public static int Set(string dev, DEVMODE d, int flags) { return ChangeDisplaySettingsEx(dev, ref d, IntPtr.Zero, flags, IntPtr.Zero); }
}
'@ -ErrorAction SilentlyContinue
Add-Type -AssemblyName System.Windows.Forms
$dev = [System.Windows.Forms.Screen]::PrimaryScreen.DeviceName
$orig = [DMS]::Cur($dev)
$fmt = { param($d) "{0}x{1}@{2} fo={3}" -f $d.dmPelsWidth, $d.dmPelsHeight, $d.dmDisplayFrequency, $d.dmDisplayFixedOutput }
"orig: $(& $fmt $orig)"
$n = $orig
$n.dmPelsWidth = $W; $n.dmPelsHeight = $H; $n.dmDisplayFrequency = $Hz; $n.dmDisplayFixedOutput = $Fixed
$n.dmFields = 0x80000 -bor 0x100000 -bor 0x400000 -bor 0x20000000  # PELSWIDTH|PELSHEIGHT|DISPLAYFREQUENCY|DISPLAYFIXEDOUTPUT
$t = [DMS]::Set($dev, $n, 2)   # CDS_TEST
"test rc=$t"
if ($t -ne 0) { "mode rejected, nothing changed"; return }
$r = [DMS]::Set($dev, $n, $(if ($Persist) { 1 } else { 0 }))   # 1 = CDS_UPDATEREGISTRY
"$(Get-Date -Format HH:mm:ss.fff) applied rc=$r now: $(& $fmt ([DMS]::Cur($dev)))"
if ($Keep) { return }
Start-Sleep -Seconds $Hold
$orig.dmFields = 0x80000 -bor 0x100000 -bor 0x400000 -bor 0x20000000
$rr = [DMS]::Set($dev, $orig, 0)
"$(Get-Date -Format HH:mm:ss.fff) reverted rc=$rr now: $(& $fmt ([DMS]::Cur($dev)))"

