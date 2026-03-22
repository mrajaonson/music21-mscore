#!/usr/bin/env python3
"""
Tonic Solfa .txt  →  MusicXML (.xml) converter
Requires: pip install music21
Output is compatible with MuseScore 4.
"""

import sys
import re
from pathlib import Path

from music21 import (
    stream, note, pitch, key, meter, tempo, clef, bar,
    duration, metadata, tie, repeat, expressions, dynamics,
)

from config import (
    DEFAULTS, HEADER_STRING_PROPS, HEADER_INT_PROPS, HEADER_SPECIAL_PROPS,
    SOLFA_TO_SEMITONE, CHROMATIC_SHARP, CHROMATIC_FLAT, ALL_SOLFA_NOTES,
    SOLFA_TOKENS_SORTED, OCTAVE_UP_CHAR, OCTAVE_DOWN_CHAR, VALID_KEYS,
    BARLINE, BEAT_SEPARATOR, SUBBEAT_SEPARATOR, HOLD, REST_STAR,
    REST_DOUBLE_STAR, NOTE_MELISMA_PREFIX, LYRICS_HYPHEN,
    VOICE_BASE_LABELS, DEFAULT_VOICE_ORDER, VOICE_CONFIG,
    MODULATION_SEPARATOR, REPEAT_START, REPEAT_END, VOLTA_1_START,
    FINE, DA_CAPO_SEGNO,
    VALID_DYNAMICS, HAIRPIN_CRESC, HAIRPIN_DIM, TEXT_EXPRESSIONS,
)


# ══════════════════════════════════════════════════════════════════════
#  DATA CLASSES
# ══════════════════════════════════════════════════════════════════════

class NoteEvent:
    """A single parsed note / rest / hold event."""
    __slots__ = ("solfa", "semitone", "octave_shift", "is_rest", "is_hold",
                 "is_melisma", "is_chromatic_sharp", "is_chromatic_flat",
                 "raw", "dynamic")

    def __init__(self, *, solfa=None, semitone=0, octave_shift=0,
                 is_rest=False, is_hold=False, is_melisma=False,
                 is_chromatic_sharp=False, is_chromatic_flat=False, raw="",
                 dynamic=None):
        self.solfa = solfa
        self.semitone = semitone
        self.octave_shift = octave_shift
        self.is_rest = is_rest
        self.is_hold = is_hold
        self.is_melisma = is_melisma
        self.is_chromatic_sharp = is_chromatic_sharp
        self.is_chromatic_flat = is_chromatic_flat
        self.raw = raw
        self.dynamic = dynamic  # e.g. "p", "f", "ff", "<", ">", "cresc"

    def __repr__(self):
        if self.is_rest:
            return "Rest"
        if self.is_hold:
            return "Hold"
        return f"Note({self.solfa}, st={self.semitone}, oct={self.octave_shift})"


class TimedEvent:
    """A NoteEvent with a computed quarter-length duration."""
    __slots__ = ("event", "quarter_length")

    def __init__(self, event: NoteEvent, quarter_length: float):
        self.event = event
        self.quarter_length = quarter_length

    def __repr__(self):
        return f"{self.event}:{self.quarter_length}ql"


# ══════════════════════════════════════════════════════════════════════
#  HEADER PARSING
# ══════════════════════════════════════════════════════════════════════

HEADER_KEYWORDS = (
    HEADER_STRING_PROPS | HEADER_INT_PROPS | HEADER_SPECIAL_PROPS
)

def parse_header(lines: list[str]) -> tuple[dict, list[str]]:
    """
    Extract property lines from the top of the file.
    Returns (properties_dict, remaining_lines).
    """
    props = dict(DEFAULTS)
    remaining = []
    header_done = False

    for line in lines:
        stripped = line.strip()
        if not header_done and stripped:
            parts = stripped.split(None, 1)
            keyword = parts[0].upper()
            if keyword in HEADER_KEYWORDS:
                # Keyword recognised — if value is present, parse it;
                # if value is missing (e.g. bare "TEMPO"), keep the default.
                if len(parts) == 2:
                    value = parts[1].strip()
                    if keyword in HEADER_INT_PROPS:
                        try:
                            props[keyword] = int(value)
                        except ValueError:
                            pass  # keep default
                    elif keyword == "TIMESIG":
                        props[keyword] = value
                    else:
                        props[keyword] = value
                # else: no value after keyword → keep default, continue parsing
                continue
            else:
                header_done = True
        if header_done or not stripped:
            if stripped:
                header_done = True
            remaining.append(line)
    return props, remaining


