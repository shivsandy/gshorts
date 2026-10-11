from dataclasses import replace
from pathlib import Path
from shorts_factory.config import Settings
import shorts_factory.main as main_module
import shorts_factory.youtube_upload as upload_module


def test_dry_run_never_calls_uploader(monkeypatch, tmp_path):
    settings=Settings.from_env(force_dry_run=True)
    settings=replace(settings,daily_upload_enabled=True,dry_run=True,output_dir=tmp_path/"output",
        history_file=tmp_path/"history.json",analytics_file=tmp_path/"analytics.json")
    monkeypatch.setattr(main_module.Settings,"from_env",classmethod(lambda cls, root=None, *, force_dry_run=False: settings))
    monkeypatch.setattr(main_module.Settings,"validate_runtime",lambda self: None)
    monkeypatch.setattr(main_module,"render_narration",lambda beats,out_dir,**kwargs:(tmp_path/"voice.wav",[{"duration":7.0,"text":b["text"]} for b in beats]))
    monkeypatch.setattr(main_module,"render_video",lambda *args,**kwargs:{"path":str(tmp_path/"short.mp4"),"duration_seconds":55.0,"file_size_mb":1.0})
    monkeypatch.setattr(main_module,"_summary",lambda *args,**kwargs:None)
    def forbidden_upload(*args,**kwargs): raise AssertionError("Uploader was called during dry-run")
    monkeypatch.setattr(upload_module,"upload_short",forbidden_upload)
    assert main_module.run_pipeline(force_dry_run=True)==0
    assert (tmp_path/"output").exists()
    assert not (tmp_path/"history.json").exists()
