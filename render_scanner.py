"""Publish representative held-out examples and a confusion-count figure."""
import json
from pathlib import Path
import shutil

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

root = Path(__file__).parent
site = root/"site"
data = json.loads((root/"scanner-results.json").read_text(encoding="utf8"))
test = [row for row in data["rows"] if row["split"] == "test"]
examples = []
for truth, predicted in (("Out of Focus",True),("In Focus",False),("In Focus",True),("Out of Focus",False)):
    match = next((r for r in test if r["label"] == truth and r["prediction"] is predicted), None)
    if match:
        name = "scanner-"+match["file"]
        shutil.copyfile(root/"cache"/"patches"/match["file"],site/name)
        examples.append({"src":name,"organ":match["organ"],"label":truth,"source_member":match["member"]})
(site/"scanner-demo.json").write_text(json.dumps({"threshold":data["threshold"],"examples":examples},indent=2)+"\n")
fig, axes=plt.subplots(1,2,figsize=(6.6,3.05),layout="constrained")
for ax,(name,key) in zip(axes,[("Local overlay baseline","baseline"),("Calibrated patch score","calibrated")]):
    c=data[key]
    matrix=[[c["tn"],c["fp"]],[c["fn"],c["tp"]]]
    ax.imshow(matrix,cmap="Blues",vmin=0,vmax=max(1,len(test)//2))
    for y in range(2):
        for x in range(2):
            ax.text(x,y,str(matrix[y][x]),ha="center",va="center",color="white" if matrix[y][x]>len(test)*.28 else "#142d50",fontsize=16)
    ax.set(title=name,xticks=[0,1],xticklabels=["No alert","Alert"],yticks=[0,1],yticklabels=["In focus","Out of focus"])
    ax.tick_params(length=0)
    ax.set_xlabel("Tool output")
    for spine in ax.spines.values():spine.set_visible(False)
axes[0].set_ylabel("Dataset annotation")
fig.savefig(site/"scanner-benchmark.png",dpi=200)