# ══════════════════════════════════════════════════════════════════════
#  NOTE TOKEN PARSING
# ══════════════════════════════════════════════════════════════════════

# Regex for inline dynamics: (p), (ff), (<), (>), (cresc), etc.
_DYNAMIC_PREFIX_RE = re.compile(r'^\(([^)]+)\)')

def _parse_single_token(s: str) -> tuple[NoteEvent | None, str]:
    """
    Parse one note token from the beginning of *s*.
    Returns (NoteEvent, remaining_string) or (None, s) on failure.
    """
    if not s:
        return None, s

    # --- dynamic prefix (p), (f), (<), (cresc), etc. ---
    dyn = None
    dm = _DYNAMIC_PREFIX_RE.match(s)
    if dm:
        dyn = dm.group(1)
        s = s[dm.end():]
        if not s:
            # Dynamic with no note after it — return as a rest with dynamic
            return NoteEvent(is_rest=True, raw=" ", dynamic=dyn), s

    # --- melisma prefix ---
    is_melisma = False
    if s.startswith(NOTE_MELISMA_PREFIX):
        is_melisma = True
        s = s[1:]
        if not s:
            return None, s

    # --- hold ---
    if s[0] == HOLD:
        return NoteEvent(is_hold=True, raw="-", dynamic=dyn), s[1:]

    # --- rest (* or **) ---
    if s.startswith(REST_DOUBLE_STAR):
        return NoteEvent(is_rest=True, raw="**", dynamic=dyn), s[2:]
    if s.startswith(REST_STAR):
        return NoteEvent(is_rest=True, raw="*", dynamic=dyn), s[1:]

    # --- solfa note (longest match) ---
    matched_solfa = None
    for tok in SOLFA_TOKENS_SORTED:
        if s.startswith(tok):
            matched_solfa = tok
            break
    if matched_solfa is None:
        if dyn:
            # Had a dynamic but no recognisable note — attach to next event
            return NoteEvent(is_rest=True, raw=" ", dynamic=dyn), s
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
        dynamic=dyn,
    )
    return evt, s


def parse_beat_tokens(beat_str: str) -> list[NoteEvent]:
    """
    Parse a beat string (content between : separators) into NoteEvents.
    Dots separate sub-beat groups; within a group, multiple notes can be
    concatenated. All tokens are flattened for duration assignment.

    Empty beat (blank) = rest (silence). Only - is a hold.
    * and ** are explicit rests (same result, just more visible in notation).
    """
    beat_str = beat_str.strip()

    # A fully empty beat = rest (silence)
    if not beat_str:
        return [NoteEvent(is_rest=True, raw=" ")]

    groups = beat_str.split(SUBBEAT_SEPARATOR)
    events: list[NoteEvent] = []

    for group in groups:
        g = group.strip()
        if not g:
            continue
        while g:
            evt, g = _parse_single_token(g)
            if evt is None:
                # skip unrecognised character
                g = g[1:] if g else ""
            else:
                events.append(evt)

    if not events:
        return [NoteEvent(is_rest=True, raw=" ")]
    return events


# ══════════════════════════════════════════════════════════════════════
#  MEASURE / VOICE LINE PARSING
# ══════════════════════════════════════════════════════════════════════

# Structural markers that can appear between barlines
_STRUCT_CHARS = {REPEAT_START, REPEAT_END, VOLTA_1_START, FINE, DA_CAPO_SEGNO}

# Regex to match voice labels: S, A, T, B, S1, S2, T1, T2, etc.
_VOICE_LABEL_RE = re.compile(
    r'^([SATB]\d*)(?=\s|\t|\|)'
)

def _extract_voice_label(line: str) -> tuple[str | None, str]:
    """
    Strip a leading voice label from a note line.
    Handles plain labels (S, A, T, B) and numbered labels (S1, S2, T1, T2).
    Returns (label_or_None, remaining_content).
    """
    stripped = line.strip()
    m = _VOICE_LABEL_RE.match(stripped)
    if m:
        label = m.group(1)
        rest = stripped[m.end():].strip()
        return label, rest
    return None, stripped


