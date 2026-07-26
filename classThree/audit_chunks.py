import json
import re
import time
from pathlib import Path
import requests

LM_STUDIO_CHAT_URL = "http://127.0.0.1:1234/v1/chat/completions"
MODEL_NAME = "google/gemma-4-12b"

BASE_DIR = Path(r"D:\Ongoing Research Works\AI-Tutor\NCTB-SchoolText\classThree")

SUBJECT_FOLDERS = [
    "processed_chapters_bangla",
    "processed_chapters_bgs",
    "processed_chapters_buddhist_religion",
    "processed_chapters_christian_religion",
    "processed_chapters_english",
    "processed_chapters_hindu_religion",
    "processed_chapters_islam",
    "processed_chapters_math",
    "processed_chapters_science",

]


def chapter_sort_key(path: Path):
    match = re.search(r'ch(\d+)', path.stem, re.IGNORECASE)
    return int(match.group(1)) if match else float('inf')


def strip_code_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def compact_issue_arrays(json_text: str) -> str:
    # Collapses "issues": [\n  "X"\n] into "issues": ["X"] on one line
    return re.sub(
        r'"issues":\s*\[\s*((?:"[^"]*"\s*,?\s*)*)\]',
        lambda m: '"issues": [' + ', '.join(re.findall(r'"[^"]*"', m.group(1))) + ']',
        json_text
    )


def process_file(jsonl_path: Path, output_dir: Path):
    raw_file_text = jsonl_path.read_text(encoding="utf-8")
    if not raw_file_text.strip():
        print(f"  ! {jsonl_path.name} is empty, skipping.")
        return

    line_count = sum(1 for line in raw_file_text.splitlines() if line.strip())
    print(f"-> {jsonl_path.name} ({line_count} lines) — sending, please wait...")

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "user", "content": raw_file_text},
        ],
    }

    start = time.time()
    try:
        resp = requests.post(LM_STUDIO_CHAT_URL, json=payload)
    except Exception as e:
        print(f"   ! Connection error: {e}")
        return

    elapsed = time.time() - start
    output_path = output_dir / (jsonl_path.stem + ".json")

    if resp.status_code != 200:
        print(f"   ! HTTP {resp.status_code}: {resp.text[:300]}")
        output_path.write_text(resp.text, encoding="utf-8")
        return

    data = resp.json()
    choices = data.get("choices") or []
    if not choices:
        print(f"   ! No choices in response after {elapsed:.0f}s")
        output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return

    raw_content = choices[0]["message"].get("content", "") or ""
    finish_reason = choices[0].get("finish_reason")

    try:
        parsed = json.loads(strip_code_fences(raw_content))
        formatted = compact_issue_arrays(json.dumps(parsed, ensure_ascii=False, indent=2))
        output_path.write_text(formatted, encoding="utf-8")
        flagged = sum(1 for r in parsed if r.get("status") == "flagged")
        print(f"   done in {elapsed:.0f}s — {flagged}/{line_count} flagged. Saved to {output_path}")
    except json.JSONDecodeError:
        # Couldn't parse as JSON — save the raw text so nothing is lost.
        output_path.write_text(raw_content, encoding="utf-8")
        print(f"   ! finished in {elapsed:.0f}s but couldn't parse JSON "
              f"(finish_reason={finish_reason}) — raw output saved to {output_path}")


def main():
    for subject_folder in SUBJECT_FOLDERS:
        input_dir = BASE_DIR / subject_folder
        output_dir = input_dir / "Audit Results"

        if not input_dir.exists():
            print(f"! Folder not found, skipping: {input_dir}")
            continue

        output_dir.mkdir(parents=True, exist_ok=True)
        jsonl_files = sorted(input_dir.glob("*.jsonl"), key=chapter_sort_key)

        if not jsonl_files:
            print(f"! No .jsonl files in {input_dir}, skipping.\n")
            continue

        print(f"=== {subject_folder} — {len(jsonl_files)} file(s) ===")
        print(f"Output -> {output_dir}\n")

        for jsonl_path in jsonl_files:
            output_path = output_dir / (jsonl_path.stem + ".json")
            if output_path.exists():
                print(f"-> {jsonl_path.name} already done, skipping.")
                continue
            process_file(jsonl_path, output_dir)
        print()

    print("All subjects processed.")


if __name__ == "__main__":
    main()