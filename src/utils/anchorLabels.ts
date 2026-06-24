export const ANCHOR_TYPE_LABELS: Record<string, string> = {
  intensity: '情绪强度',
  frequency: '频率涌现',
  structure: '写作结构',
  narrative: '叙事重复',
  silence: '沉默间隔',
  contradiction: '自我矛盾',
};

export function anchorTypeLabel(type: string): string {
  return ANCHOR_TYPE_LABELS[type] ?? type;
}