def _split_measures(raw: str) -> list[str]:
    """
    Split a voice's bar content into measure strings.
    Handles || (double barline) by treating it as a final measure boundary.
    """
    # Replace || with a sentinel, then split on |
    raw = raw.strip().strip("|")
    raw = raw.replace("||", "|")
    measures = [m for m in raw.split("|")]
    return measures


def _detect_structural_markers(measure_str: str) -> tuple[list[str], str]:
    """
    Pull out structural markers ([ ] { F D) from a measure string.
    Returns (list_of_markers, cleaned_measure_str).
    """
    markers = []
    cleaned = []
    for ch in measure_str:
        if ch in _STRUCT_CHARS:
            markers.append(ch)
        else:
            cleaned.append(ch)
    return markers, "".join(cleaned)


def _detect_modulation(beat_str: str) -> tuple[str | None, str]:
    """
    Check for a modulation marker like  s/d  inside a beat.
    Returns (modulation_string_or_None, cleaned_beat_str).
    """
    if MODULATION_SEPARATOR in beat_str:
        parts = beat_str.split(MODULATION_SEPARATOR, 1)
        # Validate: both sides should be solfa tokens
        left = parts[0].strip()
        right = parts[1].strip()
        left_valid = any(left.startswith(t) for t in SOLFA_TOKENS_SORTED)
        right_valid = any(right.startswith(t) for t in SOLFA_TOKENS_SORTED)
        if left_valid and right_valid:
            return f"{left}/{right}", ""
    return None, beat_str


def parse_voice_line(line: str) -> tuple[str | None, list]:
    """
    Parse one note line.
    Returns (voice_label_or_None, list_of_measures).
    Each measure = {"markers": [...], "beats": [list_of_NoteEvent_lists]}.
    """
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


# ══════════════════════════════════════════════════════════════════════
#  LYRICS PARSING
# ══════════════════════════════════════════════════════════════════════

# Lyrics prefix format:  <verse><voice>
# Examples: 1  1S1  2S1  RS1  1A  R  2T2  etc.
# Verse part: a digit (1, 2, 3…) or R (refrain)
# Voice part: S, A, T, B optionally followed by a digit (S1, T2, etc.)
_LYRICS_PREFIX_RE = re.compile(
    r'^(?:(?P<refrain>R)(?P<rvoice>[SATB]\d*)?|(?P<vnum>\d+)(?P<voice>[SATB]\d*)?)\s+'
)

def parse_lyrics_line(line: str) -> tuple[str | None, str | int, list[str]]:
    """
    Parse a lyrics line.
    Returns (voice_label_or_None, verse_id, list_of_syllables).

    Prefix format is <verse><voice> where verse comes FIRST:
      1       → verse 1, no specific voice
      1S1     → verse 1, Soprano 1
      2S1     → verse 2, Soprano 1
      1A      → verse 1, Alto
      R       → refrain, no specific voice
      RS1     → refrain, Soprano 1
      RA      → refrain, Alto

    verse_id is an int (verse number) or "R" (refrain).
    """
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
        stripped = stripped[m.end():]

    # Split into syllables: spaces separate words, hyphens split within words
    syllables = []
    words = stripped.split()
    for word in words:
        parts = word.split(LYRICS_HYPHEN)
        for part in parts:
            syllables.append(part)

    return voice, verse_id, syllables


# ══════════════════════════════════════════════════════════════════════
#  FILE PARSING  (top-level)
# ══════════════════════════════════════════════════════════════════════

# Regex for block-level dynamics: a line that is just (p), (f), (Cresc), etc.
_BLOCK_DYNAMIC_RE = re.compile(r'^\(([^)]+)\)$')

def _is_note_line(line: str) -> bool:
    """Heuristic: a note line contains barlines |."""
    return "|" in line


def _is_block_dynamic(line: str) -> str | None:
    """Check if a line is a standalone block dynamic like (p), (Cresc). Returns the value or None."""
    m = _BLOCK_DYNAMIC_RE.match(line.strip())
    return m.group(1) if m else None


