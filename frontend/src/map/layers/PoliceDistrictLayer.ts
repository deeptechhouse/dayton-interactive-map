import type maplibregl from 'maplibre-gl';
import type { LayerConfig } from '../../types/layer';
import { DISTRICT_COLORS } from '../../utils/colorSchemes';
import { martinTileUrl } from '../../utils/geoUtils';

const SOURCE_ID = 'police-districts-source';

/**
 * Police district layer for Dayton.
 *
 * Loads district boundaries from Martin vector tiles (police_districts table)
 * rather than embedded GeoJSON. Dayton has 7 police districts.
 */

function districtColorExpression(): unknown {
  const pairs: (string | number)[] = [];
  for (const [dist, color] of Object.entries(DISTRICT_COLORS)) {
    pairs.push(Number(dist), color);
  }
  return ['match', ['coalesce', ['to-number', ['get', 'district']], 0], ...pairs, '#888888'];
}

export function addPoliceDistrictLayer(map: maplibregl.Map, config: LayerConfig): void {
  if (!map.getSource(SOURCE_ID)) {
    map.addSource(SOURCE_ID, {
      type: 'vector',
      tiles: [martinTileUrl('police_districts')],
      minzoom: 0,
      maxzoom: 16,
    });
  }

  map.addLayer({
    id: `${config.id}-fill`,
    type: 'fill',
    source: SOURCE_ID,
    'source-layer': 'police_districts',
    layout: { visibility: config.visible ? 'visible' : 'none' },
    paint: {
      'fill-color': districtColorExpression(),
      'fill-opacity': [
        'interpolate', ['linear'], ['zoom'],
        10, 0.15 * config.opacity,
        14, 0.25 * config.opacity,
      ],
    },
  } as maplibregl.AddLayerObject);

  map.addLayer({
    id: `${config.id}-stroke`,
    type: 'line',
    source: SOURCE_ID,
    'source-layer': 'police_districts',
    layout: { visibility: config.visible ? 'visible' : 'none' },
    paint: {
      'line-color': districtColorExpression(),
      'line-width': ['interpolate', ['linear'], ['zoom'], 10, 1.5, 14, 3],
      'line-opacity': config.opacity * 0.8,
    },
  } as maplibregl.AddLayerObject);

  map.addLayer({
    id: `${config.id}-label`,
    type: 'symbol',
    source: SOURCE_ID,
    'source-layer': 'police_districts',
    minzoom: 10,
    layout: {
      visibility: config.visible ? 'visible' : 'none',
      'text-field': ['concat', 'District ', ['get', 'district']],
      'text-size': ['interpolate', ['linear'], ['zoom'], 10, 12, 14, 16],
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

export function getPoliceDistrictLayerIds(configId: string): string[] {
  return [
    `${configId}-fill`,
    `${configId}-stroke`,
    `${configId}-label`,
  ];
}
