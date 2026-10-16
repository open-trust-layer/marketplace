# Operator-only, Windows PowerShell launcher for the isolated #525 evaluator.
# Source review and inert mode are safe; active mode MUST be run manually at
# the Machine console, NEVER through remote execution tools or GitHub Actions.
# It neither starts PostgreSQL nor creates schema, auth keys, or browsers.
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$ExpectedMarketplaceSha,
    [Parameter(Mandatory = $true)][string]$ExpectedOlpSha,
    [Parameter(Mandatory = $true)][string]$OlpRoot,
    [Parameter(Mandatory = $true)][string]$PythonPath,
    [switch]$ExecuteLocalOperatorProbe
)

$ErrorActionPreference = 'Stop'
$credentialFile = 'D:\MarketplaceEvaluatorFresh\secrets\marketplace-evaluator.dpapi'
$expectedDataDirectory = 'D:\MarketplaceEvaluatorFresh\pgdata'
$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$secretVariable = 'MARKETPLACE_EVALUATOR_DB_PASSWORD'
$secretPointer = [IntPtr]::Zero
$hadSecretVariable = $false

function Fail([string]$Code) {
    Write-Output ('status=BLOCKED code=' + $Code)
    exit 1
}

function AssertCleanExactGit([string]$Root, [string]$Expected) {
    if ($Expected -cnotmatch '^[0-9a-f]{40}$') { Fail 'EXPECTED_SHA_INVALID' }
    if (-not (Test-Path -LiteralPath $Root -PathType Container)) {
        Fail 'SOURCE_ROOT_UNAVAILABLE'
    }
    $head = & git --no-optional-locks -c core.fsmonitor=false -C $Root rev-parse HEAD 2>$null
    if ($LASTEXITCODE -ne 0 -or $head.Trim() -cne $Expected) {
        Fail 'SOURCE_REVISION_MISMATCH'
    }
    $status = & git --no-optional-locks -c core.fsmonitor=false -C $Root status --porcelain=v1 --untracked-files=all 2>$null
    if ($LASTEXITCODE -ne 0 -or -not [string]::IsNullOrEmpty(($status -join ''))) {
        Fail 'SOURCE_TREE_UNVERIFIED'
    }
}

try {
    AssertCleanExactGit $repoRoot $ExpectedMarketplaceSha
    AssertCleanExactGit $OlpRoot $ExpectedOlpSha
    if (-not (Test-Path -LiteralPath $PythonPath -PathType Leaf)) {
        Fail 'EVALUATOR_PYTHON_UNAVAILABLE'
    }

    if (-not $ExecuteLocalOperatorProbe) {
        Write-Output 'status=OPERATOR_PROBE_INERT_READY credential_opened=false postgres_connection_invoked=false server_invoked=false browser_invoked=false'
        exit 0
    }

    if (-not [Environment]::UserInteractive) { Fail 'LOCAL_INTERACTIVE_OPERATOR_REQUIRED' }
    if (-not (Test-Path -LiteralPath $credentialFile -PathType Leaf)) {
        Fail 'OPERATOR_CREDENTIAL_FILE_UNAVAILABLE'
    }
    if (Test-Path ('Env:' + $secretVariable)) {
        Fail 'EXISTING_CREDENTIAL_ENVIRONMENT'
    }

    # Recheck only the isolated IPv4 localhost listener, not Johnny5's 5432.
    $listener = @(Get-NetTCPConnection -State Listen -LocalAddress '127.0.0.1' -LocalPort 15432 -ErrorAction SilentlyContinue)
    if ($listener.Count -ne 1) { Fail 'ISOLATED_POSTGRES_LISTENER_UNAVAILABLE' }
    $server = Get-CimInstance Win32_Process -Filter ('ProcessId=' + $listener[0].OwningProcess) -ErrorAction Stop
    if ($null -eq $server -or $server.Name -ne 'postgres.exe' -or
        $server.CommandLine -notlike ('*' + $expectedDataDirectory + '*')) {
        Fail 'ISOLATED_POSTGRES_PROCESS_UNVERIFIED'
    }

    Write-Host 'This performs ONE restricted, read-only SQL identity check against 127.0.0.1:15432.'
    Write-Host 'It must be run locally by the Windows account that owns the DPAPI credential.'
    $confirmation = Read-Host 'Type RUN LOCAL READONLY PROBE to proceed'
    if ($confirmation -cne 'RUN LOCAL READONLY PROBE') {
        Fail 'OPERATOR_CONFIRMATION_REQUIRED'
    }

    # The existing file was created using PowerShell ConvertFrom-SecureString,
    # encrypted to the original Windows user. Never print plaintext or errors.
    $credentialItem = Get-Item -LiteralPath $credentialFile -Force
    if (($credentialItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0 -or
        $credentialItem.Length -gt 4096 -or $credentialItem.Length -lt 100) {
        Fail 'OPERATOR_CREDENTIAL_FILE_INVALID'
    }
    $ciphertext = (Get-Content -LiteralPath $credentialFile -Raw).Trim()
    $protectedPassword = ConvertTo-SecureString -String $ciphertext -ErrorAction Stop
    $secretPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($protectedPassword)
    $password = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($secretPointer)
    if ([string]::IsNullOrEmpty($password) -or $password.Length -lt 30 -or $password.Length -gt 4096) {
        Fail 'OPERATOR_CREDENTIAL_UNAVAILABLE'
    }
    $env:MARKETPLACE_EVALUATOR_DB_PASSWORD = $password
    Remove-Variable password,ciphertext,protectedPassword -ErrorAction SilentlyContinue

    Push-Location -LiteralPath $repoRoot
    try {
        & $PythonPath -B -m tools.marketplace_evaluator_operator_db_probe --execute-operator-probe EXECUTE_MARKETPLACE_EVALUATOR_LOCAL_DB_PROBE_V1
        $probeExit = $LASTEXITCODE
    } finally {
        Pop-Location
    }
    if ($probeExit -ne 0) { exit 1 }
    exit 0
} catch {
    # Never serialize exceptions: they may include credential or machine context.
    Write-Output 'status=BLOCKED code=LOCAL_OPERATOR_PROBE_FAILED'
    exit 1
} finally {
    Remove-Item ('Env:' + $secretVariable) -ErrorAction SilentlyContinue
    if ($secretPointer -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($secretPointer)
    }
    Remove-Variable password,ciphertext,protectedPassword -ErrorAction SilentlyContinue
}
