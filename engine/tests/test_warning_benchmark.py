from benchmark.evaluator import load_fixture, run_benchmark
from benchmark.targets import WARNING_PRECISION_TARGET, WARNING_RECALL_TARGET, warning_targets_met


def test_list_fixture_names_includes_warning():
    from benchmark.evaluator import list_fixture_names

    assert "warning" in list_fixture_names()


def test_warning_benchmark_meets_targets():
    entries, labels, contexts = load_fixture("warning")
    result = run_benchmark(entries, labels, use_llm=False, contexts=contexts)
    assert result.warning is not None
    assert result.warning.recall >= WARNING_RECALL_TARGET
    assert result.warning.precision >= WARNING_PRECISION_TARGET
    assert warning_targets_met(result.warning.precision, result.warning.recall)
    assert result.details.get("warningTargets", {}).get("met") is True
