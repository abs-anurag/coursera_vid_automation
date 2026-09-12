from coursera.completion_detector import CompletionDetector, is_video_complete
from coursera.video_controller import VideoState


def test_not_complete_without_playback_progress():
    assert not is_video_complete(600, 600, True, playback_advanced=False)


def test_complete_when_ended_after_advance():
    assert is_video_complete(599, 600, True, playback_advanced=True)


def test_complete_near_duration_threshold():
    assert is_video_complete(590, 600, False, playback_advanced=True, threshold=0.98)


def test_not_complete_midway():
    assert not is_video_complete(100, 600, False, playback_advanced=True)


def test_detector_requires_observed_advance():
    detector = CompletionDetector(0.98)
    state = VideoState(present=True, currentTime=600, duration=600, ended=True, paused=True)
    assert not detector.is_complete(state)
    detector.observe(VideoState(present=True, currentTime=10, duration=600, ended=False, paused=False))
    detector.observe(VideoState(present=True, currentTime=600, duration=600, ended=True, paused=True))
    assert detector.playback_advanced
    assert detector.is_complete(VideoState(present=True, currentTime=600, duration=600, ended=True, paused=True))
