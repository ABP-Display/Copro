param(
    [Parameter(Mandatory = $true)][string]$SecretFile,
    [string]$OutputDirectory = "",
    [int]$Keep = 7,
    [string]$PythonExecutable = "python"
)
$ErrorActionPreference = "Stop"
$projectDirectory = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
if ($Keep -lt 1) { throw "Keep doit être supérieur à zéro." }
if (-not $OutputDirectory) { $OutputDirectory = Join-Path $projectDirectory "backups" }
# Import-Clixml decrypts a SecureString only for the Windows account/machine
# that created it. The secret is never passed in command arguments or logs.
$backupSecret = Import-Clixml -LiteralPath $SecretFile
if ($backupSecret -isnot [System.Security.SecureString]) { throw "Le fichier doit contenir un SecureString exporté par Export-Clixml." }
$secretPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($backupSecret)
try {
    $env:COPRO_BACKUP_PASSPHRASE = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($secretPointer)
    Push-Location -LiteralPath $projectDirectory
    try {
        & $PythonExecutable (Join-Path $PSScriptRoot "backup.py") create --verify --keep $Keep --output-dir $OutputDirectory
        if ($LASTEXITCODE -ne 0) { throw "La sauvegarde ou sa vérification a échoué (code $LASTEXITCODE)." }
    }
    finally { Pop-Location }
}
finally {
    Remove-Item Env:COPRO_BACKUP_PASSPHRASE -ErrorAction SilentlyContinue
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($secretPointer)
    $backupSecret.Dispose()
}
