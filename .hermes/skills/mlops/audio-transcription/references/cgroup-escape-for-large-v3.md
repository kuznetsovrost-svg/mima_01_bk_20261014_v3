# cgroup Escape for large-v3 Whisper on Hermes Workers

This is a **recovery recipe** for a specific failure mode. Reach for it when you see the symptom; otherwise use the default `transcribe_single.py` invocation.

## Symptom

A `large-v3` Whisper transcription job (with `--max-memory-gb 6.0+`) dies in the first 1–3 minutes with one of:

1. **Python RuntimeError, exit code 1**:
   ```
   File ".../faster_whisper/transcribe.py", line 1400, in encode
       return self.model.encode(features, to_cpu=to_cpu)
   RuntimeError: mkl_malloc: failed to allocate memory
   ```

2. **Kernel OOM kill, exit code -9** (silent — no Python traceback, just the bash wrapper dies).

**Confirm via `dmesg`**:
```bash
dmesg | grep -E "oom|hermes-worker-proc" | tail -10
```
Look for: `oom-kill:constraint=CONSTRAINT_MEMCG` and the cgroup path `.../hermes-worker-proc_*.scope`.

## Why it happens

On this environment, child processes spawned via `terminal(background=true)` are placed in a cgroup with a hard memory limit of exactly `4194304 KB = 4 GB` (visible in `dmesg` as `limit 4194304kB`). `medium` fits under this cap (peaks ~3.8 GB) so it works. `large-v3` with `--max-memory-gb ≥ 6.0` does not — its KV-cache grows with audio and crosses the cap around the 1-2 min mark.

The `--max-memory-gb` flag inside `transcribe_single.py` uses `resource.setrlimit(RLIMIT_AS, ...)` — that sets a **process-level** limit, but the cgroup limit is **kernel-enforced** and wins.

## Fix: run in a custom cgroup

Before launching Python, move the bash wrapper into a cgroup with a higher `memory.max`. The Python child inherits the new (larger) limit.

### One-liner recipe (works for any large-v3 run)

```bash
CGROUP="/sys/fs/cgroup/hermes_whisper_xlarge"
mkdir -p "$CGROUP"
echo 10737418240 > "$CGROUP/memory.max"   # 10 GB
echo $$ > "$CGROUP/cgroup.procs"          # move THIS shell

# Now run whisper — it inherits the 10 GB cap
python3 /root/.hermes/skills/mlops/audio-transcription/scripts/transcribe_single.py \
    INPUT.mp4 --output ./out --model large-v3 --beam-size 5 --max-memory-gb 9.5 \
    --prompt /root/.hermes/skills/mlops/audio-transcription/templates/initial_prompts/<topic>.txt \
    --hotwords "<topic terms>"
```

### Wrapped as a script

The skill ships `scripts/run_whisper_xlarge.sh` which does the cgroup setup and forwards all args. Use it as the production entry point for `large-v3` on Hermes workers:

```bash
bash /root/.hermes/skills/mlops/audio-transcription/scripts/run_whisper_xlarge.sh \
    INPUT.mp4 ./out \
    --model large-v3 --beam-size 5 \
    --prompt ... --hotwords ...
```

## Verified results

