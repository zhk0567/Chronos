from benchmark.evaluator import list_fixture_names, run_all_benchmarks


def test_all_benchmark_fixtures_run_without_error():
    names = list_fixture_names()
    assert len(names) >= 4
    results = run_all_benchmarks(use_llm=False)
    assert len(results) == len(names)
    for result in results:
        assert result.entry_count > 0
        assert result.anchor.f1 >= 0
