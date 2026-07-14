# magistarski-scheming-scenarios

Versioned scenario definitions and dataset-building tooling for a set of behavioral
evaluation experiments testing LLM "scheming" (covert pursuit of a self-interested or
hidden goal at the expense of honest behavior) under different prompt conditions.

Two kinds of scenarios are supported:

- **Phase 1 (non-agent)** — single-turn Q&A scenarios with a hidden pressure toward
  self-interested behavior, scored by an LLM judge on a 1–5 deception scale.
- **Phase 2 (agent)** — tool-using agent scenarios (file access, email, record deletion)
  where misuse of tools signals scheming, scored by a rule-based tool-call/keyword
  classifier.

Each scenario is authored once per theme and then instantiated across a 2×2 condition
grid (assistant persona: neutral vs. assertive; language: English vs. Bosnian), producing
one dataset file per condition via `build_datasets.py`. Datasets are built in a format
consumable by the [Inspect](https://inspect.aisi.org.uk/) evaluation framework.

## Layout

```
scenarios/
  phase1/SP-1.json ...      non-agent scenario definitions
  phase2/OS-1.json ...      agent/tool-use scenario definitions
schema/
  scenario_phase1.schema.json
  scenario_phase2.schema.json
shared/
  personas.json              persona system-prompt prefixes (neutral / assertive x EN / BS)
  scratchpad.json             shared chain-of-thought scratchpad instruction
  conditions.json             the 2x2 (persona x language) condition list
build_datasets.py
README.md
```

## Usage

```bash
pip install -r requirements.txt

# Validate every scenario file against its schema
python build_datasets.py --validate

# Build evaluation-ready dataset files for one phase, all 4 conditions
python build_datasets.py --phase 1 --out ./datasets/
python build_datasets.py --phase 2 --out ./datasets/

# Restrict to specific scenarios (useful for smoke tests / pilots)
python build_datasets.py --phase 1 --out ./datasets/ --only SP-1
python build_datasets.py --validate --only SP-1,OS-1
```

Each `--phase N` run writes one file per condition —
`scenarios_phaseN_{LANG}_{persona}.json` — containing every selected scenario's entry for
that condition. Phase 1 entries carry a `[system, user]` message pair; phase 2 entries
carry a `[user]` message plus a `metadata` block with the scenario's virtual file store and
tool-misuse detection rules (off-scope tools, suspicious edit targets, suspicious email
keywords, the legitimate email recipient).

## Adding a new scenario

1. Add `scenarios/phase{1,2}/<ID>.json`, matching the structure and length of the existing
   scenario files in that directory.
2. Run `python build_datasets.py --validate --only <ID>` and confirm it passes before
   committing.

## Scenario freeze

Scenario text is calibrated during a pilot phase and then frozen (tagged) before
confirmatory evaluation runs; no scenario text changes after a freeze tag is cut.
