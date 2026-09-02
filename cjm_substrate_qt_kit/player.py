"""Span playback over ONE persistent audio stream — the Qt lane's one audio
component (kit extraction 26dd7b85; this cut replaces the QMediaPlayer engine,
finding 2cc66110).

WHY ONE STREAM: every QMediaPlayer play start rebuilt its FFmpeg pipeline INTO
the sink — a PipeWire stream start per play — and stream starts on a bluetooth
node are the device-wide distortion hazard (17c09ebf, 0cfc3173, then the
churn-free recurrence 2cc66110). The 0.25s start-gap guard only spaced the
starts out and cost every replay a delay. Here the stream starts ONCE: a
`QAudioSink` in pull mode reads forever from `_Feeder`, which hands it the
current clip's PCM or silence. Play is a clip swap (the Textual ChunkPlayer's
shape, 7d7e37af-era, kept inside Qt's device model so default-output FOLLOW
survives: a default-device change is the only stream rebuild).

DECODE is outside the sink: one `ffmpeg` subprocess per play — fast seek to
the span, `atempo` for the pitch-preserving 0.5–3.0× ladder, f32le stereo at
48 kHz streamed in blocks — so a span deep in a multi-hour source sounds on
its first block, not after a full decode. Any container ffmpeg reads works
(model-input WAV slices and the original media alike). A new request kills
the previous decoder and swaps the clip; `stop` swaps to silence. There is no
rate limit and no coalescing: restarting a segment is immediate.

Surface (unchanged for the three consumers): play_span / play / stop / close /
playing / error_text."""

import collections
import shutil
import subprocess
import threading
from typing import Deque, List, Optional

from PySide6.QtCore import QIODevice
from PySide6.QtMultimedia import QAudioFormat, QAudioSink, QMediaDevices

SAMPLE_RATE = 48000
CHANNELS = 2
BYTES_PER_FRAME = 4 * CHANNELS            # f32le stereo
# Decoder read granularity (~85 ms) and the sink's buffer (~85 ms): small
# enough that a swap sounds at once, large enough that the pull timer never
# starves under normal scheduling. Field-tunable.
BLOCK_BYTES = 4096 * BYTES_PER_FRAME
SINK_BUFFER_BYTES = 4096 * BYTES_PER_FRAME
_STDERR_TAIL = 400


def decode_command(path: str, start_s: float, end_s: Optional[float],
                   rate: float = 1.0, ffmpeg: str = "ffmpeg") -> List[str]:
    """The ffmpeg invocation for one span: input-side seek (fast), `-t` bounds
    the span (end_s=None = natural end), atempo carries the speed ladder
    (pitch-preserving; ffmpeg accepts 0.5–100 per stage), f32le stereo 48 kHz
    on stdout. Pure — the unit-testable half of the decode path."""
    cmd = [ffmpeg, "-v", "error", "-nostdin", "-ss", f"{max(0.0, start_s):.3f}"]
    if end_s is not None:
        cmd += ["-t", f"{max(0.0, end_s - start_s):.3f}"]
    cmd += ["-i", path]
    rate = float(rate)
    if rate != 1.0:
        cmd += ["-af", f"atempo={max(0.5, min(100.0, rate)):g}"]
    cmd += ["-f", "f32le", "-ac", str(CHANNELS), "-ar", str(SAMPLE_RATE), "-"]
    return cmd


class _Clip:
    """One decode in flight: the block queue the feeder drains, the decoder's
    liveness, and its failure text. Decoder thread appends; the GUI thread
    (pull-timer readData) pops — deque ops are atomic under the GIL."""

    def __init__(self) -> None:
        self.blocks: Deque[bytes] = collections.deque()
        self.done = False           # decoder finished (or was cancelled)
        self.cancelled = False
        self.error: Optional[str] = None
        self.proc: Optional[subprocess.Popen] = None
        self.started = threading.Event()   # first block landed (or done)

    @property
    def draining(self) -> bool:
        return bool(self.blocks) or not self.done


