#!/usr/bin/env python3
"""
Walk public/images/originals/, read EXIF, and write one JSON entry per
photo into src/content/photos/. Re-running is safe: existing entries are
updated in place, and any fields you've hand-edited under `# manual`
keys are preserved (see MERGE below).

Usage:
    pip install pillow
    python scripts/extract_metadata.py

Options:
    --force   Overwrite manual fields too (title, caption, tags, collection).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from fractions import Fraction
from pathlib import Path

try:
    from PIL import Image, ExifTags
except ImportError:
    sys.exit("Pillow is required:  pip install pillow")

ROOT = Path(__file__).resolve().parents[1]
IMG_DIR = ROOT / "public" / "images" / "originals"
OUT_DIR = ROOT / "src" / "content" / "photos"
PUBLIC_PREFIX = "/images/originals"
EXTS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}

# Fields a human may edit; preserved on re-run unless --force.
MANUAL_FIELDS = ("title", "caption", "tags", "collection")

EXIF_TAGS = {v: k for k, v in ExifTags.TAGS.items()}
GPS_TAGS = {v: k for k, v in ExifTags.GPSTAGS.items()}


def _to_float(ratio) -> float:
    """PIL returns IFDRational / tuples; normalize to float."""
    try:
        return float(ratio)
    except (TypeError, ValueError):
        try:
            return ratio[0] / ratio[1]
        except Exception:
            return 0.0


def _dms_to_deg(dms, ref) -> float | None:
    try:
        deg = _to_float(dms[0]) + _to_float(dms[1]) / 60 + _to_float(dms[2]) / 3600
        if ref in ("S", "W"):
            deg = -deg
        return round(deg, 6)
    except Exception:
        return None


def _shutter(exposure) -> str | None:
    if not exposure:
        return None
    val = _to_float(exposure)
    if val <= 0:
        return None
    if val >= 1:
        return f"{val:g}s"
    frac = Fraction(val).limit_denominator(8000)
    return f"{frac.numerator}/{frac.denominator}s"


def extract(path: Path) -> dict:
    data: dict = {
        "src": f"{PUBLIC_PREFIX}/{path.name}",
        "date": None,
        "tags": [],
    }

    with Image.open(path) as im:
        data["width"], data["height"] = im.size
        raw = im.getexif()

        if raw:
            # Date taken
            for key in ("DateTimeOriginal", "DateTime"):
                tag = EXIF_TAGS.get(key)
                if tag and tag in raw:
                    try:
                        dt = datetime.strptime(str(raw[tag]), "%Y:%m:%d %H:%M:%S")
                        data["date"] = dt.isoformat()
                        break
                    except ValueError:
                        pass

            # Also check the Exif IFD for DateTimeOriginal + camera settings
            exif_ifd = raw.get_ifd(0x8769) if hasattr(raw, "get_ifd") else {}

            def ex(name):
                t = EXIF_TAGS.get(name)
                return exif_ifd.get(t) if t else None

            if not data["date"]:
                dto = ex("DateTimeOriginal")
                if dto:
                    try:
                        data["date"] = datetime.strptime(
                            str(dto), "%Y:%m:%d %H:%M:%S"
                        ).isoformat()
                    except ValueError:
                        pass

            make = raw.get(EXIF_TAGS.get("Make"), "")
            model = raw.get(EXIF_TAGS.get("Model"), "")
            camera = f"{make} {model}".strip()

            exif_out = {}
            if camera:
                exif_out["camera"] = camera
            lens = ex("LensModel")
            if lens:
                exif_out["lens"] = str(lens).strip()
            fl = ex("FocalLength")
            if fl:
                exif_out["focalLength"] = f"{_to_float(fl):g}mm"
            fn = ex("FNumber")
            if fn:
                exif_out["aperture"] = f"f/{_to_float(fn):g}"
            sh = _shutter(ex("ExposureTime"))
            if sh:
                exif_out["shutter"] = sh
            iso = ex("ISOSpeedRatings")
            if iso:
                exif_out["iso"] = int(iso if not isinstance(iso, tuple) else iso[0])
            if exif_out:
                data["exif"] = exif_out

            # GPS
            gps_ifd = raw.get_ifd(0x8825) if hasattr(raw, "get_ifd") else {}
            if gps_ifd:
                lat = _dms_to_deg(
                    gps_ifd.get(GPS_TAGS["GPSLatitude"]),
                    gps_ifd.get(GPS_TAGS["GPSLatitudeRef"]),
                )
                lng = _dms_to_deg(
                    gps_ifd.get(GPS_TAGS["GPSLongitude"]),
                    gps_ifd.get(GPS_TAGS["GPSLongitudeRef"]),
                )
                if lat is not None and lng is not None:
                    data["location"] = {"lat": lat, "lng": lng}

    # Fallback: file mtime if no EXIF date.
    if not data["date"]:
        data["date"] = datetime.fromtimestamp(path.stat().st_mtime).isoformat()

    return data


def merge(existing: dict, fresh: dict, force: bool) -> dict:
    """Keep hand-edited manual fields unless --force."""
    result = dict(fresh)
    if not force:
        for field in MANUAL_FIELDS:
            if field in existing and existing[field]:
                result[field] = existing[field]
        # Preserve a manually-added place name on the location object.
        if (
            existing.get("location", {}).get("place")
            and "location" in result
        ):
            result["location"]["place"] = existing["location"]["place"]
    return result


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    if not IMG_DIR.exists():
        sys.exit(f"Missing image dir: {IMG_DIR}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    images = sorted(p for p in IMG_DIR.iterdir() if p.suffix.lower() in EXTS)
    if not images:
        print(f"No images found in {IMG_DIR}")
        return

    written = 0
    for path in images:
        out_path = OUT_DIR / f"{path.stem}.json"
        fresh = extract(path)
        if out_path.exists():
            try:
                existing = json.loads(out_path.read_text())
            except json.JSONDecodeError:
                existing = {}
            fresh = merge(existing, fresh, args.force)
        out_path.write_text(json.dumps(fresh, indent=2) + "\n")
        written += 1
        print(f"  {path.name} → {out_path.name}")

    print(f"\nDone. {written} entr{'y' if written == 1 else 'ies'} written to {OUT_DIR}")


if __name__ == "__main__":
    main()
