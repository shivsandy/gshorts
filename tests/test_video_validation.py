import shutil, subprocess
from pathlib import Path
import pytest
from shorts_factory.validator import ValidationError, validate_video

@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"),reason="FFmpeg tools unavailable")
def test_validates_real_mp4_codecs_duration_and_dimensions(tmp_path: Path):
    path=tmp_path/"sample.mp4"
    command=["ffmpeg","-y","-v","error","-f","lavfi","-i","color=c=black:s=360x640:r=30","-f","lavfi","-i","sine=frequency=440:sample_rate=44100","-t","2","-c:v","libx264","-pix_fmt","yuv420p","-c:a","aac","-shortest",str(path)]
    subprocess.run(command,check=True,timeout=30)
    result=validate_video(path,min_seconds=1,max_seconds=3,max_file_size_mb=10,expected_size=(360,640))
    assert result["video_codec"]=="h264"
    assert result["audio_codec"]=="aac"
    assert result["duration_seconds"]>=1
    with pytest.raises(ValidationError): validate_video(path,min_seconds=50,max_seconds=60,max_file_size_mb=10,expected_size=(360,640))
