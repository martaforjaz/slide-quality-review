"""Read a folder of slides locally and render a coordinate-preserving QA report."""
import argparse
import csv
import json
from html import escape
from pathlib import Path
import sys

import numpy as np
import openslide
from PIL import Image, ImageDraw

EXTENSIONS = {".svs", ".ndpi", ".mrxs", ".scn", ".vms", ".vmu", ".bif", ".tif", ".tiff"}
TILE = 256
MAX_CELLS = 24


def focus(rgb):
    pixels = np.asarray(rgb, dtype=np.float32)
    gray = pixels @ np.array([.299, .587, .114], dtype=np.float32)
    tissue = (np.ptp(pixels, axis=2) > 17) & (gray < 237)
    if tissue.mean() < .22:
        return None
    lap = 4 * gray[1:-1, 1:-1] - gray[:-2, 1:-1] - gray[2:, 1:-1] - gray[1:-1, :-2] - gray[1:-1, 2:]
    return float(np.mean(lap ** 2))


MODEL = json.loads((Path(__file__).parent / "site/scanner-demo-v2.json").read_text())["model"]


def combined_focus(tile):
    pixels = np.asarray(tile, dtype=np.float32)
    gray = pixels @ np.array([.299, .587, .114], dtype=np.float32)
    chroma = np.ptp(pixels, axis=2)
    energies, ratios = [], []
    for y in range(0, gray.shape[0], 64):
        for x in range(0, gray.shape[1], 64):
            section = gray[y:y+64, x:x+64]
            if min(section.shape) < 16:
                continue
            center = section[1:-1, 1:-1]
            stained = chroma[y:y+64, x:x+64][1:-1, 1:-1] > 17
            if np.mean(stained & (center < 237)) < .22:
                continue
            top, bottom = section[:-2, 1:-1], section[2:, 1:-1]
            left, right = section[1:-1, :-2], section[1:-1, 2:]
            energy = float(np.mean((4*center-top-bottom-left-right)**2))
            gradient = float(np.mean((right-left)**2+(bottom-top)**2))
            energies.append(energy)
            ratios.append(energy/(1+gradient))
    if not energies:
        return None
    energies.sort()
    ratios.sort()
    last = len(energies)-1
    median = np.log1p(energies[int(last*.5)])
    features = [median, np.log1p(energies[int(last*.25)]),
                np.log1p(ratios[int(last*.5)]), np.log1p(energies[int(last*.75)])-median]
    return float(MODEL["intercept"] + sum(
        (value-mean)/scale*weight
        for value, mean, scale, weight in zip(features, MODEL["mean"], MODEL["scale"], MODEL["weights"])
    ))


