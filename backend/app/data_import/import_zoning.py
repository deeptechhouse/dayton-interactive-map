"""Import zoning districts from city open data portals.

Supports multiple source types:
- Socrata GeoJSON API (Chicago): direct download
- ArcGIS REST MapServer (Dayton): paginated via resultOffset
"""

import json
import uuid
from pathlib import Path

from shapely.geometry import shape, mapping
from shapely import MultiPolygon, Polygon

from app.data_import.base_importer import BaseImporter
from app.data_import.arcgis_rest_importer import ArcGISRestImporter


# Map zone code prefixes to zone_class categories
# Covers both Chicago and Dayton conventions
_ZONE_CLASS_MAP = {
    # Chicago prefixes
    "M": "manufacturing",
    "PMD": "manufacturing",
    "C": "commercial",
    "B": "commercial",
    "R": "residential",
    "RT": "residential",
    "RS": "residential",
    "RM": "residential",
    "DX": "mixed",
    "DC": "mixed",
    "DR": "mixed",
    "DS": "mixed",
    "PD": "special",
    "POS": "special",
    "T": "transportation",
    "P": "special",
    # Dayton prefixes (Dayton Zoning Code)
    "MF": "residential",       # multi-family
    "SF": "residential",       # single-family
    "TF": "residential",       # two-family
    "UR": "residential",       # urban residential
    "NC": "commercial",        # neighborhood commercial
    "GC": "commercial",        # general commercial
    "RC": "commercial",        # regional commercial
    "OC": "commercial",        # office commercial
    "LM": "manufacturing",     # light manufacturing
    "GM": "manufacturing",     # general manufacturing
    "HM": "manufacturing",     # heavy manufacturing
    "MU": "mixed",             # mixed use
    "MX": "mixed",             # mixed use
    "CBD": "mixed",            # central business district
    "WR": "mixed",             # waterfront/river
    "OS": "special",           # open space
    "IN": "manufacturing",     # industrial
    "I": "manufacturing",      # industrial
}


def _classify_zone(zone_code: str) -> str:
    """Map a zone code to a broad zone_class. Handles Chicago and Dayton conventions."""
    if not zone_code:
        return "other"
    code = zone_code.strip().upper()
    # Try longest prefix first
    for prefix in sorted(_ZONE_CLASS_MAP, key=len, reverse=True):
        if code.startswith(prefix):
            return _ZONE_CLASS_MAP[prefix]
    return "other"


def _ensure_multipolygon(geom) -> str | None:
    """Convert a Shapely geometry to a MultiPolygon GeoJSON string."""
    if geom is None or geom.is_empty:
        return None
    if isinstance(geom, Polygon):
        geom = MultiPolygon([geom])
    elif not isinstance(geom, MultiPolygon):
        return None
    return json.dumps(mapping(geom))


class ZoningImporter(ArcGISRestImporter):
    layer_name = "zoning"

    def download(self) -> Path:
        # Use ArcGIS REST pagination if source type is arcgis_rest
        source_type = self._config.get("type", "")
        if source_type == "arcgis_rest":
            return ArcGISRestImporter.download(self)

        # Fall back to direct GeoJSON download
        cached = self._load_json_cache()
        if cached:
            return self._cache_path()

        url = self._config.get("url", "")
        if not url:
            raise ValueError("No zoning URL configured")

        data = self._http_get_json(url)
        return self._save_json_cache(data)

    def transform(self, raw_path: Path) -> list[dict]:
        raw = json.loads(raw_path.read_text())
        features = raw.get("features", raw) if isinstance(raw, dict) else raw
        records = []
        for feat in features:
            props = feat.get("properties", {})
            geom_json = feat.get("geometry")
            if not geom_json:
                continue
            try:
                geom = shape(geom_json)
            except Exception:
                continue
            multi_json = _ensure_multipolygon(geom)
            if not multi_json:
                continue

            # Try multiple field name conventions
            # Chicago: zone_class, zone_type, zone_class_description
            # Dayton ArcGIS: DISTRICT, NAME, NEW_ZONE, NEWZONING1
            zone_code = (
                props.get("zone_class", "")
                or props.get("zone_type", "")
                or props.get("DISTRICT", "")
                or props.get("NEW_ZONE", "")
                or props.get("NEWZONING1", "")
                or ""
            )
            zone_name = (
                props.get("zone_type", "")
                or props.get("NAME", "")
                or zone_code
            )
            description = (
                props.get("zone_class_description", "")
                or props.get("FEATURE", "")
                or ""
            )

            records.append({
                "id": str(uuid.uuid4()),
                "city_id": self._city_id,
                "zone_code": zone_code,
                "zone_class": _classify_zone(zone_code),
                "zone_name": zone_name,
                "description": description,
                "ordinance_ref": props.get("ordinance", ""),
                "geom_json": multi_json,
            })
        self._log.info("transformed", count=len(records))
        return records

    def load(self, records: list[dict]) -> int:
        if not records:
            return 0
        self._truncate_table("zoning_districts")
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            sql = """
                INSERT INTO zoning_districts (id, city_id, zone_code, zone_class,
                    zone_name, description, ordinance_ref, geom)
                VALUES (%s, %s, %s, %s, %s, %s, %s,
                    ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326))
            """
            batch = [
                (r["id"], r["city_id"], r["zone_code"], r["zone_class"],
                 r["zone_name"], r["description"], r["ordinance_ref"],
                 r["geom_json"])
                for r in records
            ]
            cur.executemany(sql, batch)
            conn.commit()
            count = cur.rowcount
            cur.close()
            return count
        finally:
            conn.close()
