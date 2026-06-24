from benchmark.evaluator import list_fixture_names, load_fixture, run_benchmark


def test_list_fixture_names_includes_core_fixtures():
    names = list_fixture_names()
    assert "demo" in names
    assert "contradiction" in names
    assert "intensity" in names


def test_run_demo_benchmark_has_metrics():
    entries, labels, contexts = load_fixture("demo")
    result = run_benchmark(entries, labels, use_llm=False, contexts=contexts)
    assert result.entry_count == len(entries)
    assert result.anchor.f1 >= 0
    assert result.theme.tp + result.theme.fn >= len(labels.get("themes", []))
