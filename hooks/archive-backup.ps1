# PreToolUse hook: back up a file before Edit/Write/NotebookEdit modifies it.
# Reads the hook JSON from stdin, copies the current on-disk version of the
# target file into a central, versioned archive. Never blocks an edit: any
# failure (or a brand-new file that doesn't exist yet) just exits 0.
#
# Archive layout: %USERPROFILE%\.claude\_archive\<drive>\<original\path>\<timestamp>_<name>
# Each edit creates a new timestamped copy, so prior versions are never overwritten.

try {
    $raw = [Console]::In.ReadToEnd()
    if (-not $raw) { exit 0 }

    $j = $raw | ConvertFrom-Json
    $f = $j.tool_input.file_path
    if (-not $f) { exit 0 }

    # New file (Write creating something that doesn't exist yet) -> nothing to back up.
    if (-not (Test-Path -LiteralPath $f -PathType Leaf)) { exit 0 }

    $full = (Resolve-Path -LiteralPath $f).Path

    $archiveRoot = Join-Path $env:USERPROFILE '.claude\_archive'

    # Mirror the original path under the archive: "C:\a\b.txt" -> "C\a\b.txt"
    $rel = ($full -replace '^([A-Za-z]):', '$1').TrimStart('\')
    $destDir = Join-Path $archiveRoot (Split-Path $rel -Parent)
    New-Item -ItemType Directory -Force -Path $destDir | Out-Null

    $ts   = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
    $leaf = Split-Path $full -Leaf
    $dest = Join-Path $destDir ("${ts}_${leaf}")

    Copy-Item -LiteralPath $full -Destination $dest -Force
}
catch {
    # Backup is best-effort; never interfere with the edit itself.
}
exit 0
