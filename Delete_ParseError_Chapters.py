import pandas as pd
from pathlib import Path

BASE_DIR = Path(r"D:\Ongoing Research Works\AI-Tutor\NCTB-SchoolText")
needs_rerun = pd.read_csv(BASE_DIR / "files_needing_rerun.csv")

deleted = 0
for path_str in needs_rerun["file"]:
    path = Path(path_str)
    if path.exists():
        path.unlink()
        deleted += 1

print(f"Deleted {deleted} of {len(needs_rerun)} listed files.")
print("Now re-run your main audit script — it will regenerate just these 32 chapters.")