"""
Tonic Solfa to MusicXML Converter — Configuration & Notation Reference
======================================================================

This file defines every symbol, mapping, and default used by the converter.
Import it from the main script so all magic strings live in one place.
"""

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Register FreeSerif font for musical symbols (Coda, Segno)
try:
    pdfmetrics.registerFont(TTFont('FreeSerif', '/Library/Fonts/FreeSerif.ttf'))
    MUSIC_SYMBOL_FONT = 'FreeSerif'
except:
    MUSIC_SYMBOL_FONT = 'Helvetica'  # Fallback


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
#   (empty beat)       rest (silence) — no note is sounding
#   *                  explicit rest (same as empty, just more visible)
#   **                 explicit two-beat rest
#
# Summary:
#   -         → hold (continue previous note)
#   (blank)   → rest (silence)
#   *         → rest (silence, explicit)
#   **        → two-beat rest (silence, explicit)
#
# WHOLE-MEASURE REST:
#   If a measure contains ONLY separators and blanks (no notes, no holds),
#   it becomes a single whole-measure rest (centered in MuseScore).
#   | : : : |      → whole-measure rest (not 4 quarter rests)
#   | : |          → whole-measure rest in 2/4
#   But:
#   | d : : : |    → note + 3 beat rests (partial, NOT whole-measure)
#   | - : : : |    → hold + 3 beat rests (partial, NOT whole-measure)
#
# Duration logic:
#   In time signature N/D, each measure has N beats.
#   |d:r:m:f|      → 4 beats, each note gets 1 beat  (quarter note in 4/4)
#   |d:-:r:m|      → d lasts 2 beats (beat 1 + hold on beat 2)
#   |d: :r:m|      → d for 1 beat, silence on beat 2, then r m
#   |d.r:m:f:s|    → beat 1 subdivided: d gets half-beat, r gets half-beat
#   |d.rm:…|       → beat 1 subdivided into 3: d, r, m (triplet feel)
#   |d._r:m|       → d.r is one beat, but _ before r means r is tied to d
#                     for lyrics purposes (counts as one syllable)
#   |*:r:m:f|      → beat 1 is an explicit rest, then r m f
#   |d:-:-.m:.s|   → d for 2½ beats (beat 1 + hold beat 2 + hold half of beat 3),
#                     m for ½ beat (second half of beat 3),
#                     silence for ½ beat (first half of beat 4),
#                     s for ½ beat (second half of beat 4)
#
# STACCATO (short, detached):
#   A comma BEFORE a note (after the dot separator) means the note
#   is played short/detached (staccato). The comma is stripped before
#   parsing the note.
#     |d.,t,|       → d,(normal) + t,(staccato, octave down)
#     |m.,r|        → m(normal) + r(staccato)
#     |s,.,m,|      → s,(normal) + m,(staccato, octave down)
#   The leading comma only appears after a dot separator.

BARLINE            = "|"
DOUBLE_BARLINE     = "||"
BEAT_SEPARATOR     = ":"
SUBBEAT_SEPARATOR  = "."
HOLD               = "-"
REST_STAR          = "*"       # explicit 1-beat rest
REST_DOUBLE_STAR   = "**"      # explicit 2-beat rest
STACCATO_PREFIX    = ","       # leading comma before note = staccato


# ─────────────────────────────────────────────────────────────────────
# 5b. DYNAMICS & EXPRESSION MARKS
# ─────────────────────────────────────────────────────────────────────
# Dynamics and expressions are written in parentheses, always INLINE
# (attached to a specific note inside a measure).
#
# DYNAMICS (attached to a note):
#     | (p)d : r : m |        → piano on "d"
#     | d : (f)r : m |        → forte on "r"
#     | (pp)d.r : (ff)m : s | → pianissimo on "d", fortissimo on "m"
#
# HAIRPINS (crescendo / diminuendo):
#   (<)  → start crescendo hairpin
# CRESCENDO / DIMINUENDO:
#   (<)  → "cresc." text in the score
#   (>)  → "dim." text in the score
#     | (p)d : (<)r : m | d : r : (f)m |   → cresc. on r
#     | (f)d : (>)r : m | d : r : (p)m |   → dim. on r
#
# TEXT EXPRESSIONS (cresc., dim., etc.):
#   (cresc)  → text "cresc." in the score  (same as (<))
#   (dim)    → text "dim." in the score    (same as (>))
#     | (cresc)d : r : m | d : r : (f)m |
#
# FERMATA (hold/pause over a note):
#   (^)  → fermata on the next note
#     | d : r : (^)m : f |     → fermata on m
#     | d : (^)(p)r : m |      → fermata + piano on r (can combine)
#
# COMBINING: multiple parenthesized prefixes can be chained:
#     | (^)(f)d : r : m |      → fermata + forte on d
#
# Available dynamics:
#   (ppp) (pp) (p) (mp) (mf) (f) (ff) (fff) (sf) (sfz) (fp)

