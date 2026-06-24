export const COMPLETENESS_LABELS: Record<string, string> = {
  entries: '日记篇数',
  emotion: '情绪评分',
  weather: '天气数据',
};

export function completenessLabel(key: string): string {
  return COMPLETENESS_LABELS[key] ?? key;
}
