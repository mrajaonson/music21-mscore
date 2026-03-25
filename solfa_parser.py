"""Parsing logic for tonic solfa .txt files."""

import re
from pathlib import Path

from models import NoteEvent

from config import (
    DEFAULTS, HEADER_STRING_PROPS, HEADER_INT_PROPS, HEADER_SPECIAL_PROPS,
    ALL_SOLFA_NOTES, SOLFA_TOKENS_SORTED, SOLFA_TO_SEMITONE,
    CHROMATIC_SHARP, CHROMATIC_FLAT,
    OCTAVE_UP_CHAR, OCTAVE_DOWN_CHAR,
    BEAT_SEPARATOR, SUBBEAT_SEPARATOR, HOLD, REST_STAR, REST_DOUBLE_STAR,
    NOTE_MELISMA_PREFIX, LYRICS_HYPHEN, LYRICS_JOIN,
    VOICE_BASE_LABELS, DEFAULT_VOICE_ORDER, ALL_PART_LABELS,
    MODULATION_SEPARATOR, REPEAT_START, REPEAT_END, VOLTA_1_START,
    FINE, DA_CAPO_SEGNO, FERMATA,
    CHORD_OPEN, CHORD_CLOSE,
)


# ──────────────────────────────────────────────────────────────────────
#  HEADER PARSING
# ──────────────────────────────────────────────────────────────────────

HEADER_KEYWORDS = HEADER_STRING_PROPS | HEADER_INT_PROPS | HEADER_SPECIAL_PROPS


def parse_header(lines: list[str]) -> tuple[dict, list[str]]:
    """Extract property lines from the top of the file."""
    props = dict(DEFAULTS)
    remaining = []
    header_done = False

    for line in lines:
        stripped = line.strip()
        if not header_done and stripped:
            parts = stripped.split(None, 1)
            keyword = parts[0].upper()
            if keyword in HEADER_KEYWORDS:
                if len(parts) == 2:
                    value = parts[1].strip()
                    if keyword in HEADER_INT_PROPS:
                        try:
                            props[keyword] = int(value)
                        except ValueError:
                            pass
                    elif keyword == "TIMESIG":
                        props[keyword] = value
                    else:
                        props[keyword] = value
                continue
            else:
                header_done = True
        if header_done or not stripped:
            if stripped:
                header_done = True
            remaining.append(line)
    return props, remaining


# ──────────────────────────────────────────────────────────────────────
#  NOTE TOKEN PARSING
# ──────────────────────────────────────────────────────────────────────

_DYNAMIC_PREFIX_RE = re.compile(r'^\(([^)]+)\)')


