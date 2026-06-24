import fs from 'fs';
import path from 'path';

export interface UserSettings {
  residentCity: string;
  latitude: number | null;
  longitude: number | null;
  timezone: string;
  defaultRunId?: string | null;
  theme?: 'light' | 'dark' | 'system';
}

const DEFAULTS: UserSettings = {
  residentCity: '洛阳',
  latitude: 34.6197,
  longitude: 112.454,
  timezone: 'Asia/Shanghai',
  defaultRunId: null,
  theme: 'light',
};

const CITY_COORDS: Record<string, [number, number]> = {
  洛阳: [34.6197, 112.454],
  北京: [39.9042, 116.4074],
  上海: [31.2304, 121.4737],
  广州: [23.1291, 113.2644],
  深圳: [22.5431, 114.0579],
  杭州: [30.2741, 120.1551],
  成都: [30.5728, 104.0668],
  武汉: [30.5928, 114.3055],
  西安: [34.3416, 108.9398],
  南京: [32.0603, 118.7969],
  重庆: [29.4316, 106.9123],
};

function settingsPath(root: string): string {
  return path.join(root, 'data', 'settings.json');
}

export function getSettings(root: string): UserSettings {
  const p = settingsPath(root);
  if (!fs.existsSync(p)) return { ...DEFAULTS };
  try {
    return { ...DEFAULTS, ...JSON.parse(fs.readFileSync(p, 'utf-8')) };
  } catch {
    return { ...DEFAULTS };
  }
}

export function geocodeCity(city: string): [number, number] | null {
  const c = city.trim().replace(/市$/, '');
  if (CITY_COORDS[c]) return CITY_COORDS[c];
  for (const [name, coords] of Object.entries(CITY_COORDS)) {
    if (c.includes(name) || name.includes(c)) return coords;
  }
  return null;
}

export function saveSettings(root: string, partial: Partial<UserSettings>): UserSettings {
  const current = getSettings(root);
  const next = { ...current, ...partial };

  if (partial.residentCity && (next.latitude == null || next.longitude == null)) {
    const coords = geocodeCity(partial.residentCity);
    if (coords) {
      next.latitude = coords[0];
      next.longitude = coords[1];
    }
  }

  const dir = path.join(root, 'data');
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(settingsPath(root), JSON.stringify(next, null, 2), 'utf-8');
  return next;
}

export interface ContextCompleteness {
  weather: number;
  wearable: number;
  digital: number;
  location: number;
  rhythm: number;
}

export function getContextCompleteness(root: string, dates: string[]): ContextCompleteness {
  if (dates.length === 0) {
    return { weather: 0, wearable: 0, digital: 0, location: 0, rhythm: 0 };
  }
  const subs = ['weather', 'wearable', 'digital', 'location'] as const;
  const counts: Record<string, number> = { weather: 0, wearable: 0, digital: 0, location: 0 };
  for (const date of dates) {
    for (const sub of subs) {
      const fp = path.join(root, 'data', 'context', sub, `${date}.json`);
      if (fs.existsSync(fp)) counts[sub]++;
    }
  }
  const n = dates.length;
  return {
    weather: counts.weather / n,
    wearable: counts.wearable / n,
    digital: counts.digital / n,
    location: counts.location / n,
    rhythm: 1,
  };
}