def parse_file(filepath: str) -> dict:
    """
    Parse a tonic solfa .txt file.
    Returns a dict with keys: properties, voices, lyrics.

    Note lines and lyrics lines can be interleaved:
      [4 note lines]  [lyrics]  [4 note lines]  [lyrics]  ...
    Each block of consecutive note lines cycles through the default
    voice order (S A T B), appending measures to existing voices.
    """
    text = Path(filepath).read_text(encoding="utf-8")
    lines = text.splitlines()

    props, remaining = parse_header(lines)

    voice_data: dict[str, list] = {}   # label -> list of measures
    lyrics_data: dict[str, dict] = {}  # label -> {verse_id: [syllables]}

    default_voice_order = list(DEFAULT_VOICE_ORDER)
    voice_index = 0
    prev_was_note_line = False
    last_voice_label = "S"
    pending_block_dynamic = None

    for line in remaining:
        stripped = line.strip()

        # Blank line → signals a block boundary, reset voice cycling
        if not stripped:
            if prev_was_note_line:
                prev_was_note_line = False
            continue

        # Check for block-level dynamic: (p), (f), (Cresc), etc.
        block_dyn = _is_block_dynamic(stripped)
        if block_dyn:
            pending_block_dynamic = block_dyn
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

            # Inject pending block dynamic into first beat of first measure
            if pending_block_dynamic and measures:
                first_beat = measures[0].get("beats", [])
                if first_beat and first_beat[0]:
                    first_beat[0][0].dynamic = pending_block_dynamic
                pending_block_dynamic = None

            last_voice_label = label

            if label not in voice_data:
                voice_data[label] = []
            voice_data[label].extend(measures)

        else:
            # Lyrics line
            prev_was_note_line = False

            voice, verse_id, syllables = parse_lyrics_line(stripped)
            # No voice prefix → attach to the last voice before this lyrics line
            if voice is None:
                voice = last_voice_label
            if voice not in lyrics_data:
                lyrics_data[voice] = {}
            if verse_id not in lyrics_data[voice]:
                lyrics_data[voice][verse_id] = []
            # Append syllables (lyrics can span multiple interleaved blocks)
            lyrics_data[voice][verse_id].extend(syllables)

    return {
        "properties": props,
        "voices": voice_data,
        "lyrics": lyrics_data,
    }


# ══════════════════════════════════════════════════════════════════════
#  PITCH CONVERSION
# ══════════════════════════════════════════════════════════════════════

# Map key name → MIDI note number for that key at octave 4
_KEY_NAME_TO_MIDI_BASE = {}
for _kn in VALID_KEYS:
    _p = pitch.Pitch(_kn + "4")
    _KEY_NAME_TO_MIDI_BASE[_kn] = _p.midi


def solfa_to_pitch(evt: NoteEvent, current_key: str, base_octave: int) -> pitch.Pitch:
    """Convert a NoteEvent to a music21 Pitch, respecting key and octave."""
    tonic_midi = _KEY_NAME_TO_MIDI_BASE.get(current_key, 60)
    # Adjust tonic to base_octave (default table is octave 4)
    tonic_midi += (base_octave - 4) * 12

    midi_val = tonic_midi + evt.semitone + (evt.octave_shift * 12)

    p = pitch.Pitch(midi=midi_val)

    # Fix enharmonic spelling based on key
    k = key.Key(current_key)
    scale_pitches = [sp.name for sp in k.getScale("major").getPitches()]

    # For diatonic notes, use the scale's spelling
    if not evt.is_chromatic_sharp and not evt.is_chromatic_flat:
        # Find the matching scale degree pitch name
        degree_map = {0: 0, 2: 1, 4: 2, 5: 3, 7: 4, 9: 5, 11: 6}
        if evt.semitone in degree_map:
            idx = degree_map[evt.semitone]
            if idx < len(scale_pitches):
                correct_name = scale_pitches[idx]
                p.name = correct_name
    elif evt.is_chromatic_sharp:
        # Sharpen the base diatonic note
        base_solfa = evt.solfa[0]  # first char = base note
        base_semi = SOLFA_TO_SEMITONE.get(base_solfa, 0)
        degree_map = {0: 0, 2: 1, 4: 2, 5: 3, 7: 4, 9: 5, 11: 6}
        if base_semi in degree_map:
            idx = degree_map[base_semi]
            if idx < len(scale_pitches):
                base_name = scale_pitches[idx]
                raised = pitch.Pitch(base_name)
                raised.midi = raised.midi  # ensure computed
                # Set the name to base + sharp
                accidental_count = raised.accidental.alter if raised.accidental else 0
                p.name = base_name
                if p.accidental:
                    p.accidental = pitch.Accidental(accidental_count + 1)
                else:
                    p.accidental = pitch.Accidental(1)
    elif evt.is_chromatic_flat:
        # Flatten the base diatonic note above
        # e.g. ra = flat-re, ta = flat-ti
        _flat_base = {
            "ra": "r", "ma": "m", "sa": "s", "la": "l", "ta": "t"
        }
        base_solfa = _flat_base.get(evt.solfa, evt.solfa[0])
        base_semi = SOLFA_TO_SEMITONE.get(base_solfa, 0)
        degree_map = {0: 0, 2: 1, 4: 2, 5: 3, 7: 4, 9: 5, 11: 6}
        if base_semi in degree_map:
            idx = degree_map[base_semi]
            if idx < len(scale_pitches):
                base_name = scale_pitches[idx]
                p.name = base_name
                accidental_count = p.accidental.alter if p.accidental else 0
                p.accidental = pitch.Accidental(accidental_count - 1)

    return p


