#!/usr/bin/env python3
"""
Generate Dayton Railroad Right-of-Way GeoJSON data.

Sources:
1. City of Dayton MapServer layer 9 — parcels owned by railroad companies
2. OSM Overpass — railway ways buffered to approximate ROW corridors
3. OSM Overpass — landuse=railway areas (rail yards, etc.)

Output: frontend/src/map/layers/data/railroadRowData.ts
"""

import json
import math
import ssl
import sys
import time
import urllib.request
import urllib.parse
from pathlib import Path

import requests

from shapely.geometry import (
    LineString, MultiLineString, MultiPolygon, Polygon,
    mapping, shape
)
from shapely.ops import unary_union
from shapely import simplify

# Dayton bounding box
BBOX = {
    "south": 39.695,
    "west": -84.280,
    "north": 39.825,
    "east": -84.100,
}

# Buffer width in degrees (approx 30m = 100ft at this latitude)
# 1 degree latitude ≈ 111,000m, so 30m ≈ 0.00027 degrees
# 1 degree longitude at 39.75°N ≈ 85,400m, so 30m ≈ 0.000351 degrees
# We'll use an average for simplicity with Shapely buffer
ROW_BUFFER_DEG = 0.0003  # ~30m

# Simplification tolerance
SIMPLIFY_TOLERANCE = 0.00005  # ~5m


def fetch_dayton_parcels():
    """Fetch railroad-company-owned parcels from City of Dayton MapServer."""
    print("Fetching railroad parcels from Dayton MapServer...")

    base_url = (
        "https://maps.daytonohio.gov/gisservices/rest/services/"
        "Viewer/MapLayers_Citywide/MapServer/9/query"
    )

    where_clause = (
        "GISADMIN.WEB_CAMA.OWNER_NAME LIKE '%CSX%' OR "
        "GISADMIN.WEB_CAMA.OWNER_NAME LIKE '%NORFOLK SOUTHERN%' OR "
        "GISADMIN.WEB_CAMA.OWNER_NAME LIKE '%CONRAIL%' OR "
        "GISADMIN.WEB_CAMA.OWNER_NAME LIKE '%LITTLE MIAMI RAILROAD%' OR "
        "GISADMIN.WEB_CAMA.OWNER_NAME LIKE '%DAYTON STREET RAILWAY%' OR "
        "GISADMIN.WEB_CAMA.OWNER_NAME LIKE '%STATE OF OHIO CANAL%' OR "
        "GISADMIN.WEB_CAMA.OWNER_NAME LIKE '%PAN HANDLE%' OR "
        "GISADMIN.WEB_CAMA.OWNER_NAME LIKE '%PENN CENTRAL%' OR "
        "GISADMIN.WEB_CAMA.OWNER_NAME LIKE '%BALTIMORE%OHIO%' OR "
        "GISADMIN.WEB_CAMA.OWNER_NAME LIKE '%DAYTON XENIA%' OR "
        "GISADMIN.WEB_CAMA.OWNER_NAME LIKE '%INDIANA%OHIO%RAIL%' OR "
        "GISADMIN.WEB_CAMA.OWNER_NAME LIKE '%DAYTON%UNION%RAIL%'"
    )

    params = urllib.parse.urlencode({
        "where": where_clause,
        "outFields": (
            "GISADMIN.WEB_CAMA.PARID,"
            "GISADMIN.WEB_CAMA.OWNER_NAME,"
            "GISADMIN.WEB_CAMA.PARLOC,"
            "GISADMIN.WEB_CAMA.LUC,"
            "GISADMIN.CAMA_LANDUSECODES.Field4"
        ),
        "returnGeometry": "true",
        "outSR": "4326",
        "resultRecordCount": "500",
        "f": "geojson",
    })

    url = f"{base_url}?{params}"

    try:
        resp = requests.get(url, timeout=30, verify=False)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"  Warning: Failed to fetch parcels: {e}")
        return []

    features = data.get("features", [])
    print(f"  Found {len(features)} railroad-owned parcels")

    result = []
    for f in features:
        props = f.get("properties", {})
        geom = f.get("geometry")
        if not geom:
            continue

        owner = (
            props.get("GISADMIN.WEB_CAMA.OWNER_NAME")
            or props.get("OWNER_NAME")
            or ""
        )
        parid = (
            props.get("GISADMIN.WEB_CAMA.PARID")
            or props.get("PARID")
            or ""
        )
        address = (
            props.get("GISADMIN.WEB_CAMA.PARLOC")
            or props.get("PARLOC")
            or ""
        )
        luc_desc = (
            props.get("GISADMIN.CAMA_LANDUSECODES.Field4")
            or props.get("Field4")
            or ""
        )

        result.append({
            "type": "Feature",
            "properties": {
                "source": "parcel",
                "parcel_id": parid,
                "owner": owner,
                "address": address,
                "land_use": luc_desc,
            },
            "geometry": geom,
        })

    return result


