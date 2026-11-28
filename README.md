# Restroom Reach

A public browser map for finding OpenStreetMap toilet records, inspecting accessibility tags and keeping dated evidence. Published at **https://coolcode.ca/restroomreach/**.

<!-- coolcode:guide -->
Choose an area guide for Metro Vancouver and Langley, Halifax, central Ottawa or central Winnipeg. See its mapped washrooms, compare wheelchair-access, changing-table and fee tags, and open the matching results on the map. Each guide shows its coverage rectangle and source date. Blank tags are unknown. Distance sorting and the optional street map are available in the finder.
A weekly refresh collects all configured regions before publishing. A failed or incomplete region keeps the last good capture available.
<!-- /coolcode:guide -->

[Browse the published washroom guides by area](https://coolcode.ca/restroomreach/areas/).

## What works

- Retained extracts for Metro Vancouver/Langley, the Halifax region, central Ottawa (Ontario) and central Winnipeg (Manitoba). The city pages show the exact rectangular coverage and change with each successful refresh. These are `amenity=toilets` nodes, ways and relations, not every venue that may have a restroom.
- A map and matching list with search, wheelchair/access/fee/changing-table filters, optional street tiles, source tags and original OSM links.
- User-entered coordinates, voluntary browser geolocation, nearest-first sorting and a distance radius. Coordinates stay in the tab; no geocoding or routing server receives them.
- Download the full capture JSON or the filtered CSV; import another valid Restroom Reach receipt locally. Eight source captures are retained by default, with changed tags/location and newly present/absent object counts when geographic coverage is comparable.
- Unknown is never shown as no. Opening-hours text is preserved but is not evaluated into an “open now” promise. Approximate way/relation centres do not establish an entrance location.

## Source freshness

The first capture was downloaded **23 November 2026** from the Private.coffee Overpass instance. Its response explicitly reports an OSM database edition of **15 July 2026**. The app displays both dates. This edition is useful historical mapping evidence, but must not be treated as current availability or a current accessibility survey.

The collector queries each configured region separately and sequentially, with an identifying User-Agent, a 90-second query budget and a bounded response size. Scheduled capture runs on **Tuesdays at 08:47 UTC**. Collector/configuration changes trigger collection; other code pushes rebuild the retained copy offline. A temporary connection failure or HTTP 500/502/503/504 gets one retry after five seconds. HTTP 403/429 does not. There are no per-visitor Overpass queries or automatic endpoint failovers. A source failure, timeout, truncated response, empty region or unexpected count collapse fails the refresh and preserves the last good deployed copy.

Following repeated collection failures at the original endpoint, the four-area capture was retrieved on 28 November 2026 using the configured OpenStreetMap France Overpass endpoint. Capture metadata keeps each edition’s source URL. The collector runs one bounded GET per region and never queries the service when a visitor filters the map.

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

Then push the config and run **Actions → Restroom Reach · Capture, check and publish → Run workflow → Refresh the configured OpenStreetMap regional extracts**. The default manual `refresh` checkbox is enabled. A config push also triggers collection. A successful refresh collects, tests, commits the new capture and deploys it.

Other controls:

- `sourceUrl`: an HTTPS Overpass instance permitted for your use. The configured source is the OpenStreetMap France Overpass endpoint. For larger coverage, use an appropriate dedicated service or regional dump; don't increase workload indefinitely on public instances.
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
- [OpenStreetMap France Overpass endpoint](https://overpass.openstreetmap.fr/api/interpreter)
- [Original Private.coffee Overpass source](https://overpass.private.coffee/)
- [OSM raster tile policy](https://operations.osmfoundation.org/policies/tiles/)
- [Leaflet](https://leafletjs.com/)

## Validation

Unit tests cover missing-vs-no accessibility, access filtering, coordinates/dateline distance, expandable coverage, source-error rejection, count-collapse safeguards, unsafe IDs, formula-safe exports and retention on failed imports. Browser CI exercises the real saved extract at a project subpath, filtering, distance presets, capture export/import, safe empty results and mobile width. Browser checks use the bundled data and do not query Overpass or download street tiles.

<!-- schedule-reliability -->
## Schedule reliability

Public GitHub repositories can have scheduled workflows disabled after 60 days of inactivity. A separate weekly [schedule guard](.github/workflows/schedule-guard.yml) calls GitHub's enable-workflow API for an explicit list of refresh workflows and itself. It can restore workflows disabled for inactivity, preserves manually disabled workflows, and runs independently of collection failures.

The separate schedule guard remains a mitigation, not a scheduling guarantee. The independent [CoolCode refresh watchdog](https://github.com/jsdyer/jsdyer.github.io/blob/main/services/refresh-watchdog/README.md) is maintained in GitHub and uses the generated workflow and freshness registry; do not maintain another target list here. Using it requires installation on a Linux server and GitHub credentials with access to this repository. A generated target does not prove that a private server has adopted it; verify the installed service's report. The guard does not collect data, create dummy commits or change source/check timestamps. Successful collection and published data freshness still need monitoring.
<!-- /schedule-reliability -->

### Regional download recovery

Each configured region is collected separately, sequentially, using a bounded Overpass GET. A timeout, connection error, or HTTP 500/502/503/504 gets one retry after five seconds. HTTP 403/429 is left for a later watchdog attempt. Every region must pass validation before the published index changes; a partial result cannot replace the previous capture. The oldest source database timestamp is retained across regional responses, separately from the capture time.

Changes to the collector or its region configuration trigger collection on push. Ordinary page edits build the retained snapshot. Scheduled and requested refreshes keep their existing behavior.
