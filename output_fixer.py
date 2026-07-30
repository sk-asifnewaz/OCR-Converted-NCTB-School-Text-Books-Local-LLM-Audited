"""
Repairs malformed JSON in Audit Results files without re-running the LLM.

Most parse failures are caused by the model emitting an unescaped backslash
or a raw (unescaped) newline inside the "evidence" field, not real data loss.
This script uses json_repair to fix that class of error in-place.

Files that are truncated mid-generation (missing fields even after repair)
represent genuine data loss — those are left untouched and listed separately
so you know they still need a re-run, not just a repair.

Setup: pip install json_repair
"""

import json
import re
import shutil
from pathlib import Path
import pandas as pd
from json_repair import repair_json

BASE_DIR = Path(r"D:\Ongoing Research Works\AI-Tutor\NCTB-SchoolText")

CLASS_SUBJECTS = {
    "classOne": [
        "processed_chapters_bangla",
        "processed_chapters_english",
        "processed_chapters_math",
    ],
    "classTwo": [
        "processed_chapters_bangla",
        "processed_chapters_english",
        "processed_chapters_math",
    ],
    "classThree": [
        "processed_chapters_bangla",
        "processed_chapters_bgs",
        "processed_chapters_buddhist_religion",
        "processed_chapters_christian_religion",
        "processed_chapters_english",
        "processed_chapters_hindu_religion",
        "processed_chapters_islam",
        "processed_chapters_math",
        "processed_chapters_science",
    ],
    "classFour": [
        "processed_chapters_bangla",
        "processed_chapters_bgs",
        "processed_chapters_buddhist_religion",
        "processed_chapters_christian_religion",
        "processed_chapters_english",
        "processed_chapters_hindu_religion",
        "processed_chapters_islam",
        "processed_chapters_math",
        "processed_chapters_science",
    ],
    "classFive": [
        "processed_chapters_bangla",
        "processed_chapters_bgs",
        "processed_chapters_buddhist_religion",
        "processed_chapters_christian_religion",
        "processed_chapters_eng",
        "processed_chapters_hindu_religion",
        "processed_chapters_islam",
        "processed_chapters_math",
        "processed_chapters_science",
    ],
    "classSix": [
        "processed_chapters_agriculture",
        "processed_chapters_arabic",
        "processed_chapters_arts_and_crafts",
        "processed_chapters_bangla",
        "processed_chapters_bangla_grammar",
        "processed_chapters_bangla_rapidreader",
        "processed_chapters_bgs",
        "processed_chapters_buddhist_religion",
        "processed_chapters_christian_religion",
        "processed_chapters_english",
        "processed_chapters_english_grammar",
        "processed_chapters_hindu_religion",
        "processed_chapters_home_science",
        "processed_chapters_ict",
        "processed_chapters_islam",
        "processed_chapters_math",
        "processed_chapters_music",
        "processed_chapters_pali",
        "processed_chapters_physical_education",
        "processed_chapters_sanskrit",
        "processed_chapters_science",
        "processed_chapters_work_and_life",
    ],
    "classSeven": [
        "processed_chapters_agriculture",
        "processed_chapters_arabic",
        "processed_chapters_arts_and_crafts",
        "processed_chapters_bangla",
        "processed_chapters_bangla_grammar",
        "processed_chapters_bangla_rapidreader",
        "processed_chapters_bgs",
        "processed_chapters_buddhist_religion",
        "processed_chapters_christian_religion",
        "processed_chapters_english",
        "processed_chapters_english_grammar",
        "processed_chapters_hindu_religion",
        "processed_chapters_home_science",
        "processed_chapters_ict",
        "processed_chapters_islam",
        "processed_chapters_math",
        "processed_chapters_music",
        "processed_chapters_pali",
        "processed_chapters_physical_education",
        "processed_chapters_sanskrit",
        "processed_chapters_science",
        "processed_chapters_work_and_life",
    ],
    "classEight": [
        "processed_chapters_agriculture",
        "processed_chapters_arabic",
        "processed_chapters_arts_and_crafts",
        "processed_chapters_bangla",
        "processed_chapters_bangla_grammar",
        "processed_chapters_bangla_rapidreader",
        "processed_chapters_bgs",
        "processed_chapters_buddhist_religion",
        "processed_chapters_christian_religion",
        "processed_chapters_english",
        "processed_chapters_english_grammar",
        "processed_chapters_hindu_religion",
        "processed_chapters_home_science",
        "processed_chapters_ict",
        "processed_chapters_islam",
        "processed_chapters_math",
        "processed_chapters_music",
        "processed_chapters_pali",
        "processed_chapters_physical_education",
        "processed_chapters_sanskrit",
        "processed_chapters_science",
        "processed_chapters_work_and_life",
    ],
    "classNineTen": [
        "processed_chapters_accounting",
        "processed_chapters_agriculture",
        "processed_chapters_arabic",
        "processed_chapters_arts_and_crafts",
        "processed_chapters_bangla",
        "processed_chapters_bangla_grammar",
        "processed_chapters_bangla_rapidreader",
        "processed_chapters_bgs",
        "processed_chapters_biology_secondary",
        "processed_chapters_buddhist_religion",
        "processed_chapters_business_entrepreneurship",
        "processed_chapters_career_education",
        "processed_chapters_chemistry_secondary",
        "processed_chapters_christian_religion",
        "processed_chapters_civics",
        "processed_chapters_economics",
        "processed_chapters_english",
        "processed_chapters_english_grammar",
        "processed_chapters_finance",
        "processed_chapters_geography",
        "processed_chapters_higher_math",
        "processed_chapters_hindu_religion",
        "processed_chapters_history",
        "processed_chapters_home_science",
        "processed_chapters_ict",
        "processed_chapters_islam",
        "processed_chapters_math",
        "processed_chapters_music",
        "processed_chapters_pali",
        "processed_chapters_physical_education",
        "processed_chapters_physics_secondary",
        "processed_chapters_sanskrit",
        "processed_chapters_science",
    ],
}

