# Crop + upscale a region for close inspection.
param([string]$In = "shot12.png", [string]$Out = "crop.png",
      [int]$X = 60, [int]$Y = 60, [int]$W = 1340, [int]$H = 160, [int]$Zoom = 1)
Add-Type -AssemblyName System.Drawing
$src = [System.Drawing.Bitmap]::FromFile((Join-Path (Get-Location) $In))
$crop = $src.Clone([System.Drawing.Rectangle]::FromLTRB($X, $Y, $X + $W, $Y + $H),
                   $src.PixelFormat)
if ($Zoom -gt 1) {
    $big = New-Object System.Drawing.Bitmap($W * $Zoom, $H * $Zoom)
    $g = [System.Drawing.Graphics]::FromImage($big)
    $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::NearestNeighbor
    $g.DrawImage($crop, 0, 0, $W * $Zoom, $H * $Zoom)
    $g.Dispose()
    $crop.Dispose()
    $crop = $big
}
$crop.Save((Join-Path (Get-Location) $Out), [System.Drawing.Imaging.ImageFormat]::Png)
$crop.Dispose()
$src.Dispose()
Write-Output ("saved " + $Out)
