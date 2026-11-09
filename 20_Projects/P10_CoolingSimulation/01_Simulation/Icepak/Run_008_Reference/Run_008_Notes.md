# Run_008_MeshGlobal025

## Date
2026-11-04

## Purpose
One-factor sensitivity against Run_001, to locate the difference from the paper. Not a tuning run.

## Variables
Global mesh only: max cell 1 to 0.25 mm; die-region mesh as Run_001.
MESH_MAX = (0.25, 0.25, 0.25)

## Assumptions
Everything else as Run_001.

## Key Results
GPU peak 66.55 C, min 35.54 C; HBM die peak base 56.20; D01..D12 55.75 54.57 53.42 52.25 51.07 49.85 48.59 47.26 45.88 44.42 42.90 41.87 C. 2,269,424 cells; residual 2.80e-13 at iter 4; elapsed 5 min 47 s; Q out lid 564.17 + laminate 9.83 = 574.00 W. Change from Run_007: GPU peak +0.36 C (below the 0.5 C criterion), HBM base +0.79 C.

## Comments
Full table: ../../../Documents/sensitivity_summary.txt
