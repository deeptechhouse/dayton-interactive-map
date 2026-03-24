"""Import neighborhood boundaries from ArcGIS REST endpoints.

Used for Dayton (at-large commission — no city wards) and other cities
that have recognized neighborhood boundaries instead of ward districts.
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


class NeighborhoodsImporter(ArcGISRestImporter):
    """Import neighborhood boundary polygons.

    Stores data in the wards table (same schema) since neighborhoods
    serve the same role as wards for cities with at-large governance.
    """

    layer_name = "neighborhoods"

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

            # Dayton neighborhood fields: NAME, PLC_BEAT, PLC_DISTR
            name = (
                props.get("NAME", "")
                or props.get("name", "")
                or props.get("NEIGHBORHOOD", "")
                or ""
            )

            records.append({
                "id": str(uuid.uuid4()),
                "city_id": self._city_id,
                "name": name.strip(),
                "police_district": props.get("PLC_DISTR", ""),
                "police_beat": props.get("PLC_BEAT", ""),
                "geom_json": multi_json,
            })
        self._log.info("transformed", count=len(records))
        return records

    def load(self, records: list[dict]) -> int:
        if not records:
            return 0
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            # Create wards table if not exists (before truncate)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS wards (
                    id UUID PRIMARY KEY,
                    city_id UUID NOT NULL,
                    name TEXT,
                    ward_number INTEGER,
                    police_district TEXT,
                    police_beat TEXT,
                    geom GEOMETRY(MultiPolygon, 4326)
                )
            """)
            conn.commit()
            cur.execute("DELETE FROM wards WHERE city_id = %s", (self._city_id,))
            conn.commit()
            sql = """
                INSERT INTO wards (id, city_id, name, police_district, police_beat, geom)
                VALUES (%s, %s, %s, %s, %s,
                    ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326))
            """
            batch = [
                (r["id"], r["city_id"], r["name"],
                 r["police_district"], r["police_beat"], r["geom_json"])
                for r in records
            ]
            cur.executemany(sql, batch)
            conn.commit()
            count = cur.rowcount
            cur.close()
            return count
        finally:
            conn.close()