VALID_DYNAMICS = {
    "ppp", "pp", "p", "mp", "mf", "f", "ff", "fff", "sf", "sfz", "fp",
}
HAIRPIN_CRESC  = "<"     # inside parens: (<)
HAIRPIN_DIM    = ">"     # inside parens: (>)
FERMATA        = "^"     # inside parens: (^)
TEXT_EXPRESSIONS = {
    "cresc": "cresc.",
    "dim":   "dim.",
    "rit":   "rit.",
    "accel": "accel.",
    "Cresc": "Cresc.",
}


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
#
# PARTIAL BLOCKS:
#   Not every voice needs to appear in every block. If a voice is absent
#   from a block, it automatically gets whole-measure rests for those measures.
#
#   When a block has fewer than 4 lines, EXPLICIT labels are required
#   so the parser knows which voice each line belongs to.
#
#   Example — only S1 and B have notes in this block:
#     S1  |d:r:m:f|s:-:-:-|
#     B   | : : :d|-:r:-: |
#     1S1  A-ma-zing grace how sweet
#     1B   Oh the sound
#   → S2, A, T1, T2 get whole-measure rests for these 2 measures.
#
#   Lyrics use voice prefix to target the correct voice:
#     1S1  → verse 1, Soprano 1
#     1B   → verse 1, Bass
#   Without prefix, lyrics go to the last voice in the block.

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
    # ── Instrument parts ──
    # Piano has two staves: right hand (PR) and left hand (PL)
    "PR": {
        "name":         "Piano (R)",
        "instrument":   instrument.Piano,
        "clef":         "treble",
        "octave_offset": 0,        # d = C4
        "range":        ("A0", "C8"),
    },
    "PL": {
        "name":         "Piano (L)",
        "instrument":   instrument.Piano,
        "clef":         "bass",
        "octave_offset": -1,       # d = C3
        "range":        ("A0", "C8"),
    },
}

# All valid voice/part labels for regex matching (sorted longest first)
ALL_PART_LABELS = sorted(VOICE_CONFIG.keys(), key=len, reverse=True)


# ─────────────────────────────────────────────────────────────────────
# 6b. CHORDS & INSTRUMENT PARTS
# ─────────────────────────────────────────────────────────────────────
# For keyboard instruments (piano, organ), multiple notes can sound
# simultaneously. Chords are written with angle brackets < >.
#
# CHORD NOTATION:
#   <d.m.s>     → C-E-G chord (notes separated by dots inside brackets)
#   <d.m.s>:r   → chord on beat 1, single note on beat 2
#   <d.f.l>:-   → chord held for 2 beats
#
# INSTRUMENT PART LABELS:
#   PR  → Piano Right hand (treble clef, octave 4)
#   PL  → Piano Left hand (bass clef, octave 3)
#
# Example — SATB + Piano:
#   S   | : : : :d.d|
#   A   | : : : :d.d|
#   T   | : : : : : |
#   B   | : : : : : |
#   PR  | :d:<d.f.l>:<d.f.l>:d:d|
#   PL  |f,:-.-:<d,.f,.l,>:-:f,.f,:<d,.f,.l,>|
#   1S  Wie der
#   1A  Wie der
#
# Chords in voice parts (rare but possible — double stops, divisi):
#   S   |<d.m>:r:m:f|   → soprano sings a two-note chord on beat 1

CHORD_OPEN  = "<"
CHORD_CLOSE = ">"
CHORD_SEP   = "."    # same as sub-beat separator, but inside < >


