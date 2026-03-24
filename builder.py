"""Build a music21 Score from parsed tonic solfa data."""

from datetime import date

from music21 import (
    stream, note, pitch, key, meter, tempo, clef, bar,
    duration, metadata, tie, repeat, expressions, dynamics,
)

from config import (
    DEFAULTS, VOICE_BASE_LABELS, VOICE_CONFIG,
    REPEAT_START, REPEAT_END, VOLTA_1_START, FINE, DA_CAPO_SEGNO,
    VALID_DYNAMICS, HAIRPIN_CRESC, HAIRPIN_DIM, TEXT_EXPRESSIONS,
)

from solfa_pitch import solfa_to_pitch, resolve_modulation
from duration import assign_durations, consolidate_holds


# ──────────────────────────────────────────────────────────────────────
#  VOICE HELPERS
# ──────────────────────────────────────────────────────────────────────

def _get_voice_base(voice_label: str) -> str:
    """Extract base voice letter: 'S1' → 'S', 'T2' → 'T'."""
    if voice_label and voice_label[0] in VOICE_BASE_LABELS:
        return voice_label[0]
    return voice_label


def _get_voice_config(voice_label: str) -> dict:
    """Get VOICE_CONFIG entry, inheriting from base for numbered voices."""
    base = _get_voice_base(voice_label)
    return VOICE_CONFIG.get(base, VOICE_CONFIG["S"])


def _get_voice_full_name(voice_label: str) -> str:
    """'S' → 'Soprano', 'S1' → 'Soprano 1', 'T2' → 'Tenor 2'."""
    cfg = _get_voice_config(voice_label)
    base_name = cfg["name"]
    base = _get_voice_base(voice_label)
    suffix = voice_label[len(base):]
    return f"{base_name} {suffix}" if suffix else base_name


def _get_clef(voice_label: str):
    """Return a music21 Clef object for the given voice."""
    name = _get_voice_config(voice_label)["clef"]
    clef_map = {
        "treble": clef.TrebleClef,
        "treble8vb": clef.Treble8vbClef,
        "bass": clef.BassClef,
    }
    return clef_map.get(name, clef.TrebleClef)()


def _get_instrument(voice_label: str):
    """Return a music21 Instrument instance for the given voice."""
    return _get_voice_config(voice_label)["instrument"]()


def _get_octave_offset(voice_label: str) -> int:
    """Return octave offset for the voice (e.g. -1 for Tenor/Bass)."""
    return _get_voice_config(voice_label)["octave_offset"]


# ──────────────────────────────────────────────────────────────────────
#  NOTE / REST / DYNAMICS HELPERS
# ──────────────────────────────────────────────────────────────────────

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
    """Append a dynamic, hairpin, or text expression to a measure."""
    if dyn_str in VALID_DYNAMICS:
        measure.append(dynamics.Dynamic(dyn_str))
    elif dyn_str == HAIRPIN_CRESC:
        measure.append(dynamics.Crescendo())
    elif dyn_str == HAIRPIN_DIM:
        measure.append(dynamics.Diminuendo())
    elif dyn_str in TEXT_EXPRESSIONS:
        te = expressions.TextExpression(TEXT_EXPRESSIONS[dyn_str])
        te.style.fontStyle = "italic"
        measure.append(te)
    else:
        te = expressions.TextExpression(dyn_str)
        te.style.fontStyle = "italic"
        measure.append(te)


