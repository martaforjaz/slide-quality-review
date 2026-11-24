"""Build the public comparison and representative held-out cases."""
import json
from pathlib import Path
import shutil

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

root = Path(__file__).resolve().parent
site = root / "site"
report = json.loads((root / "holdout-results.json").read_text())
threshold = json.loads((root / "scanner-results.json").read_text())["threshold"]
cases = []
for truth, prediction in (("Out of Focus", True), ("In Focus", False),
                          ("In Focus", True), ("Out of Focus", False)):
    row = next(r for r in report["rows"] if r["label"] == truth and r["combined"] is prediction)
    src = "scanner-" + row["file"]
    shutil.copyfile(root / "cache" / "patches" / row["file"], site / src)
    cases.append(dict(src=src, organ=row["organ"], label=truth, source_member=row["member"]))
(site / "scanner-demo-v2.json").write_text(json.dumps(dict(examples=cases, model=report["model"],
    threshold=threshold, summary=report["methods"]), indent=2) + "\n")
fig, axes = plt.subplots(1,2,figsize=(8.1,2.7),layout="constrained")
labels = ["Original", "Calibrated", "Combined"]
colors = ["#849eb6","#507196","#287868"]
for ax, metric, title in zip(axes,("tp","fp"),("Blur found","False alerts")):
    vals = [c[metric] for c in report["methods"].values()]
    for y,(value,color) in enumerate(zip(vals,colors)):
        ax.scatter(value,y,c=color,s=48,zorder=2)
        ax.annotate(f"{value}/20",(value,y),xytext=(7,0),textcoords="offset points",va="center")
    ax.set(yticks=range(3),yticklabels=labels,ylim=(2.5,-.5),xlim=(0,23),xticks=[0,5,10,15,20],
           xlabel="Patches",title=title)
    ax.grid(axis="x",alpha=.22)
    ax.spines[["top","right","left"]].set_visible(False)
    ax.tick_params(axis="y",length=0)
fig.savefig(site / "scanner-holdout.png",dpi=200)