def _parse_single_token(s: str) -> tuple[NoteEvent | None, str]:
    """Parse one note token from the beginning of *s*."""
    if not s:
        return None, s

    # --- parenthesized prefixes: dynamics, hairpins, fermata ---
    # Can have multiple: (^)(p)d = fermata + piano on d
    dyn = None
    has_fermata = False
    while s:
        dm = _DYNAMIC_PREFIX_RE.match(s)
        if not dm:
            break
        value = dm.group(1)
        s = s[dm.end():]
        if value == FERMATA:
            has_fermata = True
        else:
            dyn = value  # last non-fermata dynamic wins

    if not s and (dyn or has_fermata):
        return NoteEvent(is_rest=True, raw=" ", dynamic=dyn, fermata=has_fermata), s

    # --- chord: <d.m.s> ---
    if s and s[0] == CHORD_OPEN:
        close_idx = s.find(CHORD_CLOSE)
        if close_idx > 0:
            chord_str = s[1:close_idx]
            s = s[close_idx + 1:]
            # Parse each note inside the chord (separated by .)
            chord_parts = chord_str.split(".")
            chord_notes = []
            for cp in chord_parts:
                cp = cp.strip()
                if not cp:
                    continue
                cn, _ = _parse_single_token(cp)
                if cn and not cn.is_rest and not cn.is_hold:
                    chord_notes.append(cn)
            if chord_notes:
                # Use first note as the "primary" for the NoteEvent
                first = chord_notes[0]
                return NoteEvent(
                    solfa=first.solfa, semitone=first.semitone,
                    octave_shift=first.octave_shift,
                    is_chromatic_sharp=first.is_chromatic_sharp,
                    is_chromatic_flat=first.is_chromatic_flat,
                    raw=f"<{chord_str}>",
                    dynamic=dyn, fermata=has_fermata,
                    chord_notes=chord_notes,
                ), s

    # --- melisma prefix ---
    is_melisma = False
    if s and s.startswith(NOTE_MELISMA_PREFIX):
        is_melisma = True
        s = s[1:]
        if not s:
            return None, s

    if not s:
        return None, s

    # --- hold ---
    if s[0] == HOLD:
        return NoteEvent(is_hold=True, raw="-", dynamic=dyn, fermata=has_fermata), s[1:]

    # --- rest (* or **) ---
    if s.startswith(REST_DOUBLE_STAR):
        return NoteEvent(is_rest=True, raw="**", dynamic=dyn, fermata=has_fermata), s[2:]
    if s.startswith(REST_STAR):
        return NoteEvent(is_rest=True, raw="*", dynamic=dyn, fermata=has_fermata), s[1:]

    # --- solfa note (longest match) ---
    matched_solfa = None
    for tok in SOLFA_TOKENS_SORTED:
        if s.startswith(tok):
            matched_solfa = tok
            break
    if matched_solfa is None:
        if dyn or has_fermata:
            return NoteEvent(is_rest=True, raw=" ", dynamic=dyn, fermata=has_fermata), s
        return None, s

    s = s[len(matched_solfa):]
    semitone = ALL_SOLFA_NOTES[matched_solfa]
    is_sharp = matched_solfa in CHROMATIC_SHARP
    is_flat = matched_solfa in CHROMATIC_FLAT

    # --- octave modifiers ---
    octave_shift = 0
    while s and s[0] == OCTAVE_UP_CHAR:
        octave_shift += 1
        s = s[1:]
    while s and s[0] == OCTAVE_DOWN_CHAR:
        octave_shift -= 1
        s = s[1:]

    evt = NoteEvent(
        solfa=matched_solfa, semitone=semitone, octave_shift=octave_shift,
        is_melisma=is_melisma,
        is_chromatic_sharp=is_sharp, is_chromatic_flat=is_flat,
        raw=matched_solfa + OCTAVE_UP_CHAR * max(0, octave_shift)
                         + OCTAVE_DOWN_CHAR * max(0, -octave_shift),
        dynamic=dyn, fermata=has_fermata,
    )
    return evt, s


_CHORD_DOT_PLACEHOLDER = "\x00"  # temp replacement for dots inside < >


def _protect_chord_dots(s: str) -> str:
    """Replace dots inside <> with placeholder so they aren't split as sub-beats."""
    result = []
    inside = False
    for ch in s:
        if ch == CHORD_OPEN:
            inside = True
        elif ch == CHORD_CLOSE:
            inside = False
        if ch == SUBBEAT_SEPARATOR and inside:
            result.append(_CHORD_DOT_PLACEHOLDER)
        else:
            result.append(ch)
    return "".join(result)


def _restore_chord_dots(s: str) -> str:
    """Restore placeholder back to dots."""
    return s.replace(_CHORD_DOT_PLACEHOLDER, SUBBEAT_SEPARATOR)


