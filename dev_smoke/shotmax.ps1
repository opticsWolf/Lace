# Maximize a process window (for unobstructed screenshots) + capture it.
param([string]$Proc = "dock_demo", [string]$Out = "shot.png")
Add-Type -AssemblyName System.Windows.Forms, System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;
using System.Text;
public class WM {
    public delegate bool Cb(IntPtr h, IntPtr l);
    [DllImport("user32.dll")] public static extern bool EnumWindows(Cb c, IntPtr l);
    [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int cmd);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
    public struct RECT { public int Left, Top, Right, Bottom; }
}
"@
$procs = Get-Process -Name $Proc -ErrorAction SilentlyContinue
if (-not $procs) { Write-Error "process $Proc not running"; exit 1 }
$pids = @($procs | ForEach-Object { $_.Id })
$script:hwnd = [IntPtr]::Zero
$cb = { param($h, $l)
    if ([WM]::IsWindowVisible($h)) {
        $wpid = 0
        [void][WM]::GetWindowThreadProcessId($h, [ref]$wpid)
        if ($pids -contains $wpid) {
            $sb = New-Object Text.StringBuilder 256
            if ([WM]::GetWindowText($h, $sb, 256) -gt 0) {
                $script:hwnd = $h
                return $false
            }
        }
    }
    return $true
}
[void][WM]::EnumWindows($cb, 0)
if ($script:hwnd -eq [IntPtr]::Zero) { Write-Error "no visible window for $Proc"; exit 1 }
[void][WM]::ShowWindow($script:hwnd, 3)
[void][WM]::SetForegroundWindow($script:hwnd)
Start-Sleep -Milliseconds 800
$r = New-Object WM+RECT
[void][WM]::GetWindowRect($script:hwnd, [ref]$r)
$w = $r.Right - $r.Left
$hh = $r.Bottom - $r.Top
Write-Output ("window ${w}x${hh}")
$bmp = New-Object System.Drawing.Bitmap($w, $hh)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($r.Left, $r.Top, 0, 0, (New-Object System.Drawing.Size($w, $hh)))
$g.Dispose()
$bmp.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png)
$bmp.Dispose()
Write-Output ("saved " + $Out)