# ─────────────────────────────────────────────────────────────────────
# 7. LYRICS
# ─────────────────────────────────────────────────────────────────────
# Lyrics lines follow the note lines.
#
# PREFIX FORMAT:  [verse:]voices  or just text (no prefix)
#
#   NO PREFIX → all voices, verse 1:
#     A-ma-zing grace how sweet
#
#   VOICE LIST → verse 1, those voices only:
#     SATB A-ma-zing grace how sweet      → S, A, T, B
#     SA A-ma-zing grace how sweet        → S, A only
#     S1S2T A-ma-zing grace               → S1, S2, T
#     B Oh the sound                      → B only
#
#   REFRAIN → all voices:
#     R Praise God                        → refrain, all voices
#
#   VERSE NUMBER → all voices:
#     1 A-ma-zing grace                   → verse 1, all voices
#     2 'Twas grace                       → verse 2, all voices
#
#   VERSE + VOICE LIST → that verse, those voices:
#     1:SATB A-ma-zing grace              → verse 1, S A T B
#     1:B Oh the sound                    → verse 1, B only
#     2:SA 'Twas grace                    → verse 2, S and A
#     R:SA Praise God                     → refrain, S and A
#     R:TB Praise God from whom           → refrain, T and B
#
# MULTIPLE LYRICS LINES:
#   Syllables accumulate per voice — multiple lines for the same voice
#   and verse are concatenated:
#     |d:r:m:f|s:l:t:d'|
#     |d:d:d:d|m:m:m:m|
#     |d:d:d:d|d:d:d:d|
#     |d:d:d:d|d:d:d:d|
#     SAT A-ma-zing grace how sweet the sound
#     B Oh the sound how sweet
#
# Lyrics cursor advances ONLY on singable notes (not rests, holds, melisma).
# Extra syllables at the end are silently ignored.
# Notes beyond the last syllable get no lyrics text.
#
# Syllable rules:
#   - Words are separated by spaces
#   - Hyphens split a word across multiple notes:  "Wel-come" → 2 syllables
#   - The underscore _ appears ONLY on the NOTES side (e.g. _r),
#     meaning that note is a melisma and does NOT consume a new lyric syllable.
#     The lyrics line has NO underscores — just plain words, spaces, and hyphens.
#   - An asterisk * in the lyrics line means "skip this note position"
#     (the note is a rest or silent — no syllable assigned).
#     Multiple * skip multiple positions. Each * counts as one skip.
#   - A caret ^ joins two words into one syllable on a single note:
#     "ra-no^a-n'o-ny" → 4 syllables: "ra", "no a", "n'o", "ny"
#
# Examples:
#   notes:   |d:r: :f|s:l:t:d'|
#   lyrics:  hel-lo * bye how sweet the sound
#   → d="hel", r="lo", (rest) nothing, f="bye",
#     s="how", l="sweet", t="the", d'="sound"
#
#   notes:   |d._r:m|f:s|
#   lyrics:  Wel-come my friend
#   → d="Wel", _r=melisma (no syllable), m="come", f="my", s="friend"

NOTE_MELISMA_PREFIX = "_"  # prefix on a NOTE → melisma, don't consume next lyric
LYRICS_WORD_SEP     = " "  # space separates words / syllables in the lyrics line
LYRICS_HYPHEN       = "-"  # splits a word across notes in the lyrics line
LYRICS_JOIN         = "^"  # joins two words into one syllable on one note
LYRICS_REFRAIN      = "R"  # line prefix for refrain
LYRICS_REST_SKIP    = "*"  # skip a note position in the lyrics


# ─────────────────────────────────────────────────────────────────────
# 8. KEY CHANGES (MODULATION)
# ─────────────────────────────────────────────────────────────────────
# Written inline as   old_note/new_note
# Both old_note and new_note can have octave modifiers (' or ,).
# The octave modifiers don't affect key calculation (only pitch class
# matters), but they ARE used for the first played note in the new key.
#
# FORMAT:
#   old_note/new_note   where:
#     old_note = solfa name in the OLD key (with optional octave: ' ,)
#     new_note = solfa name in the NEW key (with optional octave: ' ,)
#               AND also the first note played in the new key
#
# The converter resolves this by:
#   1. Finding the pitch class of old_note in the old key
#   2. That pitch class becomes new_note's degree in the new key
#   3. Deriving the new key from that relationship
#
# EXAMPLES (without octave modifiers):
#   key=C, s/d   → G was sol in C, G is now do → new key = G
#   key=C, s/t   → G was sol in C, G is now ti → new key = Ab
#   key=C, s/m   → G was sol in C, G is now mi → new key = Eb
#
# EXAMPLES (with octave modifiers):
#   key=Db, r/s,   → Eb(r in Db) is now sol → new key = Ab
#                     s, is also the first note played (Eb3)
#   key=Db, l,/r,  → Bb(l in Db) is now re → new key = Ab
#                     r, is also the first note played (Bb3)
#   key=Ab, d/s    → Ab(d in Ab) is now sol → new key = Db
#                     s is also the first note played (Ab4)
#   key=Db, fi/t,  → G(fi in Db) is now ti → new key = Ab
#                     t, is also the first note played (G3)
#
# INLINE USAGE:
#   |d:r:m|r/s,.s,:t,:l,|   → modulate at beat 1 of m2, play s, then t, l,
#   |d:r:m|l,/r,.r,:s,:fi,| → same key change, different voice's perspective

