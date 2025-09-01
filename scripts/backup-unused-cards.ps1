param(
  [switch]$IncludeUpdateCardAssets = $true,   # keep TasksAssignedToUserUpdated.json by default
  [switch]$DryRun = $true                     # dry-run by default
)

$ErrorActionPreference = "Stop"

# Determine project root (parent of the scripts folder)
$projectRoot = Split-Path -Parent $PSScriptRoot
$resources = Join-Path $projectRoot "resources"
$preDir   = Join-Path $resources "pre-meeting-cards"
$postDir  = Join-Path $resources "post-meeting-cards"

if (-not (Test-Path $resources)) { throw "Resources folder not found: $resources" }

# Keep lists (required by the two APIs)
$keep = @(
  (Join-Path $postDir "TasksAssignedToUser.json"),
  (Join-Path $resources "task_assigning_card_template.json"),
  (Join-Path $preDir "sample-exm.json")
)

$optionalKeep = @()
if ($IncludeUpdateCardAssets) {
  $optionalKeep += (Join-Path $postDir "TasksAssignedToUserUpdated.json")
}

# Collect candidates (all JSONs under pre/post + selected root jsons)
$candidates = @()
if (Test-Path $preDir)  { $candidates += Get-ChildItem $preDir  -Filter *.json -File -Recurse -ErrorAction SilentlyContinue }
if (Test-Path $postDir) { $candidates += Get-ChildItem $postDir -Filter *.json -File -Recurse -ErrorAction SilentlyContinue }

# Additional resource-root candidates that are sample/templates
$rootCandidates = @(
  (Join-Path $resources "sampleData-taskAssigned.json")
)
$candidates += $rootCandidates | Where-Object { Test-Path $_ }

# Filter out keep
$keepSet = @{}
($keep + $optionalKeep) | ForEach-Object { $keepSet[$_] = $true }
$toMove = $candidates | Where-Object { -not $keepSet.ContainsKey($_.FullName) }

# Safety: verify no references in code to any file we plan to move
$codePaths = @(
  (Join-Path $projectRoot "api\message_service.py"),
  (Join-Path $projectRoot "api\cards")
)
$badRefs = @()

foreach ($f in $toMove) {
  $name = Split-Path $f.FullName -Leaf
  $hits = Select-String -Path $codePaths -Pattern ([regex]::Escape($name)) -ErrorAction SilentlyContinue
  if ($hits) {
    $badRefs += [PSCustomObject]@{ File=$f.FullName; ReferencedIn=($hits.Path | Select-Object -Unique) }
  }
}

if ($badRefs.Count -gt 0) {
  Write-Host "[ABORT] Found references to files slated for move:" -ForegroundColor Yellow
  $badRefs | Format-Table -AutoSize
  exit 2
}

# Show plan
Write-Host "Keeping:" -ForegroundColor Green
($keep + $optionalKeep) | ForEach-Object { Write-Host "  $_" }

Write-Host "Will move to backup:" -ForegroundColor Cyan
$toMove | ForEach-Object { Write-Host "  $($_.FullName)" }

if ($DryRun) {
  Write-Host "[DRY RUN] No files moved. Re-run with -DryRun:\$false to execute." -ForegroundColor Yellow
  exit 0
}

# Execute move to backup
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backupDir = Join-Path $resources ("_backup_" + $stamp)
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null

foreach ($f in $toMove) {
  $rel = Resolve-Path $f.FullName | ForEach-Object { $_.Path.Replace($resources + '\\', '') }
  $dest = Join-Path $backupDir $rel
  New-Item -ItemType Directory -Path (Split-Path $dest -Parent) -Force | Out-Null
  Move-Item -Path $f.FullName -Destination $dest -Force
}
Write-Host "Moved $($toMove.Count) files to $backupDir" -ForegroundColor Green
