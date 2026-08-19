"""Readability test-bed: error-seeded reading trials measuring which theme
choices help the reader catch mistakes faster.

Feed it real reading material (a markdown file — e.g. a session scratchpad;
fence markers are stripped but fence CONTENT is kept, since scratchpad
responses live inside code fences). Paragraphs get deterministic seeded
errors (letter transposition, doubled word, dropped word, confusable-word
swap, punctuation slip) plus clean controls; each renders under a theme
variant from a small crossed grid, and every response records hit/miss +
time-to-decision to JSONL. Run:

    python -m cjm_substrate_qt_kit.testbed FILE.md [--seed N] [--trials N]
        [--out results.jsonl]
    python -m cjm_substrate_qt_kit.testbed --summarize results.jsonl ...

In a trial: click the word that reads wrong, or press C if the paragraph is
clean. Per-variant catch rate + latency are the perceptual evidence that
tunes the default theme pair (the pass-3 flywheel)."""

import argparse
import hashlib
import json
import random
import re
import statistics
import time
from pathlib import Path
from typing import Optional

from cjm_substrate_qt_kit.testbed_corpus import PARAGRAPHS
from cjm_substrate_qt_kit.theme import apply_theme, load_theme, style_text_pane
from PySide6.QtCore import QPointF, Qt, QTimer, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication, QLabel, QTextEdit, QVBoxLayout, QWidget

# Function words safe to drop for the dropped-word class — their absence
# reads wrong without changing the topic.
DROPPABLE = {"the", "a", "an", "of", "to", "is", "are", "was", "in", "on",
             "that", "it", "and", "for", "with", "as", "be", "has", "have"}

CONFUSABLES = {"their": "there", "there": "their", "then": "than",
               "than": "then", "its": "it's", "form": "from", "from": "form",
               "of": "off", "off": "of", "to": "too", "your": "you're",
               "and": "an", "an": "and", "been": "being", "being": "been",
               "affect": "effect", "effect": "affect", "lose": "loose"}

# The first crossed grid (pass-3 DEC f2d83ddf): scheme x body size x
# line-height, measure held at the default; family/measure are follow-up
# sweeps. Dimensions provisional until live-run evidence.
CLASSES = ("transpose", "double", "drop", "swap", "punct")
SCHEMES = ("light", "dark")
SIZES = (11.0, 12.0, 13.0)
LINE_HEIGHTS = (1.3, 1.45, 1.6)


def load_paragraphs(path) -> list:
    """Prose paragraphs from a markdown file: fence markers stripped (fence
    CONTENT kept — scratchpad responses live inside fences), then whole
    blocks rejected when ANY line looks structural (heading/list/table/
    quote/brace/quote/comment/terminal-glyph lead) or the letter-ratio
    falls below 0.85 — flattened structure reads like seeded errors (field
    finding 37434c1e). Survivors are 20-100 words."""
    text = Path(path).read_text()
    lines = [ln for ln in text.splitlines() if not ln.lstrip().startswith("```")]
    leads = ("#", "-", "*", "|", ">", "{", "}", "[", '"', "'", "//", "`",
             "●", "⎿")
    paragraphs = []
    for block in re.split(r"\n\s*\n", "\n".join(lines)):
        stripped = [ln.strip() for ln in block.splitlines() if ln.strip()]
        if not stripped or any(ln.startswith(leads) for ln in stripped):
            continue
        flat = " ".join(block.split())
        friendly = sum(1 for c in flat if c.isalpha() or c.isspace())
        if friendly / len(flat) < 0.85:
            continue
        if 20 <= len(flat.split()) <= 100:
            paragraphs.append(flat)
    return paragraphs


def _core(word: str) -> str:
    """A token's core with leading/trailing punctuation stripped (internal
    apostrophes survive, so contractions stay whole)."""
    return word.strip(".,;:!?\"'()[]{}")


def _seed_transpose(words: list, rng: random.Random) -> Optional[tuple]:
    """Swap two adjacent interior letters of one word of length >= 5."""
    idxs = [i for i, w in enumerate(words) if len(_core(w)) >= 5]
    if not idxs:
        return None
    i = rng.choice(idxs)
    w = words[i]
    spots = [j for j in range(1, len(w) - 2)
             if w[j].isalpha() and w[j + 1].isalpha() and w[j] != w[j + 1]]
    if not spots:
        return None
    j = rng.choice(spots)
    out = words.copy()
    out[i] = w[:j] + w[j + 1] + w[j] + w[j + 2:]
    return out, i, "transposed %r -> %r" % (w, out[i])


