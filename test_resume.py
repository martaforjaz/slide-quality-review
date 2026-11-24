"""Interrupt just after the first durable checkpoint, then verify exact resumption."""
import csv
import json
from pathlib import Path
import subprocess
import sys
import tempfile



def exercise():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        subprocess.run([sys.executable, "public_folder_example.py", "--output", str(root)], check=True)
        output = root / "interrupted"
        child = """
import os
from pathlib import Path
import sys
import review_folder as review
original = review.save_json
def checkpoint(path,value):
    original(path,value)
    if path.name == "checkpoint.json":
        os._exit(86)
review.save_json = checkpoint
review.report(Path(sys.argv[1]),Path(sys.argv[2]))
"""
        stopped = subprocess.run([sys.executable, "-c", child, str(root/"input"), str(output)])
        assert stopped.returncode == 86
        state = json.loads((output/"checkpoint.json").read_text())
        assert len(state["slides"]) == 1
        saved = {path.name:path.stat().st_mtime_ns for path in output.glob("*.png")}
        subprocess.run([sys.executable,"review_folder.py",str(root/"input"),"--output",str(output)],check=True)
        stats = json.loads((output/"run-metrics.json").read_text())
        assert (stats["processed"],stats["reused"]) == (1,1)
        assert all((output/name).stat().st_mtime_ns == value for name,value in saved.items())
        with (output/"alerts.csv").open(encoding="utf-8-sig") as file:
            rows = list(csv.DictReader(file))
        ids = {(row["slide"],row["level0_x"],row["level0_y"]) for row in rows}
        assert len(ids) == len(rows) == 1
        assert "region-" in (output/"index.html").read_text()
        result = dict(interrupted_after_completed=1,resumed_without_reprocessing=1,
                      newly_processed=1,unique_alerts=len(rows),duplicate_alerts=len(rows)-len(ids))
        Path("resume-results.json").write_text(json.dumps(result,indent=2)+"\n")
        print(result)


if __name__ == "__main__":
    exercise()