def fetch_osm_railways():
    """Fetch railway ways and landuse areas from OSM Overpass."""
    print("Fetching OSM railway data...")

    bbox_str = (
        f"{BBOX['south']},{BBOX['west']},{BBOX['north']},{BBOX['east']}"
    )

    query = f"""
    [out:json][timeout:60];
    (
      way["railway"](
        {BBOX['south']},{BBOX['west']},{BBOX['north']},{BBOX['east']}
      );
      way["landuse"="railway"](
        {BBOX['south']},{BBOX['west']},{BBOX['north']},{BBOX['east']}
      );
      relation["landuse"="railway"](
        {BBOX['south']},{BBOX['west']},{BBOX['north']},{BBOX['east']}
      );
    );
    out body;
    >;
    out skel qt;
    """

    url = "https://overpass-api.de/api/interpreter"

    try:
        resp = requests.post(
            url, data={"data": query}, timeout=60, verify=False
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"  Warning: Failed to fetch OSM data: {e}")
        return [], []

    elements = data.get("elements", [])

    # Index nodes by ID
    nodes = {}
    for el in elements:
        if el["type"] == "node":
            nodes[el["id"]] = (el["lon"], el["lat"])

    # Collect ways
    ways = [el for el in elements if el["type"] == "way"]
    print(f"  Found {len(ways)} ways, {len(nodes)} nodes")

    rail_lines = []
    landuse_areas = []

    for way in ways:
        tags = way.get("tags", {})
        node_refs = way.get("nodes", [])

        coords = []
        for nid in node_refs:
            if nid in nodes:
                coords.append(nodes[nid])

        if len(coords) < 2:
            continue

        is_landuse = tags.get("landuse") == "railway"
        railway_type = tags.get("railway", "")

        # Skip non-physical railway features
        if railway_type in (
            "signal", "switch", "buffer_stop", "crossing",
            "level_crossing", "railway_crossing", "milestone",
            "derail", "turntable",
        ):
            continue

        name = tags.get("name", "")
        operator = tags.get("operator", "")
        status = "active"
        if railway_type in ("abandoned", "disused", "razed"):
            status = railway_type
        elif railway_type == "spur":
            status = "spur"
        elif tags.get("railway:status"):
            status = tags["railway:status"]

        props = {
            "osm_id": way["id"],
            "name": name,
            "operator": operator,
            "railway_type": railway_type,
            "status": status,
        }

        if is_landuse:
            # Landuse areas are closed ways (polygons)
            if coords[0] == coords[-1] and len(coords) >= 4:
                landuse_areas.append({
                    "type": "Feature",
                    "properties": {**props, "source": "osm_landuse"},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [coords],
                    },
                })
        else:
            rail_lines.append({
                "coords": coords,
                "props": {**props, "source": "osm_buffered"},
            })

    print(
        f"  Rail lines to buffer: {len(rail_lines)}, "
        f"landuse areas: {len(landuse_areas)}"
    )
    return rail_lines, landuse_areas


