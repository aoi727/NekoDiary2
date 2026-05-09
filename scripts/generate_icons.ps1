$ErrorActionPreference = "Stop"

Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class NativeIcon {
    [DllImport("user32.dll", CharSet = CharSet.Auto)]
    public static extern bool DestroyIcon(IntPtr handle);
}
"@

function New-Color($hex) {
    [System.Drawing.ColorTranslator]::FromHtml($hex)
}

function New-RoundRectPath {
    param(
        [float]$X,
        [float]$Y,
        [float]$Width,
        [float]$Height,
        [float]$Radius
    )

    $path = New-Object System.Drawing.Drawing2D.GraphicsPath
    $diameter = $Radius * 2
    $path.AddArc($X, $Y, $diameter, $diameter, 180, 90)
    $path.AddArc($X + $Width - $diameter, $Y, $diameter, $diameter, 270, 90)
    $path.AddArc($X + $Width - $diameter, $Y + $Height - $diameter, $diameter, $diameter, 0, 90)
    $path.AddArc($X, $Y + $Height - $diameter, $diameter, $diameter, 90, 90)
    $path.CloseFigure()
    return $path
}

function Use-GraphicsSmoothing {
    param([System.Drawing.Graphics]$Graphics)
    $Graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $Graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $Graphics.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
    $Graphics.CompositingQuality = [System.Drawing.Drawing2D.CompositingQuality]::HighQuality
    $Graphics.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit
}

function New-Canvas {
    param([int]$Size = 256)
    $bmp = New-Object System.Drawing.Bitmap $Size, $Size, ([System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
    $graphics = [System.Drawing.Graphics]::FromImage($bmp)
    Use-GraphicsSmoothing -Graphics $graphics
    $graphics.Clear([System.Drawing.Color]::Transparent)
    return @{ Bitmap = $bmp; Graphics = $graphics }
}

function Draw-Badge {
    param(
        [System.Drawing.Graphics]$Graphics,
        [string]$ColorHex
    )
    $brush = New-Object System.Drawing.SolidBrush (New-Color $ColorHex)
    $rect = New-Object System.Drawing.RectangleF 24, 24, 208, 208
    $Graphics.FillEllipse($brush, $rect)
    $brush.Dispose()
}

function Draw-RingBadge {
    param(
        [System.Drawing.Graphics]$Graphics,
        [string]$FillHex,
        [string]$BorderHex
    )
    $fill = New-Object System.Drawing.SolidBrush (New-Color $FillHex)
    $border = New-Object System.Drawing.Pen (New-Color $BorderHex), 12
    $rect = New-Object System.Drawing.RectangleF 28, 28, 200, 200
    $Graphics.FillEllipse($fill, $rect)
    $Graphics.DrawEllipse($border, $rect)
    $fill.Dispose()
    $border.Dispose()
}

function Draw-Check {
    param([System.Drawing.Graphics]$Graphics)
    $pen = New-Object System.Drawing.Pen ([System.Drawing.Color]::White), 22
    $pen.StartCap = [System.Drawing.Drawing2D.LineCap]::Round
    $pen.EndCap = [System.Drawing.Drawing2D.LineCap]::Round
    $Graphics.DrawLines($pen, @(
        (New-Object System.Drawing.PointF 72, 136),
        (New-Object System.Drawing.PointF 114, 178),
        (New-Object System.Drawing.PointF 188, 92)
    ))
    $pen.Dispose()
}

function Draw-Cross {
    param([System.Drawing.Graphics]$Graphics)
    $pen = New-Object System.Drawing.Pen ([System.Drawing.Color]::White), 20
    $pen.StartCap = [System.Drawing.Drawing2D.LineCap]::Round
    $pen.EndCap = [System.Drawing.Drawing2D.LineCap]::Round
    $Graphics.DrawLine($pen, 82, 82, 174, 174)
    $Graphics.DrawLine($pen, 174, 82, 82, 174)
    $pen.Dispose()
}

function Draw-Search {
    param([System.Drawing.Graphics]$Graphics)
    $pen = New-Object System.Drawing.Pen ([System.Drawing.Color]::White), 18
    $pen.StartCap = [System.Drawing.Drawing2D.LineCap]::Round
    $pen.EndCap = [System.Drawing.Drawing2D.LineCap]::Round
    $Graphics.DrawEllipse($pen, 64, 64, 88, 88)
    $Graphics.DrawLine($pen, 142, 142, 190, 190)
    $pen.Dispose()
}

function Draw-Home {
    param([System.Drawing.Graphics]$Graphics)
    $brush = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::White)
    $Graphics.FillPolygon($brush, @(
        (New-Object System.Drawing.PointF 56, 116),
        (New-Object System.Drawing.PointF 128, 56),
        (New-Object System.Drawing.PointF 200, 116)
    ))
    $Graphics.FillRectangle($brush, 76, 112, 104, 78)
    $cut = New-Object System.Drawing.SolidBrush (New-Color "#8ec5ff")
    $Graphics.FillRectangle($cut, 116, 138, 24, 52)
    $cut.Dispose()
    $brush.Dispose()
}

function Draw-Notebook {
    param([System.Drawing.Graphics]$Graphics)
    $cover = New-Object System.Drawing.SolidBrush (New-Color "#5d7df4")
    $page = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::White)
    $spiral = New-Object System.Drawing.SolidBrush (New-Color "#f7b2c8")
    $coverPath = New-RoundRectPath -X 48 -Y 34 -Width 160 -Height 188 -Radius 24
    $pagePath = New-RoundRectPath -X 76 -Y 54 -Width 112 -Height 148 -Radius 14
    $Graphics.FillPath($cover, $coverPath)
    $Graphics.FillPath($page, $pagePath)
    0..4 | ForEach-Object {
        $Graphics.FillEllipse($spiral, 60, 62 + ($_ * 28), 12, 12)
    }
    $linePen = New-Object System.Drawing.Pen (New-Color "#ced7ff"), 6
    foreach ($y in 92, 122, 152) {
        $Graphics.DrawLine($linePen, 92, $y, 168, $y)
    }
    $cover.Dispose()
    $page.Dispose()
    $spiral.Dispose()
    $coverPath.Dispose()
    $pagePath.Dispose()
    $linePen.Dispose()
}

