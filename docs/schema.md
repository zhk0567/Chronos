# Chronos JSON Schema 概要

分析结果以 JSON 存储于 `data/analysis/runs/{runId}/`。

## 核心类型

- `DiaryEntry` - 日记条目
- `MorphResult` - 段落形态分类
- `InfoUnit` - 信息单元（事件包/思维锚/情绪标记/节律信息）
- `AnchorCard` - 锚点信息卡
- `EmotionPoint` - 情绪时间点
- `FactorConclusion` - 因素结论
- `PersonNode` - 关系网络节点
- `LanguageMetric` - 语言模式指标
- `ThemeTrack` - 主题生命周期
- `InsightReport` - 完整洞察报告

详见 `engine/schemas/models.py` 与 `src/types/analysis.ts`。