# ──────────────────────────────────────────────────────────────────────
#  SCORE BUILDING
# ──────────────────────────────────────────────────────────────────────

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
    md.date = date.today().isoformat()
    score.metadata = md

    time_sig_str = props.get("TIMESIG", DEFAULTS["TIMESIG"])
    current_key = props.get("KEY", DEFAULTS["KEY"])
    base_octave = props.get("OCTAVE", DEFAULTS["OCTAVE"])
    bpm = props.get("TEMPO", DEFAULTS["TEMPO"])

    ts_num, ts_den = map(int, time_sig_str.split("/"))
    measure_ql = ts_num * (4.0 / ts_den)

    is_first_part = True

    # ── Build each voice part ──
    for voice_label, measures_raw in voices.items():
        part = stream.Part()
        part.id = voice_label
        part.partName = _get_voice_full_name(voice_label)

        part.insert(0, _get_instrument(voice_label))

        # Fresh objects per part (music21 objects can only belong to one stream)
        part.append(_get_clef(voice_label))
        part.append(key.Key(current_key))
        part.append(meter.TimeSignature(time_sig_str))

        voice_octave = base_octave + _get_octave_offset(voice_label)

        timed = assign_durations(measures_raw, time_sig_str)
        timed = consolidate_holds(timed)

        # Lyrics cursors
        voice_lyrics = lyrics_data.get(voice_label, {})
        sorted_verses = sorted(
            ((vid, syls) for vid, syls in voice_lyrics.items()),
            key=lambda x: (isinstance(x[0], str), x[0])
        )
        lyrics_cursors: dict[int, tuple[list[str], int]] = {}
        for lyric_num, (vid, syls) in enumerate(sorted_verses, start=1):
            lyrics_cursors[lyric_num] = (syls, 0)

        active_key = current_key
        prev_note_obj = None
        needs_tie_start = False

        for m_idx, events in enumerate(timed):
            m21_measure = stream.Measure(number=m_idx + 1)

            # Tempo mark: only in measure 1 of the first part
            if m_idx == 0 and is_first_part:
                beat_dur = duration.Duration(quarterLength=4.0 / ts_den)
                m21_measure.insert(0, tempo.MetronomeMark(
                    referent=beat_dur, number=bpm))

            markers = measures_raw[m_idx].get("markers", []) if m_idx < len(measures_raw) else []
            modulations = measures_raw[m_idx].get("modulations", []) if m_idx < len(measures_raw) else []

            for mod in modulations:
                new_key = resolve_modulation(mod, active_key, base_octave)
                if new_key != active_key:
                    active_key = new_key
                    m21_measure.append(key.Key(active_key))

            if REPEAT_START in markers:
                m21_measure.leftBarline = bar.Repeat(direction="start")
            if VOLTA_1_START in markers:
                pass

            first_event_in_measure = True

            # Whole-measure rest detection
            all_rests = all(te.event.is_rest for te in events) if events else True
            if all_rests and events:
                r = note.Rest()
                r.duration = duration.Duration(quarterLength=measure_ql)
                r.fullMeasure = True
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

                    if evt.dynamic:
                        _apply_dynamic(m21_measure, evt.dynamic)

                    if evt.is_rest:
                        r = _make_rest(ql)
                        if evt.fermata:
                            r.expressions.append(expressions.Fermata())
                        m21_measure.append(r)
                        prev_note_obj = None
                        needs_tie_start = False
                    elif evt.is_hold:
                        if prev_note_obj is not None and first_event_in_measure:
                            tied_n = _make_note(prev_note_obj.pitch, ql)
                            prev_note_obj.tie = tie.Tie("start")
                            tied_n.tie = tie.Tie("stop")
                            if evt.fermata:
                                tied_n.expressions.append(expressions.Fermata())
                            m21_measure.append(tied_n)
                            prev_note_obj = tied_n
                        else:
                            m21_measure.append(_make_rest(ql))
                            prev_note_obj = None
                    else:
                        p = solfa_to_pitch(evt, active_key, voice_octave)
                        n = _make_note(p, ql)

                        if evt.fermata:
                            n.expressions.append(expressions.Fermata())

                        if not evt.is_melisma:
                            for lyric_num, (syls, cursor) in list(lyrics_cursors.items()):
                                if cursor < len(syls):
                                    syl = syls[cursor]
                                    n.addLyric(syl, lyricNumber=lyric_num)
                                    lyrics_cursors[lyric_num] = (syls, cursor + 1)

                        m21_measure.append(n)
                        prev_note_obj = n

                    first_event_in_measure = False

            if REPEAT_END in markers:
                m21_measure.rightBarline = bar.Repeat(direction="end")
            if FINE in markers:
                m21_measure.append(expressions.TextExpression("Fine"))
            if DA_CAPO_SEGNO in markers:
                if REPEAT_START in [mk for mm in measures_raw[:m_idx]
                                     for mk in mm.get("markers", [])]:
                    m21_measure.append(repeat.DalSegno())
                else:
                    m21_measure.append(repeat.DaCapo())

            part.append(m21_measure)

        if part.getElementsByClass(stream.Measure):
            last_meas = part.getElementsByClass(stream.Measure)[-1]
            if not isinstance(last_meas.rightBarline, bar.Repeat):
                last_meas.rightBarline = bar.Barline("final")

        score.append(part)
        is_first_part = False

    return score
