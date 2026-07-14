import { getCollection, type CollectionEntry } from 'astro:content';

export type Photo = CollectionEntry<'photos'>;

/** All photos, newest first. */
export async function getPhotos(): Promise<Photo[]> {
  const photos = await getCollection('photos');
  return photos.sort(
    (a, b) => b.data.date.valueOf() - a.data.date.valueOf()
  );
}

/** Photos grouped by year (newest year first), each year newest-first. */
export async function getPhotosByYear(): Promise<[string, Photo[]][]> {
  const photos = await getPhotos();
  const map = new Map<string, Photo[]>();
  for (const p of photos) {
    const year = String(p.data.date.getFullYear());
    (map.get(year) ?? map.set(year, []).get(year)!).push(p);
  }
  return [...map.entries()].sort((a, b) => Number(b[0]) - Number(a[0]));
}

/** Unique tags with counts, most-used first. */
export async function getTags(): Promise<{ tag: string; count: number }[]> {
  const photos = await getPhotos();
  const counts = new Map<string, number>();
  for (const p of photos) {
    for (const t of p.data.tags) counts.set(t, (counts.get(t) ?? 0) + 1);
  }
  return [...counts.entries()]
    .map(([tag, count]) => ({ tag, count }))
    .sort((a, b) => b.count - a.count);
}

/** Unique collections with counts. */
export async function getCollections(): Promise<{ name: string; count: number }[]> {
  const photos = await getPhotos();
  const counts = new Map<string, number>();
  for (const p of photos) {
    const c = p.data.collection;
    if (c) counts.set(c, (counts.get(c) ?? 0) + 1);
  }
  return [...counts.entries()]
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => a.name.localeCompare(b.name));
}

/** Only photos that carry coordinates — for the map. */
export async function getGeoPhotos(): Promise<Photo[]> {
  const photos = await getPhotos();
  return photos.filter((p) => p.data.location);
}

/** Stable accession number, e.g. AR-0001, from position in the full index. */
export function accession(index: number): string {
  return `AR-${String(index + 1).padStart(4, '0')}`;
}

/** Slugify a tag or collection name for use in URLs. */
export function slug(value: string): string {
  return value
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}
