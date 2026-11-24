"""Acquire a balanced, slide-disjoint subset from the public TCGA@Focus archive."""
import csv
import hashlib
import json
from pathlib import Path
from remotezip import RemoteZip

ROOT = Path(__file__).parent
CACHE = ROOT / "cache"
URL = "https://zenodo.org/records/3910757/files/TCGA%40Focus.zip?download=1"


def main():
    source = CACHE / "labels.txt"
    if not source.exists():
        import requests
        response = requests.get("https://raw.githubusercontent.com/icbcbicc/FocusLiteNN/master/data/TCGA%40Focus.txt", timeout=30)
        response.raise_for_status()
        CACHE.mkdir(exist_ok=True)
        source.write_bytes(response.content)
    groups = {}
    for path, organ, *_ in csv.reader(source.read_text(encoding="utf-8-sig").splitlines()):
        parts = path.split("/")
        if len(parts) != 4 or parts[0] not in {"In Focus", "Out of Focus"}:
            continue
        groups.setdefault((organ, parts[0]), {}).setdefault(parts[2], []).append(path)
    organs = sorted({organ for organ, _ in groups
                     if min(len(groups.get((organ,label),{})) for label in ("In Focus","Out of Focus")) >= 4})
    rows = []
    used = set()
    key = lambda path: hashlib.sha256(("slide-quality-v1:" + path).encode()).digest()
    for organ in organs:
        for split in ("calibration","test"):
            for label in ("In Focus","Out of Focus"):
                options = groups.get((organ,label),{})
                for _ in range(2):
                    slide = next((slide for slide in sorted(options,key=key) if slide not in used),None)
                    if slide is None:
                        break
                    used.add(slide)
                    rows.append(dict(split=split, organ=organ, label=label, slide=slide,
                                     member="TCGA@Focus/Image Patches Database/"+min(options[slide],key=key)))
        if len(rows) >= 40:
            break
    assert len({row["slide"] for row in rows}) == len(rows)
    assert {"test","calibration"} == {row["split"] for row in rows}
    cached = CACHE / "patches"
    cached.mkdir(exist_ok=True)
    with RemoteZip(URL) as archive:
        for i,row in enumerate(rows):
            name = f"patch-{i:02}.png"
            row["file"] = name
            target = cached / name
            if not target.exists():
                target.write_bytes(archive.read(row["member"]))
            print(i,row["split"],row["organ"],row["label"],flush=True)
    (ROOT/"cohort.json").write_text(json.dumps(rows,indent=2)+"\n")


if __name__ == "__main__":
    main()
