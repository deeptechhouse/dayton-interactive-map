import type maplibregl from 'maplibre-gl';
import type { LayerConfig } from '../../types/layer';
import { NEIGHBORHOOD_PALETTE } from '../../utils/colorSchemes';
import { martinTileUrl } from '../../utils/geoUtils';

const SOURCE_ID = 'neighborhoods-source';

/**
 * Neighborhood layer for Dayton.
 *
 * Loads boundaries from Martin vector tiles (wards table in PostGIS)
 * rather than embedded GeoJSON. Colors cycle through the palette
 * using a step expression on feature ID.
 */

function neighborhoodColorExpr(): unknown {
  // Build a step expression that cycles colors by feature id
  // step(input, default, stop1, output1, stop2, output2, ...)
  const stops: (number | string)[] = [];
  for (let i = 0; i < NEIGHBORHOOD_PALETTE.length; i++) {
    stops.push(i + 1, NEIGHBORHOOD_PALETTE[i]);
  }
  return ['match',
    ['%', ['coalesce', ['to-number', ['id']], 1], NEIGHBORHOOD_PALETTE.length],
    ...stops,
    '#888888',
  ];
}

export function addWardLayer(map: maplibregl.Map, config: LayerConfig): void {
  if (!map.getSource(SOURCE_ID)) {
    map.addSource(SOURCE_ID, {
      type: 'vector',
      tiles: [martinTileUrl('wards')],
      minzoom: 0,
      maxzoom: 16,
      promoteId: 'name',
    });
  }

  // Use a simpler color approach — interpolate hue by feature id
  const colorExpr: unknown = [
    'interpolate', ['linear'],
    ['%', ['coalesce', ['to-number', ['id']], 0], 100],
    0, '#ef4444',
    10, '#f97316',
    20, '#eab308',
    30, '#22c55e',
    40, '#14b8a6',
    50, '#3b82f6',
    60, '#8b5cf6',
    70, '#ec4899',
    80, '#f43f5e',
    90, '#06b6d4',
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
