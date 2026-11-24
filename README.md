# Slide Quality Review

A small out-of-focus region can make a scanned tissue image hard to analyze, and it is easy to miss when reviewing a batch at thumbnail scale. I built Slide Quality Review to prioritize images with suspicious regions, show reviewers where to look, and turn their decisions into a rescan list.

[Open the browser tool](https://martaforjaz.github.io/slide-quality/)

Load the example pair or add a batch of PNG or JPEG images. The queue is sorted by the fraction of tissue tiles flagged. Toggle the overlay to inspect the original texture, record a decision, and export the decisions and region coordinates as CSV. Images are processed in the current browser tab and review state is kept for that session.

## Controlled validation

The example uses an IHC micrograph from the Center for Microscopy and Molecular Imaging, distributed by [scikit-image](https://scikit-image.org/docs/stable/api/skimage.data.html#skimage.data.immunohistochemistry). A second copy has a 192 × 192 pixel region blurred with a Gaussian filter. The original produced zero alerts across 52 eligible tiles. The edited copy produced seven alerts, all inside the injected region. Nine grid tiles intersect the region, and the tissue mask determines which tiles are eligible.

[Raw validation results](results.json)

The algorithm filters low-saturation background and compares local Laplacian energy with the upper quartile of tissue tiles in the same image. Relative scores prioritize localized patches. Tissue texture and magnification can affect alerts and uniformly blurred images can lack a sharp internal reference. The validation uses one source micrograph and controlled blur. Performance on scanner-native focus defects and time savings in a human review study remain unmeasured. Inputs are raster previews, resized to at most 1,600 pixels on the long side.

## Reproduce

```sh
pip install scikit-image Pillow
python prepare_example.py
node evaluate.mjs
python -m http.server 8781 --directory site
```

Open http://127.0.0.1:8781. No thesis data or code is included.
