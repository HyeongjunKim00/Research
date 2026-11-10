# run_next.ps1 — Re-validate corrected power map (NVLink removed, HBM PHY kept).
# Works under the repo Icepak folder; outputs to Icepak\Runs\Run_XXX.
#   Run_012_Lidded_BG50  : Phase 1 bracket low  (expect ~66.5 C, was 66.55)
#   Run_013_Lidded_BG30  : Phase 1 bracket high (expect ~71.1 C, was 71.08)
#   Run_014_Lidded_BG39  : Phase 2 lidded, paper-anchored (expect ~69.1 C)
#   Run_015_Lidless_BG39 : Phase 2 lidless (LIDLESS, HTC on TIM top), same BG
# Power map corrected 2026-11-10: edge I/O is GPU-side HBM PHY on the HBM-facing
# (+-x) edges; the mislabeled "NVLink" and the extra top/bottom strips are gone.
# Distribution is back to GPC 16.78 W x8 / NV-HBI 27.97 W x2 / PHY 8.39 W x2, so
# results should match the earlier validated baseline within solver noise.
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

  # summary.json is made separately by analyze_results.py (numpy); the real per-object
  # data is object_temperatures.csv. Compute gpu_max / HBM base inline (analyze definition).
  $ot = "$dst\Export\object_temperatures.csv"
  if (Test-Path $ot) {
    $rows = Import-Csv $ot | Where-Object { $_.Tmax_C -ne 'nan' -and $_.Tmin_C -ne 'nan' }
    $gpu  = $rows | Where-Object { $_.group -eq 'gpu' -or $_.group -eq 'src_gpu' }
    $gmax = ($gpu | ForEach-Object { [double]$_.Tmax_C } | Measure-Object -Maximum).Maximum
    $gmin = ($gpu | ForEach-Object { [double]$_.Tmin_C } | Measure-Object -Minimum).Minimum
    $bsum = 0.0; $bn = 0
    foreach ($tag in 'L1','L2','R1','R2') {
      $bm = $rows | Where-Object { $_.name -like "HBM_${tag}_Base*" -or $_.name -like "Src_${tag}_*" } | ForEach-Object { [double]$_.Tmax_C } | Measure-Object -Maximum
      if ($bm.Count -gt 0) { $bsum += $bm.Maximum; $bn++ }
    }
    $hbm  = if ($bn) { $bsum / $bn } else { [double]::NaN }
    $mmin = ($rows | ForEach-Object { [double]$_.Tmin_C } | Measure-Object -Minimum).Minimum
    $line = ("{0}: GPU_peak={1:N2}  GPU_min={2:N2}  HBM_base={3:N2}  model_min={4:N2}" -f $name,$gmax,$gmin,$hbm,$mmin)
    Write-Host "  >>> $line"
    $line | Out-File -Encoding UTF8 "$dst\Export\summary_quick.txt"
  } else {
    Write-Host "  !! $name : no object_temperatures.csv (solve/post failed)"
    foreach ($tb in 'build_traceback.txt','solve_traceback.txt') {
      if (Test-Path "$dst\Export\$tb") { Write-Host "  -- $tb --"; Get-Content "$dst\Export\$tb" -Raw }
    }
  }
}

Stage-And-Run 'Run_012_Lidded_BG50'  '0.50' $false
Stage-And-Run 'Run_013_Lidded_BG30'  '0.30' $false
Stage-And-Run 'Run_014_Lidded_BG39'  '0.39' $false
Stage-And-Run 'Run_015_Lidless_BG39' '0.39' $true
Write-Host "===== ALL DONE $(Get-Date -Format HH:mm:ss) ====="