def _seed_double(words: list, rng: random.Random) -> Optional[tuple]:
    """Duplicate one plain word ("the the")."""
    idxs = [i for i, w in enumerate(words) if w.isalpha() and len(w) >= 2]
    if not idxs:
        return None
    i = rng.choice(idxs)
    out = words[:i] + [words[i]] + words[i:]
    return out, i + 1, "doubled %r" % words[i]


def _seed_drop(words: list, rng: random.Random) -> Optional[tuple]:
    """Remove one interior function word; the gap is what reads wrong."""
    idxs = [i for i, w in enumerate(words)
            if w.lower() in DROPPABLE and 0 < i < len(words) - 1]
    if not idxs:
        return None
    i = rng.choice(idxs)
    out = words[:i] + words[i + 1:]
    return out, i, "dropped %r" % words[i]


def _seed_swap(words: list, rng: random.Random) -> Optional[tuple]:
    """Replace one word with its confusable (their/there, affect/effect)."""
    idxs = [i for i, w in enumerate(words) if _core(w).lower() in CONFUSABLES]
    if not idxs:
        return None
    i = rng.choice(idxs)
    w = words[i]
    core = _core(w)
    repl = CONFUSABLES[core.lower()]
    if core[0].isupper():
        repl = repl.capitalize()
    out = words.copy()
    out[i] = w.replace(core, repl, 1)
    return out, i, "swapped %r -> %r" % (core, repl)


def _seed_punct(words: list, rng: random.Random) -> Optional[tuple]:
    """Turn a sentence-internal period into a comma. The stranded capital on
    the next word keeps the error decidable without the original text; the
    comma-REMOVAL variant is retired as undecidable (addendum 6b5d48c9)."""
    idxs = [i for i, w in enumerate(words[:-1])
            if w.endswith(".") and words[i + 1][:1].isupper()]
    if not idxs:
        return None
    i = rng.choice(idxs)
    out = words.copy()
    out[i] = words[i][:-1] + ","
    return out, i, "punct %r -> %r" % (words[i], out[i])


def seed_error(words: list, cls: str, rng: random.Random) -> Optional[tuple]:
    """Apply one error class to a token list; (mutated_words, target_token,
    detail) or None when the class has nothing to bite on."""
    fn = {"transpose": _seed_transpose, "double": _seed_double,
          "drop": _seed_drop, "swap": _seed_swap, "punct": _seed_punct}[cls]
    return fn(words, rng)


def build_trials(paragraphs: list, rng: random.Random, n_trials: int,
                 clean_ratio: float = 0.2, variants: Optional[list] = None) -> list:
    """The trial plan: variants covered evenly (shuffled round-robin over the
    grid — the default crossed grid, or a focused sweep from build_variants),
    ~clean_ratio control paragraphs, error classes tried in shuffled order
    until one bites."""
    variants = list(variants) if variants else build_variants()
    rng.shuffle(variants)
    classes = list(CLASSES)
    trials = []
    for k in range(n_trials):
        para = rng.choice(paragraphs)
        trial = {"paragraph": para, "variant": variants[k % len(variants)],
                 "cls": None, "text": para, "target": None, "detail": ""}
        if rng.random() >= clean_ratio:
            rng.shuffle(classes)
            for cls in classes:
                seeded = seed_error(para.split(), cls, rng)
                if seeded is not None:
                    trial.update(cls=cls, text=" ".join(seeded[0]),
                                 target=seeded[1], detail=seeded[2])
                    break
        trials.append(trial)
    return trials


def _token_index(text: str, pos: int) -> int:
    """Whitespace-token index at character offset pos (clamped to the text)."""
    before = text[:pos]
    idx = len(before.split()) - 1
    if pos < len(text) and (not before or before[-1].isspace()):
        idx += 1
    return max(idx, 0)


class ClickPane(QTextEdit):
    """Read-only pane reporting the whitespace-token index of clicks that
    land ON a word — blank space, margins, and gaps never count."""

    word_clicked = Signal(int)

    def __init__(self):
        super().__init__()
        self.setReadOnly(True)

    def hit_token(self, point) -> Optional[int]:
        """Token index for a viewport point; None when no character is hit
        (blank space, margins, and inter-word gaps do not count)."""
        doc_point = QPointF(point.x() + self.horizontalScrollBar().value(),
                            point.y() + self.verticalScrollBar().value())
        pos = self.document().documentLayout().hitTest(
            doc_point, Qt.HitTestAccuracy.ExactHit)
        text = self.toPlainText()
        if pos < 0 or pos >= len(text) or text[pos].isspace():
            return None
        return _token_index(text, pos)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        idx = self.hit_token(event.position())
        if idx is not None:
            self.word_clicked.emit(idx)
        super().mousePressEvent(event)


