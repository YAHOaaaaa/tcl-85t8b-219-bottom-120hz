# Lists the display modes Windows offers on \\.\DISPLAY1 (fo = fixed output: 0 default, 1 stretch, 2 center).
param([string]$Filter = '.')
Add-Type -TypeDefinition @'
using System; using System.Runtime.InteropServices; using System.Collections.Generic;
public class DML {
  [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)] public struct DEVMODE {
    [MarshalAs(UnmanagedType.ByValTStr, SizeConst=32)] public string dmDeviceName; public short dmSpecVersion, dmDriverVersion, dmSize, dmDriverExtra; public int dmFields;
    public int dmPositionX, dmPositionY, dmDisplayOrientation, dmDisplayFixedOutput; public short dmColor, dmDuplex, dmYResolution, dmTTOption, dmCollate;
    [MarshalAs(UnmanagedType.ByValTStr, SizeConst=32)] public string dmFormName; public short dmLogPixels; public int dmBitsPerPel, dmPelsWidth, dmPelsHeight, dmDisplayFlags, dmDisplayFrequency;
    public int dmICMMethod, dmICMIntent, dmMediaType, dmDitherType, dmReserved1, dmReserved2, dmPanningWidth, dmPanningHeight; }
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern bool EnumDisplaySettingsEx(string dev, int mode, ref DEVMODE dm, int flags);
  public static List<string> All(string dev) { var r = new List<string>(); var d = new DEVMODE(); d.dmSize=(short)Marshal.SizeOf(d);
    for (int i=0; EnumDisplaySettingsEx(dev, i, ref d, 2); i++) r.Add(d.dmPelsWidth+"x"+d.dmPelsHeight+"@"+d.dmDisplayFrequency+" fo="+d.dmDisplayFixedOutput); return r; } }
'@ -ErrorAction SilentlyContinue
Add-Type -AssemblyName System.Windows.Forms
[DML]::All([System.Windows.Forms.Screen]::PrimaryScreen.DeviceName) | Sort-Object -Unique | Where-Object { $_ -match $Filter }

