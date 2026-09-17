Add-Type @"
using System;
using System.Runtime.InteropServices;
using System.Text;
public class EW {
    public delegate bool Cb(IntPtr h, IntPtr l);
    [DllImport("user32.dll")] public static extern bool EnumWindows(Cb c, IntPtr l);
    [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
}
"@
$titles = @()
$cb = { param($h, $l)
    if ([EW]::IsWindowVisible($h)) {
        $sb = New-Object Text.StringBuilder 256
        if ([EW]::GetWindowText($h, $sb, 256) -gt 0) {
            $wpid = 0
            [void][EW]::GetWindowThreadProcessId($h, [ref]$wpid)
            $script:titles += ("$wpid :: " + $sb.ToString())
        }
    }
    return $true
}
[void][EW]::EnumWindows($cb, 0)
$titles | Select-Object
Write-Output ("total visible: " + $titles.Count)
