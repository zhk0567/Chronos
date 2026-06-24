export function confidenceLabel(confidence: number): '高' | '中' | '低' {
  if (confidence >= 0.7) return '高';
  if (confidence >= 0.45) return '中';
  return '低';
}