| Lecture | Audio | Model | Cgroup | Wall time | Words | Words/min | Exit |
|---|---|---|---|---|---|---|---|
| 1.1 | 17.8 min WAV | large-v3 | (no cgroup) | 44 min | 2031 | 114 | ✅ 0 |
| 1.2 | 14.7 min MP4 H.265 | large-v3 | **custom 10 GB** | 38 min | 1169 | 80 | ✅ 0 |
| 1.3 | 8.97 min MP4 H.265 | large-v3 | **custom 10 GB** | 14 min | 418 | 47 | ✅ 0 |
| 1.4 | 17.5 min MP4 H.265 | large-v3 | **custom 10 GB** | 32 min | 1456 | 83 | ✅ 0 |
| 1.2.1 | 7.7 min MP4 H.265 | large-v3 | **custom 10 GB** | 16 min | 839 | 109 | ✅ 0 |
| 1.2.2 | 17.0 min MP4 H.265 | large-v3 | **custom 10 GB** | 37 min | 2200 | 129 | ✅ 0 |
| 1.2.3 | 17.9 min MP4 H.265 | large-v3 | **custom 10 GB** | 45 min | 2382 | 133 | ✅ 0 |
| 1.2.4 | 11.3 min MP4 H.265 | large-v3 | **custom 10 GB** | 26 min | 1111 | 98 | ✅ 0 |
| 1.2.5 | 19.5 min MP4 H.265 | large-v3 | **custom 10 GB** | 42 min | 2508 | 129 | ✅ 0 |
| 1.2.6 | 6.0 min MP4 H.265 | large-v3 | **custom 10 GB** | 12 min | 739 | 123 | ✅ 0 |
| 1.2.7 | 7.6 min MP4 H.265 | large-v3 | **custom 10 GB** | 15 min | 876 | 115 | ✅ 0 |
| 1.3.1 | 8.6 min MP4 H.265 | large-v3 | **custom 10 GB** | 18.5 min | 985 | 115 | ✅ 0 |
| 1.3.2 | 4.3 min MP4 H.265 | large-v3 | **custom 10 GB** | 8.6 min | 569 | 132 | ✅ 0 |
| 1.3.3 | 20.5 min MP4 H.265 | large-v3 | **custom 10 GB** | 54 min | 1613 | 79 | ✅ 0 |
| 1.3.4 | 9.2 min MP4 H.265 | large-v3 | **custom 10 GB** | 19.5 min | 1211 | 132 | ✅ 0 |
| 1.3.5 | 13.1 min MP4 H.265 | large-v3 | **custom 10 GB** | 31 min | 1805 | 138 | ✅ 0 |
| 1.3.6 | 19.7 min MP4 H.265 | large-v3 | **custom 10 GB** | 47.6 min | 2601 | 132 | ✅ 0 |
| 1.3.7 | 7.4 min MP4 H.265 | large-v3 | **custom 10 GB** | 15 min | 936 | 127 | ✅ 0 |
| 1.3.8 | 8.9 min MP4 H.265 | large-v3 | **custom 10 GB** | 18.4 min | 1150 | 129 | ✅ 0 |
| 1.4.1 | 6.7 min MP4 H.265 | large-v3 | **custom 10 GB** | 20 min | 853 | 127 | ✅ 0 |
| 1.4.2 | 5.0 min MP4 H.265 | large-v3 | **custom 10 GB** | 9.8 min | 589 | 118 | ✅ 0 |
| 1.4.3 | 7.9 min MP4 H.265 | large-v3 | **custom 10 GB** | 24.4 min | 954 | 121 | ✅ 0 |
| 1.4.4 | 11.1 min MP4 H.265 | large-v3 | **custom 10 GB** | 25.9 min | 1418 | 128 | ✅ 0 |
| 1.4.5 | 12.6 min MP4 H.265 | large-v3 | **custom 10 GB** | 31.7 min | 1557 | 123 | ✅ 0 |
| 1.4.6 | 10.7 min MP4 H.265 | large-v3 | **custom 10 GB** | 25.9 min | 1190 | 111 | ✅ 0 |
| 1.4.7 | 7.7 min MP4 H.265 | large-v3 | **custom 10 GB** | 16.9 min | 943 | 123 | ✅ 0 |
| 1.4.8 | 6.8 min MP4 H.265 | large-v3 | **custom 10 GB** | 16.9 min | 773 | 114 | ✅ 0 |
| 1.5.1 | 12.3 min MP4 H.265 | large-v3 | **custom 10 GB** | 25.8 min | 1473 | 120 | ✅ 0 |
| 1.5.2 | 11.7 min MP4 H.265 | large-v3 | **custom 10 GB** | 25.0 min | 1463 | 125 | ✅ 0 |
| 1.5.3 | 7.6 min MP4 H.265 | large-v3 | **custom 10 GB** | 16.4 min | 926 | 122 | ✅ 0 |
| 1.5.4 | 9.5 min MP4 H.265 | large-v3 | **custom 10 GB** | 21.7 min | 1181 | 124 | ✅ 0 |
| 1.5.5 | 10.4 min MP4 H.265 | large-v3 | **custom 10 GB** | 22.2 min | 1286 | 124 | ✅ 0 |
| 1.5.6 | 8.3 min MP4 H.265 | large-v3 | **custom 10 GB** | 21.8 min | 951 | 115 | ✅ 0 |
| 1.5.7 | 9.2 min MP4 H.265 | large-v3 | **custom 10 GB** | 18.8 min | 1068 | 116 | ✅ 0 |
| 1.5.8 | 2.3 min MP4 H.265 | large-v3 | **custom 10 GB** | 4.4 min | 247 | 107 | ✅ 0 |
| 1.6.1 | 12.1 min MP4 H.265 | large-v3 | **custom 10 GB** | 25.4 min | 1434 | 118 | ✅ 0 |
| 1.6.2 | 9.3 min MP4 H.265 | large-v3 | **custom 10 GB** | 27.8 min | 1052 | 113 | ✅ 0 |
| 1.6.3 | 10.1 min MP4 H.265 | large-v3 | **custom 10 GB** | 22.2 min | 1270 | 126 | ✅ 0 |
| 1.6.4 | 8.0 min MP4 H.265 | large-v3 | **custom 10 GB** | 16.5 min | 999 | 125 | ✅ 0 |
| 2.1.1 | 24.2 min MP4 H.265 | large-v3 | **custom 10 GB** | 59.5 min | 2677 | 111 | ✅ 0 |
| 2.1.2 | 18.9 min MP4 H.265 | large-v3 | **custom 10 GB** | ~45 min (in progress) | — | — | — |

