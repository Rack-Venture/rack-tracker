param(
    [string]$RemoteName,
    [string]$RemoteUrl,
    [string]$StdinFile
)

$ErrorActionPreference = "Stop"

$protectedBranches = @('main', 'develop')
$validBranchTypes   = @('feature', 'fix', 'refactor', 'docs', 'test', 'chore', 'ci', 'perf', 'hotfix', 'release')
$branchPattern      = '^(' + ($validBranchTypes -join '|') + ')/\d+-.+$'

# 1. Block push to upstream
if ($RemoteName -eq 'upstream') {
    Write-Error @"
Push 금지: 'upstream' 에는 직접 push할 수 없습니다.
  - origin 에 push 후 PR을 통해 upstream/develop 에 병합하세요.
  - PR base 는 항상 'develop' 으로 설정하세요.
"@
    exit 1
}

# Read push refs from temp file
$lines = @()
if ($StdinFile -and (Test-Path $StdinFile)) {
    $lines = Get-Content $StdinFile | Where-Object { $_.Trim() -ne '' }
}

foreach ($line in $lines) {
    $parts = $line -split ' '
    if ($parts.Count -lt 4) { continue }

    $localSha  = $parts[1]
    $remoteRef = $parts[2]
    $remoteSha = $parts[3]

    $branch = $remoteRef -replace '^refs/heads/', ''

    # 2. Block direct push to protected branches
    if ($protectedBranches -contains $branch) {
        Write-Error @"
Push 금지: '$branch' 는 보호된 브랜치입니다.
  - feature 브랜치에서 작업 후 PR을 통해 병합하세요.
  - 직접 push는 허용되지 않습니다.
"@
        exit 1
    }

    # 3. Detect force push (remote sha exists but is not an ancestor of local sha)
    $zeroSha = '0000000000000000000000000000000000000000'
    if ($remoteSha -ne $zeroSha -and $localSha -ne $zeroSha) {
        git merge-base --is-ancestor $remoteSha $localSha 2>$null | Out-Null
        if ($LASTEXITCODE -ne 0) {
            Write-Error @"
Force push 금지: '$branch' 브랜치의 히스토리를 덮어쓸 수 없습니다.
  - --force, --force-with-lease 사용은 금지되어 있습니다.
"@
            exit 1
        }
    }

    # 4. Warn on invalid branch name format (not blocking)
    if ($localSha -ne $zeroSha -and $branch -notmatch $branchPattern) {
        Write-Warning @"
브랜치 이름 형식 권고: '$branch'
  권장 형식: type/이슈번호-설명  (예: chore/11-push-hooks)
  허용 타입: $($validBranchTypes -join ', ')
"@
    }
}

Write-Host "Push rules check passed. (remote: $RemoteName)"
exit 0
