<#
  Installa (o rimuove) i sottotitoli italiani di Phantasmagoria per ScummVM.
  Uso:  .\install.ps1 [-GamePath <cartella del gioco>] [-Uninstall]
  Senza -GamePath cerca il gioco nelle librerie Steam.
#>
param(
    [string]$GamePath,
    [switch]$Uninstall
)
$ErrorActionPreference = 'Stop'

function Find-DataDir([string]$root) {
    # Accetta la cartella del gioco o direttamente quella con VMD\ e ROBOT\ (Phant)
    foreach ($c in @($root, (Join-Path $root 'Phant'))) {
        if ((Test-Path (Join-Path $c 'VMD')) -and (Test-Path (Join-Path $c 'ROBOT')) -and (Test-Path (Join-Path $c 'RESOURCE.AUD'))) {
            return (Resolve-Path $c).Path
        }
    }
    return $null
}

function Find-SteamGame {
    $steam = (Get-ItemProperty 'HKCU:\Software\Valve\Steam' -ErrorAction SilentlyContinue).SteamPath
    if (-not $steam) { return $null }
    $libs = @($steam)
    $vdf = Join-Path $steam 'steamapps\libraryfolders.vdf'
    if (Test-Path $vdf) {
        $libs += Select-String -Path $vdf -Pattern '"path"\s+"([^"]+)"' | ForEach-Object { $_.Matches[0].Groups[1].Value -replace '\\\\', '\' }
    }
    foreach ($lib in $libs) {
        $d = Find-DataDir (Join-Path $lib 'steamapps\common\Phantasmagoria')
        if ($d) { return $d }
    }
    return $null
}

$game = if ($GamePath) { Find-DataDir $GamePath } else { Find-SteamGame }
if (-not $game) {
    $GamePath = Read-Host 'Gioco non trovato. Incolla il percorso della cartella di Phantasmagoria'
    $game = Find-DataDir $GamePath.Trim('"')
}
if (-not $game) { throw "Cartelle VMD\ROBOT\RESOURCE.AUD non trovate in '$GamePath'." }

# sottocartella di srt\  ->  destinazione nel gioco
$targets = @{ 'VMD' = (Join-Path $game 'VMD'); 'ROBOT' = (Join-Path $game 'ROBOT'); 'AUD' = $game }
$n = 0
foreach ($sub in $targets.Keys) {
    $files = Get-ChildItem (Join-Path $PSScriptRoot "srt\$sub") -Filter '*.srt'
    if ($Uninstall) {
        foreach ($f in $files) {
            $t = Join-Path $targets[$sub] $f.Name
            if (Test-Path $t) { Remove-Item $t; $n++ }
        }
    } else {
        Copy-Item $files.FullName -Destination $targets[$sub] -Force
        $n += $files.Count
    }
}

if ($Uninstall) {
    Write-Host "Rimossi $n sottotitoli da $game"
} else {
    Write-Host "Installati $n sottotitoli in $game"
    Write-Host 'Filmati VMD: funzionano con ScummVM normale. Personaggi e teschio: serve lo ScummVM con la patch (vedi README).'
}
