"""SpanPlayer over ONE persistent stream (finding 2cc66110): the decode
command, the feeder's PCM-or-silence contract, clip swap + cancel, and the
device-follow wiring. The sink is NOT started here (bind=False) — a real
stream on the dev box's default output is field-verified per the paint-path
craft — so these drive the bookkeeping and the real ffmpeg decode into the
feeder, offscreen and silent."""
import math
import shutil
import struct
import sys
import time
import wave

import pytest
from PySide6.QtWidgets import QApplication

from cjm_substrate_qt_kit.player import (BYTES_PER_FRAME, CHANNELS, SAMPLE_RATE,
                                          SpanPlayer, _Clip, _Feeder, decode_command)

HAVE_FFMPEG = shutil.which("ffmpeg") is not None


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication(sys.argv[:1])
    yield app


@pytest.fixture
def tone_wav(tmp_path):
    """A 2 s 16 kHz mono sine WAV (the model-input rendition's shape)."""
    path = tmp_path / "tone.wav"
    sr, secs = 16000, 2.0
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        n = int(sr * secs)
        w.writeframes(b"".join(struct.pack("<h", int(12000 * math.sin(2 * math.pi * 440 * i / sr)))
                               for i in range(n)))
    return str(path)


def _wait(pred, timeout=5.0):
    t0 = time.monotonic()
    while not pred():
        if time.monotonic() - t0 > timeout:
            return False
        time.sleep(0.01)
    return True


# ---- decode command ----------------------------------------------------------

def test_decode_command_shape():
    cmd = decode_command("/x/a.wav", 12.345, 15.0, ffmpeg="ffmpeg")
    assert cmd[:6] == ["ffmpeg", "-v", "error", "-nostdin", "-ss", "12.345"]
    assert cmd[6:8] == ["-t", "2.655"]                      # span length, not end
    assert cmd[8:10] == ["-i", "/x/a.wav"]
    assert "-af" not in cmd                                  # 1.0x = no filter
    assert cmd[-7:] == ["-f", "f32le", "-ac", str(CHANNELS), "-ar", str(SAMPLE_RATE), "-"]


def test_decode_command_rate_and_open_end():
    cmd = decode_command("/x/a.mp3", 0.0, None, rate=1.5)
    assert "-t" not in cmd                                   # natural end
    assert cmd[cmd.index("-af") + 1] == "atempo=1.5"        # pitch-preserving ladder
    assert decode_command("/x/a.mp3", 0, None, rate=0.5)[-8] == "atempo=0.5"


# ---- feeder ------------------------------------------------------------------

def test_feeder_is_silence_without_a_clip(qapp):
    f = _Feeder()
    assert f.isSequential()
    assert f.readData(64) == bytes(64)


def test_feeder_drains_blocks_in_order_then_pads_silence(qapp):
    f = _Feeder()
    clip = _Clip()
    clip.blocks.extend([b"\x01" * 10, b"\x02" * 10])
    clip.done = True
    f.set_clip(clip)
    assert f.readData(4) == b"\x01" * 4                      # partial block -> carry
    assert f.readData(12) == b"\x01" * 6 + b"\x02" * 6       # carry, then next block
    assert f.readData(8) == b"\x02" * 4 + bytes(4)           # tail, then silence
    assert f.readData(8) == bytes(8)                          # never short, never empty
    assert not clip.draining


def test_feeder_swap_drops_the_old_carry(qapp):
    f = _Feeder()
    a, b = _Clip(), _Clip()
    a.blocks.append(b"\x01" * 10)
    b.blocks.append(b"\x02" * 10)
    f.set_clip(a)
    f.readData(4)
    f.set_clip(b)                                            # a play swap mid-block
    assert f.readData(10) == b"\x02" * 10


# ---- player bookkeeping (no sink) ---------------------------------------------