function Draw-Pencil {
    param(
        [System.Drawing.Graphics]$Graphics,
        [string]$BodyHex = "#ffffff",
        [string]$AccentHex = "#f8c68c"
    )
    $Graphics.TranslateTransform(128, 128)
    $Graphics.RotateTransform(-35)
    $body = New-Object System.Drawing.SolidBrush (New-Color $BodyHex)
    $accent = New-Object System.Drawing.SolidBrush (New-Color $AccentHex)
    $tip = New-Object System.Drawing.SolidBrush (New-Color "#7a5a40")
    $lead = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::White)
    $Graphics.FillRectangle($body, -18, -68, 36, 108)
    $Graphics.FillRectangle($accent, -18, 24, 36, 26)
    $Graphics.FillPolygon($tip, @(
        (New-Object System.Drawing.PointF -18, -68),
        (New-Object System.Drawing.PointF 18, -68),
        (New-Object System.Drawing.PointF 0, -108)
    ))
    $Graphics.FillPolygon($lead, @(
        (New-Object System.Drawing.PointF -8, -84),
        (New-Object System.Drawing.PointF 8, -84),
        (New-Object System.Drawing.PointF 0, -102)
    ))
    $Graphics.ResetTransform()
    $body.Dispose()
    $accent.Dispose()
    $tip.Dispose()
    $lead.Dispose()
}

function Draw-Eraser {
    param([System.Drawing.Graphics]$Graphics)
    $Graphics.TranslateTransform(128, 128)
    $Graphics.RotateTransform(-28)
    $pink = New-Object System.Drawing.SolidBrush (New-Color "#ffb3c7")
    $white = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::White)
    $shadow = New-Object System.Drawing.Pen (New-Color "#f18ea7"), 8
    $Graphics.FillRectangle($pink, -54, -30, 64, 60)
    $Graphics.FillRectangle($white, 10, -30, 46, 60)
    $Graphics.DrawRectangle($shadow, -54, -30, 110, 60)
    $Graphics.ResetTransform()
    $pink.Dispose()
    $white.Dispose()
    $shadow.Dispose()
}