def inspect(path, output, stem):
    with openslide.OpenSlide(str(path)) as slide:
        width, height = slide.dimensions
        # Prefer approximately 10x when the objective is available.
        objective = slide.properties.get(openslide.PROPERTY_NAME_OBJECTIVE_POWER)
        try:
            downsample = max(1, float(objective) / 10)
        except (TypeError, ValueError):
            downsample = 4
        level = slide.get_best_level_for_downsample(downsample)
        step = slide.level_downsamples[level]
        window = min(width, height, round(TILE * step))
        read_side = max(1, int(window / step))
        single = slide.level_count == 1 and width * height > 80_000_000
        if single:
            scale = 1000 / max(width, height)
            preview = Image.new("RGB", (max(1, round(width * scale)), max(1, round(height * scale))), "white")
        else:
            preview = slide.get_thumbnail((1500, 1500)).convert("RGB")
        sampled = []
        grid_limit = 12 if single else MAX_CELLS
        xs = np.unique(np.linspace(0, width-window, min(grid_limit, max(1, width//window)), dtype=int))
        ys = np.unique(np.linspace(0, height-window, min(grid_limit, max(1, height//window)), dtype=int))
        for j, y in enumerate(ys):
            for i, x in enumerate(xs):
                tile = slide.read_region((int(x), int(y)), level, (read_side, read_side)).convert("RGB")
                energy = focus(tile)
                if single:
                    left, right = round(i*preview.width/len(xs)), round((i+1)*preview.width/len(xs))
                    top, bottom = round(j*preview.height/len(ys)), round((j+1)*preview.height/len(ys))
                    preview.paste(tile.resize((right-left, bottom-top), Image.Resampling.BILINEAR), (left,top))
                    box = (left, top, right-1, bottom-1)
                else:
                    sx, sy = preview.width / width, preview.height / height
                    box = (x*sx, y*sy, (x+window)*sx, (y+window)*sy)
                if energy is not None:
                    sampled.append((int(x), int(y), energy, box, combined_focus(tile)))
        preview.save(output / f"{stem}.png")
        baseline = float(np.percentile([row[2] for row in sampled], 75)) if sampled else 0
        highlights = []
        legacy, combined = preview.copy(), preview.copy()
        legacy_draw, combined_draw = ImageDraw.Draw(legacy), ImageDraw.Draw(combined)
        for x, y, energy, box, score in sampled:
            old = bool(baseline and energy / baseline < .20)
            new = score is not None and score >= 0
            if old:
                legacy_draw.rectangle(box, outline="#ef6d32", width=2)
            if new:
                combined_draw.rectangle(box, outline="#ef6d32", width=2)
            if old or new or score is None:
                highlights.append((x, y, window, level, round(energy / baseline, 5) if baseline else "",
                                   old, "" if score is None else new, round(score, 5) if score is not None else ""))
        legacy.save(output / f"{stem}-original-alerts.png")
        combined.save(output / f"{stem}-alerts.png")
        return len(sampled), highlights, level, single


def report(folder, output):
    if not folder.is_dir():
        raise ValueError("Folder unavailable. Check the path and your network access.")
    output.mkdir(parents=True, exist_ok=True)
    cards, errors, results = [], [], []
    for index, path in enumerate(sorted(folder.iterdir())):
        if not path.is_file() or path.suffix.lower() not in EXTENSIONS:
            continue
        stem = f"slide-{index:04}"
        try:
            count, hits, level, sampled_map = inspect(path, output, stem)
        except (OSError, openslide.OpenSlideError) as exc:
            errors.append(f"{path.name}: {exc}")
            continue
        original = sum(hit[5] for hit in hits)
        combined = sum(hit[6] is True for hit in hits)
        overlap = sum(hit[5] and hit[6] is True for hit in hits)
        missing = sum(hit[6] == "" for hit in hits)
        label = (f"Original: {original} | Combined: {combined} | Both: {overlap} | Tissue samples: {count} | Combined unscored: {missing}" if count
                 else "No eligible tissue samples")
        preview_kind = "sampled tile map" if sampled_map else "slide thumbnail"
        print(f"Reviewed slide {len(cards)+1}: {original} original, {combined} combined, {overlap} shared / {count} tissue samples; {missing} unscored", flush=True)
        cards.append((combined, f'<article><h2>{escape(path.name)}</h2><p>{label} · pyramid level {level}</p>'
                      f'<a href="{stem}.png">PNG without alerts</a><div class="pair"><div><h3>Original</h3><a href="{stem}-original-alerts.png"><img loading="lazy" src="{stem}-original-alerts.png" alt="Original detector alerts"></a></div><div><h3>Combined</h3><a href="{stem}-alerts.png"><img loading="lazy" src="{stem}-alerts.png" alt="Combined detector alerts"></a></div></div></article>'))
        safe_name = "'" + path.name if path.name.startswith(("=", "+", "-", "@", "\t", "\r")) else path.name
        results.extend((safe_name, count, *hit) for hit in hits)
    with (output / "alerts.csv").open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file)
        writer.writerow(("slide", "tissue_samples", "level0_x", "level0_y", "level0_window", "read_level", "focus_ratio", "original_alert", "combined_alert", "combined_score"))
        writer.writerows(results)
    body = "".join(card for _, card in sorted(cards, key=lambda item: -item[0]))
    failures = "".join(f"<li>{escape(error)}</li>" for error in errors)
    (output / "index.html").write_text(
        '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
        '<title>Slide review report</title><style>body{max-width:1000px;margin:2rem auto;padding:0 1rem;'
        'font:16px system-ui;color:#142d50}img{display:block;width:min(100%,850px);margin:1rem 0}'
        ' .pair{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px}article{border-top:1px solid #cbd9e8;margin-top:1.5rem}</style>'
        '<h1>Slide review</h1><a href="alerts.csv">Download alerts CSV</a>'
        f'<p>{len(cards)} slides reviewed · {len(errors)} unreadable</p>'
        '<p>Orange outlines show suspicious sampled regions. Review at full resolution before deciding. The combined detector was trained on public patches and these slides have no reference focus labels.</p>'
        + body + (f"<h2>Unreadable slides</h2><ul>{failures}</ul>" if errors else "")
        + ("<p>No compatible slides were opened.</p>" if not cards else ""),
        encoding="utf-8",
    )
    return len(cards), len(errors)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("folder", type=Path)
    parser.add_argument("--output", type=Path, default=Path("slide-review-output"))
    args = parser.parse_args()
    try:
        done, unreadable = report(args.folder, args.output)
    except (ValueError, OSError) as exc:
        sys.exit(str(exc))
    print(f"{done} slides reviewed, {unreadable} unreadable. Open {args.output / 'index.html'}.")