**Total verified clean: 39 lectures across 6 modules, 0 OOM, 0 ASR-fixes needed.**

The 2.1.1 lecture (24.2 min, 2677 words, 59.5 min wall) is the longest so far and confirms the cgroup escape scales to ~25-min single-chunk audio on large-v3. Wall time stays at ~2.5× real-time, no KV-cache overflow, no `mkl_malloc` errors.

Words/min varies 47–138 by lecture (lecturer pace, not model).

Without the cgroup escape, lecture 1.2 OOM-killed at ~3 min. With it, identical configuration finished cleanly. Every MP4 H.265 lecture since 1.2 has used the custom cgroup and run without issue.

**No ASR-fix needed across the 10+ lecture batch.** large-v3 with the BA Modeling prompt + hotwords produced clean Russian text consistently (zero `фактальной`/`имперической` regressions; the prompt biases the model away from those errors). `asr_fix.py` is now a defensive layer, not a routine post-pass.

## When NOT needed

- **`medium` model**: peaks at ~3.8 GB, fits under 4 GB cgroup. Default invocation is fine.
- **`large-v3` with `--max-memory-gb < 6.0`**: the internal `setrlimit` is the binding cap, so the cgroup is not the bottleneck (though it does no harm).
- **No cgroup at all** (running outside Hermes, e.g., a fresh `ssh` session on a bare host): no `hermes-worker-proc_*.scope`, no fix needed.

## Requirements

- `CAP_SYS_ADMIN` (root) — needed to create a cgroup v2 directory under `/sys/fs/cgroup/`.
- cgroup v2 mounted (this environment has it).
- Free system RAM ≥ 10 GB so the 10 GB cap is actually achievable.

## Pitfalls

- **Run the `mkdir` and `echo` BEFORE the python process.** If you try to retroactively move a running process into the new cgroup, it doesn't un-break the already-allocated memory. The pattern is "set the limit, then start the work."
- **Don't reuse the cgroup name across concurrent jobs.** Each large-v3 run should use a fresh cgroup name (e.g., `hermes_whisper_xlarge_$(date +%s)`) to avoid one job's leftover state affecting the next.
- **`memory.max` is in BYTES, not MB.** 10 GB = `10737418240`. A common mistake is writing `10240` (10 MB) instead.
- **Check dmesg for `failcnt` to know if you hit the cap** even if the job didn't crash — `dmesg | grep "failcnt"` will show if the new cgroup was actually needed.
- **Cgroup survives across runs.** It will sit at 0 usage when idle. Delete with `rmdir /sys/fs/cgroup/hermes_whisper_xlarge` when done if you care about cleanup.