function Draw-Trash {
    param([System.Drawing.Graphics]$Graphics)
    $pen = New-Object System.Drawing.Pen ([System.Drawing.Color]::White), 14
    $pen.StartCap = [System.Drawing.Drawing2D.LineCap]::Round
    $pen.EndCap = [System.Drawing.Drawing2D.LineCap]::Round
    $pen.LineJoin = [System.Drawing.Drawing2D.LineJoin]::Round
    $Graphics.DrawLine($pen, 88, 82, 168, 82)
    $Graphics.DrawLine($pen, 104, 64, 152, 64)
    $Graphics.DrawRectangle($pen, 92, 84, 72, 96)
    foreach ($x in 110, 128, 146) {
        $Graphics.DrawLine($pen, $x, 102, $x, 162)
    }
    $pen.Dispose()
}

function Draw-Floppy {
    param([System.Drawing.Graphics]$Graphics)
    $body = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::White)
    $cut = New-Object System.Drawing.SolidBrush (New-Color "#7ea9ff")
    $label = New-Object System.Drawing.SolidBrush (New-Color "#dfe8ff")
    $path = New-RoundRectPath -X 58 -Y 50 -Width 140 -Height 156 -Radius 18
    $Graphics.FillPath($body, $path)
    $Graphics.FillRectangle($cut, 88, 64, 80, 34)
    $Graphics.FillRectangle($label, 86, 124, 84, 48)
    $slotPen = New-Object System.Drawing.Pen (New-Color "#7ea9ff"), 10
    $Graphics.DrawLine($slotPen, 96, 82, 160, 82)
    $body.Dispose()
    $cut.Dispose()
    $label.Dispose()
    $path.Dispose()
    $slotPen.Dispose()
}

function Draw-Camera {
    param([System.Drawing.Graphics]$Graphics)
    $body = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::White)
    $lens = New-Object System.Drawing.SolidBrush (New-Color "#7ea9ff")
    $accent = New-Object System.Drawing.SolidBrush (New-Color "#dbe7ff")
    $bodyPath = New-RoundRectPath -X 56 -Y 82 -Width 144 -Height 96 -Radius 22
    $Graphics.FillPath($body, $bodyPath)
    $Graphics.FillRectangle($accent, 84, 62, 44, 28)
    $Graphics.FillEllipse($lens, 96, 98, 64, 64)
    $shine = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::White)
    $Graphics.FillEllipse($shine, 114, 116, 18, 18)
    $body.Dispose()
    $lens.Dispose()
    $accent.Dispose()
    $bodyPath.Dispose()
    $shine.Dispose()
}

function Draw-SDCard {
    param([System.Drawing.Graphics]$Graphics)
    $body = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::White)
    $chip = New-Object System.Drawing.SolidBrush (New-Color "#dfe8ff")
    $points = @(
        (New-Object System.Drawing.PointF 86, 46),
        (New-Object System.Drawing.PointF 162, 46),
        (New-Object System.Drawing.PointF 190, 76),
        (New-Object System.Drawing.PointF 190, 196),
        (New-Object System.Drawing.PointF 66, 196),
        (New-Object System.Drawing.PointF 66, 76)
    )
    $Graphics.FillPolygon($body, $points)
    foreach ($x in 88, 108, 128, 148) {
        $Graphics.FillRectangle($chip, $x, 58, 10, 24)
    }
    $Graphics.FillRectangle($chip, 92, 112, 72, 46)
    $body.Dispose()
    $chip.Dispose()
}

