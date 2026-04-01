"""Data classes for the tonic solfa converter."""


class NoteEvent:
    """A single parsed note / rest / hold / chord event."""
    __slots__ = ("solfa", "semitone", "octave_shift", "is_rest", "is_hold",
                 "is_melisma", "is_chromatic_sharp", "is_chromatic_flat",
                 "raw", "dynamic", "fermata", "chord_notes", "navigation",
                 "is_staccato")

    def __init__(self, *, solfa=None, semitone=0, octave_shift=0,
                 is_rest=False, is_hold=False, is_melisma=False,
                 is_chromatic_sharp=False, is_chromatic_flat=False, raw="",
                 dynamic=None, fermata=False, chord_notes=None, navigation=None,
                 is_staccato=False):
        self.solfa = solfa
        self.semitone = semitone
        self.octave_shift = octave_shift
        self.is_rest = is_rest
        self.is_hold = is_hold
        self.is_melisma = is_melisma
        self.is_chromatic_sharp = is_chromatic_sharp
        self.is_chromatic_flat = is_chromatic_flat
        self.raw = raw
        self.dynamic = dynamic       # e.g. "p", "f", "ff", "<", ">", "cresc"
        self.fermata = fermata       # True if (^) was present
        self.chord_notes = chord_notes  # list of NoteEvent for chord members, or None
        self.navigation = navigation # e.g. "DC", "FINE", "SEGNO", "TC", "CODA", "DSF", etc.
        self.is_staccato = is_staccato  # True if leading comma = staccato (played short, detached)

    @property
    def is_chord(self):
        return self.chord_notes is not None and len(self.chord_notes) > 0

    def __repr__(self):
        if self.is_rest:
            return "Rest"
        if self.is_hold:
            return "Hold"
        if self.is_chord:
            return f"Chord({len(self.chord_notes)} notes)"
        return f"Note({self.solfa}, st={self.semitone}, oct={self.octave_shift})"


class TimedEvent:
    """A NoteEvent with a computed quarter-length duration."""
    __slots__ = ("event", "quarter_length")

    def __init__(self, event: NoteEvent, quarter_length: float):
        self.event = event
        self.quarter_length = quarter_length

    def __repr__(self):
        return f"{self.event}:{self.quarter_length}ql"
