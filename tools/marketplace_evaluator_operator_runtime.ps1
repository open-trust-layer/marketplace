# Source-only helper for #525. Active mode is strictly operator-console only.
# NEVER execute through GitHub Actions, Remote Desktop Commander, agents or
# automated shells. It does not provision keys, start PostgreSQL, or deploy.
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$ExpectedMarketplaceSha,
    [Parameter(Mandatory = $true)][string]$ExpectedOlpSha,
    [Parameter(Mandatory = $true)][string]$OlpRoot,
    [Parameter(Mandatory = $true)][string]$PythonPath,
    [Parameter(Mandatory = $true)][string]$AuthenticationProvisioningDirectory,
    [switch]$ExecuteLocalOperatorRuntime
)

$ErrorActionPreference = 'Stop'
$repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$expectedDataDirectory = 'D:\MarketplaceEvaluatorFresh\pgdata'
$credentialFile = 'D:\MarketplaceEvaluatorFresh\secrets\marketplace-evaluator.dpapi'
$expectedPostgresExe = 'C:\Users\ilyav\Johnny5\runtime\postgresql-16.15\bin\postgres.exe'
$expectedPythonExe = 'D:\MarketplaceEvaluatorFresh\marketplace-sources-main-94d659bc-20261016\evaluator-venv\Scripts\python.exe'
$secretPointer = [IntPtr]::Zero
$previousPythonPath = [Environment]::GetEnvironmentVariable('PYTHONPATH', 'Process')
$hadPythonPath = (Test-Path Env:PYTHONPATH)

function Fail([string]$Code) {
    Write-Output ('status=BLOCKED code=' + $Code)
    exit 1
}

function AssertCleanExactGit([string]$Root, [string]$Expected) {
    if ($Expected -cnotmatch '^[0-9a-f]{40}$') { Fail 'EXPECTED_SHA_INVALID' }
    if (-not (Test-Path -LiteralPath $Root -PathType Container)) { Fail 'SOURCE_ROOT_UNAVAILABLE' }
    $head = & git --no-optional-locks -c core.fsmonitor=false -C $Root rev-parse HEAD 2>$null
    if ($LASTEXITCODE -ne 0 -or ($head -join '').Trim() -cne $Expected) {
        Fail 'SOURCE_REVISION_MISMATCH'
    }
    $status = & git --no-optional-locks -c core.fsmonitor=false -C $Root status --porcelain=v1 --untracked-files=all 2>$null
    if ($LASTEXITCODE -ne 0 -or -not [string]::IsNullOrEmpty(($status -join ''))) {
        Fail 'SOURCE_TREE_UNVERIFIED'
    }
}

