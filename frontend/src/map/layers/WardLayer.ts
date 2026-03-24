import type maplibregl from 'maplibre-gl';
import type { LayerConfig } from '../../types/layer';
import { NEIGHBORHOOD_PALETTE } from '../../utils/colorSchemes';
import { martinTileUrl } from '../../utils/geoUtils';

const SOURCE_ID = 'neighborhoods-source';

/**
 * Neighborhood layer for Dayton.
 *
 * Loads boundaries from Martin vector tiles (wards table in PostGIS)
 * rather than embedded GeoJSON. Colors assigned by feature index
 * cycling through the NEIGHBORHOOD_PALETTE.
 */

export function addWardLayer(map: maplibregl.Map, config: LayerConfig): void {
  if (!map.getSource(SOURCE_ID)) {
    map.addSource(SOURCE_ID, {
      type: 'vector',
      tiles: [martinTileUrl('wards')],
      minzoom: 0,
      maxzoom: 16,
    });
  }

  // Color expression: cycle through palette by OBJECTID or row number
  const colorExpr: unknown = [
    'at',
    ['%', ['coalesce', ['get', 'ward_number'], ['id'], 0], NEIGHBORHOOD_PALETTE.length],
    ['literal', NEIGHBORHOOD_PALETTE],
  ];

  map.addLayer({
    id: `${config.id}-fill`,
    type: 'fill',
    source: SOURCE_ID,
    'source-layer': 'wards',
    layout: { visibility: config.visible ? 'visible' : 'none' },
    paint: {
      'fill-color': colorExpr,
      'fill-opacity': [
        'interpolate', ['linear'], ['zoom'],
        10, 0.12 * config.opacity,
        14, 0.22 * config.opacity,
      ],
    },
  } as maplibregl.AddLayerObject);

  map.addLayer({
    id: `${config.id}-stroke`,
    type: 'line',
    source: SOURCE_ID,
    'source-layer': 'wards',
    layout: { visibility: config.visible ? 'visible' : 'none' },
    paint: {
      'line-color': colorExpr,
      'line-width': ['interpolate', ['linear'], ['zoom'], 10, 1, 14, 2.5],
      'line-opacity': config.opacity * 0.7,
    },
  } as maplibregl.AddLayerObject);

  map.addLayer({
    id: `${config.id}-label`,
    type: 'symbol',
    source: SOURCE_ID,
    'source-layer': 'wards',
    minzoom: 12,
    layout: {
      visibility: config.visible ? 'visible' : 'none',
      'text-field': ['coalesce', ['get', 'name'], ''],
      'text-size': ['interpolate', ['linear'], ['zoom'], 12, 10, 15, 13],
      'text-font': ['Noto Sans Bold'],
      'text-anchor': 'center',
      'text-allow-overlap': false,
    },
    paint: {
      'text-color': '#ffffff',
      'text-halo-color': '#000000',
      'text-halo-width': 2,
      'text-opacity': config.opacity,
    },
  } as maplibregl.AddLayerObject);
}

export function getWardLayerIds(configId: string): string[] {
  return [
    `${configId}-fill`,
    `${configId}-stroke`,
    `${configId}-label`,
  ];
}
