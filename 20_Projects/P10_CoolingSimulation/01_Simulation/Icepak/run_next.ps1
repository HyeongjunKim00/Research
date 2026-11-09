# run_next.ps1 — Phase 2: lid vs lidless at BG=0.39 (paper-anchored).
# Works under the repo Icepak folder; outputs to Icepak\Runs\Run_XXX.
#   Run_010_Lidded_BG39  : validated baseline, background 0.39 -> expect ~69.1 C
#   Run_011_Lidless_BG39 : lid removed (LIDLESS), HTC on TIM top, same BG
$ErrorActionPreference = 'Stop'
$base = 'E:\0_DSIL_Member\Hyeongjun\Research\20_Projects\P10_CoolingSimulation\01_Simulation\Icepak'
$ref  = Join-Path $base 'Run_008_Reference'
$runs = Join-Path $base 'Runs'
$exe  = 'C:\Program Files\ANSYS Inc\v261\AnsysEM\ansysedt.exe'
$U8   = New-Object System.Text.UTF8Encoding $false
$UTF8 = [System.Text.Encoding]::UTF8
if (-not (Test-Path $exe))                   { throw "ansysedt not found: $exe" }
if (-not (Test-Path "$ref\hbm_gpu_2p5d.py")) { throw "reference not found: $ref" }

function Stage-And-Run([string]$name, [string]$bg, [bool]$lidless) {
  $dst = Join-Path $runs $name
  Write-Host "########## $name (BG=$bg lidless=$lidless) $(Get-Date -Format HH:mm:ss) ##########"
  if (Test-Path $dst) { Remove-Item $dst -Recurse -Force }
  New-Item -ItemType Directory -Path "$dst\Model","$dst\Export" | Out-Null
  foreach ($f in 'driver_1_build.py','driver_2_solve.py','driver_3_post.py',
                 'analyze_results.py','plot_results.py','hbm_gpu_2p5d.py','hbm_gpu_2p5d_geometry.csv') {
    Copy-Item "$ref\$f" "$dst\Model\$f"
  }
  $model = "$dst\Model"

  # hbm_gpu_2p5d.py : set BG and (if lidless) LIDLESS.  Read/write as UTF-8 to keep Korean comments intact.
  $h = "$model\hbm_gpu_2p5d.py"
  $t = [System.IO.File]::ReadAllText($h, $UTF8)
  $t = $t -replace 'GPU_BG_FRAC(\s*=\s*)0\.5\b', ('GPU_BG_FRAC${1}' + $bg)
  if ($lidless) { $t = $t -replace 'LIDLESS(\s*=\s*)False', 'LIDLESS${1}True' }
  [System.IO.File]::WriteAllText($h, $t, $U8)
  if ($t -notmatch ('GPU_BG_FRAC\s*=\s*' + [regex]::Escape($bg))) { throw "$name BG edit failed" }
  if ($lidless -and ($t -notmatch 'LIDLESS\s*=\s*True'))          { throw "$name LIDLESS edit failed" }

  # drivers : rewrite the whole MODEL path line to this run's Model folder
  foreach ($d in 'driver_1_build.py','driver_2_solve.py','driver_3_post.py') {
    $p = "$model\$d"
    $c = [System.IO.File]::ReadAllText($p, $UTF8)
    $c = $c -replace '(?m)^MODEL = r".*"', ('MODEL = r"' + $model + '"')
    [System.IO.File]::WriteAllText($p, $c, $U8)
  }

  foreach ($step in 'driver_1_build.py','driver_2_solve.py','driver_3_post.py') {
    Write-Host "  RUN $step $(Get-Date -Format HH:mm:ss)"
    & $exe -ng -RunScriptAndExit "$model\$step"
  }
  if (Test-Path "$dst\Export\summary.json") {
    Write-Host "  --- $name summary ---"; Get-Content "$dst\Export\summary.json" -Raw
  } else {
    Write-Host "  !! $name NO summary.json"
    if (Test-Path "$dst\Export\build_traceback.txt") { Write-Host "  -- build_traceback --"; Get-Content "$dst\Export\build_traceback.txt" -Raw }
  }
}

Stage-And-Run 'Run_010_Lidded_BG39'  '0.39' $false
Stage-And-Run 'Run_011_Lidless_BG39' '0.39' $true
Write-Host "===== ALL DONE $(Get-Date -Format HH:mm:ss) ====="
