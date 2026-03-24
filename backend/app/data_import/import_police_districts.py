"""Import police district boundaries from ArcGIS REST endpoints.

Dayton Police Department publishes district, beat, and sector boundaries
via ArcGIS MapServer. This importer fetches district-level polygons.
"""

import json
import uuid
from pathlib import Path

from shapely.geometry import shape, mapping
from shapely import MultiPolygon, Polygon

from app.data_import.arcgis_rest_importer import ArcGISRestImporter


def _ensure_multipolygon(geom) -> str | None:
    """Convert a Shapely geometry to a MultiPolygon GeoJSON string."""
    if geom is None or geom.is_empty:
        return None
    if isinstance(geom, Polygon):
        geom = MultiPolygon([geom])
    elif not isinstance(geom, MultiPolygon):
        return None
    return json.dumps(mapping(geom))


class PoliceDistrictsImporter(ArcGISRestImporter):
    """Import police district boundary polygons from ArcGIS REST."""

    layer_name = "police_districts"

    def transform(self, raw_path: Path) -> list[dict]:
        raw = json.loads(raw_path.read_text())
        features = raw.get("features", [])
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

            # Dayton PD fields: District, Id
            district = props.get("District", "") or props.get("district", "") or ""
            district_id = props.get("Id", "") or props.get("OBJECTID", "")

            records.append({
                "id": str(uuid.uuid4()),
                "city_id": self._city_id,
                "district": str(district).strip(),
                "district_id": str(district_id),
                "geom_json": multi_json,
            })
        self._log.info("transformed", count=len(records))
        return records

    def load(self, records: list[dict]) -> int:
        if not records:
            return 0
        self._truncate_table("police_districts")
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            # Create table if not exists
            cur.execute("""
                CREATE TABLE IF NOT EXISTS police_districts (
                    id UUID PRIMARY KEY,
                    city_id UUID NOT NULL,
                    district TEXT,
                    district_id TEXT,
                    geom GEOMETRY(MultiPolygon, 4326)
                )
            """)
            sql = """
                INSERT INTO police_districts (id, city_id, district, district_id, geom)
                VALUES (%s, %s, %s, %s,
                    ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326))
            """
            batch = [
                (r["id"], r["city_id"], r["district"], r["district_id"], r["geom_json"])
                for r in records
            ]
            cur.executemany(sql, batch)
            conn.commit()
            count = cur.rowcount
            cur.close()
            return count
        finally:
            conn.close()
