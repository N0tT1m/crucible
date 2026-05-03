# L1 — `weight-sniffer`

A static scanner for model-weight files. Detects:

- Embedded code (pickle exploits in `.bin`, `.pt`, `.ckpt` files).
- Suspicious metadata (training-data fingerprints, custom tokenizers).
- Backdoor-trigger signatures known from public catalogues.
- Deviations from the published checksum / model card.

L1 is the **supply-chain wedge** entry point (Section L per
PROJECT_IDEAS.md). Most red-team vendors stop at runtime; L1 is the
"check what you downloaded before you load it" layer that's near-zero in
the commercial market.

## Why this matters

- **Pickle-based weight files can execute arbitrary code on load.** The
  vulnerability is well-known but defenders rarely scan.
- **HuggingFace Hub hosts ~700,000 models** — enterprises pulling
  weights need a fast pre-load scanner. None ships by default.
- **Compliance angle.** EU AI Act Article 13 obligates "transparency"
  on AI-system components — knowing what's in your weight file is a
  precondition.

## Standard checks

| Check | Mechanism |
|---|---|
| **Pickle deserialization probe** | Disassemble `.bin`/`.pt` files via `pickletools`, surface any `GLOBAL`/`REDUCE` ops referencing imports outside numpy/torch. |
| **Tokenizer mismatch** | Hash tokenizer vs canonical checksum; flag custom tokenizers. |
| **Architecture mismatch** | Compare reported architecture in config vs actual layer shapes. |
| **Embedded payload** | Search for high-entropy data segments not consistent with weight values (sometimes used to smuggle data). |
| **Backdoor-trigger DB** | Match against public catalogues of known backdoor triggers (BackdoorBench, OdySSEy). |
| **Provenance** | Verify `model.safetensors` checksum matches the publisher's stated SHA-256. |

## What it produces

- A Go CLI `proxies/weight-sniffer/` (per `[GO]` tag) with a `scan`
  subcommand: `weight-sniffer scan ./pytorch_model.bin`.
- A scan-report schema:
  ```
  weight_scans: file_path, sha256, scan_ts, total_findings,
                findings (Array(Tuple(severity, kind, detail)))
  ```
- A new ClickHouse table `raw.weight_scans` for tracking scans over time.
- Integration with the `redbox` Python side via JSONL output (per the
  polyglot pattern).

## Hard prereqs

- A1 / A2 / A4 / A5 — for storage + reporting.
- Go 1.23+ for the scanner binary.
- Python helper (uses `pickletools`, `safetensors`) — Go calls into a
  Python subprocess for pickle disassembly because Go pickle support
  is limited.

## What's deferred

- **Active loading test.** Loading the weights in an isolated sandbox
  to see what they do. Goes to L4 `backdoor-prober`.
- **Adversarial training detection.** Statistical analysis of weight
  distribution to detect "this model was trained on poisoned data."
  Research-grade; defer.
- **Model-format coverage.** v1 covers PyTorch / SafeTensors / GGUF.
  ONNX, JAX, mlx-format added on demand.

## Concept questions

- Does L1 catch *all* malicious weight files? (no — sophisticated
  adversaries can evade. L1 catches the bulk; L4 catches the rest by
  observing behaviour).
- Should L1 reject files with any finding, or rank findings by
  severity? (rank — false positives are common and rejection is
  expensive).
- Is L1 useful when pulling from "trusted" hubs (HuggingFace,
  PyTorch Hub)? (yes — those hubs have been compromised before).

## When done

You can pre-flight every weight-file download with mechanical scanning,
catch obvious supply-chain attacks before load, and contribute a
critical missing layer to the supply-chain story.