def parse_beat_tokens(beat_str: str) -> list[NoteEvent]:
    """Parse a beat string (between : separators) into NoteEvents."""
    beat_str = beat_str.strip()

    if not beat_str:
        return [NoteEvent(is_rest=True, raw=" ")]

    # Protect dots inside chord brackets <d.m.s> from being split
    beat_str = _protect_chord_dots(beat_str)

    groups = beat_str.split(SUBBEAT_SEPARATOR)
    events: list[NoteEvent] = []

    for group in groups:
        g = _restore_chord_dots(group.strip())
        if not g:
            continue
        while g:
            evt, g = _parse_single_token(g)
            if evt is None:
                g = g[1:] if g else ""
            else:
                events.append(evt)

    if not events:
        return [NoteEvent(is_rest=True, raw=" ")]
    return events


# ──────────────────────────────────────────────────────────────────────
#  MEASURE / VOICE LINE PARSING
# ──────────────────────────────────────────────────────────────────────

_STRUCT_CHARS = {REPEAT_START, REPEAT_END, VOLTA_1_START, FINE, DA_CAPO_SEGNO}

# Build voice label regex from config: matches PR, PL, OR, OL, OP, S, A, T, B, S1, S2, etc.
_label_alts = "|".join(re.escape(lbl) for lbl in ALL_PART_LABELS)
_VOICE_LABEL_RE = re.compile(rf'^({_label_alts}|[SATB]\d+)(?=\s|\t|\|)')


def _extract_voice_label(line: str) -> tuple[str | None, str]:
    """Strip a leading voice label from a note line."""
    stripped = line.strip()
    m = _VOICE_LABEL_RE.match(stripped)
    if m:
        return m.group(1), stripped[m.end():].strip()
    return None, stripped


def _split_measures(raw: str) -> list[str]:
    """Split a voice's bar content into measure strings."""
    raw = raw.strip().strip("|")
    raw = raw.replace("||", "|")
    return [m for m in raw.split("|")]


def _detect_structural_markers(measure_str: str) -> tuple[list[str], str]:
    """Pull out structural markers from a measure string."""
    markers = []
    cleaned = []
    for ch in measure_str:
        if ch in _STRUCT_CHARS:
            markers.append(ch)
        else:
            cleaned.append(ch)
    return markers, "".join(cleaned)


def _detect_modulation(beat_str: str) -> tuple[str | None, str]:
    """Check for a modulation marker like s/d inside a beat."""
    if MODULATION_SEPARATOR in beat_str:
        parts = beat_str.split(MODULATION_SEPARATOR, 1)
        left = parts[0].strip()
        right = parts[1].strip()
        left_valid = any(left.startswith(t) for t in SOLFA_TOKENS_SORTED)
        right_valid = any(right.startswith(t) for t in SOLFA_TOKENS_SORTED)
        if left_valid and right_valid:
            return f"{left}/{right}", ""
    return None, beat_str


def parse_voice_line(line: str) -> tuple[str | None, list]:
    """Parse one note line into (voice_label, list_of_measures)."""
    label, content = _extract_voice_label(line)
    raw_measures = _split_measures(content)

    measures = []
    for mstr in raw_measures:
        mstr = mstr.strip()
        if not mstr:
            continue
        markers, mstr_clean = _detect_structural_markers(mstr)

        beats_raw = mstr_clean.split(BEAT_SEPARATOR)
        beats = []
        modulations = []
        for b in beats_raw:
            mod, b_clean = _detect_modulation(b)
            if mod:
                modulations.append(mod)
            else:
                tokens = parse_beat_tokens(b_clean)
                beats.append(tokens)

        measures.append({
            "markers": markers,
            "beats": beats,
            "modulations": modulations,
        })

    return label, measures


# ──────────────────────────────────────────────────────────────────────
#  LYRICS PARSING
# ──────────────────────────────────────────────────────────────────────

# Build lyrics voice pattern from all known labels
_voice_alt = "|".join(re.escape(lbl) for lbl in ALL_PART_LABELS)
_LYRICS_PREFIX_RE = re.compile(
    rf'^(?:'
    rf'(?P<refrain>R)(?P<rvoice>{_voice_alt})?'   # R or RS1 etc.
    rf'|(?P<vnum>\d+)(?P<voice>{_voice_alt})?'     # 1 or 1S1 etc.
    rf'|(?P<bare_voice>{_voice_alt})'               # S or A or PR etc. (no verse)
    rf')\s+'
)


