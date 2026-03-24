"""ArcGIS REST API importer for City of Dayton and other ArcGIS-served data.

Handles paginated feature queries from ArcGIS MapServer and FeatureServer
endpoints, returning standard GeoJSON for downstream processing.

ArcGIS REST endpoints cap results per request (typically 1000 or 2000 features).
This importer handles pagination via resultOffset/resultRecordCount parameters.
"""

import json
from pathlib import Path

import httpx
import structlog

from app.data_import.base_importer import BaseImporter

logger = structlog.get_logger(__name__)

# ArcGIS REST default page size
ARCGIS_PAGE_SIZE = 1000


class ArcGISRestImporter(BaseImporter):
    """Base importer for ArcGIS REST MapServer/FeatureServer endpoints.

    Subclasses should set layer_name and implement transform() and load().
    The download() method handles paginated GeoJSON queries from ArcGIS REST.
    """

    layer_name = "arcgis_generic"

    def download(self) -> Path:
        """Download all features from an ArcGIS REST endpoint with pagination."""
        cached = self._load_json_cache()
        if cached:
            return self._cache_path()

        url = self._config.get("url", "")
        if not url:
            raise ValueError(f"No URL configured for {self.layer_name}")

        # Query features with pagination
        all_features = self._query_all_features(url)

        collection = {"type": "FeatureCollection", "features": all_features}
        self._log.info("download_complete", total_features=len(all_features))
        return self._save_json_cache(collection)

    def _query_all_features(self, base_url: str) -> list[dict]:
        """Query all features from an ArcGIS REST endpoint, handling pagination.

        Args:
            base_url: The ArcGIS REST endpoint URL (e.g., .../MapServer/307)

        Returns:
            List of GeoJSON feature dicts.
        """
        query_url = f"{base_url}/query"
        all_features: list[dict] = []
        offset = 0

        # Build bbox geometry filter if configured
        bbox = self._config.get("bbox")
        geometry_params = {}
        if bbox:
            # bbox format: [west, south, east, north]
            geometry_params = {
                "geometry": f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}",
                "geometryType": "esriGeometryEnvelope",
                "spatialRel": "esriSpatialRelIntersects",
                "inSR": "4326",
            }

        while True:
            params = {
                "where": "1=1",
                "outFields": "*",
                "outSR": "4326",
                "f": "geojson",
                "resultOffset": str(offset),
                "resultRecordCount": str(ARCGIS_PAGE_SIZE),
                **geometry_params,
            }

            self._log.info("arcgis_query", url=query_url[:100], offset=offset)

            with httpx.Client(timeout=120.0, follow_redirects=True) as client:
                resp = client.get(query_url, params=params)
                resp.raise_for_status()
                data = resp.json()

            # ArcGIS GeoJSON response has a "features" array
            features = data.get("features", [])
            if not features:
                break

            all_features.extend(features)
            self._log.info("arcgis_page", offset=offset, features=len(features),
                           cumulative=len(all_features))

            # Check if there are more results
            # ArcGIS signals end by returning fewer features than requested
            # or by setting exceededTransferLimit
            exceeded = data.get("properties", {}).get("exceededTransferLimit", False)
            if len(features) < ARCGIS_PAGE_SIZE and not exceeded:
                break

            offset += len(features)

        return all_features

    def _get_field(self, properties: dict, field_name: str, fallbacks: list[str] | None = None) -> str:
        """Extract a field value from feature properties, trying field_map first.

        Uses the field_map from config to translate ArcGIS field names to
        the application's expected field names.
        """
        field_map = self._config.get("field_map", {})

        # Check if there's a mapped field name
        mapped_name = field_map.get(field_name, "")
        if mapped_name and mapped_name in properties:
            val = properties[mapped_name]
            return str(val).strip() if val is not None else ""

        # Try direct field name
        if field_name in properties:
            val = properties[field_name]
            return str(val).strip() if val is not None else ""

        # Try fallbacks
        for fb in (fallbacks or []):
            if fb in properties:
                val = properties[fb]
                return str(val).strip() if val is not None else ""

        return ""