# Fields every clean chunk-result entry is expected to have. Used to detect
# truncation: if repair "succeeds" but entries are missing these, real data
# was lost mid-generation, not just malformed.
EXPECTED_KEYS = {"chunk_id", "status", "issues", "severity", "confidence", "evidence", "note"}

BACKUP_SUFFIX = ".bak"


def compact_issue_arrays(json_text: str) -> str:
    return re.sub(
        r'"issues":\s*\[\s*((?:"[^"]*"\s*,?\s*)*)\]',
        lambda m: '"issues": [' + ', '.join(re.findall(r'"[^"]*"', m.group(1))) + ']',
        json_text
    )


def get_subject_name(subject_folder: str) -> str:
    return subject_folder.replace("processed_chapters_", "", 1)


def repair_file(audit_path: Path):
    """
    Returns a dict describing what happened: status is one of
    'already_valid', 'repaired', 'needs_rerun_truncated', 'needs_rerun_unrepairable'.
    """
    original_text = audit_path.read_text(encoding="utf-8")

    # Already valid — leave alone.
    try:
        content = json.loads(original_text)
        if isinstance(content, list):
            return {"status": "already_valid"}
    except json.JSONDecodeError:
        pass

    # Attempt repair.
    try:
        repaired_text = repair_json(original_text)
        content = json.loads(repaired_text)
    except Exception as e:
        return {"status": "needs_rerun_unrepairable", "detail": str(e)}

    if not isinstance(content, list) or len(content) == 0:
        return {"status": "needs_rerun_unrepairable", "detail": "Repaired output is not a non-empty list"}

    # Check for real data loss (truncation): every entry should have all
    # expected keys with non-null values.
    incomplete_entries = [
        i for i, entry in enumerate(content)
        if not isinstance(entry, dict) or not EXPECTED_KEYS.issubset(entry.keys())
    ]
    if incomplete_entries:
        return {
            "status": "needs_rerun_truncated",
            "detail": f"{len(incomplete_entries)} of {len(content)} entries missing expected fields "
                      f"(likely truncated mid-generation)",
        }

    # Full repair succeeded with no data loss — back up original, then overwrite.
    backup_path = audit_path.with_suffix(audit_path.suffix + BACKUP_SUFFIX)
    if not backup_path.exists():
        shutil.copy2(audit_path, backup_path)

    formatted = compact_issue_arrays(json.dumps(content, ensure_ascii=False, indent=2))
    audit_path.write_text(formatted, encoding="utf-8")

    return {"status": "repaired", "detail": f"{len(content)} chunk(s) recovered"}


def main():
    rows = []
    for class_name, subject_folders in CLASS_SUBJECTS.items():
        for subject_folder in subject_folders:
            subject_dir = BASE_DIR / class_name / subject_folder
            audit_dir = subject_dir / "Audit Results"
            if not audit_dir.exists():
                continue

            subject_name = get_subject_name(subject_folder)
            for audit_path in sorted(audit_dir.glob("*.json")):
                if audit_path.name.endswith(BACKUP_SUFFIX):
                    continue
                result = repair_file(audit_path)
                rows.append({
                    "class": class_name,
                    "subject": subject_name,
                    "file": str(audit_path),
                    "status": result["status"],
                    "detail": result.get("detail", ""),
                })

    report_df = pd.DataFrame(rows)

    print("=== Summary ===")
    print(report_df["status"].value_counts().to_string())
    print()

    repaired = report_df[report_df["status"] == "repaired"]
    if not repaired.empty:
        print(f"Repaired in-place ({len(repaired)} file(s)) — originals backed up as *.json.bak:")
        print(repaired[["class", "subject", "file"]].to_string(index=False))
        print()

    needs_rerun = report_df[report_df["status"].isin(["needs_rerun_truncated", "needs_rerun_unrepairable"])]
    if not needs_rerun.empty:
        print(f"STILL NEED A RE-RUN ({len(needs_rerun)} file(s)) — genuine data loss, not just malformed:")
        print(needs_rerun[["class", "subject", "file", "detail"]].to_string(index=False))
        needs_rerun_path = BASE_DIR / "files_needing_rerun.csv"
        needs_rerun.to_csv(needs_rerun_path, index=False)
        print(f"\nList saved to: {needs_rerun_path}")
        print("Delete these specific files and re-run your audit script to fill them in.")


if __name__ == "__main__":
    main()