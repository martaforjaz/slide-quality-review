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

## Real scanner validation

![Confusion counts on held-out scanner patches](site/scanner-benchmark.png)

I sampled **40 TCGA@Focus patches from 40 different source slides** across adrenal gland, bladder, brain, breast and bronchus/lung. The source labels are region-level focus annotations. Twenty patches were reserved for calibration and twenty for evaluation. Both splits contain ten in-focus and ten out-of-focus patches. The cohort manifest records the exact ZIP members, and the acquisition script uses HTTP range requests to avoid downloading the full archive.

| Held-out result | Found blur | False alerts | Clear patches correctly passed | Missed blur |
| --- | ---: | ---: | ---: | ---: |
| Original local heuristic | 8/10 | 5/10 | 5/10 | 2/10 |
| Calibrated patch score | 5/10 | 0/10 | 10/10 | 5/10 |

The local heuristic treats a patch as an alert if any eligible sub-tile falls below 20% of that image's upper-quartile focus energy. The calibrated mode uses median absolute Laplacian energy and selects its threshold on the calibration slides only, maximizing balanced accuracy and preferring fewer false alerts on ties. The two modes make different tradeoffs. The calibrated mode reduced false alerts in this sample while missing more annotated blur. The demo offers both modes for the scanner examples. Results are patch-level and do not establish pixel-level localization accuracy or generalization to other scanners.

[Per-patch predictions](scanner-results.json) · [Cohort manifest](cohort.json) · [Source dataset and licence](https://zenodo.org/records/3910757)

To rerun the scanner benchmark, install remotezip, requests and matplotlib alongside Pillow, then run:

```sh
python acquire_tcga.py
node evaluate_scanner.mjs
python render_scanner.py
```

## Supported inputs

The browser tool accepts exported PNG and JPEG tiles or raster previews. Scanner formats such as SVS, NDPI, MRXS and pyramidal OME-TIFF need a separate reader to extract tiles at a consistent magnification. Importing a downsampled screenshot of a whole slide cannot reveal focus defects at native resolution. The absolute threshold in this project is applied to the provided TCGA examples. User uploads use the local overlay, whose scores depend on stain, texture, compression and scale.

## Review a WSI folder

Download the repository and run these commands on the computer that can already open the slide folder. On Windows, paste the full UNC path beginning with two backslashes in the desktop window, or use **Browse**. Select **Review folder** to open the report.

```sh
pip install openslide-python openslide-bin numpy Pillow
python desktop.py
```

For a saved report or scripted runs, use `python review_folder.py "PATH_TO_SLIDES" --output "PATH_TO_REPORT"`. The report stores a reduced PNG of each slide, a second PNG with suspicious sampled regions, and an alerts CSV with level-zero coordinates. Desktop runs create a separate local temporary report for each batch. Files are read locally with the current Windows account; nothing is uploaded to the portfolio.

OpenSlide must recognize the scanner format. The reader selects a pyramid level near 10× when the objective is recorded, samples a bounded grid, and scores tissue regions. The PNG is a map for review. Sampling can miss small focus defects, and the WSI workflow has not been validated across scanner formats or on the private example folder.
