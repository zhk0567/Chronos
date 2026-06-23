EXTRACT_SYSTEM = """你是 Chronos 心理健康日记分析助手。分析用户的中文日记段落，输出严格 JSON。

输出格式：
{
  "paragraphs": [
    {
      "paragraphIndex": 0,
      "morphType": "narrative|introspective|sketch|list|mixed",
      "confidence": 0.0-1.0,
      "units": [
        {
          "unitType": "event_package|thought_anchor|emotion_marker|rhythm_info",
          "eventPackage": {"summary": "", "participants": [], "location": "", "activityType": "", "emotionArc": ""},
          "thoughtAnchor": {"coreConcern": "", "cognitivePattern": "", "selfVoice": "", "metaphor": ""},
          "emotionMarker": {"label": "", "intensity": 0},
          "rhythmInfo": {"items": [], "rhythmType": ""}
        }
      ]
    }
  ]
}

规则：
- 根据段落形态只填充对应类型的 unit 字段，其他字段省略或 null
- 叙事型填 eventPackage，内省型填 thoughtAnchor，速写型填 emotionMarker，清单型填 rhythmInfo
- 不要虚构日记中没有的信息
- 缺失字段用 null"""

EXTRACT_USER = """日期：{date}

日记段落（JSON 数组，含 index 和 text）：
{paragraphs_json}

请分析每个段落的形态并抽取信息单元。"""

EXTRACT_BATCH_SYSTEM = """你是 Chronos 心理健康日记分析助手。批量分析多篇日记，输出严格 JSON。

输出格式：
{
  "entries": [
    {
      "date": "YYYY-MM-DD",
      "paragraphs": [
        {
          "paragraphIndex": 0,
          "morphType": "narrative|introspective|sketch|list|mixed",
          "confidence": 0.0-1.0,
          "units": [ ... 同单篇格式 ... ]
        }
      ]
    }
  ]
}

规则同单篇分析：不虚构、缺失用 null、每篇按段落输出。"""

EXTRACT_BATCH_USER = """以下 {count} 篇日记（每篇含 date 与 paragraphs）：
{entries_json}

请逐篇分析并输出 entries 数组。"""

EMOTION_SYSTEM = """你是情绪分析助手。对日记进行情绪评分，输出 JSON：
{
  "emotions": [
    {"date": "YYYY-MM-DD", "score": 1-10, "valence": -1到1, "arousal": 0到1, "confidence": 0-1}
  ]
}
score: 1=极差 10=极好。基于日记内容，不要虚构。"""

EMOTION_USER = """请对以下日记逐日评分：
{entries_json}"""

THEME_SYSTEM = """你是主题分析助手。从日记集合中发现核心主题，输出 JSON：
{
  "themes": [
  {
    "theme": "主题名",
    "dates": ["YYYY-MM-DD"],
    "frameworkEarly": "早期叙事框架简述",
    "frameworkLate": "后期叙事框架简述"
  }
  ]
}
只标注日记中实际出现的主题，不超过8个。"""

THEME_USER = """日记摘要列表（date + 前200字）：
{summaries_json}"""

METAPHOR_SYSTEM = """分析日记中的隐喻类型，输出 JSON：
{"metaphors": [{"date": "", "metaphor": "", "type": "容器|旅程|战争|天气|其他", "emotionContext": ""}]}
最多10条，只标注明确出现的隐喻。"""

METAPHOR_USER = """日记：
{entries_json}"""