class TrialWindow(QWidget):
    """The trial loop: render the paragraph under its variant, take the
    click-or-clean response, score with +/-1 token tolerance, append one
    JSONL row per response, auto-advance."""

    def __init__(self, trials: list, out_path):
        super().__init__()
        self.trials = trials
        self.out_path = Path(out_path)
        self.index = -1
        self.t0 = 0.0
        self.answered = False
        self.setWindowTitle("readability test-bed")
        self.pane = ClickPane()
        self.status = QLabel("")
        layout = QVBoxLayout(self)
        layout.addWidget(self.pane, 1)
        layout.addWidget(self.status)
        self.pane.word_clicked.connect(self.respond)
        self.resize(900, 560)
        self.show_intro()

    def show_intro(self) -> None:
        intro = (
            "READABILITY TEST-BED\n\n"
            "Each trial shows one paragraph. Most contain exactly one seeded "
            "error; some are clean controls.\n\n"
            "Error classes:\n"
            "transpose — two adjacent letters swapped inside a word\n"
            "double — a word repeated\n"
            "drop — a small connecting word missing\n"
            "swap — a confusable word substituted (their/there, affect/effect)\n"
            "punct — a mid-sentence period turned into a comma\n\n"
            "Click the word that reads wrong, or press C if the paragraph is "
            "clean. Timing starts the moment a paragraph appears.\n\n"
            "Press Enter to start.")
        theme = apply_theme(QApplication.instance())
        self.pane.setPlainText(intro)
        style_text_pane(self.pane, theme)
        self.status.setText("%d trials queued — press Enter to start"
                            % len(self.trials))

    def next_trial(self) -> None:
        self.index += 1
        if self.index >= len(self.trials):
            self.close()
            return
        trial = self.trials[self.index]
        variant = trial["variant"]
        overrides = {k: v for k, v in variant.items()
                     if k not in ("scheme", "theme")}
        theme = apply_theme(QApplication.instance(), overrides, variant["scheme"])
        self.pane.setPlainText(trial["text"])
        style_text_pane(self.pane, theme)
        self.status.setText("%d/%d — click the word that reads wrong, or press "
                            "C if the paragraph is clean"
                            % (self.index + 1, len(self.trials)))
        self.answered = False
        self.t0 = time.monotonic()

    def keyPressEvent(self, event) -> None:
        if self.index < 0:
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self.next_trial()
            else:
                super().keyPressEvent(event)
        elif event.key() == Qt.Key.Key_C:
            self.respond(None)
        else:
            super().keyPressEvent(event)

    def respond(self, clicked: Optional[int]) -> None:
        if self.index < 0 or self.answered or self.index >= len(self.trials):
            return
        self.answered = True
        trial = self.trials[self.index]
        ms = round((time.monotonic() - self.t0) * 1000.0)
        target = trial["target"]
        hit = (clicked is None and target is None) or (
            clicked is not None and target is not None
            and abs(clicked - target) <= 1)
        row = {"ts": round(time.time(), 3), "trial": self.index,
               "variant": trial["variant"], "cls": trial["cls"],
               "target": target, "clicked": clicked, "hit": hit, "ms": ms,
               "n_tokens": len(trial["text"].split()),
               "detail": trial["detail"],
               "paragraph_sha1":
                   hashlib.sha1(trial["paragraph"].encode()).hexdigest()[:12]}
        with self.out_path.open("a") as f:
            f.write(json.dumps(row) + "\n")
        verdict = "HIT" if hit else "MISS"
        what = trial["detail"] or "clean"
        self.status.setText("%s — %s · %d ms" % (verdict, what, ms))
        QTimer.singleShot(700, self.next_trial)


