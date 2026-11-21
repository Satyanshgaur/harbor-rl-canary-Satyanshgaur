# Harbor RL Submission — Satyansh Gaur (@Satyanshgaur)

## 1. Loom Walkthrough Video
- **Video URL:** [Watch 5-Minute Walkthrough](https://www.loom.com/share/cd3df8991c14491c94c6f69481c6f602)
  *(Make sure link sharing is set to "Anyone with the link can view")*

## 2. Task & Calibration Summary
- **Bug 1 (Easy):** The argument check expects 3 command-line arguments instead of 2, so the documented command always exits with a usage error.
- **Bug 2 (Medium):** The amount regex accepts any number of decimal places, so amounts like `10.125` are counted instead of being skipped as malformed.
- **Bug 3 (Hard):** Timestamps are checked only by `datetime.fromisoformat`, which on Python 3.12 also accepts forms the spec forbids (a space instead of `T`, fractional seconds, `+0530`, basic format and more), so those malformed rows are counted.
- **Calibration Scores:** `nop` = `0.00` | `oracle` (`solve.sh`) = `1.00` | Partial `oracle` (Bug 1+2 fixed, Bug 3 broken, shown in video) = `0.50` | `hack.sh` = `0.00`
- Model note: the spec's gemini-2.5-flash returns 404 ("no longer available to new users"), and Groq's free tier caps gpt-oss-120b at 8K tokens/min (429 after 4 calls in my probe), so all terminus-2 runs used the spec's Option B model, gpt-oss-120b, via Fireworks (about $0.003–0.006 per trial). 
- Calibration note: my first Bug 3 (offset added instead of subtracted) scored 3/3 (jobs/2026-11-21__12-59-58): every agent spotted just by reading the 82-line file. I replaced it with a bug that only shows up under testing.

## 3. Ablation & RL Advantage Table (`terminus-2`, `k=3` Trials)

| Run | Change Tested | Trial 1 (Binary / Dense) | Trial 2 (Binary / Dense) | Trial 3 (Binary / Dense) | Mean Binary | Mean Dense ($\bar{R}$) | Binary Advantage ($R_1-\bar{R}, R_2-\bar{R}, R_3-\bar{R}$) | Dense Advantage ($R_1-\bar{R}, R_2-\bar{R}, R_3-\bar{R}$) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Run 1: Baseline** | Original 3-bug task | `0 / 0.50` | `0 / 0.50` | `0 / 0.50` | `0.00` | `0.50` | `0.00, 0.00, 0.00` | `0.00, 0.00, 0.00` |
| **Run 2: Ablation** | Added one malformed row (`TX7`, space instead of `T` in the timestamp) to the instruction example | `1 / 1.00` | `1 / 1.00` | `1 / 1.00` | `1.00` | `1.00` | `0.00, 0.00, 0.00` | `0.00, 0.00, 0.00` |

Binary scores come from the original runs (`jobs/2026-11-21__13-27-19` and `jobs/2026-11-21__13-46-05`). Dense scores come from re-scoring each trial's final script under the hardened dense verifier, with 3 seeds each.
The instruction.md in this repo is the Run 2 version; the Run 1 version is the commit before 27bc701 (the ablation is that single commit). Every job ID is in RUNLOG.md.

## 4. Trajectory Forensics (`trajectory.json`)
- **Where the Agent Failed in Run 1:** At step 3 of trial `qEQwgGr`, the agent wrote that `datetime.fromisoformat` "does not understand Z" and added `if value.endswith('Z'): value = value[:-1] + '+00:00'`, which is false on Python 3.12 and left the lenient parsing in place; the other two trials made the same change. The only test any trial ran was the instruction example (e.g. `python3 /app/reconcile.py /tmp/sample.csv` at step 3 of `Y8vBZpP`), which has no lenient timestamps, so all three failed case3 with `valid_count` 3.
- **Ablation Hypothesis & Result:** I expected that if the example contained one lenient timestamp, agents that run the example would see a wrong total and tighten timestamp validation. That is what happened: at step 4 of `dYHBC52` the agent saw `138.49` instead of `130.49` and added a strict timestamp regex, and all three final scripts rejected all seven lenient forms, not just the space, for 3/3.

## 5. Dense Reward & Anti-Cheat Design
- **My Dense Reward Weights (`tests/test.sh`):** Group 1 (20 points) checks well-formed rows and mostly needs the argument fix, group 2 (30) adds amounts with 3–4 decimals, and group 3 (50) adds lenient timestamps. A group pays only if its fixed fixture and all 5 random files pass, and the reward is points/100, so the hardest bug carries the most weight and the easy fix alone gives only 0.20.
- **How `solution/hack.sh` Cheated & How I Blocked It:** `hack.sh` replaced `reconcile.py` with a stub that never read the CSV and printed the `caseN.expected.json` sitting next to the input, which scored 1.00 on the naive verifier (`jobs/2026-11-21__16-24-00`). The hardened `test.sh` locks `/tests` to root, runs the candidate as `nobody` on copies in a fresh work dir with no answer files, and checks 5 random files per group against a hidden reference, so the stub prints nothing and scores 0.00 (`jobs/2026-11-21__16-47-29`).
- **Remaining Reward-Hacking Risk:** The agent is root during its run, so it could replace `python3` or edit the standard library that `reference.py` and `compare.py` also run on, or leave a root process running into verification. The fix is Harbor's environment_mode = "separate", where the verifier runs in a fresh container that only receives /app/reconcile.py.

## 6. AI Tool Workflow
- **AI Tool & Model Used:** Claude Code with Claude Opus 5.5
- **How I Avoided Prompt Leakage:** I wrote `instruction.md` myself as a description of correct behaviour only and told the AI never to edit it, so it never names the bugs, the regexes or `fromisoformat`. The bugs were planted with no hinting comments or names, and the only later change to the spec was the Run 2 example row, which shows a wrong total without saying where the bug is. I also wrote the test fixtures and their expected answers by hand, and did the RL math and trajectory reading myself. (Used Chatgpt and google for planning and learning). (Claude Code Transcript is in ai_transcripts/)
