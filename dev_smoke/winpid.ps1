Add-Type @"
using System;
using System.Runtime.InteropServices;
using System.Text;
public class PW {
    public delegate bool Cb(IntPtr h, IntPtr l);
    [DllImport("user32.dll")] public static extern bool EnumWindows(Cb c, IntPtr l);
    [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
}
"@
$want = 31556
$found = @()
$cb = { param($h, $l)
    $wpid = 0
    [void][PW]::GetWindowThreadProcessId($h, [ref]$wpid)
    if ($wpid -eq $want) {
        $sb = New-Object Text.StringBuilder 256
        [void][PW]::GetWindowText($h, $sb, 256)
        $vis = [PW]::IsWindowVisible($h)
        $script:found += ("vis=" + $vis + " :: " + $sb.ToString())
    }
    return $true
}
[void][PW]::EnumWindows($cb, 0)
if ($found.Count -eq 0) { Write-Output "NO WINDOWS for pid $want" } else { $found | Select-Object }
$proc = Get-Process -Id $want -ErrorAction SilentlyContinue
if ($proc) { Write-Output ("alive, handle=" + $proc.MainWindowHandle + " title=" + $proc.MainWindowTitle) }
else { Write-Output "process gone" }
