"""
Finds exactly which chunks are missing from your audit results — chapters
that parse as valid JSON but contain fewer chunk_ids than their source
.jsonl file. This catches silent data loss that a JSON-validity check alone
would miss (e.g. a repaired file that dropped trailing incomplete entries
instead of preserving them).
"""

import json
from pathlib import Path
import pandas as pd

BASE_DIR = Path(r"D:\Ongoing Research Works\AI-Tutor\NCTB-SchoolText")

CLASS_SUBJECTS = {
    "classOne": ["processed_chapters_bangla", "processed_chapters_english", "processed_chapters_math"],
    "classTwo": ["processed_chapters_bangla", "processed_chapters_english", "processed_chapters_math"],
    "classThree": [
        "processed_chapters_bangla", "processed_chapters_bgs", "processed_chapters_buddhist_religion",
        "processed_chapters_christian_religion", "processed_chapters_english", "processed_chapters_hindu_religion",
        "processed_chapters_islam", "processed_chapters_math", "processed_chapters_science",
    ],
    "classFour": [
        "processed_chapters_bangla", "processed_chapters_bgs", "processed_chapters_buddhist_religion",
        "processed_chapters_christian_religion", "processed_chapters_english", "processed_chapters_hindu_religion",
        "processed_chapters_islam", "processed_chapters_math", "processed_chapters_science",
    ],
    "classFive": [
        "processed_chapters_bangla", "processed_chapters_bgs", "processed_chapters_buddhist_religion",
        "processed_chapters_christian_religion", "processed_chapters_eng", "processed_chapters_hindu_religion",
        "processed_chapters_islam", "processed_chapters_math", "processed_chapters_science",
    ],
    "classSix": [
        "processed_chapters_agriculture", "processed_chapters_arabic", "processed_chapters_arts_and_crafts",
        "processed_chapters_bangla", "processed_chapters_bangla_grammar", "processed_chapters_bangla_rapidreader",
        "processed_chapters_bgs", "processed_chapters_buddhist_religion", "processed_chapters_christian_religion",
        "processed_chapters_english", "processed_chapters_english_grammar", "processed_chapters_hindu_religion",
        "processed_chapters_home_science", "processed_chapters_ict", "processed_chapters_islam",
        "processed_chapters_math", "processed_chapters_music", "processed_chapters_pali",
        "processed_chapters_physical_education", "processed_chapters_sanskrit", "processed_chapters_science",
        "processed_chapters_work_and_life",
    ],
    "classSeven": [
        "processed_chapters_agriculture", "processed_chapters_arabic", "processed_chapters_arts_and_crafts",
        "processed_chapters_bangla", "processed_chapters_bangla_grammar", "processed_chapters_bangla_rapidreader",
        "processed_chapters_bgs", "processed_chapters_buddhist_religion", "processed_chapters_christian_religion",
        "processed_chapters_english", "processed_chapters_english_grammar", "processed_chapters_hindu_religion",
        "processed_chapters_home_science", "processed_chapters_ict", "processed_chapters_islam",
        "processed_chapters_math", "processed_chapters_music", "processed_chapters_pali",
        "processed_chapters_physical_education", "processed_chapters_sanskrit", "processed_chapters_science",
        "processed_chapters_work_and_life",
    ],
    "classEight": [
        "processed_chapters_agriculture", "processed_chapters_arabic", "processed_chapters_arts_and_crafts",
        "processed_chapters_bangla", "processed_chapters_bangla_grammar", "processed_chapters_bangla_rapidreader",
        "processed_chapters_bgs", "processed_chapters_buddhist_religion", "processed_chapters_christian_religion",
        "processed_chapters_english", "processed_chapters_english_grammar", "processed_chapters_hindu_religion",
        "processed_chapters_home_science", "processed_chapters_ict", "processed_chapters_islam",
        "processed_chapters_math", "processed_chapters_music", "processed_chapters_pali",
        "processed_chapters_physical_education", "processed_chapters_sanskrit", "processed_chapters_science",
        "processed_chapters_work_and_life",
    ],
    "classNineTen": [
        "processed_chapters_accounting", "processed_chapters_agriculture", "processed_chapters_arabic",
        "processed_chapters_arts_and_crafts", "processed_chapters_bangla", "processed_chapters_bangla_grammar",
        "processed_chapters_bangla_rapidreader", "processed_chapters_bgs", "processed_chapters_biology_secondary",
        "processed_chapters_buddhist_religion", "processed_chapters_business_entrepreneurship",
        "processed_chapters_career_education", "processed_chapters_chemistry_secondary",
        "processed_chapters_christian_religion", "processed_chapters_civics", "processed_chapters_economics",
        "processed_chapters_english", "processed_chapters_english_grammar", "processed_chapters_finance",
        "processed_chapters_geography", "processed_chapters_higher_math", "processed_chapters_hindu_religion",
        "processed_chapters_history", "processed_chapters_home_science", "processed_chapters_ict",
        "processed_chapters_islam", "processed_chapters_math", "processed_chapters_music",
        "processed_chapters_pali", "processed_chapters_physical_education", "processed_chapters_physics_secondary",
        "processed_chapters_sanskrit", "processed_chapters_science",
    ],
}