MODULATION_SEPARATOR = "/"


# ─────────────────────────────────────────────────────────────────────
# 9. NAVIGATION MARKERS (repeats, jumps, codas, segnos)
# ─────────────────────────────────────────────────────────────────────
# All navigation markers are written in parentheses, inline before a note,
# just like dynamics and fermata.
#
# MARKERS:
#   (DC)   → D.C. (Da Capo — repeat from the beginning)
#   (DCF)  → D.C. al Fine (repeat from beginning, stop at Fine)
#   (DCC)  → D.C. al Coda (repeat from beginning, jump to Coda at To Coda)
#   (DS)   → D.S. (Dal Segno — repeat from Segno)
#   (DSF)  → D.S. al Fine (repeat from Segno, stop at Fine)
#   (DSC)  → D.S. al Coda (repeat from Segno, jump to Coda at To Coda)
#   (FINE)    → Fine (end point)
#   (TC)   → To Coda (jump to Coda sign)
#   (CODA)    → Coda (the coda section starts here, with coda sign)
#   (SEGNO)    → Segno (the segno sign, jump target for D.S.)
#
# USAGE (inline, before a note):
#   | d : r : (FINE)m : f |          → Fine on m
#   | d : r : m : (DC)f |         → D.C. on f
#   | d : r : m : (DS)f |         → D.S. on f
#   | (SEGNO)d : r : m : f |          → Segno on d
#   | d : r : (TC)m : f |         → To Coda on m
#   | (CODA)d : r : m : f |          → Coda section starts on d
#   | d : r : m : (DCF)f |        → D.C. al Fine on f
#   | d : r : m : (DSF)f |        → D.S. al Fine on f
#
# Can combine with dynamics and fermata:
#   | (^)(FINE)(p)d : r : m |        → fermata + Fine + piano on d
#
# COMMON PATTERNS:
#
#   D.C. al Fine:
#     | (SEGNO)d:r:m:f | d:r:(FINE)m:f | d:r:m:(DCF)f |
#     → play all, at DCF jump to start, stop at FINE
#
#   D.S. al Fine:
#     | d:r:m:f | (SEGNO)d:r:m:f | d:r:(FINE)m:f | d:r:m:(DSF)f |
#     → play all, at DSF jump to SEGNO, stop at FINE
#
#   D.C. al Coda:
#     | d:r:(TC)m:f | d:r:m:(DCC)f | (CODA)d:r:m:f |
#     → play m1-m2, at DCC jump to start, at TC jump to CODA
#
#   D.S. al Coda:
#     | d:r:m:f | (SEGNO)d:r:(TC)m:f | d:r:m:(DSC)f | (CODA)d:r:m:f |
#     → play all, at DSC jump to SEGNO, at TC jump to CODA

# Musical symbol constants
CODA_SYMBOL = "\U0001D10C"  # 𝄌
SEGNO_SYMBOL = "\U0001D10B"  # 𝄋
FERMATA_SYMBOL = "\U0001D110"  # 𝄐

NAVIGATION_MARKERS = {
    "DC":  "D.C.",
    "DCF": "D.C. al Fine",
    "DCC": "D.C. al Coda",
    "DS":  "D.S.",
    "DSF": "D.S. al Fine",
    "DSC": "D.S. al Coda",
    "FINE":   "Fine",
    "TC":  "To Coda",
    "CODA":   CODA_SYMBOL,
    "SEGNO":   SEGNO_SYMBOL,
}


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

# EXAMPLE 4: Partial blocks — not all voices in every block, per-voice lyrics
"""
TITLE Oratorio Excerpt
KEY F
TIMESIG 4/4

S   |d:r:m:f|s:-:-:-|
A   |d:d:d:d|m:-:-:-|
T   |d:d:d:d|d:-:-:-|
B   |d:d:d:d|d,:-:-:-|
1S  Glo-ry to God in the high-est
1B  Glo-ry to God in the high-est

S   | : : : | : : : |
B   | : : :d|-:r:-: |
1B  Oh hear

S   |d:r:m:f|s:-:-:-|
A   |d:d:d:d|m:-:-:-|
T   |d:d:d:d|d:-:-:-|
B   |d:d:d:d|d,:-:-:-|
1S  And peace on earth
1A  And peace on earth
1T  And peace on earth
1B  And peace on earth
"""
