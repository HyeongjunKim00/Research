# run_next.ps1 — Phase 2: lid vs lidless at BG=0.39 (paper-anchored).
# Works under the repo Icepak folder; outputs to Icepak\Runs\Run_XXX.
#   Run_010_Lidded_BG39  : validated baseline, background 0.39 -> expect ~69.1 C
#   Run_011_Lidless_BG39 : lid removed (LIDLESS), HTC on TIM top, same BG
# NOTE: ansysedt -ng returns immediately (non-blocking) under a .bat, so we
#       launch each driver then WAIT for its done-file and for the .aedt lock
#       to release before the next step. Otherwise solve/post race the build.
$ErrorActionPreference = 'Stop'
$base = 'E:\0_DSIL_Member\Hyeongjun\Research\20_Projects\P10_CoolingSimulation\01_Simulation\Icepak'
$ref  = Join-Path $base 'Run_008_Reference'
$runs = Join-Path $base 'Runs'
$exe  = 'C:\Program Files\ANSYS Inc\v261\AnsysEM\ansysedt.exe'
$aedtname = '20261104_HBM2p5D_MeshGlobal025.aedt'
$U8   = New-Object System.Text.UTF8Encoding $false
$UTF8 = [System.Text.Encoding]::UTF8
if (-not (Test-Path $exe))                   { throw "ansysedt not found: $exe" }
if (-not (Test-Path "$ref\hbm_gpu_2p5d.py")) { throw "reference not found: $ref" }

function Wait-Driver([string]$scriptpath, [string]$donefile, [string]$lock, [int]$maxMin) {
  if (Test-Path $donefile) { Remove-Item $donefile -Force }
  Start-Process -FilePath $exe -ArgumentList '-ng','-RunScriptAndExit',"$scriptpath" -NoNewWindow | Out-Null
  $deadline = (Get-Date).AddMinutes($maxMin)
  while (-not (Test-Path $donefile)) {
    Start-Sleep -Seconds 3
    if ((Get-Date) -gt $deadline) { Write-Host "    TIMEOUT waiting for $(Split-Path $donefile -Leaf)"; return }
  }
  # let AEDT save and release the project lock before the next step opens it
  $t2 = (Get-Date).AddMinutes(3)
  while ((Test-Path $lock) -and ((Get-Date) -lt $t2)) { Start-Sleep -Seconds 2 }
  Start-Sleep -Seconds 2
}

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

  # hbm_gpu_2p5d.py : set BG and (if lidless) LIDLESS.  UTF-8 I/O keeps Korean comments intact.
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

  $lock = "$model\$aedtname.lock"
  Write-Host "  BUILD $(Get-Date -Format HH:mm:ss)"; Wait-Driver "$model\driver_1_build.py" "$dst\Export\build_done.txt" $lock 20
  Write-Host "  SOLVE $(Get-Date -Format HH:mm:ss)"; Wait-Driver "$model\driver_2_solve.py" "$dst\Export\solve_done.txt" $lock 30
  Write-Host "  POST  $(Get-Date -Format HH:mm:ss)"; Wait-Driver "$model\driver_3_post.py"  "$dst\Export\post_done.txt"  $lock 20

  if (Test-Path "$dst\Export\summary.json") {
    Write-Host "  --- $name summary ---"; Get-Content "$dst\Export\summary.json" -Raw
  } else {
    Write-Host "  !! $name NO summary.json"
    foreach ($tb in 'build_traceback.txt','solve_traceback.txt') {
      if (Test-Path "$dst\Export\$tb") { Write-Host "  -- $tb --"; Get-Content "$dst\Export\$tb" -Raw }
    }
  }
}

Stage-And-Run 'Run_010_Lidded_BG39'  '0.39' $false
Stage-And-Run 'Run_011_Lidless_BG39' '0.39' $true
Write-Host "===== ALL DONE $(Get-Date -Format HH:mm:ss) ====="
