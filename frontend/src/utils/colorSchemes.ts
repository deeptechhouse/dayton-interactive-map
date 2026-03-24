/** Railroad owner colors */
export const RAILROAD_COLORS: Record<string, string> = {
  BNSF: '#FF6600',
  CP: '#FF0000',
  CPKC: '#FF0000',
  'Canadian Pacific': '#FF0000',
  NS: '#006400',
  'Norfolk Southern': '#006400',
  CSX: '#0000FF',
  CN: '#EE0000',
  CTA: '#00A1DE',
};

export const RAILROAD_DEFAULT_COLOR = '#888888';

/** Railroad line style by status */
export const RAILROAD_STATUS_STYLES: Record<
  string,
  { dasharray: number[] | null; width: number; opacity: number; colorOverride?: string }
> = {
  active: { dasharray: null, width: 3, opacity: 1.0 },
  abandoned: { dasharray: [4, 4], width: 2.5, opacity: 0.85, colorOverride: '#ef4444' },
  disused: { dasharray: [6, 3], width: 2.5, opacity: 0.8, colorOverride: '#f59e0b' },
  spur: { dasharray: null, width: 1.5, opacity: 0.9 },
  razed: { dasharray: [2, 4], width: 1.5, opacity: 0.5, colorOverride: '#6b7280' },
};

/** GDRTA bus transit colors (by route group) */
export const TRANSIT_COLORS: Record<string, string> = {
  'Route 1': '#C60C30',
  'Route 2': '#00A1DE',
  'Route 3': '#009B3A',
  'Route 4': '#F9461C',
  'Route 5': '#522398',
  'Route 6': '#E27EA6',
  'Route 7': '#62361B',
  'Route 8': '#F9E300',
  'Route 9': '#0ea5e9',
  'Route 10': '#ef4444',
  default: '#58a6ff',
};

/** Zoning class colors */
export const ZONING_COLORS: Record<string, string> = {
  manufacturing: '#D4A574',
  commercial: '#FF6B6B',
  residential: '#90EE90',
  mixed: '#DDA0DD',
  special: '#FFD700',
};

/** Zoning stroke colors (darker shade of fill) */
export const ZONING_STROKE_COLORS: Record<string, string> = {
  manufacturing: '#A67C52',
  commercial: '#CC4444',
  residential: '#5CB85C',
  mixed: '#AA66AA',
  special: '#CCA800',
};

/** POI category colors */
export const POI_COLORS: Record<string, string> = {
  performance_arts: '#E53E3E',
  hospitality_events: '#DD6B20',
  creative_production: '#805AD5',
  cultural_community: '#2B6CB0',
  parks: '#38A169',
};

/** Building fill colors by property class */
export const BUILDING_CLASS_COLORS: Record<string, string> = {
  commercial: '#ef4444',       // red
  residential: '#22c55e',      // green
  industrial: '#f59e0b',       // amber
  mixed_use: '#a855f7',        // purple
  institutional: '#3b82f6',    // blue
  government: '#06b6d4',       // cyan
  religious: '#ec4899',        // pink
  educational: '#8b5cf6',      // violet
  medical: '#14b8a6',          // teal
  entertainment: '#f97316',    // orange
  hotel: '#eab308',            // yellow
  warehouse: '#78716c',        // stone
  parking: '#6b7280',          // gray
  vacant: '#374151',           // dark gray
};

export const BUILDING_DEFAULT_COLOR = '#334155';

/** Building owner type colors (used for border highlighting) */
export const OWNER_TYPE_COLORS: Record<string, string> = {
  government: '#06b6d4',
  corporate: '#ef4444',
  nonprofit: '#22c55e',
  individual: '#8b949e',
  religious: '#ec4899',
  educational: '#8b5cf6',
};

/** Dayton police district colors (7 districts) */
export const DISTRICT_COLORS: Record<number, string> = {
  1: '#ef4444',  2: '#f97316',  3: '#f59e0b',  4: '#22c55e',
  5: '#3b82f6',  6: '#8b5cf6',  7: '#ec4899',
};

/** Neighborhood colors — cycling hues for Dayton's ~80 neighborhoods.
 * Used by the wards/neighborhoods layer. Colors assigned by index, not name. */
export const NEIGHBORHOOD_PALETTE: string[] = [
  '#ef4444', '#f97316', '#f59e0b', '#eab308', '#84cc16',
  '#22c55e', '#10b981', '#14b8a6', '#06b6d4', '#0ea5e9',
  '#3b82f6', '#6366f1', '#8b5cf6', '#a855f7', '#d946ef',
  '#ec4899', '#f43f5e', '#fb7185', '#fda4af', '#fdba74',
  '#fcd34d', '#bef264', '#86efac', '#6ee7b7', '#5eead4',
  '#67e8f9', '#7dd3fc', '#93c5fd', '#a5b4fc', '#c4b5fd',
  '#d8b4fe', '#f0abfc', '#f9a8d4', '#fca5a5', '#fdba74',
  '#fde047', '#a3e635', '#4ade80', '#34d399', '#2dd4bf',
];

/** Legacy alias — ward colors now backed by NEIGHBORHOOD_PALETTE */
export const WARD_COLORS: Record<number, string> = Object.fromEntries(
  NEIGHBORHOOD_PALETTE.map((c, i) => [i + 1, c]),
);

/** Federal property category colors */
export const FEDERAL_CATEGORY_COLORS: Record<string, string> = {
  law_enforcement: '#ef4444',  // red
  courts: '#3b82f6',           // blue
  regulatory: '#22c55e',       // green
  revenue_services: '#eab308', // yellow
  postal: '#8b5cf6',           // violet
  military: '#ec4899',         // pink
  financial: '#10b981',        // emerald
  healthcare: '#06b6d4',       // cyan
};

/** App theme colors */
export const THEME = {
  bg: '#0d1117',
  bgSecondary: '#161b22',
  bgTertiary: '#21262d',
  text: '#c9d1d9',
  textMuted: '#8b949e',
  accent: '#58a6ff',
  border: '#30363d',
  success: '#3fb950',
  warning: '#d29922',
  danger: '#f85149',
} as const;
