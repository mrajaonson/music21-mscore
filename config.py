"""
Tonic Solfa to MusicXML Converter — Configuration & Notation Reference
======================================================================

This file defines every symbol, mapping, and default used by the converter.
Import it from the main script so all magic strings live in one place.
"""

# ─────────────────────────────────────────────────────────────────────
# 1. FILE-LEVEL PROPERTIES (parsed from header lines)
# ─────────────────────────────────────────────────────────────────────
# Each property appears on its own line as   PROPERTY value
# All are optional; defaults are shown below.

DEFAULTS = {
    "TITLE":    "Untitled",
    "AUTHOR":   "",
    "COMPOSER": "",
    "KEY":      "C",
    "TEMPO":    120,
    "TIMESIG":  "4/4",      # e.g. "3/4", "6/8"
    "METER":    None,        # optional descriptive meter label
    "OCTAVE":   4,           # base octave for unmarked notes (middle-C octave)
    "COMMENTS": "",
}

# Properties that are parsed as strings
HEADER_STRING_PROPS = {"TITLE", "AUTHOR", "COMPOSER", "KEY", "METER", "COMMENTS"}
# Properties that are parsed as integers
HEADER_INT_PROPS    = {"TEMPO", "OCTAVE"}
# Properties that are parsed with special logic
HEADER_SPECIAL_PROPS = {"TIMESIG"}  # "4/4" → (4, 4)


# ─────────────────────────────────────────────────────────────────────
# 2. SOLFA NOTE NAMES  →  SEMITONE OFFSETS FROM "do"
# ─────────────────────────────────────────────────────────────────────
# Natural (diatonic) notes of the major scale
SOLFA_TO_SEMITONE = {
    "d":  0,   # do
    "r":  2,   # re
    "m":  4,   # mi
    "f":  5,   # fa
    "s":  7,   # sol
    "l":  9,   # la
    "t":  11,  # ti
}

# Chromatic alterations — ascending (sharps / raised)
# Suffix "e" raises the natural note by 1 semitone (primary notation)
# Suffix "i" is the traditional alternative (di, ri, fi, si, li)
CHROMATIC_SHARP = {
    "de": 1,   # di  (raised do)
    "di": 1,   # di  (traditional alias for de)
    "re": 3,   # ri  (raised re)
    "ri": 3,   # ri  (traditional alias for re)
    "fe": 6,   # fi  (raised fa)
    "fi": 6,   # fi  (traditional alias for fe)
    "se": 8,   # si  (raised sol)
    "si": 8,   # si  (traditional alias for se)
    "le": 10,  # li  (raised la)
    "li": 10,  # li  (traditional alias for le)
}

# Chromatic alterations — descending (flats / lowered)
# Suffix "a" lowers the natural note by 1 semitone
CHROMATIC_FLAT = {
    "ra": 1,   # ra  (lowered re)
    "ma": 3,   # me  (lowered mi)  — sometimes written "ma"
    "sa": 6,   # se  (lowered sol)
    "la": 8,   # le  (lowered la)
    "ta": 10,  # te  (lowered ti)
}

# Combined lookup: try longest match first (2-char before 1-char)
ALL_SOLFA_NOTES = {}
ALL_SOLFA_NOTES.update(CHROMATIC_SHARP)
ALL_SOLFA_NOTES.update(CHROMATIC_FLAT)
ALL_SOLFA_NOTES.update(SOLFA_TO_SEMITONE)

# Ordered for regex matching: longest tokens first
SOLFA_TOKENS_SORTED = sorted(ALL_SOLFA_NOTES.keys(), key=len, reverse=True)


# ─────────────────────────────────────────────────────────────────────
# 3. OCTAVE MODIFIERS
# ─────────────────────────────────────────────────────────────────────
# After the solfa letter(s), octave is shifted by trailing marks:
#   '  (apostrophe / single quote)  → +1 octave each
#   ,  (comma)                      → −1 octave each
#
# Examples (base octave = 4):
#   d,,  → octave 2   (4 − 2)
#   d,   → octave 3   (4 − 1)
#   d    → octave 4   (4 + 0)
#   d'   → octave 5   (4 + 1)
#   d''  → octave 6   (4 + 2)

OCTAVE_UP_CHAR   = "'"   # apostrophe / single quote
OCTAVE_DOWN_CHAR = ","   # comma


