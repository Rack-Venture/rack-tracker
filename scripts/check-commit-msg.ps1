param([string]$CommitMsgFile)

$ErrorActionPreference = "Stop"

$validTypes  = @('feat', 'fix', 'docs', 'style', 'refactor', 'perf', 'test', 'build', 'ci', 'chore', 'revert')
$typePattern = '^(' + ($validTypes -join '|') + '): .+ \(#\d+\)$'

$content   = Get-Content $CommitMsgFile -Raw -Encoding UTF8
$firstLine = ($content -split "`n")[0].Trim()

# Skip merge / revert / fixup commits
if ($firstLine -match '^(Merge|Revert|fixup!|squash!) ') {
    exit 0
}

if ($firstLine -notmatch $typePattern) {
    Write-Error @"
커밋 메시지 형식 오류.
현재  : $firstLine

올바른 형식 : type: 변경 내용 요약 (#이슈번호)
예시        : chore: pre-push 훅 추가 (#11)

허용 타입: $($validTypes -join ', ')
"@
    exit 1
}

Write-Host "Commit message check passed."
exit 0
