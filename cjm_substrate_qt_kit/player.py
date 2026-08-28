"""Span playback via QMediaPlayer — the Qt lane's one audio component (kit
extraction 26dd7b85 at the N=3 mark: decomp-qt original, correction-qt carried
copy per warts 1052ce38, transcription-qt SegmentPlayer sibling reconciled
onto the same class). Plays one file span at a time — a model-input WAV slice,
a source-coordinate span of original media, or a whole file (end_s=None, the
former SegmentPlayer's p-verb shape) — at the bracket ladder's 0.5–3.0× speed.
The FFmpeg backend's setPlaybackRate is pitch-preserving (leg-3 field
ratification), so the speed ladder's behavior carries everywhere.

Mechanics: seeks land only once media is loaded, so play_span defers the
setPosition+play to mediaStatusChanged when the source is fresh (an already-
loaded source replays immediately); positionChanged stops at the span end
(backend-granular — a sub-100ms overshoot, inaudible at these spans)."""

import time
from typing import Optional, Tuple

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaDevices, QMediaPlayer

_READY = (QMediaPlayer.LoadedMedia, QMediaPlayer.BufferedMedia,
          QMediaPlayer.EndOfMedia)

# Minimum seconds between actual play STARTS (drive-1 field find, held-r
# variant; the 039c9a62 wedge class): every QMediaPlayer stop()->play() tears
# down and recreates the sink stream — same source or not — and a key-repeat
# storm of restarts wedges the PipeWire node DEVICE-WIDE until it reconnects.
# Requests inside the gap coalesce (latest wins, audio stops at once) and
# play when the burst settles, so a held replay goes quiet and sounds once
# on release.
_MIN_START_GAP_S = 0.25


class SpanPlayer:
    """Play/stop one file span at a time; replay gestures re-enter, escape
    stops. Play starts are rate-limited at this choke point — EVERY caller
    (replay, autoplay, auditions, gesture replays, whole-file toggles) rides
    the same guard."""

    def __init__(self, parent=None):
        self._player = QMediaPlayer(parent)
        self._out = QAudioOutput(parent)
        self._player.setAudioOutput(self._out)
        # Qt 6 binds the default output DEVICE at construction and never
        # looks again: an app launched before the earbuds connect keeps
        # sounding on the old sink until relaunch (walkthrough call-out
        # 76d404bc). QMediaDevices is the only change signal — its
        # audioOutputsChanged fires on every device add/remove (a default
        # swap always rides one), so the output re-binds to the CURRENT
        # system default there. This is dynamic FOLLOW of the system
        # sink, not device SELECTION (the retired --audio-device, 128066f1).
        self._devices = QMediaDevices(self._player)
        self._devices.audioOutputsChanged.connect(self._follow_default_output)
        self._player.positionChanged.connect(self._check_end)
        self._player.mediaStatusChanged.connect(self._on_status)
        self._start_ms = 0
        self._end_ms: Optional[int] = None
        self._pending = False
        self._last_start = 0.0
        self._req: Optional[Tuple[str, float, Optional[float], float]] = None
        self._req_timer = QTimer(self._player)
        self._req_timer.setSingleShot(True)
        self._req_timer.timeout.connect(self._flush_req)

    @property
    def playing(self) -> bool:
        return self._player.playbackState() == QMediaPlayer.PlayingState

    def play_span(self, path: str, start_s: float, end_s: Optional[float],
                  rate: float = 1.0) -> None:
        """Request `path` at start_s, stopping at end_s (file-local seconds —
        source-coordinate seconds ARE file-local on the original media;
        end_s=None plays to the file's natural end).

        An idle request starts immediately; inside the start gap it coalesces
        (see _MIN_START_GAP_S). Stop-then-play always: stale audio under a
        fresh focus would mismatch the card on screen."""
        if end_s is not None and int(end_s * 1000) <= max(0, int(start_s * 1000)):
            # Degenerate span at the player's ms resolution (a chunk nudged
            # down to nothing, e.g. the partial-word case): sound NOTHING.
            # Handed to QMediaPlayer, a start==end window never trips the
            # stop-at-end check cleanly and the file runs on to its natural
            # end — the whole aseg WAV (zero-span replay finding, 2026-08-26).
            # Stop-then-return keeps the stale-audio rule for every caller.
            self.stop()
            return
        if time.monotonic() - self._last_start < _MIN_START_GAP_S:
            self._req = (path, start_s, end_s, rate)
            self._player.stop()
            self._req_timer.start(int(_MIN_START_GAP_S * 1000))
            return
        self._start_span(path, start_s, end_s, rate)

    def play(self, path: str, rate: float = 1.0) -> None:
        """Whole-file convenience (the former SegmentPlayer surface): play
        `path` from the top to its natural end, through the same guard."""
        self.play_span(path, 0.0, None, rate)

    def _flush_req(self) -> None:
        if self._req is not None:
            req, self._req = self._req, None
            self._start_span(*req)

    def _start_span(self, path: str, start_s: float, end_s: Optional[float],
                    rate: float) -> None:
        self._last_start = time.monotonic()
        self._player.stop()
        self._start_ms = max(0, int(start_s * 1000))
        self._end_ms = None if end_s is None else int(end_s * 1000)
        self._player.setPlaybackRate(max(0.1, float(rate)))
        url = QUrl.fromLocalFile(path)
        if (self._player.source() == url
                and self._player.mediaStatus() in _READY):
            self._begin()
        else:
            self._pending = True
            self._player.setSource(url)

    def _on_status(self, status) -> None:
        if self._pending and status in _READY:
            self._pending = False
            self._begin()

    def _begin(self) -> None:
        self._player.setPosition(self._start_ms)
        self._player.play()

    def _check_end(self, pos: int) -> None:
        if self._end_ms is not None and pos >= self._end_ms:
            self.stop()

    def _follow_default_output(self) -> None:
        """Re-bind the sink to the system's current default output when the
        device set changes (earbuds connected after launch). A no-op when
        the default is unchanged, so a mid-span change of an unrelated
        device never restarts the stream."""
        default = QMediaDevices.defaultAudioOutput()
        if self._out.device() != default:
            self._out.setDevice(default)

    def stop(self) -> None:
        self._pending = False
        self._req = None            # an explicit stop cancels a coalesced request
        self._req_timer.stop()
        self._end_ms = None
        self._player.stop()

    def close(self) -> None:
        self.stop()
        self._player.setSource(QUrl())

    def error_text(self) -> Optional[str]:
        """The player's last error string, or None (surfaced in-status)."""
        if self._player.error() == QMediaPlayer.NoError:
            return None
        return self._player.errorString() or "playback error"