# ══════════════════════════════════════════════════════════════════════
#  KEY CHANGE (MODULATION) RESOLUTION
# ══════════════════════════════════════════════════════════════════════

def resolve_modulation(mod_str: str, current_key: str, base_octave: int) -> str:
    """
    Given a modulation string like 's/d', compute the new key.
    old_solfa / new_solfa means: the pitch that was old_solfa in the
    current key is now new_solfa in the new key.
    """
    parts = mod_str.split(MODULATION_SEPARATOR)
    old_solfa_str = parts[0].strip()
    new_solfa_str = parts[1].strip()

    # Parse old solfa to get its semitone offset
    old_evt, _ = _parse_single_token(old_solfa_str)
    new_evt, _ = _parse_single_token(new_solfa_str)
    if old_evt is None or new_evt is None:
        return current_key

    # The actual pitch of the old solfa note in current key
    old_pitch = solfa_to_pitch(old_evt, current_key, base_octave)

    # That pitch is now new_solfa in the new key.
    # new_key_tonic = old_pitch - new_semitone_offset
    new_tonic_midi = old_pitch.midi - new_evt.semitone
    # Normalise to octave 4
    while new_tonic_midi < 60:
        new_tonic_midi += 12
    while new_tonic_midi >= 72:
        new_tonic_midi -= 12

    new_tonic = pitch.Pitch(midi=new_tonic_midi)

    # Find the closest valid key name
    best = current_key
    for kn in VALID_KEYS:
        kp = pitch.Pitch(kn)
        if kp.pitchClass == new_tonic.pitchClass:
            best = kn
            break
    return best


# ══════════════════════════════════════════════════════════════════════
#  DURATION ASSIGNMENT
# ══════════════════════════════════════════════════════════════════════

def assign_durations(measures: list[dict], time_sig: str) -> list[list[TimedEvent]]:
    """
    Walk through parsed measures and compute quarter-length durations.
    Returns a list of measures, each being a flat list of TimedEvents.

    Duration logic:
      measure_ql = num_beats * (4.0 / denominator)
      Each beat group (separated by :) gets measure_ql / num_groups.
      If fewer groups than expected beats, each group is proportionally longer.
      e.g. 2/4 with one group (no colon): that group spans the whole measure.
      Within a group, notes share the group's duration equally.
    """
    num, den = map(int, time_sig.split("/"))
    beat_ql = 4.0 / den               # quarter-length per beat
    measure_ql = num * beat_ql         # total quarter-length per measure

    result = []
    for meas in measures:
        timed_events: list[TimedEvent] = []
        beats = meas["beats"]
        n_groups = len(beats) if beats else 1
        group_ql = measure_ql / n_groups   # duration per beat group

        for beat_notes in beats:
            n_events = len(beat_notes)
            if n_events == 0:
                continue
            sub_ql = group_ql / n_events
            for evt in beat_notes:
                # Special: ** = 2-beat rest
                if evt.is_rest and evt.raw == "**":
                    timed_events.append(TimedEvent(evt, beat_ql * 2))
                else:
                    timed_events.append(TimedEvent(evt, sub_ql))

        result.append(timed_events)
    return result


# ══════════════════════════════════════════════════════════════════════
#  CONSOLIDATE HOLDS INTO LONGER NOTES  (within a measure)
# ══════════════════════════════════════════════════════════════════════

