import pytest
from shorts_factory.youtube_upload import run_marker, upload_short

def test_run_marker_is_deterministic_and_unambiguous():
    assert run_marker("2026-10-11")=="[SHORTS_FACTORY_RUN:2026-10-11]"

def test_invalid_privacy_is_rejected_before_network_or_credentials():
    with pytest.raises(ValueError,match="Invalid upload privacy"):
        upload_short(object(),"missing.mp4",{},run_key="2026-10-11",privacy="everyone")

def test_upload_never_uses_markerless_script():
    assert "SHORTS_FACTORY_RUN" in run_marker("manual-test")

class _Request:
    def __init__(self, value): self.value=value
    def execute(self, **kwargs): return self.value
class _Channels:
    def list(self, **kwargs): return _Request({"items":[{"contentDetails":{"relatedPlaylists":{"uploads":"uploads-playlist"}}}]})
class _PlaylistItems:
    def list(self, **kwargs): return _Request({"items":[{"snippet":{"publishedAt":"2026-10-11T03:17:00Z","resourceId":{"kind":"youtube#video","videoId":"already-there"}}}]})
class _Videos:
    def __init__(self, marker): self.marker=marker
    def list(self, **kwargs): return _Request({"items":[{"id":"already-there","snippet":{"title":"An existing Short","description":"Generated item\n"+self.marker},"status":{"privacyStatus":"unlisted"},"contentDetails":{"duration":"PT55S"}}]})
class _FakeYouTube:
    def __init__(self, marker): self.marker=marker
    def channels(self): return _Channels()
    def playlistItems(self): return _PlaylistItems()
    def videos(self): return _Videos(self.marker)

def test_existing_run_marker_recovers_video_instead_of_reuploading():
    from shorts_factory.youtube_upload import find_existing_upload
    marker=run_marker("2026-10-11")
    found=find_existing_upload(_FakeYouTube(marker),marker)
    assert found["video_id"]=="already-there"
    assert found["duration"]=="PT55S"

def test_missing_remote_marker_is_not_mistaken_for_a_match():
    from shorts_factory.youtube_upload import find_existing_upload
    found=find_existing_upload(_FakeYouTube(run_marker("another-day")),run_marker("2026-10-11"))
    assert found is None

def test_recent_remote_topic_markers_prevent_republication_after_state_push_failure():
    from shorts_factory.youtube_upload import remote_used_topic_ids
    topics=[{"id":"moon-recedes","title":"The Moon is slowly moving away from Earth"},
            {"id":"venus-day-year","title":"Venus has a day longer than its year"}]
    uploads=[{"title":"Renamed Short","description":"Text\n[SHORTS_FACTORY_TOPIC:moon-recedes]"},
             {"title":"Venus has a day longer than its year","description":"Legacy upload without metadata marker"}]
    assert remote_used_topic_ids(uploads,topics)=={"moon-recedes","venus-day-year"}

def _install_fake_google_client(monkeypatch):
    import sys, types
    package=types.ModuleType("googleapiclient"); package.__path__=[]
    http_module=types.ModuleType("googleapiclient.http")
    errors_module=types.ModuleType("googleapiclient.errors")
    class FakeMediaFileUpload:
        def __init__(self,path,**kwargs): self.path=path; self.kwargs=kwargs
    class FakeHttpError(Exception):
        def __init__(self,status):
            super().__init__("fake HTTP error")
            self.resp=types.SimpleNamespace(status=status)
    http_module.MediaFileUpload=FakeMediaFileUpload; errors_module.HttpError=FakeHttpError
    monkeypatch.setitem(sys.modules,"googleapiclient",package)
    monkeypatch.setitem(sys.modules,"googleapiclient.http",http_module)
    monkeypatch.setitem(sys.modules,"googleapiclient.errors",errors_module)
    return FakeMediaFileUpload,FakeHttpError

class _InsertRequest:
    def __init__(self, owner, fail=False): self.owner=owner; self.fail=fail
    def next_chunk(self, num_retries=0):
        self.owner.chunk_retry_values.append(num_retries)
        if self.fail: raise ConnectionError("simulated network interruption")
        return None,{"id":"fresh-video-id"}
class _UploadVideos(_Videos):
    def __init__(self, marker, *, fail=False):
        super().__init__(marker); self.fail=fail; self.insert_count=0; self.body=None; self.media=None; self.chunk_retry_values=[]
    def insert(self, *, part, body, media_body):
        self.insert_count+=1; self.body=body; self.media=media_body; self.part=part
        return _InsertRequest(self,fail=self.fail)
class _UploadYouTube(_FakeYouTube):
    def __init__(self, marker, *, fail=False):
        super().__init__(marker); self.video_endpoint=_UploadVideos(marker,fail=fail)
    def videos(self): return self.video_endpoint

def test_successful_upload_sets_visibility_and_both_idempotency_markers(monkeypatch,tmp_path):
    FakeMediaFileUpload,_=_install_fake_google_client(monkeypatch)
    from shorts_factory.youtube_upload import upload_short
    mp4=tmp_path/"short.mp4"; mp4.write_bytes(b"fake MP4 bytes")
    yt=_UploadYouTube("[SHORTS_FACTORY_RUN:other-date]")
    script={"topic_id":"moon-recedes","title":"Moon fact","description":"A cited explanation.\n\n#ScienceShorts #Shorts","hashtags":["#ScienceShorts","#Shorts"]}
    result=upload_short(yt,str(mp4),script,run_key="2026-10-11",privacy="unlisted",language="en",max_retries=2)
    assert result["video_id"]=="fresh-video-id"
    assert yt.video_endpoint.insert_count==1
    assert yt.video_endpoint.body["status"]["privacyStatus"]=="unlisted"
    desc=yt.video_endpoint.body["snippet"]["description"]
    assert run_marker("2026-10-11") in desc
    assert "[SHORTS_FACTORY_TOPIC:moon-recedes]" in desc
    assert yt.video_endpoint.media.kwargs["resumable"] is True
    assert yt.video_endpoint.chunk_retry_values==[2]

def test_ambiguous_upload_failure_does_not_issue_a_second_insert(monkeypatch,tmp_path):
    _install_fake_google_client(monkeypatch)
    from shorts_factory.youtube_upload import upload_short
    mp4=tmp_path/"short.mp4"; mp4.write_bytes(b"fake MP4 bytes")
    yt=_UploadYouTube("[SHORTS_FACTORY_RUN:other-date]",fail=True)
    script={"topic_id":"moon-recedes","title":"Moon fact","description":"A cited explanation.","hashtags":["#Shorts"]}
    with pytest.raises(RuntimeError,match="No automatic second insert was attempted"):
        upload_short(yt,str(mp4),script,run_key="2026-10-11",privacy="unlisted",max_retries=1)
    assert yt.video_endpoint.insert_count==1
