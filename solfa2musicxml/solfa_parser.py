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
    STACCATO_PREFIX,
    NOTE_MELISMA_PREFIX, LYRICS_HYPHEN, LYRICS_JOIN,
    VOICE_BASE_LABELS, DEFAULT_VOICE_ORDER, ALL_PART_LABELS,
    MODULATION_SEPARATOR, FERMATA, NAVIGATION_MARKERS,
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

    # --- parenthesized prefixes: dynamics, fermata, navigation ---
    # Can have multiple: (^)(F)(p)d = fermata + Fine + piano on d
    dyn = None
    nav = None
    has_fermata = False
    while s:
        dm = _DYNAMIC_PREFIX_RE.match(s)
        if not dm:
            break
        value = dm.group(1)
        s = s[dm.end():]
        if value == FERMATA:
            has_fermata = True
        elif value in NAVIGATION_MARKERS:
            nav = value
        else:
            dyn = value  # last non-fermata, non-nav = dynamic

    if not s and (dyn or has_fermata or nav):
        return NoteEvent(is_rest=True, raw=" ", dynamic=dyn, fermata=has_fermata, navigation=nav), s

    # --- chord: <d.m.s> ---
    if s and s[0] == CHORD_OPEN:
        close_idx = s.find(CHORD_CLOSE)
        if close_idx > 0:
            chord_str = s[1:close_idx]
            s = s[close_idx + 1:]
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
                first = chord_notes[0]
                return NoteEvent(
                    solfa=first.solfa, semitone=first.semitone,
                    octave_shift=first.octave_shift,
                    is_chromatic_sharp=first.is_chromatic_sharp,
                    is_chromatic_flat=first.is_chromatic_flat,
                    raw=f"<{chord_str}>",
                    dynamic=dyn, fermata=has_fermata, navigation=nav,
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
        return NoteEvent(is_hold=True, raw="-", dynamic=dyn, fermata=has_fermata, navigation=nav), s[1:]

    # --- rest (* or **) ---
    if s.startswith(REST_DOUBLE_STAR):
        return NoteEvent(is_rest=True, raw="**", dynamic=dyn, fermata=has_fermata, navigation=nav), s[2:]
    if s.startswith(REST_STAR):
        return NoteEvent(is_rest=True, raw="*", dynamic=dyn, fermata=has_fermata, navigation=nav), s[1:]

    # --- solfa note (longest match) ---
    matched_solfa = None
    for tok in SOLFA_TOKENS_SORTED:
        if s.startswith(tok):
            matched_solfa = tok
            break
    if matched_solfa is None:
        if dyn or has_fermata or nav:
            return NoteEvent(is_rest=True, raw=" ", dynamic=dyn, fermata=has_fermata, navigation=nav), s
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
        dynamic=dyn, fermata=has_fermata, navigation=nav,
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
    has_multiple_groups = len(groups) > 1

    for group in groups:
        g = _restore_chord_dots(group.strip())
        if not g:
            # Empty group: if part of a sub-beat split (e.g. ".s" → ["","s"]),
            # produce a rest so it takes its share of the beat duration.
            if has_multiple_groups:
                events.append(NoteEvent(is_rest=True, raw=" "))
            continue

        # Leading comma = staccato marker (not octave down)
        is_staccato = False
        if g.startswith(STACCATO_PREFIX):
            is_staccato = True
            g = g[1:]  # strip the leading comma

        while g:
            evt, g = _parse_single_token(g)
            if evt is None:
                g = g[1:] if g else ""
            else:
                if is_staccato:
                    evt.is_staccato = True
                    is_staccato = False  # only first event in group
                events.append(evt)

    if not events:
        return [NoteEvent(is_rest=True, raw=" ")]
    return events


# ──────────────────────────────────────────────────────────────────────
#  MEASURE / VOICE LINE PARSING
# ──────────────────────────────────────────────────────────────────────

# Build voice label regex from config
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


def _detect_modulation(beat_str: str) -> tuple[str | None, str]:
    """
    Check for a modulation marker like r/s, inside a beat.
    The right side token is both the modulation target AND the first note
    to play in the new key.

    Example: "r/s,.t," → modulation "r/s,", remaining "s,.t,"
             (s, is played as first note in new key, then t,)
             "d/s:s:s" → modulation "d/s", remaining "s"
    """
    if MODULATION_SEPARATOR not in beat_str:
        return None, beat_str

    slash_idx = beat_str.index(MODULATION_SEPARATOR)
    left_str = beat_str[:slash_idx].strip()
    right_str = beat_str[slash_idx + 1:]

    # Validate left side: strip octave modifiers (' ,) then check for solfa token
    left_bare = left_str.rstrip(OCTAVE_UP_CHAR + OCTAVE_DOWN_CHAR)
    left_valid = any(left_bare == t for t in SOLFA_TOKENS_SORTED)
    if not left_valid:
        return None, beat_str

    # Parse the right side: consume solfa token + octave modifiers
    right_stripped = right_str.lstrip()
    matched_right = None
    for tok in SOLFA_TOKENS_SORTED:
        if right_stripped.startswith(tok):
            matched_right = tok
            break
    if matched_right is None:
        return None, beat_str

    # Consume octave modifiers (they're part of the modulation target,
    # e.g. s, means "sol octave down" — pitch class is the same but
    # we consume to avoid leaving a dangling comma)
    pos = len(matched_right)
    while pos < len(right_stripped) and right_stripped[pos] in (OCTAVE_UP_CHAR, OCTAVE_DOWN_CHAR):
        pos += 1

    right_token = right_stripped[:pos]
    remaining = right_stripped  # right token is also the first note to play

    mod_str = f"{left_str}/{right_token}"
    return mod_str, remaining


def parse_voice_line(line: str) -> tuple[str | None, list]:
    """Parse one note line into (voice_label, list_of_measures)."""
    label, content = _extract_voice_label(line)
    raw_measures = _split_measures(content)

    measures = []
    for mstr in raw_measures:
        mstr = mstr.strip()
        if not mstr:
            continue

        beats_raw = mstr.split(BEAT_SEPARATOR)
        beats = []
        modulations = []
        for b in beats_raw:
            mod, b_clean = _detect_modulation(b)
            if mod:
                modulations.append(mod)
            # Parse remaining content as notes (even after a modulation)
            if b_clean.strip():
                tokens = parse_beat_tokens(b_clean)
                beats.append(tokens)
            else:
                # Empty beat (or modulation consumed all content) = rest
                beats.append(parse_beat_tokens(""))

        # Extract navigation markers to measure level.
        # Navigation is always applied to the measure (barline + text),
        # never creates extra events.
        # Correct usage: (DC)f  → nav is prefix on the note
        #                (DC)   → nav alone as a beat (beat is dropped)
        measure_nav = None
        cleaned_beats = []
        for beat_events in beats:
            # Check if this beat is just a nav-only rest: |(DC)|
            if (len(beat_events) == 1
                    and beat_events[0].is_rest
                    and beat_events[0].navigation
                    and not beat_events[0].dynamic
                    and not beat_events[0].fermata):
                measure_nav = beat_events[0].navigation
                # Drop this beat entirely — it's not real music
                continue
            # Extract nav from note events: |(DC)f|
            for evt in beat_events:
                if evt.navigation:
                    measure_nav = evt.navigation
                    evt.navigation = None
            cleaned_beats.append(beat_events)

        measures.append({
            "beats": cleaned_beats,
            "modulations": modulations,
            "navigation": measure_nav,
        })

    return label, measures


# ──────────────────────────────────────────────────────────────────────
#  LYRICS PARSING
# ──────────────────────────────────────────────────────────────────────

def _extract_voice_labels(s: str) -> list[str]:
    """Greedily extract concatenated voice labels from a string.
    E.g. 'SATB' → ['S','A','T','B'], 'S1S2T' → ['S1','S2','T']"""
    labels = []
    pos = 0
    while pos < len(s):
        matched = None
        for lbl in ALL_PART_LABELS:  # sorted longest first
            if s[pos:].startswith(lbl):
                matched = lbl
                break
        if matched:
            labels.append(matched)
            pos += len(matched)
        else:
            break  # not a voice label, stop
    # Only valid if we consumed the entire string
    if pos == len(s) and labels:
        return labels
    return []


def parse_lyrics_line(line: str) -> tuple[list[str] | None, str | int, list]:
    """
    Parse a lyrics line into (voices, verse_id, syllables).

    Returns:
        voices: list of voice labels, or None for all voices
        verse_id: int (verse number) or "R" (refrain)
        syllables: list of (text, syllabic) tuples

    Prefix format:
        (none)          → verse 1, all voices
        R               → refrain, all voices
        SATB            → verse 1, those voices
        SA              → verse 1, S and A
        S1S2T           → verse 1, S1 S2 T
        1:SATB          → verse 1, those voices
        1:B             → verse 1, B only
        R:SA            → refrain, S and A
        R:TB            → refrain, T and B
    """
    stripped = line.strip()
    voices = None
    verse_id: str | int = 1

    # Try to match prefix before the first space
    space_idx = stripped.find(" ")
    if space_idx > 0:
        prefix = stripped[:space_idx]
        rest = stripped[space_idx + 1:].strip()

        # Check for verse:voices format (e.g. "1:SATB", "R:SA")
        if ":" in prefix:
            vpart, vlist = prefix.split(":", 1)
            if vpart == "R":
                verse_id = "R"
            elif vpart.isdigit():
                verse_id = int(vpart)
            else:
                # Not a valid prefix, treat entire line as lyrics
                rest = stripped
                vlist = ""

            if vlist:
                labels = _extract_voice_labels(vlist)
                if labels:
                    voices = labels
                    stripped = rest
                else:
                    stripped = rest  # verse parsed, no valid voices
            else:
                stripped = rest

        # Check for R alone (refrain, all voices)
        elif prefix == "R":
            verse_id = "R"
            stripped = rest

        # Check for voice labels only (e.g. "SATB", "SA", "S1S2T")
        else:
            labels = _extract_voice_labels(prefix)
            if labels:
                voices = labels
                stripped = rest
            # else: not a prefix, treat entire line as lyrics (stripped unchanged)

    # Split into syllables with syllabic type for MusicXML hyphenation
    syllables = []
    words = stripped.split()
    for word in words:
        parts = word.split(LYRICS_HYPHEN)
        if len(parts) == 1:
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

    return voices, verse_id, syllables


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

            voices, verse_id, syllables = parse_lyrics_line(stripped)
            if voices is None:
                # No voice prefix → all voices
                targets = list(voice_data.keys())
            else:
                targets = voices

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