def consolidate_holds(timed_measures: list[list[TimedEvent]]) -> list[list[TimedEvent]]:
    """
    Merge consecutive holds into the preceding note, extending its duration.
    Cross-measure holds are handled separately via ties.
    """
    result = []
    for events in timed_measures:
        consolidated: list[TimedEvent] = []
        for te in events:
            if te.event.is_hold and consolidated:
                # Extend previous note
                consolidated[-1].quarter_length += te.quarter_length
            else:
                consolidated.append(TimedEvent(te.event, te.quarter_length))
        result.append(consolidated)
    return result


# ══════════════════════════════════════════════════════════════════════
#  SCORE BUILDING
# ══════════════════════════════════════════════════════════════════════

def _get_voice_base(voice_label: str) -> str:
    """Extract the base voice letter from a label like 'S1' → 'S', 'T2' → 'T'."""
    if voice_label and voice_label[0] in VOICE_BASE_LABELS:
        return voice_label[0]
    return voice_label


def _get_voice_config(voice_label: str) -> dict:
    """Get the VOICE_CONFIG entry for a voice, inheriting from base for numbered voices."""
    base = _get_voice_base(voice_label)
    return VOICE_CONFIG.get(base, VOICE_CONFIG["S"])  # fallback to Soprano


def _get_voice_full_name(voice_label: str) -> str:
    """Get full part name: 'S' → 'Soprano', 'S1' → 'Soprano 1', 'T2' → 'Tenor 2'."""
    cfg = _get_voice_config(voice_label)
    base_name = cfg["name"]
    base = _get_voice_base(voice_label)
    suffix = voice_label[len(base):]  # e.g. "1", "2", or ""
    if suffix:
        return f"{base_name} {suffix}"
    return base_name


def _get_clef(voice_label: str):
    """Return a music21 Clef object for the given voice."""
    cfg = _get_voice_config(voice_label)
    name = cfg["clef"]
    if name == "treble":
        return clef.TrebleClef()
    elif name == "treble8vb":
        return clef.Treble8vbClef()
    elif name == "bass":
        return clef.BassClef()
    return clef.TrebleClef()


def _get_instrument(voice_label: str):
    """Return a music21 Instrument instance for the given voice."""
    cfg = _get_voice_config(voice_label)
    return cfg["instrument"]()


def _get_octave_offset(voice_label: str) -> int:
    """Return the octave offset for the given voice (e.g. -1 for Tenor/Bass)."""
    cfg = _get_voice_config(voice_label)
    return cfg["octave_offset"]


def _make_note(p: pitch.Pitch, ql: float) -> note.Note:
    """Create a music21 Note with the given pitch and quarter length."""
    n = note.Note(p)
    n.duration = duration.Duration(quarterLength=ql)
    return n


def _make_rest(ql: float) -> note.Rest:
    """Create a music21 Rest with the given quarter length."""
    r = note.Rest()
    r.duration = duration.Duration(quarterLength=ql)
    return r


def _apply_dynamic(measure: stream.Measure, dyn_str: str):
    """
    Append a dynamic, hairpin, or text expression to a measure.
    dyn_str can be: "p", "ff", "<", ">", "cresc", etc.
    """
    if dyn_str in VALID_DYNAMICS:
        d = dynamics.Dynamic(dyn_str)
        measure.append(d)
    elif dyn_str == HAIRPIN_CRESC:
        # Start a crescendo wedge
        w = dynamics.Crescendo()
        measure.append(w)
    elif dyn_str == HAIRPIN_DIM:
        # Start a diminuendo wedge
        w = dynamics.Diminuendo()
        measure.append(w)
    elif dyn_str in TEXT_EXPRESSIONS:
        te = expressions.TextExpression(TEXT_EXPRESSIONS[dyn_str])
        te.style.fontStyle = "italic"
        measure.append(te)
    else:
        # Unknown — treat as text expression
        te = expressions.TextExpression(dyn_str)
        te.style.fontStyle = "italic"
        measure.append(te)


