# Chronos JSON Schema 概要

分析结果以 JSON 存储于 `data/analysis/runs/{runId}/`。

## 一期核心类型

- `DiaryEntry` - 日记条目
- `MorphResult` - 段落形态分类
- `InfoUnit` - 信息单元（事件包/思维锚/情绪标记/节律信息）
- `AnchorCard` - 锚点信息卡（三期含 `chainLinks`）
- `EmotionPoint` - 情绪时间点
- `FactorConclusion` - 因素结论（含 `controlledFor`）
- `PersonNode` - 关系网络节点
- `LanguageMetric` - 语言模式指标
- `ThemeTrack` - 主题生命周期
- `InsightReport` - 完整洞察报告

## 二期扩展类型

### 用户设置（`data/settings.json`）

- `UserSettings` - `residentCity`, `latitude`, `longitude`, `timezone`

### 按日语境（`data/context/`）

- `DailyContext` - weather / rhythm / wearable / digital / location / `missingFlags`

### 二期分析产物

- `WeatherSensitivity`, `SpaceEmotionLink`, `PhysioCoupling`, `InteractionEffect`, `WarningPattern`

## 三期扩展类型（叙事）

- `ChainLink` - 锚点关联链（causal / theme / person / contrast / evolution）
- `StoryNode`, `NarrativeLine`, `LifeStoryBook` - 生命故事书（`data/analysis/runs/{runId}/story.json`）
- `SelfVoiceProfile`, `VoiceTimelinePoint`, `VoiceTransition`, `SelfVoiceMap` - 多元自我（`selves.json`）
- `ReframeCandidate` - 内化问题叙事候选（`reframe_candidates.json`）
- `ReframeSession`, `ReframeMessage` - 重构对话（`data/reframe/sessions/{id}.json`）
- 用户叙事线编辑：`data/story/edits/{runId}.json`

### InsightReport 三期字段

- `chainLinks[]`, `lifeStory`, `selfVoiceMap`, `reframeCandidates[]`
- 报告新增「叙事脉络」板块

## 数据目录

```
data/
├── settings.json
├── entries/
├── context/
├── story/edits/       # 叙事线用户标注
├── reframe/sessions/  # 重构对话会话
└── analysis/runs/     # chains.json, story.json, selves.json 等
```

详见 `engine/schemas/models.py` 与 `src/types/analysis.ts`。
