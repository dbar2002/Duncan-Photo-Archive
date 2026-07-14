# The Archive

A static photography archive built with [Astro](https://astro.build). Photos
are catalogued by date, location, and subject, with four ways to browse:

- **Index** — the full masonry grid, newest first
- **Timeline** — grouped by year
- **Map** — geotagged frames plotted on an interactive map (MapLibre GL, no API key)
- **Collections & Tags** — curated groupings and free-form tags

Images are optimized at build time; metadata is generated from EXIF by a small
Python script. Designed to scale from a few hundred photos to several thousand.

---

## Quick start

```bash
# 1. Install dependencies
npm install
pip install -r scripts/requirements.txt   # or: pip install pillow

# 2. Add photos
#    Drop image files into public/images/originals/

# 3. Generate metadata from EXIF
npm run metadata

# 4. Run the dev server
npm run dev            # http://localhost:4321

# 5. Build for production
npm run build          # output in dist/
```

If you open the site before adding any photos, every view renders an empty
state — that's expected.

---

## How it works

### The pipeline

```
public/images/originals/*.jpg
        │
        ▼   npm run metadata   (scripts/extract_metadata.py)
src/content/photos/*.json      ← one entry per photo, EXIF extracted
        │
        ▼   npm run build      (Astro + Sharp)
dist/                          ← optimized responsive images + static HTML
```

1. **You** add original images to `public/images/originals/`.
2. **`npm run metadata`** reads each file's EXIF (date, GPS, camera settings,
   dimensions) and writes a JSON entry to `src/content/photos/`.
3. **`npm run build`** turns those entries into pages and generates the site.

### Metadata

Each photo is one JSON file in `src/content/photos/`, validated against the
schema in `src/content/config.ts`. Generated fields come from EXIF; a few are
meant for you to fill in by hand:

| Field        | Source     | Notes                                              |
|--------------|------------|----------------------------------------------------|
| `src`        | auto       | Path under `/public`                               |
| `date`       | EXIF       | Falls back to file modified-time if no EXIF date   |
| `width/height` | auto     | Used to reserve layout space (no reflow)           |
| `location`   | EXIF GPS   | Only present if the photo is geotagged             |
| `exif`       | EXIF       | Camera, lens, focal length, aperture, shutter, ISO |
| `title`      | **manual** | Shown on the detail page                           |
| `caption`    | **manual** | Short description                                  |
| `tags`       | **manual** | Array of strings; each becomes a filter page       |
| `collection` | **manual** | Single grouping name                               |
| `location.place` | **manual** | Human-readable place name for the map popup    |

**Re-running is safe.** `npm run metadata` updates entries in place and
preserves your hand-edited `title`, `caption`, `tags`, `collection`, and
`location.place`. Pass `--force` (`python3 scripts/extract_metadata.py --force`)
to overwrite those too.

See `src/content/photos/_example.json` for a fully populated entry. Files
starting with `_` are ignored by Astro, so it's a safe reference.

---

## Adding photos day-to-day

1. Copy new images into `public/images/originals/`.
2. `npm run metadata`
3. Open the new JSON files in `src/content/photos/` and add titles, captions,
   tags, and a collection.
4. `npm run dev` to preview, `npm run build` to ship.

No geotag on a photo? It simply won't appear on the map — everything else works.

---

## Project structure

```
photo-archive/
├── astro.config.mjs           # Astro + Sharp image config
├── package.json
├── scripts/
│   ├── extract_metadata.py     # EXIF → JSON metadata
│   └── requirements.txt
├── public/
│   ├── favicon.svg
│   └── images/originals/       # ← your source images live here
└── src/
    ├── content/
    │   ├── config.ts            # photo schema (Zod)
    │   └── photos/              # ← generated metadata, one JSON per photo
    ├── layouts/
    │   └── Base.astro           # shell: masthead, nav, footer
    ├── components/
    │   ├── Gallery.astro        # masonry grid (CSS columns, no JS)
    │   ├── PhotoTile.astro      # single grid tile
    │   └── SectionHead.astro    # page headers
    ├── lib/
    │   └── photos.ts            # query helpers (sort, group, tags, geo)
    ├── styles/
    │   └── global.css           # design tokens + base styles
    └── pages/
        ├── index.astro          # Index (full grid)
        ├── timeline.astro       # Timeline (by year)
        ├── map.astro            # Map (MapLibre GL)
        ├── about.astro
        ├── collections/
        │   ├── index.astro      # collections + tag cloud
        │   └── [collection].astro
        ├── tags/
        │   └── [tag].astro
        └── photo/
            └── [id].astro       # detail view with EXIF + prev/next
```

---

## Image optimization at scale

The grid currently serves originals directly with lazy-loading, which is fine
into the low hundreds. As you approach thousands of photos, switch the tiles to
Astro's build-time image pipeline for responsive `srcset` + WebP/AVIF:

1. Move originals into `src/images/` (so Astro can process them), or use
   [`astro:assets`](https://docs.astro.build/en/guides/images/) with remote/public images.
2. In `PhotoTile.astro`, replace the raw `<img>` with the `<Image />` /
   `<Picture />` component and point it at the source.

Sharp (already a dependency) generates the variants during `npm run build`.
This keeps large galleries fast without changing the metadata pipeline.

---

## Design

Near-black canvas so images carry the page; one warm off-white for text, a
single brass accent, and a monospace utility face for the accession labels
(`AR-0001`) that give the archive its museum-catalogue voice. Everything
responds down to mobile, keyboard focus is always visible, and reduced-motion
preferences are respected.

Tokens live at the top of `src/styles/global.css` — change the palette there
and it propagates everywhere.

---

## Deploying

Any static host works. **Cloudflare Pages** is a good default (fast image CDN,
generous free tier):

- Build command: `npm run build`
- Output directory: `dist`

Also fine: Netlify, Vercel, GitHub Pages. Set your production URL in
`astro.config.mjs` (`site:`) so canonical links and sitemaps are correct.

> Note: `npm run metadata` is a local authoring step. Commit the generated
> JSON in `src/content/photos/` and your images so the host only needs to run
> `npm run build`.
```
