from utils.confidence import confidence_label


def test_confidence_label_tiers():
    assert confidence_label(0.85) == "高"
    assert confidence_label(0.7) == "高"
    assert confidence_label(0.55) == "中"
    assert confidence_label(0.45) == "中"
    assert confidence_label(0.2) == "低"