function TestExactDataDirectory([object]$CommandLine, [string]$Expected) {
    if ($CommandLine -isnot [string] -or [string]::IsNullOrWhiteSpace($CommandLine)) {
        return $false
    }
    $normalized = $CommandLine.Replace('/', '\')
    if ([Regex]::Matches($normalized, '(?i)(?:^|\s)-D\s+').Count -ne 1) {
        return $false
    }
    $literal = [Regex]::Escape($Expected.Replace('/', '\'))
    return [Regex]::IsMatch(
        $normalized, ('(?i)(?:^|\s)-D\s+(?:"' + $literal + '"|' + $literal + ')(?=\s|$)')
    )
}

try {
    AssertCleanExactGit $repoRoot $ExpectedMarketplaceSha
    AssertCleanExactGit $OlpRoot $ExpectedOlpSha
    if (-not (Test-Path -LiteralPath $PythonPath -PathType Leaf) -or
        -not [IO.Path]::GetFullPath($PythonPath).Equals(
            $expectedPythonExe, [StringComparison]::OrdinalIgnoreCase)) {
        Fail 'REVIEWED_EVALUATOR_PYTHON_UNAVAILABLE'
    }
    if (-not (Test-Path -LiteralPath $AuthenticationProvisioningDirectory -PathType Container) -or
        -not [IO.Path]::IsPathRooted($AuthenticationProvisioningDirectory)) {
        Fail 'PROVISIONING_DIRECTORY_UNAVAILABLE'
    }
    $provisioningItem = Get-Item -LiteralPath $AuthenticationProvisioningDirectory -Force
    if (($provisioningItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
        Fail 'PROVISIONING_DIRECTORY_REPARSE_POINT'
    }
    $provisioningRoot = [IO.Path]::GetFullPath($AuthenticationProvisioningDirectory)
    foreach ($root in @($repoRoot, ([IO.Path]::GetFullPath($OlpRoot)))) {
        $prefix = $root.TrimEnd('\') + '\'
        if ($provisioningRoot.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase) -or
            $provisioningRoot.Equals($root, [StringComparison]::OrdinalIgnoreCase)) {
            Fail 'PROVISIONING_WITHIN_SOURCE_TREE'
        }
    }

    if (-not $ExecuteLocalOperatorRuntime) {
        Write-Output 'status=OPERATOR_RUNTIME_INERT_READY credential_opened=false postgres_connection_invoked=false server_invoked=false browser_invoked=false'
        exit 0
    }

    if (-not [Environment]::UserInteractive -or $env:GITHUB_ACTIONS -or $env:CI -or
        -not [Environment]::GetEnvironmentVariable('USERNAME', 'Process')) {
        Fail 'LOCAL_INTERACTIVE_OPERATOR_REQUIRED'
    }
    if ((Test-Path Env:MARKETPLACE_POSTGRES_DSN) -or
        (Test-Path Env:MARKETPLACE_EVALUATOR_DB_PASSWORD)) {
        Fail 'EXISTING_CREDENTIAL_ENVIRONMENT'
    }
    if (Test-Path Env:PYTHONHOME) { Fail 'UNREVIEWED_PYTHON_ENVIRONMENT' }
    foreach ($item in (Get-ChildItem Env:)) {
        if ($item.Name -match '^PG(?:PASSWORD|HOST|HOSTADDR|PORT|USER|DATABASE|SERVICE|SERVICEFILE|PASSFILE|OPTIONS|SSLMODE|CONNECT_TIMEOUT|TARGETSESSIONATTRS)$') {
            Fail 'AMBIGUOUS_POSTGRES_ENVIRONMENT'
        }
    }
    if (-not (Test-Path -LiteralPath $credentialFile -PathType Leaf)) {
        Fail 'OPERATOR_CREDENTIAL_FILE_UNAVAILABLE'
    }
    $fileItem = Get-Item -LiteralPath $credentialFile -Force
    if (($fileItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0 -or
        $fileItem.Length -gt 4096 -or $fileItem.Length -lt 100) {
        Fail 'OPERATOR_CREDENTIAL_FILE_INVALID'
    }

    $listeners = @(Get-NetTCPConnection -State Listen -LocalPort 15432 -ErrorAction SilentlyContinue)
    if ($listeners.Count -ne 1 -or $listeners[0].LocalAddress -cne '127.0.0.1') {
        Fail 'ISOLATED_POSTGRES_LISTENER_UNVERIFIED'
    }
    $server = Get-CimInstance Win32_Process -Filter ('ProcessId=' + $listeners[0].OwningProcess)
    if ($null -eq $server -or $server.Name -cne 'postgres.exe' -or
        -not [string]::Equals($server.ExecutablePath, $expectedPostgresExe, [StringComparison]::OrdinalIgnoreCase) -or
        -not (TestExactDataDirectory $server.CommandLine $expectedDataDirectory)) {
        Fail 'ISOLATED_POSTGRES_PROCESS_UNVERIFIED'
    }
    # The static preview must be stopped manually first. Never kill it here.
    $occupied = @(Get-NetTCPConnection -State Listen -LocalPort 18480 -ErrorAction SilentlyContinue)
    if ($occupied.Count -ne 0) { Fail 'AUTHENTICATED_LOOPBACK_PORT_OCCUPIED' }

    $env:PYTHONPATH = $repoRoot + ';' + (Join-Path $OlpRoot 'src')
    Push-Location -LiteralPath $repoRoot
    try {
        # This also independently verifies the 2-party signed lease >=1800s.
        # Browser public carriers are collected through hidden local-console
        # input, never argv, and no browser private key is touched.
        & $PythonPath -B -m tools.marketplace_evaluator_browser_handoff --authentication-provisioning-directory $provisioningRoot
        if ($LASTEXITCODE -ne 0) { Fail 'BROWSER_BINDING_NOT_VERIFIED' }

        Write-Host 'Only the isolated 127.0.0.1:15432 evaluator will be used.'
        Write-Host 'The static preview must already be stopped; seller and buyer tabs must stay open at the same origin.'
        $confirmation = Read-Host 'Type RUN AUTHENTICATED LOCAL EVALUATOR to initialize DB and start the server'
        if ($confirmation -cne 'RUN AUTHENTICATED LOCAL EVALUATOR') {
            Fail 'OPERATOR_CONFIRMATION_REQUIRED'
        }

        # DPAPI decrypts only in this original Windows user's local process.
        # The transient password env is for one restricted SQL identity probe.
        $ciphertext = (Get-Content -LiteralPath $credentialFile -Raw).Trim()
        $protectedPassword = ConvertTo-SecureString -String $ciphertext -ErrorAction Stop
        $secretPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($protectedPassword)
        $password = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($secretPointer)
        if ([string]::IsNullOrEmpty($password) -or $password.Length -lt 30 -or $password.Length -gt 4096 -or
            $password.Contains([char]0) -or $password.Contains([char]10) -or $password.Contains([char]13)) {
            Fail 'OPERATOR_CREDENTIAL_UNAVAILABLE'
        }
        Remove-Variable ciphertext,protectedPassword -ErrorAction SilentlyContinue
        $env:MARKETPLACE_EVALUATOR_DB_PASSWORD = $password
        try {
            & $PythonPath -B -m tools.marketplace_evaluator_operator_db_probe --execute-operator-probe EXECUTE_MARKETPLACE_EVALUATOR_LOCAL_DB_PROBE_V1
            if ($LASTEXITCODE -ne 0) { Fail 'ISOLATED_DATABASE_IDENTITY_FAILED' }
        } finally {
            Remove-Item Env:MARKETPLACE_EVALUATOR_DB_PASSWORD -ErrorAction SilentlyContinue
        }

        # UTF-8 percent-encoded URI password; only process-local environment,
        # no DSN in shell arguments, files, transcripts or GitHub.
        $encoded = [uri]::EscapeDataString($password)
        $dsn = 'postgresql://marketplace_evaluator:' + $encoded +
            '@127.0.0.1:15432/marketplace_evaluator?connect_timeout=6&sslmode=disable'
        if ($dsn.Length -gt 8192) { Fail 'OPERATOR_DSN_INVALID' }
        $env:MARKETPLACE_POSTGRES_DSN = $dsn
        Remove-Variable encoded,dsn,password -ErrorAction SilentlyContinue

        & $PythonPath -B -m tools.marketplace_localhost --port 18480 --execute-fulfillment-completion-localhost EXECUTE_FULFILLMENT_COMPLETION_AUTHENTICATED_MARKETPLACE_LOCALHOST_V1 --authentication-provisioning-directory $provisioningRoot
        if ($LASTEXITCODE -ne 0) { Fail 'AUTHENTICATED_RUNTIME_FAILED' }
    } finally {
        Pop-Location
    }
} catch {
    # Never serialize exception text; it may contain credentials or paths.
    Write-Output 'status=BLOCKED code=OPERATOR_RUNTIME_LAUNCH_FAILED'
    exit 1
} finally {
    Remove-Item Env:MARKETPLACE_POSTGRES_DSN -ErrorAction SilentlyContinue
    Remove-Item Env:MARKETPLACE_EVALUATOR_DB_PASSWORD -ErrorAction SilentlyContinue
    if ($hadPythonPath) {
        $env:PYTHONPATH = $previousPythonPath
    } else {
        Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
    }
    if ($secretPointer -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($secretPointer)
    }
    Remove-Variable password,encoded,dsn,ciphertext,protectedPassword -ErrorAction SilentlyContinue
}
