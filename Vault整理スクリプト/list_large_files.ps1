param(
    [string]$Path = (Resolve-Path "$PSScriptRoot\..\.." ).Path,  # shared/Vault整理スクリプト → shared → Colours
    [int]$Top = 20
)

Get-ChildItem -Path $Path -Filter "*.md" -Recurse |
    Select-Object @{N='Size(KB)';E={[math]::Round($_.Length / 1KB, 1)}},
                  @{N='Path';E={$_.FullName.Replace($Path, '').TrimStart('\')}} |
    Sort-Object 'Size(KB)' -Descending |
    Select-Object -First $Top |
    Format-Table -AutoSize