def parse_lyrics_line(line: str) -> tuple[str | None, str | int, list[str]]:
    """Parse a lyrics line into (voice, verse_id, syllables)."""
    stripped = line.strip()
    voice = None
    verse_id: str | int = 1

    m = _LYRICS_PREFIX_RE.match(stripped)
    if m:
        if m.group("refrain"):
            verse_id = "R"
            if m.group("rvoice"):
                voice = m.group("rvoice")
        elif m.group("vnum"):
            verse_id = int(m.group("vnum"))
            if m.group("voice"):
                voice = m.group("voice")
        elif m.group("bare_voice"):
            voice = m.group("bare_voice")
            verse_id = 1
        stripped = stripped[m.end():]

    # Split into syllables with syllabic type for MusicXML hyphenation.
    # Each syllable is a tuple: (text, syllabic)
    #   syllabic = "single" (whole word), "begin", "middle", "end"
    # Example: "A-ma-zing grace" → [("A","begin"), ("ma","middle"), ("zing","end"), ("grace","single")]
    syllables = []
    words = stripped.split()
    for word in words:
        parts = word.split(LYRICS_HYPHEN)
        if len(parts) == 1:
            # Whole word, no hyphen
            part = parts[0].replace(LYRICS_JOIN, " ")
            syllables.append((part, "single"))
        else:
            for i, part in enumerate(parts):
                part = part.replace(LYRICS_JOIN, " ")
                if i == 0:
                    syllables.append((part, "begin"))
                elif i == len(parts) - 1:
                    syllables.append((part, "end"))
                else:
                    syllables.append((part, "middle"))

    return voice, verse_id, syllables


# ──────────────────────────────────────────────────────────────────────
#  FILE PARSING  (top-level)
# ──────────────────────────────────────────────────────────────────────

def _is_note_line(line: str) -> bool:
    """Heuristic: a note line contains barlines |."""
    return "|" in line


def parse_file(filepath: str) -> dict:
    """
    Parse a tonic solfa .txt file.
    Returns dict with keys: properties, voices, lyrics.
    """
    text = Path(filepath).read_text(encoding="utf-8")
    lines = text.splitlines()

    props, remaining = parse_header(lines)

    voice_data: dict[str, list] = {}
    lyrics_data: dict[str, dict] = {}

    default_voice_order = list(DEFAULT_VOICE_ORDER)
    voice_index = 0
    prev_was_note_line = False
    last_voice_label = "S"

    for line in remaining:
        stripped = line.strip()

        if not stripped:
            if prev_was_note_line:
                prev_was_note_line = False
            continue

        if _is_note_line(stripped):
            if not prev_was_note_line:
                voice_index = 0
            prev_was_note_line = True

            label, measures = parse_voice_line(stripped)
            if label is None:
                if voice_index < len(default_voice_order):
                    label = default_voice_order[voice_index]
                else:
                    label = f"V{voice_index + 1}"
                voice_index += 1
            else:
                voice_index += 1

            last_voice_label = label

            if label not in voice_data:
                voice_data[label] = []
            voice_data[label].extend(measures)

        else:
            prev_was_note_line = False

            voice, verse_id, syllables = parse_lyrics_line(stripped)
            if voice is None:
                # No voice prefix → attach to ALL voices.
                # Each voice's cursor skips rests independently,
                # so lyrics appear under whichever voice has notes.
                targets = list(voice_data.keys())
            else:
                targets = [voice]

            for target in targets:
                if target not in lyrics_data:
                    lyrics_data[target] = {}
                if verse_id not in lyrics_data[target]:
                    lyrics_data[target][verse_id] = []
                lyrics_data[target][verse_id].extend(syllables)

    return {
        "properties": props,
        "voices": voice_data,
        "lyrics": lyrics_data,
    }