def summarize(paths: list) -> None:
    """Catch rate + latency per dimension marginal, per variant cell, per
    error class, and per error POSITION (early/middle/late thirds — early
    errors get caught faster, addendum 6b5d48c9). Latency prints the group
    median plus a hits-only median, since miss and clean latencies measure
    giving-up and proving-absence rather than catching."""
    rows = []
    for p in paths:
        rows += [json.loads(ln) for ln in Path(p).read_text().splitlines()
                 if ln.strip()]
    if not rows:
        print("no rows")
        return

    def report(subset, keyfn, label):
        groups = {}
        for r in subset:
            groups.setdefault(str(keyfn(r)), []).append(r)
        print("\n== %s ==" % label)
        for key in sorted(groups):
            g = groups[key]
            hits = [r for r in g if r["hit"]]
            ms = statistics.median(r["ms"] for r in g)
            note = ("" if not hits else
                    " · hits %d ms" % statistics.median(r["ms"] for r in hits))
            print("  %s: %d/%d caught (%.0f%%) · median %d ms%s"
                  % (key, len(hits), len(g), 100.0 * len(hits) / len(g),
                     ms, note))

    report(rows, lambda r: r["variant"]["scheme"], "scheme")
    report(rows, lambda r: r["variant"]["font-body-size"], "body size")
    report(rows, lambda r: r["variant"]["font-body-line-height"], "line-height")
    if any("font-body-family" in r["variant"] for r in rows):
        report(rows, lambda r: r["variant"].get("font-body-family") or "(system)",
               "family")
    if any("theme" in r["variant"] for r in rows):
        report(rows, lambda r: r["variant"].get("theme", "(default)"), "theme")

    def cell(r):
        v = r["variant"]
        key = [v["scheme"], v["font-body-size"], v["font-body-line-height"]]
        if "font-body-family" in v:
            key.append(v["font-body-family"] or "(system)")
        if "theme" in v:
            key.append(v["theme"])
        return tuple(key)

    report(rows, cell, "variant")
    report(rows, lambda r: r["cls"] or "clean", "error class")
    placed = [r for r in rows
              if r.get("target") is not None and r.get("n_tokens")]
    if placed:
        thirds = ("1-early", "2-middle", "3-late")
        report(placed,
               lambda r: thirds[min(2, 3 * r["target"] // r["n_tokens"])],
               "error position")
    print("\ntotal rows: %d" % len(rows))


def main(argv: Optional[list] = None) -> int:
    """CLI: run trials over a markdown file, or summarize result JSONLs."""
    parser = argparse.ArgumentParser(prog="python -m cjm_substrate_qt_kit.testbed")
    parser.add_argument("source", nargs="?",
                        help="markdown file to read from (default: the "
                             "bundled clean-prose corpus)")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--trials", type=int, default=36)
    parser.add_argument("--out", default="", help="results JSONL (appended)")
    parser.add_argument("--summarize", nargs="+", metavar="JSONL",
                        help="skip the UI; report over these result files")
    parser.add_argument("--schemes", default="",
                        help="sweep: comma-separated from light,dark")
    parser.add_argument("--sizes", default="",
                        help="sweep: comma-separated body point sizes")
    parser.add_argument("--line-heights", default="",
                        help="sweep: comma-separated line-height ratios")
    parser.add_argument("--families", default="",
                        help="sweep: comma-separated font families; the "
                             "literal word system means the system default")
    parser.add_argument("--themes", default="",
                        help="sweep: comma-separated theme JSON files "
                             "(palette candidates race like typography)")
    args = parser.parse_args(argv)
    if args.summarize:
        summarize(args.summarize)
        return 0
    if args.source:
        paragraphs = load_paragraphs(args.source)
        if not paragraphs:
            parser.error("no usable prose paragraphs in %s" % args.source)
    else:
        paragraphs = list(PARAGRAPHS)
    rng = random.Random(args.seed)

    def parse_list(raw: str) -> Optional[list]:
        items = [x.strip() for x in raw.split(",") if x.strip()]
        return items or None

    variants = None
    if any((args.schemes, args.sizes, args.line_heights, args.families,
            args.themes)):
        families = parse_list(args.families)
        if families:
            families = ["" if f.lower() == "system" else f for f in families]
        themes = None
        if args.themes:
            themes = [(Path(p).stem, load_theme(p))
                      for p in parse_list(args.themes)]
        variants = build_variants(parse_list(args.schemes),
                                  parse_list(args.sizes),
                                  parse_list(args.line_heights),
                                  families, themes)
    trials = build_trials(paragraphs, rng, args.trials, variants=variants)
    out = args.out or time.strftime("readability-trials-%Y%m%d-%H%M%S.jsonl")
    app = QApplication.instance() or QApplication([])
    window = TrialWindow(trials, out)
    window.show()
    app.exec()
    if Path(out).exists():
        summarize([out])
        print("\nresults: %s" % out)
    else:
        print("no responses recorded")
    return 0


def build_variants(schemes=None, sizes=None, line_heights=None,
                   families=None, themes=None) -> list:
    """Cross the sweep dimensions into variant dicts. Defaults reproduce the
    first grid (scheme x size x line-height). families adds font-body-family
    values ("" = system default); themes adds (name, overrides) pairs read
    from theme JSON files — their tokens merge into the variant and the name
    lands under the "theme" label key, so palette candidates race exactly
    like typography values."""
    dims = [("scheme", list(schemes or SCHEMES)),
            ("font-body-size", [float(s) for s in (sizes or SIZES)]),
            ("font-body-line-height",
             [float(h) for h in (line_heights or LINE_HEIGHTS)])]
    if families:
        dims.append(("font-body-family", list(families)))
    variants = [{}]
    for key, values in dims:
        variants = [dict(v, **{key: val}) for v in variants for val in values]
    if themes:
        variants = [dict(v, **overrides, theme=name)
                    for v in variants for name, overrides in themes]
    return variants


if __name__ == "__main__":
    raise SystemExit(main())