def build_score(parsed: dict) -> stream.Score:
    """Convert fully parsed data into a music21 Score."""
    props = parsed["properties"]
    voices = parsed["voices"]
    lyrics_data = parsed["lyrics"]

    score = stream.Score()

    # ── Metadata ──
    md = metadata.Metadata()
    md.title = props.get("TITLE", DEFAULTS["TITLE"])
    md.composer = props.get("COMPOSER", DEFAULTS["COMPOSER"])
    if props.get("AUTHOR"):
        md.lyricist = props["AUTHOR"]
    score.metadata = md

    time_sig_str = props.get("TIMESIG", DEFAULTS["TIMESIG"])
    current_key = props.get("KEY", DEFAULTS["KEY"])
    base_octave = props.get("OCTAVE", DEFAULTS["OCTAVE"])
    bpm = props.get("TEMPO", DEFAULTS["TEMPO"])

    ts = meter.TimeSignature(time_sig_str)
    ks = key.Key(current_key)

    # Compute measure duration for whole-measure rests
    ts_num, ts_den = map(int, time_sig_str.split("/"))
    measure_ql = ts_num * (4.0 / ts_den)

    # Create tempo mark with proper beat unit from time signature denominator
    # denominator 4 → quarter note, 8 → eighth note, 2 → half note, etc.
    beat_duration = duration.Duration(quarterLength=4.0 / ts_den)
    tempo_mark = tempo.MetronomeMark(
        referent=beat_duration,
        number=bpm,
    )

    # ── Build each voice part ──
    for voice_label, measures_raw in voices.items():
        part = stream.Part()
        part.id = voice_label
        part.partName = _get_voice_full_name(voice_label)

        # Instrument (helps MuseScore assign correct sound/range)
        part.insert(0, _get_instrument(voice_label))

        # Clef, key sig, time sig, tempo on first measure
        part.append(_get_clef(voice_label))
        part.append(ks)
        part.append(ts)
        part.append(tempo_mark)

        # Voice-specific octave: base octave + voice offset
        voice_octave = base_octave + _get_octave_offset(voice_label)

        # Assign durations and consolidate holds
        timed = assign_durations(measures_raw, time_sig_str)
        timed = consolidate_holds(timed)

        # Prepare lyrics syllables for this voice
        voice_lyrics = lyrics_data.get(voice_label, {})
        # Flatten verses in order: verse 1, 2, … then refrain
        # For now, assign verse 1 (or the first available verse) as lyric number 1
        sorted_verses = sorted(
            ((vid, syls) for vid, syls in voice_lyrics.items()),
            key=lambda x: (isinstance(x[0], str), x[0])  # ints first, then "R"
        )

        # Build a lyrics cursor per verse
        lyrics_cursors: dict[int, tuple[list[str], int]] = {}
        for lyric_num, (vid, syls) in enumerate(sorted_verses, start=1):
            lyrics_cursors[lyric_num] = (syls, 0)  # (syllables, cursor_pos)

        # Track state for cross-measure ties and modulations
        active_key = current_key
        prev_note_obj = None  # last music21.note.Note for cross-measure ties
        needs_tie_start = False

        for m_idx, events in enumerate(timed):
            m21_measure = stream.Measure(number=m_idx + 1)

            # Structural markers → repeat barlines etc.
            markers = measures_raw[m_idx].get("markers", []) if m_idx < len(measures_raw) else []
            modulations = measures_raw[m_idx].get("modulations", []) if m_idx < len(measures_raw) else []

            # Process modulations
            for mod in modulations:
                new_key = resolve_modulation(mod, active_key, base_octave)
                if new_key != active_key:
                    active_key = new_key
                    m21_measure.append(key.Key(active_key))

            # Repeat start
            if REPEAT_START in markers:
                m21_measure.leftBarline = bar.Repeat(direction="start")
            # Volta 1 (first ending)
            if VOLTA_1_START in markers:
                # music21 uses Spanner for volta brackets — simplified approach
                pass  # handled below with repeat logic

            first_event_in_measure = True

            # Detect whole-measure rest: all events are rests, no notes or holds
            all_rests = all(te.event.is_rest for te in events) if events else True
            if all_rests and events:
                # Create a single whole-measure rest
                r = note.Rest()
                r.duration = duration.Duration(quarterLength=measure_ql)
                r.fullMeasure = True
                # Check if any rest carries a dynamic
                for te in events:
                    if te.event.dynamic:
                        _apply_dynamic(m21_measure, te.event.dynamic)
                        break
                m21_measure.append(r)
                prev_note_obj = None
            else:
                for te in events:
                    evt = te.event
                    ql = te.quarter_length

                    # Apply dynamics if present on this event
                    if evt.dynamic:
                        _apply_dynamic(m21_measure, evt.dynamic)

                    if evt.is_rest:
                        r = _make_rest(ql)
                        m21_measure.append(r)
                        prev_note_obj = None
                        needs_tie_start = False
                    elif evt.is_hold:
                        # Cross-measure hold: tie from previous measure's last note
                        if prev_note_obj is not None and first_event_in_measure:
                            tied_n = _make_note(prev_note_obj.pitch, ql)
                            prev_note_obj.tie = tie.Tie("start")
                            tied_n.tie = tie.Tie("stop")
                            m21_measure.append(tied_n)
                            prev_note_obj = tied_n
                        else:
                            m21_measure.append(_make_rest(ql))
                            prev_note_obj = None
                    else:
                        # Normal note
                        p = solfa_to_pitch(evt, active_key, voice_octave)
                        n = _make_note(p, ql)

                        # Assign lyrics (one syllable per non-melisma note per verse)
                        if not evt.is_melisma:
                            for lyric_num, (syls, cursor) in list(lyrics_cursors.items()):
                                if cursor < len(syls):
                                    syl = syls[cursor]
                                    n.addLyric(syl, lyricNumber=lyric_num)
                                    lyrics_cursors[lyric_num] = (syls, cursor + 1)

                        m21_measure.append(n)
                        prev_note_obj = n

                    first_event_in_measure = False

            # Repeat end
            if REPEAT_END in markers:
                m21_measure.rightBarline = bar.Repeat(direction="end")
            # Fine
            if FINE in markers:
                m21_measure.append(expressions.TextExpression("Fine"))
            # D.C. / D.S.
            if DA_CAPO_SEGNO in markers:
                if REPEAT_START in [mk for mm in measures_raw[:m_idx]
                                     for mk in mm.get("markers", [])]:
                    m21_measure.append(repeat.DalSegno())
                else:
                    m21_measure.append(repeat.DaCapo())

            part.append(m21_measure)

        # Final double barline
        if part.getElementsByClass(stream.Measure):
            last_meas = part.getElementsByClass(stream.Measure)[-1]
            if not isinstance(last_meas.rightBarline, bar.Repeat):
                last_meas.rightBarline = bar.Barline("final")

        score.append(part)

    return score


