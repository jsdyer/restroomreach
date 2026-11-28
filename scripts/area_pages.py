"""Build accessible washroom guides from the same dated capture as the finder."""
from collections import Counter
from html import escape
import json
from pathlib import Path
import re
from urllib.parse import urlencode
import xml.etree.ElementTree as ET

OSM = "https://www.openstreetmap.org"
SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


def region_links(regions, prefix):
    return '<ul class="region-links">' + ''.join(
        f'<li><a href="{prefix}{r["id"]}/">{escape(r["name"])}</a></li>' for r in regions
    ) + '</ul>'


def layout(title, description, url, back, content):
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)} · Restroom Reach</title><meta name="description" content="{escape(description, quote=True)}">
<link rel="canonical" href="{escape(url, quote=True)}"><link rel="stylesheet" href="{back}style.css"></head>
<body class="guide"><header><a class="brand" href="{back}">Restroom Reach</a><a href="https://coolcode.ca/">CoolCode</a></header>
<main><h1>{escape(title)}</h1><p class="intro">{escape(description)}</p>{content}</main>
<footer><a href="{OSM}/copyright">© OpenStreetMap contributors</a>
<a href="https://opendatacommons.org/licenses/odbl/1-0/">Open Database Licence 1.0</a>
<a href="{back}#method">Sources and method</a></footer></body></html>'''


def map_link(region, **filters):
    params = urlencode({"region": region, **filters})
    return f'../../?{escape(params, quote=True)}#explore'


def area_page(region, records, capture, edition, url):
    region_id = region["id"]
    title = f'Mapped washrooms in {region["name"]}'
    description = f'{len(records):,} mapped washroom records inside this area. Choose a filter to open the matching places on the map.'
    features = (
        ("Wheelchair access", "wheelchair", "wheelchair", "yes", "Mapped accessible"),
        ("Changing table", "changing_table", "changing", "yes", "Table mapped"),
        ("Free entry", "fee", "fee", "no", "No fee mapped"),
    )
    lines = []
    for label, tag, key, value, action in features:
        counts = Counter(r['tags'].get(tag) or 'unknown' for r in records)
        match = map_link(region_id, **{key: value})
        missing = map_link(region_id, **{key: 'unknown'})
        lines.append(f'<tr><th scope="row">{label}</th><td><a href="{match}">{action} ({counts[value]:,})</a></td>'
                     f'<td><a href="{missing}">Unrecorded ({counts["unknown"]:,})</a></td></tr>')
    entries = []
    for r in records:
        tags = r['tags']
        name = tags.get('name') or tags.get('name:en')
        if not name and tags.get('addr:street'):
            name = 'Washroom on ' + tags['addr:street']
        if not name:
            continue
        if not re.fullmatch(r'(?:node|way|relation)/[1-9][0-9]*', r['id']):
            raise ValueError('Invalid OpenStreetMap record ID')
        entries.append((name.casefold(), r['id'], f'<li><a href="{map_link(region_id, place=r["id"])}">{escape(name)}</a> · '
                        f'<a href="{OSM}/{r["id"]}">OSM record</a></li>'))
    named = ''
    if entries:
        named = '<h2>Find a named or street-labelled place</h2><ul>' + ''.join(item[2] for item in sorted(entries)[:8]) + '</ul>'
    south, west, north, east = region['bbox']
    bounds = urlencode({'minlon': west, 'minlat': south, 'maxlon': east, 'maxlat': north})
    content = f'''<p><a class="hero-link" href="{map_link(region_id)}">Open all {len(records):,} places on the map</a></p>
<h2>Choose what matters for your visit</h2>
<table><thead><tr><th>Detail</th><th>Matching places</th><th>Missing detail</th></tr></thead>
<tbody>{"".join(lines)}</tbody></table>
<p>A missing tag leaves the answer unknown. Check each place’s access restrictions and opening-hours notes before visiting.</p>
{named}<h2>Area and source dates</h2>
<p>This extract covers the rectangle from {south}° to {north}° latitude and {west}° to {east}° longitude.
<a href="{OSM}/?{escape(bounds, quote=True)}">See its bounds on OpenStreetMap</a>.</p>
<p>Downloaded {escape(capture)} UTC. The oldest OpenStreetMap database edition in this capture is {escape(edition)} UTC.
Mapped facilities can change between edits. Some facilities require a purchase or have private access.</p>
<p><a href="../">Browse every area</a></p>'''
    return layout(title, description, url, '../../', content)


def build_areas(stage, tool):
    base = 'https://coolcode.ca' + tool['url']
    directory = tool['result_directory']['path']
    if directory != 'areas/':
        raise ValueError('The published area directory must be areas/')
    path = stage / directory
    path.mkdir()
    index = json.loads((stage / 'data/index.json').read_text())
    file = index['captures'][0]['file']
    if not re.fullmatch(r'captures/[0-9TZ-]+\.json', file):
        raise ValueError('Unexpected capture filename')
    data = json.loads((stage / 'data' / file).read_text())
    regions = data['regions']
    if not regions or any(not SLUG.fullmatch(r['id']) for r in regions):
        raise ValueError('Invalid region identifier')
    urls = [base + directory]
    listings = []
    for region in regions:
        records = [r for r in data['records'] if region['id'] in r['regions']]
        if not records:
            raise ValueError('Empty region in published capture')
        folder = path / region['id']
        folder.mkdir()
        urls.append(base + directory + region['id'] + '/')
        date = data['capturedAt'][:10]
        (folder / 'index.html').write_text(area_page(region, records, date, data['sourceUpdatedAt'][:10], urls[-1]))
        listings.append(f'<li><a href="{region["id"]}/">{escape(region["name"])}</a> · {len(records):,} mapped records</li>')
    content = '<ul class="area-list">'+''.join(listings)+'</ul><p>Each guide includes its map boundary, source date and links to individual records.</p>'
    (path / 'index.html').write_text(layout('Washroom guides by area',
        'Look up mapped wheelchair access, changing tables and fees before choosing a place to stop.', urls[0], '../', content))
    sitemap = ET.Element('urlset', xmlns='http://www.sitemaps.org/schemas/sitemap/0.9')
    for url in urls:
        ET.SubElement(ET.SubElement(sitemap, 'url'), 'loc').text = url
    ET.ElementTree(sitemap).write(stage / 'sitemap.xml', encoding='utf-8', xml_declaration=True)
    return region_links(regions, directory)