def buffer_rail_lines(rail_lines):
    """Buffer rail line coordinates into ROW corridor polygons."""
    print(f"Buffering {len(rail_lines)} rail lines...")

    features = []
    buffered_geoms = []

    for rl in rail_lines:
        coords = rl["coords"]
        props = rl["props"]

        try:
            line = LineString(coords)
            # Buffer width varies by type
            status = props.get("status", "active")
            railway_type = props.get("railway_type", "rail")

            if railway_type in ("light_rail", "subway", "tram"):
                buf = ROW_BUFFER_DEG * 0.6
            elif status in ("abandoned", "razed"):
                buf = ROW_BUFFER_DEG * 0.8
            elif railway_type == "spur":
                buf = ROW_BUFFER_DEG * 0.5
            else:
                buf = ROW_BUFFER_DEG

            buffered = line.buffer(buf, cap_style="flat", join_style="mitre")

            if buffered.is_empty:
                continue

            # Simplify to reduce coordinate count
            buffered = simplify(buffered, SIMPLIFY_TOLERANCE)
            buffered_geoms.append(buffered)

            features.append({
                "type": "Feature",
                "properties": props,
                "geometry": mapping(buffered),
            })
        except Exception as e:
            print(f"  Warning: Failed to buffer line: {e}")
            continue

    # Merge overlapping buffers for cleaner output
    print(f"  Merging overlapping polygons...")
    if buffered_geoms:
        merged = unary_union(buffered_geoms)
        merged = simplify(merged, SIMPLIFY_TOLERANCE)

        # Convert merged geometry to features
        merged_features = []
        if merged.geom_type == "Polygon":
            polys = [merged]
        elif merged.geom_type == "MultiPolygon":
            polys = list(merged.geoms)
        else:
            polys = []

        for poly in polys:
            # Find which original features contributed to this polygon
            centroid = poly.centroid
            source_props = {"source": "osm_buffered"}

            for rl in rail_lines:
                line = LineString(rl["coords"])
                if poly.intersects(line):
                    if rl["props"].get("name"):
                        source_props["name"] = rl["props"]["name"]
                    if rl["props"].get("operator"):
                        source_props["operator"] = rl["props"]["operator"]
                    if rl["props"].get("status") != "active":
                        source_props["status"] = rl["props"]["status"]
                    break

            if "status" not in source_props:
                source_props["status"] = "active"

            merged_features.append({
                "type": "Feature",
                "properties": source_props,
                "geometry": mapping(poly),
            })

        print(
            f"  Merged into {len(merged_features)} polygons "
            f"(from {len(features)} buffered lines)"
        )
        return merged_features

    return features


def round_coords(geojson, precision=6):
    """Round all coordinates to reduce file size."""
    if isinstance(geojson, dict):
        if "coordinates" in geojson:
            geojson["coordinates"] = _round_nested(
                geojson["coordinates"], precision
            )
        else:
            for k, v in geojson.items():
                geojson[k] = round_coords(v, precision)
    elif isinstance(geojson, list):
        return [round_coords(item, precision) for item in geojson]
    return geojson


def _round_nested(coords, precision):
    """Recursively round nested coordinate arrays."""
    if isinstance(coords, (int, float)):
        return round(coords, precision)
    return [_round_nested(c, precision) for c in coords]


def write_typescript(features, output_path):
    """Write GeoJSON FeatureCollection as a TypeScript module."""
    collection = {
        "type": "FeatureCollection",
        "features": features,
    }

    # Round coordinates
    round_coords(collection)

    geojson_str = json.dumps(collection, separators=(",", ":"))
    data_size = len(geojson_str)
    print(f"GeoJSON data size: {data_size:,} bytes ({data_size/1024:.1f} KB)")

    ts_content = (
        "// Dayton Railroad Right-of-Way parcels and corridor polygons\n"
        "// Sources:\n"
        "//   - City of Dayton MapServer (railroad-company-owned parcels)\n"
        "//   - OpenStreetMap Overpass (railway ways buffered to ~30m ROW corridors)\n"
        "//   - OpenStreetMap (landuse=railway areas)\n"
        f"// Generated: {time.strftime('%Y-%m-%d')}\n"
        f"// Features: {len(features)}\n"
        "\n"
        "export const RAILROAD_ROW_PARCELS = "
        f"{json.dumps(collection, indent=2)}"
        " as const;\n"
    )

    output_path.write_text(ts_content)
    file_size = output_path.stat().st_size
    print(f"Written to {output_path} ({file_size:,} bytes)")


def main():
    project_root = Path(__file__).resolve().parent.parent
    output_path = (
        project_root
        / "frontend"
        / "src"
        / "map"
        / "layers"
        / "data"
        / "railroadRowData.ts"
    )

    # 1. Fetch parcel data
    parcel_features = fetch_dayton_parcels()

    # 2. Fetch OSM railway data
    rail_lines, landuse_features = fetch_osm_railways()

    # 3. Buffer rail lines into ROW corridors
    buffered_features = buffer_rail_lines(rail_lines)

    # 4. Combine all features
    all_features = parcel_features + landuse_features + buffered_features
    print(f"\nTotal features: {len(all_features)}")
    print(
        f"  Parcels: {len(parcel_features)}, "
        f"Landuse: {len(landuse_features)}, "
        f"Buffered corridors: {len(buffered_features)}"
    )

    if not all_features:
        print("ERROR: No features generated!")
        sys.exit(1)

    # 5. Write output
    write_typescript(all_features, output_path)
    print("\nDone!")


if __name__ == "__main__":
    main()