# ─────────────────────────────────────────────────────────────────────
# 4. KEY SIGNATURES
# ─────────────────────────────────────────────────────────────────────
# Valid key names (major keys only for tonic solfa "do = tonic")
VALID_KEYS = [
    "C",  "D",  "E",  "F",  "G",  "A",  "B",
    "C#", "D#", "F#", "G#", "A#",
    "Db", "Eb", "Gb", "Ab", "Bb",
]


# ─────────────────────────────────────────────────────────────────────
# 5. RHYTHM / DURATION WITHIN A MEASURE
# ─────────────────────────────────────────────────────────────────────
# Bar structure:
#   |  …  |           single barline separates measures
#   ||                 double barline = end of piece
#   :                  beat separator (splits a measure into beats)
#   .                  sub-beat separator (splits a beat into subdivisions)
#   -                  hold / tie — extends the previous note for that slot
#   (space)            rest for that slot
#   *                  explicit one-beat rest
#   **                 explicit two-beat rest
#
# Duration logic:
#   In time signature N/D, each measure has N beats.
#   |d:r:m:f|      → 4 beats, each note gets 1 beat  (quarter note in 4/4)
#   |d:-:r:m|      → d lasts 2 beats (beat 1 + hold on beat 2)
#   |d.r:m:f:s|    → beat 1 subdivided: d gets half-beat, r gets half-beat
#   |d.rm:…|       → beat 1 subdivided into 3: d, r, m (triplet feel)
#   |d._r:m|       → d.r is one beat, but _ before r means r is tied to d
#                     for lyrics purposes (counts as one syllable)

BARLINE            = "|"
DOUBLE_BARLINE     = "||"
BEAT_SEPARATOR     = ":"
SUBBEAT_SEPARATOR  = "."
HOLD               = "-"
REST_SPACE         = " "       # a space in a beat position = rest
REST_STAR          = "*"       # explicit 1-beat rest
REST_DOUBLE_STAR   = "**"      # explicit 2-beat rest


# ─────────────────────────────────────────────────────────────────────
# 6. VOICES / PARTS
# ─────────────────────────────────────────────────────────────────────
# Default voice order is S A T B (top to bottom).
#
# IMPLICIT LABELS:
#   When note lines have NO label prefix, they are assigned in order:
#     line 1 → S,  line 2 → A,  line 3 → T,  line 4 → B
#   This is the most common case for standard 4-part SATB hymns.
#
# EXPLICIT LABELS:
#   A note line can start with a voice label:  S, A, T, B
#   This is required when fewer than 4 voices are used (e.g. just S and A).
#
# NUMBERED VOICES:
#   For divisi or multiple voice parts, append a number: S1, S2, T1, T2, etc.
#   Each numbered voice becomes its own part in the output.
#   Examples:
#     S1  |d:r:m:f|      ← Soprano 1
#     S2  |d:d:d:d|      ← Soprano 2
#     T1  |d:d:d:d|      ← Tenor 1
#     T2  |s,:s,:s,:s,|  ← Tenor 2

# Base voice labels (without numbers)
VOICE_BASE_LABELS = ["S", "A", "T", "B"]

# Default implicit assignment order (when lines have no labels)
DEFAULT_VOICE_ORDER = ["S", "A", "T", "B"]

# ── Voice configuration ──
# Each voice has: full name, instrument class, clef, octave offset, range.
#
# OCTAVE OFFSET:
#   In tonic solfa, "d" with no octave marks always means the natural
#   register of that voice. But the file-level OCTAVE default is 4 (C4).
#   For tenor and bass, unmarked "d" should sound in octave 3 (C3), so
#   they get an offset of -1. Soprano and alto stay at 0.
#
#   This offset is added to the base octave BEFORE resolving pitch.
#   Octave marks (' and ,) still work on top of the shifted base.
#
# VOICE RANGE:
#   Used for validation and to help music21/MuseScore place notes correctly.
#   Format: (lowest_note, highest_note) as pitch strings.
#
#   Standard choral tessituras:
#     Soprano:  C4 – A5  (middle C up to high A)
#     Alto:     F3 – D5  (below middle C to D above staff)
#     Tenor:    C3 – A4  (octave below middle C up to A above middle C)
#     Bass:     E2 – D4  (low E up to middle D)

from music21 import instrument

