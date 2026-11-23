# Restroom Reach

A public browser map for finding OpenStreetMap toilet records, inspecting accessibility tags and keeping dated evidence. Published at **https://coolcode.ca/restroomreach/**.

<!-- coolcode:guide -->
Choose a region, then filter wheelchair access, fees or changing tables. **Mapped yes** is a contributor’s report; **Not recorded** is a separate state. Expand **Sort by distance from a point** for coordinates or the Willoughby, Vancouver and Halifax presets. Distances are straight-line, not walking routes. Turn on **Show street map** only when you want background tiles. The capture date and OSM database edition are displayed separately: downloading an old source edition does not make the observations current. Export a receipt to retain the evidence outside this tab.
<!-- /coolcode:guide -->

## What works

- A retained **1,285-object** initial extract covering Metro Vancouver/Langley and the Halifax region. These are `amenity=toilets` nodes, ways and relations, not every venue that may have a restroom.
- A map and matching list with search, wheelchair/access/fee/changing-table filters, optional street tiles, source tags and original OSM links.
- User-entered coordinates, voluntary browser geolocation, nearest-first sorting and a distance radius. Coordinates stay in the tab; no geocoding or routing server receives them.
- Download the full capture JSON or the filtered CSV; import another valid Restroom Reach receipt locally. Eight source captures are retained by default, with changed tags/location and newly present/absent object counts when geographic coverage is comparable.
- Unknown is never shown as no. Opening-hours text is preserved but is not evaluated into an “open now” promise. Approximate way/relation centres do not establish an entrance location.

## Source freshness

The first capture was downloaded **23 November 2026** from the Private.coffee Overpass instance. Its response explicitly reports an OSM database edition of **15 July 2026**. The app displays both dates. This edition is useful historical mapping evidence, but must not be treated as current availability or a current accessibility survey.

The collector queries the configured endpoint once per run, with an identifying User-Agent, a 90-second query budget and a bounded response size. Scheduled capture runs on **Tuesdays at 08:47 UTC**. Normal code pushes rebuild the retained copy offline. There are no per-visitor Overpass queries and no automatic retries or failover that could multiply load. A source failure, timeout, truncated response, empty region or unexpected count collapse fails the refresh and preserves the last good deployed copy.

The primary overpass-api.de endpoint returned HTTP 502 while seeding this release. Its former Kumi alternative returned 503; the currently documented **overpass.private.coffee** endpoint returned a complete JSON response. These are independent service failures, not evidence of an OSM data deletion.

## Expand or customize

Edit [`web/config.json`](web/config.json). `regions` is the coverage watchlist; `presets` only chooses convenient local reference points. Adding a preset does not download data for a new area.

For example, append a new region and a reference point:

```json
{
  "region": {
    "id": "victoria",
    "name": "Victoria area",
    "bbox": [48.35, -123.60, 48.60, -123.20],
    "center": [48.4284, -123.3656]
  },
  "preset": {
    "name": "Victoria",
    "region": "victoria",
    "lat": 48.4284,
    "lon": -123.3656
  }
}
```

Place the `region` object inside the `regions` array and the `preset` object inside `presets`. Bounds use **south, west, north, east**. Keep 1–10 regions, each below four square degrees. These are source safeguards, not a hard-coded number of example cities. The selected capture supplies its own regions, so older captures still work after the current configuration expands.

Then push the config and run **Actions → Restroom Reach · Capture, check and publish → Run workflow → Refresh the configured OpenStreetMap regional extracts**. The default manual `refresh` checkbox is enabled. A config push alone rebuilds the saved dataset; a successful refresh collects, tests, commits the new capture and deploys it.

Other controls:

- `sourceUrl`: an HTTPS Overpass instance permitted for your use. The default is the documented Private.coffee service. For larger coverage, use an appropriate dedicated service or regional dump; don't increase workload indefinitely on public instances.
- `minimumRecordsPerRegion`, `maximumRecords`, `maximumDropFraction`: reject likely partial/source-error captures. Investigate a legitimate coverage change before adjusting these.
- `retainedCaptures`: 1–52 retained files; default 8.
- `pageSize`: number of list entries at once, capped in the browser at 100. All filtered points remain on the map.
- `tileUrl` and `tileAttribution`: optional background service; default OSM raster tiles. Use a provider whose terms permit the intended traffic. Attribution must remain accurate and visible.

Local refresh and build:

```sh
python3 scripts/refresh.py
node --test tests/*.test.mjs
python3 -m unittest discover -s tests -v
python3 scripts/build.py
```

`python3 scripts/refresh.py --input path/to/overpass.json` normalizes an already downloaded response for reproducibility. It records the response’s source edition separately from the import/capture time. No API key or registration is required.

## Privacy and licence

Searches, coordinates, selected places and imported JSON are processed in this tab. No location or imported receipt is saved in browser storage. The browser’s geolocation permission is requested only after **Use my location** is pressed. The export contains the published extract, not the user's reference point.

Background street tiles are **off by default**. Enabling them sends normal tile requests to OpenStreetMap, which receives the viewer's IP address and can infer the viewed area. Tiles are only loaded for the current viewport, are not bulk downloaded, use browser caching and retain the origin referrer. Source links contact their named service when opened. CoolCode’s shared visit counter and issue-report link use the normal site infrastructure.

Database and derived extracts: **© OpenStreetMap contributors, ODbL 1.0**. The retained JSON is distributed under that licence. Preserve attribution and licence when reusing it. Mapper usernames and user IDs are not included. Leaflet 1.9.4 is vendored under its BSD-2-Clause licence in `web/vendor/leaflet/LICENSE`.

Official source documentation:

- [OSM copyright and attribution](https://www.openstreetmap.org/copyright)
- [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/)
- [Toilet tagging](https://wiki.openstreetmap.org/wiki/Tag:amenity%3Dtoilets)
- [Overpass public instances and usage policies](https://wiki.openstreetmap.org/wiki/Overpass_API#Public_Overpass_API_instances)
- [Private.coffee Overpass](https://overpass.private.coffee/)
- [OSM raster tile policy](https://operations.osmfoundation.org/policies/tiles/)
- [Leaflet](https://leafletjs.com/)

## Validation

Unit tests cover missing-vs-no accessibility, access filtering, coordinates/dateline distance, expandable coverage, source-error rejection, count-collapse safeguards, unsafe IDs, formula-safe exports and retention on failed imports. Browser CI exercises the real saved extract at a project subpath, filtering, distance presets, capture export/import, safe empty results and mobile width. Browser checks use the bundled data and do not query Overpass or download street tiles.