function Draw-Gear {
    param([System.Drawing.Graphics]$Graphics)
    $Graphics.TranslateTransform(128, 128)
    $gearBrush = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::White)
    foreach ($angle in 0, 45, 90, 135) {
        $Graphics.RotateTransform($angle)
        $Graphics.FillRectangle($gearBrush, -16, -84, 32, 168)
        $Graphics.RotateTransform(-$angle)
    }
    $Graphics.FillEllipse($gearBrush, -56, -56, 112, 112)
    $hole = New-Object System.Drawing.SolidBrush (New-Color "#8e78ff")
    $Graphics.FillEllipse($hole, -24, -24, 48, 48)
    $Graphics.ResetTransform()
    $gearBrush.Dispose()
    $hole.Dispose()
}

function Draw-Plus {
    param([System.Drawing.Graphics]$Graphics)
    $pen = New-Object System.Drawing.Pen ([System.Drawing.Color]::White), 18
    $pen.StartCap = [System.Drawing.Drawing2D.LineCap]::Round
    $pen.EndCap = [System.Drawing.Drawing2D.LineCap]::Round
    $Graphics.DrawLine($pen, 128, 78, 128, 178)
    $Graphics.DrawLine($pen, 78, 128, 178, 128)
    $pen.Dispose()
}

function Draw-Underline {
    param([System.Drawing.Graphics]$Graphics)
    $pen = New-Object System.Drawing.Pen ([System.Drawing.Color]::White), 16
    $pen.StartCap = [System.Drawing.Drawing2D.LineCap]::Round
    $pen.EndCap = [System.Drawing.Drawing2D.LineCap]::Round
    $Graphics.DrawArc($pen, 72, 64, 112, 104, 15, 150)
    $Graphics.DrawLine($pen, 82, 184, 174, 184)
    $pen.Dispose()
}

function Draw-BoldGlyph {
    param([System.Drawing.Graphics]$Graphics)
    $font = New-Object System.Drawing.Font("Segoe UI", 112, [System.Drawing.FontStyle]::Bold, [System.Drawing.GraphicsUnit]::Pixel)
    $brush = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::White)
    $format = New-Object System.Drawing.StringFormat
    $format.Alignment = [System.Drawing.StringAlignment]::Center
    $format.LineAlignment = [System.Drawing.StringAlignment]::Center
    $Graphics.DrawString("B", $font, $brush, (New-Object System.Drawing.RectangleF 0, 0, 256, 256), $format)
    $font.Dispose()
    $brush.Dispose()
    $format.Dispose()
}

function Draw-Highlighter {
    param([System.Drawing.Graphics]$Graphics)
    $Graphics.TranslateTransform(128, 128)
    $Graphics.RotateTransform(-22)
    $body = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::White)
    $cap = New-Object System.Drawing.SolidBrush (New-Color "#ffc2d6")
    $tip = New-Object System.Drawing.SolidBrush (New-Color "#f48fb1")
    $Graphics.FillRectangle($cap, -22, -92, 44, 44)
    $Graphics.FillRectangle($body, -22, -48, 44, 110)
    $Graphics.FillPolygon($tip, @(
        (New-Object System.Drawing.PointF -22, 62),
        (New-Object System.Drawing.PointF 22, 62),
        (New-Object System.Drawing.PointF 0, 104)
    ))
    $Graphics.ResetTransform()
    $body.Dispose()
    $cap.Dispose()
    $tip.Dispose()
}

function Draw-BookmarkBird {
    param(
        [System.Drawing.Graphics]$Graphics,
        [string]$ColorHex
    )
    $brush = New-Object System.Drawing.SolidBrush (New-Color $ColorHex)
    $Graphics.FillEllipse($brush, 54, 70, 112, 112)
    $Graphics.FillEllipse($brush, 132, 98, 40, 40)
    $Graphics.FillPolygon($brush, @(
        (New-Object System.Drawing.PointF 112, 172),
        (New-Object System.Drawing.PointF 86, 214),
        (New-Object System.Drawing.PointF 126, 194),
        (New-Object System.Drawing.PointF 154, 216)
    ))
    $eye = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::White)
    $Graphics.FillEllipse($eye, 144, 110, 10, 10)
    $brush.Dispose()
    $eye.Dispose()
}