VOICE_CONFIG = {
    "S": {
        "name":         "Soprano",
        "instrument":   instrument.Soprano,
        "clef":         "treble",
        "octave_offset": 0,        # d = C4
        "range":        ("C4", "A5"),
    },
    "A": {
        "name":         "Alto",
        "instrument":   instrument.Alto,
        "clef":         "treble",
        "octave_offset": 0,        # d = C4
        "range":        ("F3", "D5"),
    },
    "T": {
        "name":         "Tenor",
        "instrument":   instrument.Tenor,
        "clef":         "treble8vb",
        "octave_offset": -1,       # d = C3  (one octave below soprano)
        "range":        ("C3", "A4"),
    },
    "B": {
        "name":         "Bass",
        "instrument":   instrument.Bass,
        "clef":         "bass",
        "octave_offset": -1,       # d = C3  (one octave below soprano)
        "range":        ("E2", "D4"),
    },
}


# ─────────────────────────────────────────────────────────────────────
# 7. LYRICS
# ─────────────────────────────────────────────────────────────────────
# Lyrics lines follow the note lines.
#
# PREFIX FORMAT:  <verse><voice>   (optional — omit entirely for a single verse)
#   The verse identifier comes FIRST, then the voice label.
#
#   NO PREFIX (single verse / shared lyrics):
#     Lyrics with no prefix are attached to the LAST voice that appeared
#     before the lyrics line. In a standard SATB layout where lyrics come
#     after all 4 voice lines, this means Bass (the last voice parsed).
#     Example:
#       |d:r:m:f|      ← S
#       |d:d:d:d|      ← A
#       |d:d:d:d|      ← T
#       |d:d:d:d|      ← B
#       A ma zing grace   ← attached to B (last voice above)
#
#   With prefixes (multiple verses / specific voices):
#     1        → verse 1, last voice before the lyrics line
#     2        → verse 2, last voice before the lyrics line
#     1S1      → verse 1 of Soprano 1
#     2S1      → verse 2 of Soprano 1
#     1A       → verse 1 of Alto
#     3T2      → verse 3 of Tenor 2
#     R        → refrain, last voice before the lyrics line
#     RS1      → refrain of Soprano 1
#     RA       → refrain of Alto
#
#   When there are no numbered voices (plain SATB), these also work:
#     1S       → verse 1 of Soprano
#     2B       → verse 2 of Bass
#
# Syllable rules:
#   - Words are separated by spaces
#   - Hyphens split a word across multiple notes:  "Wel-come" → 2 syllables
#   - The underscore _ appears ONLY on the NOTES side (e.g. _r),
#     meaning that note is a melisma and does NOT consume a new lyric syllable.
#     The lyrics line has NO underscores — just plain words, spaces, and hyphens.
#
# Example:
#   notes:   |d._r:m|f:s|
#   lyrics:  Wel-come my friend
#   → d gets "Wel", _r is melisma (still "Wel"), m gets "come",
#     f gets "my", s gets "friend"
#
# Alignment logic:
#   Walk through notes and lyrics in parallel.
#   For each note:
#     - if the note has a _ prefix → melisma, reuse previous syllable, do NOT
#       advance the lyrics cursor
#     - otherwise → assign the next syllable from the lyrics and advance cursor

NOTE_MELISMA_PREFIX = "_"  # prefix on a NOTE → melisma, don't consume next lyric
LYRICS_WORD_SEP     = " "  # space separates words / syllables in the lyrics line
LYRICS_HYPHEN       = "-"  # splits a word across notes in the lyrics line
LYRICS_REFRAIN      = "R"  # line prefix for refrain


# ─────────────────────────────────────────────────────────────────────
# 8. KEY CHANGES (MODULATION)
# ─────────────────────────────────────────────────────────────────────
# Written inline as   old_solfa/new_solfa
# e.g.  s/d  means "the note that was sol in the old key is now do"
# This tells us the interval of modulation so we can compute the new key.
#
# The converter resolves this by:
#   1. Finding the MIDI pitch of the old solfa in the old key
#   2. That pitch becomes the new solfa degree in the new key
#   3. Deriving the new key from that relationship
#
# Example:  key=C, s/d  → G was sol in C, G is now do → new key = G
#           key=C, s/t  → G was sol in C, G is now ti → new key = Ab
#           key=C, s/m  → G was sol in C, G is now mi → new key = Eb

MODULATION_SEPARATOR = "/"