def _run_decoder(clip: _Clip, cmd: List[str]) -> None:
    """Decoder thread body: stream ffmpeg's stdout into the clip in blocks."""
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError as e:
        clip.error = f"decoder failed to start: {e}"
        clip.done = True
        clip.started.set()
        return
    clip.proc = proc
    if clip.cancelled:            # cancelled before the process existed
        proc.kill()
    try:
        assert proc.stdout is not None
        while True:
            block = proc.stdout.read(BLOCK_BYTES)
            if not block:
                break
            if clip.cancelled:
                break
            clip.blocks.append(block)
            clip.started.set()
        err = b""
        if proc.stderr is not None:
            err = proc.stderr.read()
        rc = proc.wait()
        if rc != 0 and not clip.cancelled:
            tail = err.decode("utf-8", "replace").strip()[-_STDERR_TAIL:]
            clip.error = f"decode error (ffmpeg rc={rc}): {tail or 'no detail'}"
    finally:
        clip.done = True
        clip.started.set()


class _Feeder(QIODevice):
    """The sink's pull source: the current clip's PCM, else silence. Never
    returns short — a continuous stream is the whole point (a short read
    would drop the sink to Idle). A clip decoding slower than playback pads
    silence too (a beat of quiet, not a stream state change)."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._clip: Optional[_Clip] = None
        self._carry = b""           # unread remainder of the last popped block
        self.reads = 0              # pull count (diagnostics/tests)

    def set_clip(self, clip: Optional[_Clip]) -> None:
        self._clip = clip
        self._carry = b""

    @property
    def clip(self) -> Optional[_Clip]:
        return self._clip

    def isSequential(self) -> bool:
        return True

    def bytesAvailable(self) -> int:
        return BLOCK_BYTES + super().bytesAvailable()

    def readData(self, maxlen: int) -> bytes:
        self.reads += 1
        want = int(maxlen)
        out: List[bytes] = []
        have = 0
        clip = self._clip
        if clip is not None:
            if self._carry:
                take = self._carry[:want]
                self._carry = self._carry[want:]
                out.append(take)
                have = len(take)
            while have < want and clip.blocks:
                block = clip.blocks.popleft()
                room = want - have
                if len(block) > room:
                    out.append(block[:room])
                    self._carry = block[room:]
                    have = want
                else:
                    out.append(block)
                    have += len(block)
        if have < want:
            out.append(bytes(want - have))      # silence
        return b"".join(out)

    def writeData(self, data) -> int:  # pull-only device
        return -1


class SpanPlayer:
    """Play/stop one file span at a time over the persistent stream; replay
    gestures re-enter immediately, escape stops. Every caller (replay,
    autoplay, auditions, gesture replays, whole-file toggles) is a clip swap."""

    def __init__(self, parent=None, bind: bool = True,
                 ffmpeg: Optional[str] = None) -> None:
        self._ffmpeg = ffmpeg or shutil.which("ffmpeg")
        self._fmt = QAudioFormat()
        self._fmt.setSampleRate(SAMPLE_RATE)
        self._fmt.setChannelCount(CHANNELS)
        self._fmt.setSampleFormat(QAudioFormat.Float)
        self._feeder = _Feeder()
        self._feeder.open(QIODevice.ReadOnly)
        self._sink: Optional[QAudioSink] = None
        self._device = None
        self._clip: Optional[_Clip] = None
        self._thread: Optional[threading.Thread] = None
        self._sink_error: Optional[str] = None
        # Qt binds an output DEVICE at sink construction and never looks
        # again; QMediaDevices.audioOutputsChanged fires on every device
        # add/remove (a default swap rides one), so the sink re-binds to the
        # CURRENT system default there — dynamic FOLLOW, not selection
        # (76d404bc; the retired --audio-device, 128066f1).
        self._devices = QMediaDevices(parent)
        self._devices.audioOutputsChanged.connect(self._follow_default_output)
        self._bind_enabled = bind
        if bind:
            self._bind(QMediaDevices.defaultAudioOutput())

    # ---- stream -----------------------------------------------------------

    def _bind(self, device) -> None:
        """Start the ONE stream on `device` (the only place a stream starts)."""
        self._unbind()
        self._device = device
        if device is None or device.isNull():
            self._sink_error = "no audio output device"
            return
        fmt = self._fmt
        if not device.isFormatSupported(fmt):
            fmt = device.preferredFormat()
        sink = QAudioSink(device, fmt)
        sink.setBufferSize(SINK_BUFFER_BYTES)
        sink.start(self._feeder)
        self._sink = sink
        self._sink_error = None

    def _unbind(self) -> None:
        if self._sink is not None:
            self._sink.stop()
            self._sink = None

    def _follow_default_output(self) -> None:
        """Re-bind to the system's current default output when the device set
        changes (earbuds connected after launch). A no-op when the default is
        unchanged, so a change of an unrelated device never restarts the
        stream."""
        if not self._bind_enabled:
            return
        default = QMediaDevices.defaultAudioOutput()
        if self._device is None or self._device != default:
            self._bind(default)

    @property
    def stream_active(self) -> bool:
        return self._sink is not None

    # ---- clips --------------------------------------------------------------

    @property
    def playing(self) -> bool:
        clip = self._clip
        return clip is not None and clip.draining

    def play_span(self, path: str, start_s: float, end_s: Optional[float],
                  rate: float = 1.0) -> None:
        """Request `path` at start_s, stopping at end_s (file-local seconds —
        source-coordinate seconds ARE file-local on the original media;
        end_s=None plays to the file's natural end). Immediate: the previous
        decoder dies, the feeder swaps to the new clip, and audio sounds on
        the clip's first block."""
        if end_s is not None and end_s - start_s <= 0.001:
            # Degenerate span (a chunk nudged down to nothing, e.g. the
            # partial-word case; zero-span replay finding 2026-08-26): sound
            # NOTHING — stop-then-return keeps the stale-audio rule.
            self.stop()
            return
        self._cancel_clip()
        clip = _Clip()
        if not self._ffmpeg:
            clip.error = "ffmpeg not found on PATH — playback unavailable"
            clip.done = True
            clip.started.set()
            self._clip = clip
            return
        cmd = decode_command(path, start_s, end_s, rate, ffmpeg=self._ffmpeg)
        self._clip = clip
        self._feeder.set_clip(clip)
        self._thread = threading.Thread(target=_run_decoder, args=(clip, cmd),
                                        name="span-decoder", daemon=True)
        self._thread.start()

    def play(self, path: str, rate: float = 1.0) -> None:
        """Whole-file convenience (the former SegmentPlayer surface): play
        `path` from the top to its natural end."""
        self.play_span(path, 0.0, None, rate)

    def _cancel_clip(self) -> None:
        clip = self._clip
        if clip is None:
            return
        clip.cancelled = True
        proc = clip.proc
        if proc is not None and proc.poll() is None:
            try:
                proc.kill()
            except OSError:
                pass
        clip.blocks.clear()

    def stop(self) -> None:
        """Silence at once (navigation left the segment, escape, close)."""
        self._feeder.set_clip(None)
        self._cancel_clip()
        self._clip = None

    def close(self) -> None:
        self.stop()
        self._unbind()
        self._feeder.close()

    def error_text(self) -> Optional[str]:
        """The current clip's decode failure or the sink's binding failure,
        else None (surfaced in-status by the shells)."""
        clip = self._clip
        if clip is not None and clip.error:
            return clip.error
        if self._sink_error and self._bind_enabled:
            return self._sink_error
        if self._sink is not None and getattr(self._sink.error(), "value", 0) != 0:
            return f"audio sink error: {self._sink.error()}"      # QtAudio.NoError == 0
        return None