# ══════════════════════════════════════════════════════════════════════
#  LYRICS SYLLABIC ASSIGNMENT  (post-processing)
# ══════════════════════════════════════════════════════════════════════

def refine_lyrics_syllabic(score: stream.Score, parsed: dict):
    """
    Post-process lyrics to assign correct syllabic values
    (begin, middle, end, single) based on the original hyphenated text.
    """
    lyrics_data = parsed["lyrics"]

    for part in score.parts:
        voice_label = part.id
        voice_lyrics = lyrics_data.get(voice_label, {})
        sorted_verses = sorted(
            ((vid, syls) for vid, syls in voice_lyrics.items()),
            key=lambda x: (isinstance(x[0], str), x[0])
        )

        for lyric_num, (vid, raw_text) in enumerate(sorted_verses, start=1):
            # Rebuild the original word structure to know syllabic type
            # We need the original text line for this
            pass  # Lyrics syllabic is best handled during initial assignment
            # For now, music21's default "single" is acceptable for MuseScore


# ══════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════

OUTPUT_DIR = Path("outputs")

def convert(input_path: str, output_path: str | None = None):
    """Convert a tonic solfa .txt file to MusicXML."""
    input_p = Path(input_path)

    if output_path is None:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_path = str(OUTPUT_DIR / input_p.with_suffix(".xml").name)
    else:
        # If user provided a path, ensure its parent dir exists
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)

    print(f"Parsing: {input_p}")
    parsed = parse_file(str(input_p))

    props = parsed["properties"]
    print(f"  Title:    {props.get('TITLE')}")
    print(f"  Key:      {props.get('KEY')}")
    print(f"  Tempo:    {props.get('TEMPO')}")
    print(f"  TimeSig:  {props.get('TIMESIG')}")
    print(f"  Voices:   {list(parsed['voices'].keys())}")
    print(f"  Lyrics:   {list(parsed['lyrics'].keys())}")

    print("Building score …")
    score = build_score(parsed)

    print(f"Writing: {output_path}")
    score.write("musicxml", fp=output_path)
    print("Done.")


def main():
    if len(sys.argv) < 2:
        print("Usage: python converter.py <input.txt> [output.xml]")
        print("  Converts tonic solfa notation to MusicXML for MuseScore 4.")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    convert(input_file, output_file)


if __name__ == "__main__":
    main()
