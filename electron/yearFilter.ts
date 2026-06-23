/** 分析范围：仅当前自然年的日记 */
export function getAnalysisYear(): number {
  return new Date().getFullYear();
}

export function isInAnalysisYear(date: string, year = getAnalysisYear()): boolean {
  const y = parseInt(date.slice(0, 4), 10);
  return y === year;
}

export function yearFilePattern(year = getAnalysisYear()): RegExp {
  return new RegExp(`^${year}-\\d{2}-\\d{2}\\.json$`);
}
