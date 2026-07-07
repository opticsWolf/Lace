param (
    [Parameter(Mandatory=$true)]
    [string]$Session,
    
    [Parameter(Mandatory=$true)]
    [string]$OutputFile
)

$pythonExe = "C:\Users\Frank\AppData\Local\Python\developenv\Scripts\python.exe"
if (-not (Test-Path $pythonExe)) {
    $pythonExe = "python"
}

$scriptPath = Join-Path $PSScriptRoot "capture.py"
& $pythonExe $scriptPath $Session $OutputFile
