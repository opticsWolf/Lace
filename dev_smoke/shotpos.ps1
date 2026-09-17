# Move/size a process window, bring to front, capture its rect.
param([string]$Proc = "dock_demo", [string]$Out = "shot.png",
      [int]$X = 40, [int]$Y = 40, [int]$W = 1380, [int]$H = 860)
Add-Type -AssemblyName System.Windows.Forms, System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;
using System.Text;
public class WP {
    public delegate bool Cb(IntPtr h, IntPtr l);
    [DllImport("user32.dll")] public static extern bool EnumWindows(Cb c, IntPtr l);
    [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
    [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr h, IntPtr after, int x, int y, int cx, int cy, uint flags);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
    public struct RECT { public int Left, Top, Right, Bottom; }
}
"@
$procs = Get-Process -Name $Proc -ErrorAction SilentlyContinue
if (-not $procs) { Write-Error "process $Proc not running"; exit 1 }
$pids = @($procs | ForEach-Object { $_.Id })
$script:hwnd = [IntPtr]::Zero
$cb = { param($h, $l)
    if ([WP]::IsWindowVisible($h)) {
        $wpid = 0
        [void][WP]::GetWindowThreadProcessId($h, [ref]$wpid)
        if ($pids -contains $wpid) {
            $sb = New-Object Text.StringBuilder 256
            if ([WP]::GetWindowText($h, $sb, 256) -gt 0) {
                $script:hwnd = $h
                return $false
            }
        }
    }
    return $true
}
[void][WP]::EnumWindows($cb, 0)
if ($script:hwnd -eq [IntPtr]::Zero) { Write-Error "no visible window for $Proc"; exit 1 }
[void][WP]::SetWindowPos($script:hwnd, [IntPtr]-1, $X, $Y, $W, $H, 0x0040)
Start-Sleep -Milliseconds 300
[void][WP]::SetWindowPos($script:hwnd, [IntPtr]-2, 0, 0, 0, 0, 0x0001 -bor 0x0002)
[void][WP]::SetForegroundWindow($script:hwnd)
Start-Sleep -Milliseconds 600
$r = New-Object WP+RECT
[void][WP]::GetWindowRect($script:hwnd, [ref]$r)
$w = $r.Right - $r.Left
$hh = $r.Bottom - $r.Top
Write-Output ("window at $($r.Left),$($r.Top) ${w}x${hh}")
$bmp = New-Object System.Drawing.Bitmap($w, $hh)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($r.Left, $r.Top, 0, 0, (New-Object System.Drawing.Size($w, $hh)))
$g.Dispose()
$bmp.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png)
$bmp.Dispose()
Write-Output ("saved " + $Out)
