"""Fit a small logistic detector on the original cohort and measure a fresh holdout."""
import json
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).parent


def counts(rows, name):
    result = dict(tp=0, fp=0, tn=0, fn=0, abstain=0)
    for r in rows:
        p, truth = r[name], r["label"] == "Out of Focus"
        result["abstain" if p is None else ("tp" if p else "fn") if truth else ("fp" if p else "tn")] += 1
    return result


def main():
    rows = json.loads((ROOT/"cache/focus-features.json").read_text())
    train = [r for r in rows if r["split"] == "train" and r["features"] is not None]
    test = [r for r in rows if r["split"] == "test"]
    x = np.array([r["features"] for r in train])
    y = [r["label"]=="Out of Focus" for r in train]
    scaler = StandardScaler().fit(x)
    model = LogisticRegression(C=1).fit(scaler.transform(x),y)
    config = dict(mean=scaler.mean_.tolist(),scale=scaler.scale_.tolist(),
                  weights=model.coef_[0].tolist(),intercept=float(model.intercept_[0]))
    threshold = json.loads((ROOT/"scanner-results.json").read_text())["threshold"]
    for r in test:
        values = r["features"]
        r["calibrated"] = None if values is None else r["energy"] < threshold
        r["combined"] = None if values is None else bool(model.predict(scaler.transform([values]))[0])
    report = dict(training=len(train),test=len(test),model=config,
                  methods={mode:counts(test,mode) for mode in ("original","calibrated","combined")},rows=test)
    (ROOT/"holdout-results.json").write_text(json.dumps(report,indent=2)+"\n")
    print(report["methods"])


if __name__=="__main__":
    main()
