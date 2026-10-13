from inspection_report.cli import list_images, main
from inspection_report.config import Settings


def test_defaults_are_local():
    assert Settings().backend == "local"


def test_api_backend_via_env(monkeypatch):
    monkeypatch.setenv("INSPECTION_BACKEND", "api")
    assert Settings().backend == "api"


def test_list_images_filters_by_suffix(tmp_path):
    (tmp_path / "b.JPG").write_bytes(b"x")
    (tmp_path / "a.png").write_bytes(b"x")
    (tmp_path / "notes.txt").write_text("x")
    assert list_images(Settings(images_dir=tmp_path)) == ["a.png", "b.JPG"]


def test_list_images_missing_dir(tmp_path):
    assert list_images(Settings(images_dir=tmp_path / "nope")) == []


def test_status_command(capsys, monkeypatch, tmp_path):
    monkeypatch.setenv("INSPECTION_IMAGES_DIR", str(tmp_path))
    assert main(["status"]) == 0
    out = capsys.readouterr().out
    assert "Backend: local" in out and "Images in" in out
