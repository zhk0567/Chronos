from pipeline.checkpoint import entry_fingerprint, load_checkpoint, resume_step_index, save_checkpoint
from pipeline.artifacts import save_run_artifact
from schemas.models import DiaryEntry


def test_fingerprint_stable():
    entries = [
        DiaryEntry(date="2026-01-01", content="hello"),
        DiaryEntry(date="2026-01-02", content="world"),
    ]
    assert entry_fingerprint(entries) == entry_fingerprint(list(reversed(entries)))


def test_resume_step_index(tmp_path, monkeypatch):
    monkeypatch.setenv("CHRONOS_DATA_DIR", str(tmp_path))
    run_id = "run_test"
    entries = [DiaryEntry(date="2026-01-01", content="x")]
    fp = entry_fingerprint(entries)
    save_run_artifact(run_id, "meta.json", {"runId": run_id})
    save_checkpoint(run_id, 2, "gemma3:4b", fp)
    assert resume_step_index(run_id, entries, "gemma3:4b") == 3
    ck = load_checkpoint(run_id)
    assert ck["lastCompletedStep"] == "context"
