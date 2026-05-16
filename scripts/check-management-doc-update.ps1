param(
    [switch]$Staged
)

$ErrorActionPreference = "Stop"

$managementDocPattern = '^docs/issues/[^/]+/.+\.md$'
$currentBranch = (git branch --show-current).Trim()

function Get-ChangedPaths {
    param([switch]$UseStaged)

    if ($UseStaged) {
        $output = git diff --cached --name-only --diff-filter=ACMR
        if (-not $output) {
            return @()
        }

        return @($output | Where-Object { $_ -and $_.Trim().Length -gt 0 })
    }

    $trackedChanges = git diff --name-only --diff-filter=ACMR HEAD
    $untrackedFiles = git ls-files --others --exclude-standard

    $paths = @()
    if ($trackedChanges) {
        $paths += @($trackedChanges | Where-Object { $_ -and $_.Trim().Length -gt 0 })
    }

    if ($untrackedFiles) {
        $paths += @($untrackedFiles | Where-Object { $_ -and $_.Trim().Length -gt 0 })
    }

    return @($paths | Select-Object -Unique)
}

$changedPaths = Get-ChangedPaths -UseStaged:$Staged

if ($changedPaths.Count -eq 0) {
    Write-Host "No changed files detected for management-document check."
    exit 0
}

$managementDocs = @($changedPaths | Where-Object { $_ -match $managementDocPattern })
$nonManagementDocs = @($changedPaths | Where-Object { $_ -notmatch $managementDocPattern })

if ($nonManagementDocs.Count -eq 0) {
    Write-Host "Only management documents changed."
    exit 0
}

if ($managementDocs.Count -gt 0) {
    Write-Host "Management-document check passed."
    Write-Host "Changed management document(s):"
    $managementDocs | ForEach-Object { Write-Host " - $_" }
    exit 0
}

Write-Error @"
Management-document check failed.
Changed files were found without an updated management document.

Current branch: $currentBranch
Expected management document location: docs/issues/{type}/{N}-{slug}.md

Add or update the matching management document before commit.
If this is not issue-tracked work, re-check AGENTS.md and docs/agent-workflow/documentation-rules.md before proceeding.
"@
