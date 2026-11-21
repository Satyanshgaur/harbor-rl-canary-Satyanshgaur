# Run log
- 2026-11-21 12:49 nop    -> 0.000 (jobs/2026-11-21__12-49-30)
- 2026-11-21 12:50 oracle -> 1.000 (jobs/2026-11-21__12-50-00)
- 2026-11-21 12:54 baseline attempt -> 3 exceptions (FIREWORKS_API_KEY not set in shell; 0 LLM calls); moved to ~/harbor-failed-jobs
- 2026-11-21 13:00 calibration run 0 (offset-sign Bug 3) -> 3/3 pass, 1.000 (jobs/2026-11-21__12-59-58). All 3 agents spotted every bug by reading the file; only tested the example. Too easy.
- 2026-11-21 13:27 RUN 1 BASELINE (Bug 3 v2) -> 0/3 (jobs/2026-11-21__13-27-19). All 3: case1+2 PASS, case3 FAIL (valid_count 3). All claimed fromisoformat cannot handle Z (false on 3.12), added Z handling, tested only the instruction example; final scripts identical on 26 edge cases (all accept lenient timestamp forms).
