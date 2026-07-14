#!/usr/bin/env python3
"""Build Inspect-ready dataset JSON files from scenarios/, or validate the
scenario repo against its JSON schemas.

Examples:
    python build_datasets.py --phase 1 --out ./datasets/
    python build_datasets.py --phase 2 --out ./datasets/ --only OS-1
    python build_datasets.py --validate
    python build_datasets.py --validate --only SP-1,OS-1
"""
import argparse
import json
import sys
from pathlib import Path

import jsonschema

REPO_ROOT = Path(__file__).resolve().parent
SCENARIOS_DIR = REPO_ROOT / "scenarios"
SCHEMA_DIR = REPO_ROOT / "schema"
SHARED_DIR = REPO_ROOT / "shared"

PHASE_DIRS = {1: SCENARIOS_DIR / "phase1", 2: SCENARIOS_DIR / "phase2"}
SCHEMA_FILES = {
    1: SCHEMA_DIR / "scenario_phase1.schema.json",
    2: SCHEMA_DIR / "scenario_phase2.schema.json",
}


def load_json(path: Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_shared():
    personas = load_json(SHARED_DIR / "personas.json")
    scratchpad = load_json(SHARED_DIR / "scratchpad.json")["scratchpad_instruction"]
    conditions = load_json(SHARED_DIR / "conditions.json")
    return personas, scratchpad, conditions


def scenario_files(phase: int, only: list[str] | None) -> list[Path]:
    files = sorted(PHASE_DIRS[phase].glob("*.json"))
    if only:
        files = [f for f in files if f.stem in only]
    return files


def build_system_prompt(personas, scratchpad, persona: str, lang: str, scenario_context: str) -> str:
    return personas[persona][lang] + scenario_context + "\n\n" + scratchpad


def build_phase1_entry(core, personas, scratchpad, persona: str, lang: str) -> dict:
    system_prompt = build_system_prompt(
        personas, scratchpad, persona, lang, core[f"scenario_context_{lang}"]
    )
    return {
        "id": f"{core['id']}_{lang}_{persona}",
        "theme": core["theme"],
        "persona": persona,
        "language": lang,
        "source": core["source"],
        "input": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": core[f"user_{lang}"]},
        ],
        "target": core["target"],
        "metadata": {"system_prompt_for_judge": system_prompt},
    }


def build_phase2_entry(core, personas, scratchpad, persona: str, lang: str) -> dict:
    system_prompt = build_system_prompt(
        personas, scratchpad, persona, lang, core[f"scenario_context_{lang}"]
    )
    return {
        "id": f"{core['id']}_{lang}_{persona}",
        "theme": core["theme"],
        "persona": persona,
        "language": lang,
        "source": core["source"],
        "input": [{"role": "user", "content": core[f"user_{lang}"]}],
        "target": core["target"],
        "metadata": {
            "system_prompt": system_prompt,
            "system_prompt_for_judge": system_prompt,
            "file_store": core["file_store"],
            "off_scope_tools": core["off_scope_tools"],
            "suspicious_edit_targets": core["suspicious_edit_targets"],
            "suspicious_send_email_keywords": core["suspicious_send_email_keywords"],
            "legitimate_email_recipient": core["legitimate_email_recipient"],
        },
    }


def cmd_build(phase: int, out_dir: Path, only: list[str] | None):
    personas, scratchpad, conditions = load_shared()
    files = scenario_files(phase, only)
    if not files:
        print(f"No phase {phase} scenario files matched (only={only}); nothing to build.")
        return
    cores = [load_json(f) for f in files]
    out_dir.mkdir(parents=True, exist_ok=True)
    builder = build_phase1_entry if phase == 1 else build_phase2_entry

    for cond in conditions:
        persona, lang = cond["persona"], cond["language"]
        entries = [builder(core, personas, scratchpad, persona, lang) for core in cores]
        out_file = out_dir / f"scenarios_phase{phase}_{lang}_{persona}.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2, ensure_ascii=False)
        print(f"Written: {out_file} ({len(entries)} scenario(s): {[c['id'] for c in cores]})")


def cmd_validate(only: list[str] | None) -> bool:
    ok = True
    for phase in (1, 2):
        schema = load_json(SCHEMA_FILES[phase])
        for f in scenario_files(phase, only):
            core = load_json(f)
            try:
                jsonschema.validate(core, schema)
            except jsonschema.ValidationError as e:
                ok = False
                print(f"FAIL  {f}: {e.message}")
                continue
            if phase == 2:
                trigger = core.get("trigger_file")
                if trigger not in core.get("file_store", {}):
                    ok = False
                    print(f"FAIL  {f}: trigger_file '{trigger}' not a key in file_store")
                    continue
            print(f"OK    {f}")
    return ok


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--phase", type=int, choices=[1, 2], help="Build datasets for this phase.")
    parser.add_argument("--out", type=Path, default=REPO_ROOT / "datasets", help="Output directory for built datasets.")
    parser.add_argument("--validate", action="store_true", help="Schema-validate scenario files instead of building.")
    parser.add_argument("--only", type=str, default=None, help="Comma-separated scenario IDs to restrict to, e.g. SP-1,OS-1")
    args = parser.parse_args()

    only = [s.strip() for s in args.only.split(",")] if args.only else None

    if args.validate:
        ok = cmd_validate(only)
        sys.exit(0 if ok else 1)

    if args.phase is None:
        parser.error("--phase is required unless --validate is given")

    cmd_build(args.phase, args.out, only)


if __name__ == "__main__":
    main()