# ─────────────────────────────────────────────────────────────────────
# 9. REPEATS, JUMPS & STRUCTURAL MARKERS
# ─────────────────────────────────────────────────────────────────────
# [    → segno / repeat-start marker
# ]    → repeat-end: go back to [ (or to the beginning if no [)
# {    → marks the start of a first ending (volta 1)
#        when the repeat is taken, skip from { to after ] (volta 2)
# F    → Fine (end point for Da Capo / Da Segno)
# D    → Da Capo (go to beginning) or Da Segno (go to [), stop at F
#
# Patterns:
#   section1[section2]section3
#       → play section1, section2, section2 again, section3
#
#   section1]section2
#       → play section1, section1 again, section2
#
#   section1[section2{ending1]ending2
#       → play section1, section2, ending1, section2, ending2
#
#   section1{ending1]ending2
#       → play section1, ending1, section1, ending2
#
#   section1 F section2 D
#       → play section1, section2, then jump to start, stop at F (DC al Fine)
#
#   section1 [ section2 F section3 D
#       → play section1, section2, section3, then jump to [, stop at F (DS al Fine)

REPEAT_START   = "["    # segno / repeat start
REPEAT_END     = "]"    # repeat end (go back to [ or beginning)
VOLTA_1_START  = "{"    # first ending begins here
FINE           = "F"    # Fine marker
DA_CAPO_SEGNO  = "D"    # Da Capo or Da Segno jump


# ─────────────────────────────────────────────────────────────────────
# 10. CHROMATIC SCALE REFERENCE (for validation / debugging)
# ─────────────────────────────────────────────────────────────────────
# Ascending:   d  de  r  re  m  f  fe  s  se  l  le  t  d'
# Descending:  d' t   ta l   la s  sa  f  m   ma r  ra  d
#
# Semitones:   0  1   2  3   4  5  6   7  8   9  10  11 12

CHROMATIC_ASCENDING  = ["d", "de", "r", "re", "m", "f", "fe", "s", "se", "l", "le", "t"]
CHROMATIC_DESCENDING = ["d'", "t", "ta", "l", "la", "s", "sa", "f", "m", "ma", "r", "ra"]


# ─────────────────────────────────────────────────────────────────────
# 11. MUSIC21 / MUSESCORE EXPORT SETTINGS
# ─────────────────────────────────────────────────────────────────────

MUSICXML_VERSION = "4.0"          # MusicXML version for MuseScore 4 compat
DEFAULT_DIVISIONS = 1             # let music21 handle divisions automatically
EXPORT_FORMAT = "musicxml"        # music21 export format string


# ─────────────────────────────────────────────────────────────────────
# 12. QUICK-REFERENCE: FULL EXAMPLES
# ─────────────────────────────────────────────────────────────────────

# EXAMPLE 1: Single verse — no prefix needed on the lyrics line
"""
TITLE Amazing Grace
COMPOSER John Newton
KEY G
TEMPO 80
TIMESIG 3/4

|d:d.r|m:-:m.r|m:s:s.l|s:-: |
|d:d.r|m:-:m.r|d:m:m.f|m:-: |
|d:d  |d:-:d  |d:d:d  |d:-: |
|d:d  |s,:-:s,|d:d:d  |d:-: |

A ma zing grace how sweet the sound
"""

# EXAMPLE 2: Multiple verses — prefix with verse number
"""
TITLE Amazing Grace
KEY G
TIMESIG 3/4

|d:d.r|m:-:m.r|m:s:s.l|s:-: |
|d:d.r|m:-:m.r|d:m:m.f|m:-: |
|d:d  |d:-:d  |d:d:d  |d:-: |
|d:d  |s,:-:s,|d:d:d  |d:-: |

1  A ma zing grace how sweet the sound
2  'Twas grace that taught my heart to fear
R  Praise God praise God
"""

# EXAMPLE 3: Numbered voices with explicit labels
"""
TITLE Choral Piece
KEY C
TIMESIG 4/4

S1  |d:r:m:f|s:-:-:-|
S2  |d:d:d:d|m:-:-:-|
A   |d:t,:d:r|d:-:-:-|
T1  |s,:l,:t,:d|d:-:-:-|
T2  |s,:s,:s,:s,|s,:-:-:-|
B   |d,:d,:d,:d,|d,:-:-:-|

1S1  A-ma-zing grace how sweet
1S2  A-ma-zing grace how sweet
2S1  'Twas grace that taught my heart
RS1  Praise God praise God a-men
"""