def get_subject_name(subject_folder: str) -> str:
    return subject_folder.replace("processed_chapters_", "", 1)


def get_source_chunk_ids(jsonl_path: Path) -> set:
    ids = set()
    with jsonl_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                ids.add(obj.get("chunk_id"))
            except json.JSONDecodeError:
                pass
    return ids


def get_audit_chunk_ids(audit_path: Path):
    try:
        content = json.loads(audit_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if not isinstance(content, list):
        return None
    return {entry.get("chunk_id") for entry in content if isinstance(entry, dict)}


def main():
    rows = []
    for class_name, subject_folders in CLASS_SUBJECTS.items():
        for subject_folder in subject_folders:
            subject_dir = BASE_DIR / class_name / subject_folder
            audit_dir = subject_dir / "Audit Results"
            if not subject_dir.exists():
                continue
            subject_name = get_subject_name(subject_folder)

            for jsonl_path in sorted(subject_dir.glob("*.jsonl")):
                audit_path = audit_dir / (jsonl_path.stem + ".json")
                source_ids = get_source_chunk_ids(jsonl_path)

                if not audit_path.exists():
                    rows.append({
                        "class": class_name, "subject": subject_name, "chapter": jsonl_path.stem,
                        "source_chunks": len(source_ids), "audited_chunks": 0,
                        "missing_count": len(source_ids),
                        "missing_chunk_ids": sorted(source_ids), "status": "no_audit_file"
                    })
                    continue

                audit_ids = get_audit_chunk_ids(audit_path)
                if audit_ids is None:
                    rows.append({
                        "class": class_name, "subject": subject_name, "chapter": jsonl_path.stem,
                        "source_chunks": len(source_ids), "audited_chunks": 0,
                        "missing_count": len(source_ids),
                        "missing_chunk_ids": sorted(source_ids), "status": "unparseable"
                    })
                    continue

                missing = source_ids - audit_ids
                rows.append({
                    "class": class_name, "subject": subject_name, "chapter": jsonl_path.stem,
                    "source_chunks": len(source_ids), "audited_chunks": len(audit_ids),
                    "missing_count": len(missing),
                    "missing_chunk_ids": sorted(missing),
                    "status": "complete" if not missing else "missing_chunks",
                })

    df = pd.DataFrame(rows)

    print("=== Status summary ===")
    print(df["status"].value_counts().to_string())
    print()

    incomplete = df[df["status"] != "complete"].sort_values("missing_count", ascending=False)
    total_missing = incomplete["missing_count"].sum()
    print(f"Total missing chunks across all incomplete chapters: {total_missing}")
    print()

    if not incomplete.empty:
        print("=== Chapters with missing chunks (worst first) ===")
        print(incomplete[["class", "subject", "chapter", "source_chunks", "audited_chunks",
                          "missing_count", "status"]].to_string(index=False))

        incomplete.to_csv(BASE_DIR / "chapters_with_missing_chunks.csv", index=False)
        print(f"\nFull list (including exact missing chunk_ids) saved to:")
        print(f"  {BASE_DIR / 'chapters_with_missing_chunks.csv'}")


if __name__ == "__main__":
    main()