def test_degenerate_span_sounds_nothing(qapp):
    """Zero-span replay finding (2026-08-26): a start==end request must
    never reach a decoder — stop-then-return keeps the stale-audio rule."""
    p = SpanPlayer(bind=False, ffmpeg="ffmpeg")
    p.play_span("/tmp/a.wav", 506.8, 506.8)
    assert p._clip is None and p._feeder.clip is None and not p.playing
    p.close()


def test_missing_ffmpeg_surfaces_an_error_not_a_crash(qapp):
    p = SpanPlayer(bind=False, ffmpeg=None)
    p._ffmpeg = None
    p.play_span("/tmp/a.wav", 0.0, 1.0)
    assert "ffmpeg" in (p.error_text() or "")
    assert not p.playing
    p.close()


@pytest.mark.skipif(not HAVE_FFMPEG, reason="ffmpeg not on PATH")
def test_play_span_decodes_into_the_feeder(qapp, tone_wav):
    p = SpanPlayer(bind=False)
    p.play_span(tone_wav, 0.5, 1.0)                          # 0.5 s of tone
    clip = p._clip
    assert clip is p._feeder.clip and p.playing
    assert _wait(lambda: clip.done), "decoder never finished"
    assert clip.error is None
    total = sum(len(b) for b in clip.blocks)
    frames = total // BYTES_PER_FRAME
    assert abs(frames - int(0.5 * SAMPLE_RATE)) < SAMPLE_RATE // 50   # 48 kHz stereo, ~0.5 s
    pcm = p._feeder.readData(total)
    assert pcm != bytes(total), "decoded audio is not silence"
    assert not p.playing                                     # drained
    p.close()


@pytest.mark.skipif(not HAVE_FFMPEG, reason="ffmpeg not on PATH")
def test_restart_is_immediate_and_cancels_the_previous_decoder(qapp, tone_wav):
    p = SpanPlayer(bind=False)
    p.play_span(tone_wav, 0.0, None, rate=0.5)               # long: 4 s of output
    first = p._clip
    assert _wait(lambda: first.started.is_set())
    p.play_span(tone_wav, 1.0, 1.2)                          # r again: no gap, no coalescing
    second = p._clip
    assert second is not first and p._feeder.clip is second
    assert first.cancelled
    assert _wait(lambda: first.done and (first.proc is None or first.proc.poll() is not None))
    assert _wait(lambda: second.done) and second.error is None
    p.close()


@pytest.mark.skipif(not HAVE_FFMPEG, reason="ffmpeg not on PATH")
def test_stop_silences_and_kills_the_decoder(qapp, tone_wav):
    p = SpanPlayer(bind=False)
    p.play_span(tone_wav, 0.0, None, rate=0.5)
    clip = p._clip
    assert _wait(lambda: clip.started.is_set())
    p.stop()
    assert p._clip is None and p._feeder.clip is None and not p.playing
    assert p._feeder.readData(16) == bytes(16)
    assert _wait(lambda: clip.done)
    p.close()


@pytest.mark.skipif(not HAVE_FFMPEG, reason="ffmpeg not on PATH")
def test_decode_failure_is_reported(qapp, tmp_path):
    p = SpanPlayer(bind=False)
    p.play_span(str(tmp_path / "missing.wav"), 0.0, 1.0)
    clip = p._clip
    assert _wait(lambda: clip.done)
    assert "decode error" in (p.error_text() or "")
    p.close()


def test_output_follows_the_system_default_device(qapp):
    """Device-follow (walkthrough call-out 76d404bc): the sink is bound at
    construction; QMediaDevices.audioOutputsChanged re-binds to the CURRENT
    default. With bind=False the listener is wired but the slot is a no-op —
    the contract checked offscreen is the wiring and the no-restart rule."""
    from PySide6.QtCore import QMetaMethod
    p = SpanPlayer(bind=False)
    sig = QMetaMethod.fromSignal(p._devices.audioOutputsChanged)
    assert p._devices.isSignalConnected(sig)
    p._follow_default_output()
    assert p._sink is None                                    # bind=False: never starts a stream
    p._devices.audioOutputsChanged.emit()
    assert p._sink is None
    p.close()