function Draw-AssetIcon {
    param(
        [string]$Name,
        [string]$DestinationPath
    )

    $canvas = New-Canvas
    $bmp = $canvas.Bitmap
    $g = $canvas.Graphics

    switch ($Name) {
        "check.png" { Draw-Badge $g "#6ecf95"; Draw-Check $g; break }
        "close.png" { Draw-Badge $g "#ef8b97"; Draw-Cross $g; break }
        "search.png" { Draw-Badge $g "#8cbcf8"; Draw-Search $g; break }
        "home.png" { Draw-Badge $g "#7db2ff"; Draw-Home $g; break }
        "notebook.png" { Draw-Notebook $g; break }
        "note-add.png" { Draw-Badge $g "#8e78ff"; Draw-Pencil $g "#ffffff" "#f7b37a"; break }
        "note-edit.png" { Draw-Badge $g "#6bb9d6"; Draw-Pencil $g "#ffffff" "#8ddad5"; break }
        "eraser.png" { Draw-Badge $g "#f4a9c0"; Draw-Eraser $g; break }
        "trash.png" { Draw-Badge $g "#96a7c9"; Draw-Trash $g; break }
        "backup.png" { Draw-Badge $g "#7ea9ff"; Draw-Floppy $g; break }
        "camera.png" { Draw-Badge $g "#6dbbd0"; Draw-Camera $g; break }
        "attachment.png" { Draw-Badge $g "#7392f4"; Draw-SDCard $g; break }
        "settings.png" { Draw-Badge $g "#8e78ff"; Draw-Gear $g; break }
        "plus.png" { Draw-Badge $g "#7bcaa4"; Draw-Plus $g; break }
        "underline.png" { Draw-Badge $g "#74c0a3"; Draw-Underline $g; break }
        "bold.png" { Draw-Badge $g "#6a8ff0"; Draw-BoldGlyph $g; break }
        "highlight.png" { Draw-Badge $g "#f49fbc"; Draw-Highlighter $g; break }
        "bookmark-red.png" { Draw-RingBadge $g "#ffe1e5" "#ef8b97"; Draw-BookmarkBird $g "#ef8b97"; break }
        "bookmark-green.png" { Draw-RingBadge $g "#e0f7ea" "#7bcaa4"; Draw-BookmarkBird $g "#7bcaa4"; break }
        default { throw "Unknown icon definition: $Name" }
    }

    $bmp.Save($DestinationPath, [System.Drawing.Imaging.ImageFormat]::Png)
    $g.Dispose()
    $bmp.Dispose()
}

function Save-AppIcon {
    param(
        [string]$SourcePngPath,
        [string]$DestinationIcoPath
    )
    $bitmap = [System.Drawing.Bitmap]::FromFile($SourcePngPath)
    $handle = $bitmap.GetHicon()
    $icon = [System.Drawing.Icon]::FromHandle($handle)
    $stream = [System.IO.File]::Open($DestinationIcoPath, [System.IO.FileMode]::Create)
    try {
        $icon.Save($stream)
    }
    finally {
        $stream.Dispose()
        $icon.Dispose()
        [NativeIcon]::DestroyIcon($handle) | Out-Null
        $bitmap.Dispose()
    }
}

$root = Split-Path -Parent $PSScriptRoot
$sozai = Join-Path $root "Sozai"

$iconNames = @(
    "attachment.png",
    "backup.png",
    "bold.png",
    "bookmark-green.png",
    "bookmark-red.png",
    "camera.png",
    "check.png",
    "close.png",
    "eraser.png",
    "highlight.png",
    "home.png",
    "notebook.png",
    "note-add.png",
    "note-edit.png",
    "plus.png",
    "search.png",
    "settings.png",
    "trash.png",
    "underline.png"
)

foreach ($iconName in $iconNames) {
    Draw-AssetIcon -Name $iconName -DestinationPath (Join-Path $sozai $iconName)
}

Save-AppIcon -SourcePngPath (Join-Path $sozai "notebook.png") -DestinationIcoPath (Join-Path $root "app-icon.ico")
Write-Host "Generated original icon assets in $sozai and app-icon.ico"
