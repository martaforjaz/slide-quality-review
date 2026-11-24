"""Generate a public tiled-TIFF example and its local WSI review report."""
from pathlib import Path
import argparse

import numpy as np
from PIL import Image, ImageFilter
import tifffile

from review_folder import report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("slide-review-output"))
    args = parser.parse_args()
    inputs = args.output / "input"
    inputs.mkdir(parents=True, exist_ok=True)
    site = Path(__file__).resolve().parent / "site"
    with Image.open(site / "reference.png") as original:
        reference = original.convert("RGB")
    altered = reference.copy()
    region = (256, 0, 512, 256)
    altered.paste(reference.crop(region).filter(ImageFilter.GaussianBlur(7)), region[:2])
    for name, image in (("reference", reference), ("defocus", altered)):
        tifffile.imwrite(inputs / f"{name}.tiff", np.asarray(image),
                         tile=(128, 128), photometric="rgb")
    print(report(inputs, args.output / "report"))


if __name__ == "__main__":
    main()
