"""Download a fresh slide-disjoint holdout from TCGA@Focus using HTTP ranges."""
from concurrent.futures import ThreadPoolExecutor
import csv
import hashlib
import json
from pathlib import Path
from threading import local

from remotezip import RemoteZip
from acquire_tcga import CACHE, URL

ROOT = Path(__file__).parent
worker = local()


def download(row):
    target = CACHE / "patches" / row["file"]
    if not target.exists():
        if not hasattr(worker, "archive"):
            worker.archive = RemoteZip(URL)
        data = worker.archive.read(row["member"])
        target.write_bytes(data)
    return row


def main():
    previous = json.loads((ROOT/"cohort.json").read_text(encoding="utf8"))
    used = {r["slide"] for r in previous}
    source = CACHE/"labels.txt"
    if not source.exists():
        raise SystemExit("Run acquire_tcga.py first.")
    groups = {}
    for path, organ, *_ in csv.reader(source.read_text(encoding="utf-8-sig").splitlines()):
        parts = path.split("/")
        if len(parts) == 4 and parts[2] not in used and parts[0] in ("In Focus","Out of Focus"):
            groups.setdefault((organ,parts[0]),{}).setdefault(parts[2],[]).append(path)
    key = lambda text: hashlib.sha256(("slide-quality-holdout-v2:"+text).encode()).digest()
    rows = []
    for organ in sorted({k[0] for k in groups},key=key):
        if min(len(set(groups.get((organ,label),{}))-used) for label in ("In Focus","Out of Focus")) < 4:
            continue
        for label in ("In Focus","Out of Focus"):
            for _ in range(2):
                matches = groups[organ,label]
                slide = min(set(matches)-used,key=key)
                used.add(slide)
                rows.append(dict(split="test",organ=organ,label=label,slide=slide,
                                 member="TCGA@Focus/Image Patches Database/"+min(matches[slide],key=key),
                                 file=f"holdout-{len(rows):02}.png"))
        if len(rows)==40:
            break
    assert len(rows)==40
    with ThreadPoolExecutor(max_workers=8) as pool:
        for n,_ in enumerate(pool.map(download,rows),1):
            if n%5==0:
                print(f"Downloaded {n}/40",flush=True)
    (ROOT/"holdout.json").write_text(json.dumps(rows,indent=2)+"\n")


if __name__=="__main__":
    main()
