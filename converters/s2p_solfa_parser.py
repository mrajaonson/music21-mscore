import re
from typing import List, Dict, Optional, Tuple, Any
from config import (HEADER_INT_PROPS, HEADER_STRING_PROPS, HEADER_SPECIAL_PROPS, BARLINE, DEFAULT_VOICE_ORDER,
                    DOUBLE_BARLINE, BEAT_SEPARATOR, SUBBEAT_SEPARATOR, STACCATO_PREFIX, VALID_KEYS, HOLD, REST_STAR,
                    REST_DOUBLE_STAR, CHORD_OPEN, CHORD_CLOSE, MODULATION_SEPARATOR, NOTE_MELISMA_PREFIX,
                    SOLFA_TOKENS_SORTED, OCTAVE_UP_CHAR, OCTAVE_DOWN_CHAR, VALID_DYNAMICS, HAIRPIN_CRESC, HAIRPIN_DIM,
                    FERMATA, NAVIGATION_MARKERS, TEXT_EXPRESSIONS, SEGNO_SYMBOL, CODA_SYMBOL, LYRICS_JOIN,
                    LYRICS_REST_SKIP, LYRICS_HYPHEN, DEFAULTS)
from s2p_data_structures import (Song, VoiceLine, Measure, Note, NoteType, Block, LyricLine, Expression, Beat)

class TonicSolfaParser:
    """Parser for tonic solfa notation files"""

    def __init__(self):
        self.song = Song()
        self.current_measure_num = 0

    def parse(self, text: str) -> Song:
        """Parse the complete tonic solfa text"""
        lines = text.strip().split('\n')

        # Initialize song with defaults
        for key, value in DEFAULTS.items():
            if key == "TIMESIG":
                self.song.time_sig = (4, 4)
            elif hasattr(self.song, key.lower()):
                setattr(self.song, key.lower(), value)

        # Separate header and content
        content_lines = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                content_lines.append("")
                continue

            # Skip comment lines
            if stripped.startswith('#'):
                continue

            # Check if it's a header property
            header_parsed = False
            for prop in HEADER_STRING_PROPS | HEADER_INT_PROPS | HEADER_SPECIAL_PROPS:
                if stripped.upper().startswith(prop + " ") or stripped.upper() == prop:
                    self._parse_header_line(stripped)
                    header_parsed = True
                    break

            if not header_parsed:
                content_lines.append(line)

        # Parse content blocks
        self._parse_blocks(content_lines)

        return self.song

    def _parse_header_line(self, line: str):
        """Parse a header property line"""
        parts = line.split(None, 1)
        if not parts:
            return

        prop = parts[0].upper()
        value = parts[1] if len(parts) > 1 else ""

        if prop in HEADER_STRING_PROPS:
            attr = prop.lower()
            if hasattr(self.song, attr):
                setattr(self.song, attr, value)
        elif prop in HEADER_INT_PROPS:
            attr = prop.lower()
            try:
                setattr(self.song, attr, int(value))
            except ValueError:
                pass
        elif prop == "TIMESIG":
            if "/" in value:
                num, denom = value.split("/")
                try:
                    self.song.time_sig = (int(num), int(denom))
                except ValueError:
                    pass

    def _parse_blocks(self, lines: List[str]):
        """Parse content into blocks of voice lines and lyrics"""
        current_block_lines = []

        for line in lines:
            stripped = line.strip()

            if not stripped:
                # Empty line might signal end of block
                if current_block_lines:
                    # Check if we have a complete block
                    has_notes = any(self._is_note_line(l) for l in current_block_lines)
                    if has_notes:
                        block = self._parse_single_block(current_block_lines)
                        if block:
                            self.song.blocks.append(block)
                        current_block_lines = []
                continue

            # Skip comment lines
            if stripped.startswith('#'):
                continue

            current_block_lines.append(stripped)

        # Don't forget the last block
        if current_block_lines:
            block = self._parse_single_block(current_block_lines)
            if block:
                self.song.blocks.append(block)

    def _is_note_line(self, line: str) -> bool:
        """Check if a line contains note notation (has barlines)"""
        return BARLINE in line

    def _parse_single_block(self, lines: List[str]) -> Optional[Block]:
        """Parse a single block of voice lines and lyrics"""
        block = Block(measure_start=self.current_measure_num + 1)

        note_lines = []
        lyric_lines = []

        for line in lines:
            if self._is_note_line(line):
                note_lines.append(line)
            else:
                lyric_lines.append(line)

        if not note_lines:
            return None

        # Parse voice lines
        voice_labels_used = []
        for i, note_line in enumerate(note_lines):
            voice_line = self._parse_voice_line(note_line, i, len(note_lines))
            if voice_line:
                block.voice_lines.append(voice_line)
                voice_labels_used.append(voice_line.voice_label)

        # Update measure count
        if block.voice_lines:
            num_measures = len(block.voice_lines[0].measures)
            self.current_measure_num += num_measures

        # Parse lyrics
        for lyric_line in lyric_lines:
            parsed_lyric = self._parse_lyric_line(lyric_line, voice_labels_used)
            if parsed_lyric:
                block.lyric_lines.append(parsed_lyric)

        return block

    def _parse_voice_line(self, line: str, line_index: int, total_lines: int) -> Optional[VoiceLine]:
        """Parse a single voice line with its measures"""
        # Check for explicit voice label at start
        voice_label = None
        notation = line

        # Try to match voice label at start (e.g., "S1 |d:r:m:f|" or "S |d:r:m:f|")
        label_match = re.match(r'^([SATB]\d*|PR|PL)\s+(\|.*)$', line)
        if label_match:
            voice_label = label_match.group(1)
            notation = label_match.group(2)
        else:
            # Implicit label based on line order
            if total_lines <= 4:
                voice_label = DEFAULT_VOICE_ORDER[line_index] if line_index < 4 else f"V{line_index + 1}"
            else:
                voice_label = f"V{line_index + 1}"

        voice_line = VoiceLine(voice_label=voice_label)

        # Parse measures
        measures = self._split_into_measures(notation)

        for m_idx, measure_str in enumerate(measures):
            measure = self._parse_measure(measure_str)
            measure.number = self.current_measure_num + m_idx + 1
            voice_line.measures.append(measure)

        return voice_line

    def _split_into_measures(self, notation: str) -> List[str]:
        """Split notation string into individual measures"""
        # Remove leading/trailing barlines and split
        notation = notation.strip()

        # Handle double barline at end
        if notation.endswith(DOUBLE_BARLINE):
            notation = notation[:-2]

        # Split by single barlines
        parts = notation.split(BARLINE)

        # Filter out empty parts
        measures = [p.strip() for p in parts if p.strip()]

        return measures

    def _parse_measure(self, measure_str: str) -> Measure:
        """Parse a single measure into beats"""
        measure = Measure()

        if not measure_str:
            measure.is_empty = True
            return measure

        # Split into beats by ':'
        beat_strs = measure_str.split(BEAT_SEPARATOR)

        # Check if all beats are empty (whole-measure rest)
        all_empty = all(not b.strip() or b.strip() == "" for b in beat_strs)
        if all_empty:
            measure.is_empty = True
            # Still create empty beats for structure
            for _ in beat_strs:
                measure.beats.append(Beat())
            return measure

        for beat_str in beat_strs:
            beat = self._parse_beat(beat_str)
            measure.beats.append(beat)

        return measure

    def _parse_beat(self, beat_str: str) -> Beat:
        """Parse a single beat, potentially subdivided"""
        beat = Beat()
        beat_str = beat_str.strip()

        if not beat_str:
            # Empty beat = rest
            beat.notes.append(Note(type=NoteType.REST))
            return beat

        # Check for subdivision (one dot splits the beat in half)
        if SUBBEAT_SEPARATOR in beat_str:
            beat.is_subdivided = True
            parts = beat_str.split(SUBBEAT_SEPARATOR, 1)  # Split on first dot only

            # First half
            if parts[0]:
                first_half_notes = self._parse_note_group(parts[0])
                for n in first_half_notes:
                    n.duration_fraction = 0.5 / len(first_half_notes) if first_half_notes else 0.5
                beat.first_half = first_half_notes
            else:
                beat.first_half = [Note(type=NoteType.REST, duration_fraction=0.5)]

            # Second half
            if len(parts) > 1 and parts[1]:
                second_half_notes = self._parse_note_group(parts[1])
                for n in second_half_notes:
                    n.duration_fraction = 0.5 / len(second_half_notes) if second_half_notes else 0.5
                beat.second_half = second_half_notes
            else:
                beat.second_half = [Note(type=NoteType.REST, duration_fraction=0.5)]
        else:
            # No subdivision - parse as note group (could be tuplet)
            notes = self._parse_note_group(beat_str)
            for n in notes:
                n.duration_fraction = 1.0 / len(notes) if notes else 1.0
            beat.notes = notes

        return beat

    def _parse_note_group(self, group_str: str) -> List[Note]:
        """Parse a group of notes (could be single note, hold, rest, or tuplet)"""
        notes = []

        if not group_str:
            return [Note(type=NoteType.REST)]

        # Check for staccato prefix (comma at start after separator)
        is_staccato = False
        if group_str.startswith(STACCATO_PREFIX):
            # Check if this is really staccato or octave modifier
            # Staccato is comma BEFORE the note letter, not after
            # So ",d" is staccato d, but "d," is d octave down
            is_staccato = True
            group_str = group_str[1:]

        # Parse expressions (in parentheses) and check for key change
        expressions = []
        key_change = ""
        while group_str.startswith('('):
            close_idx = group_str.find(')')
            if close_idx > 0:
                expr_content = group_str[1:close_idx]
                # Check if this is a key change (for modulation)
                # Key changes are like (Ab), (C#), (Db), etc.
                if expr_content in VALID_KEYS:
                    key_change = expr_content
                else:
                    expr = self._parse_expression(expr_content)
                    if expr:
                        expressions.append(expr)
                group_str = group_str[close_idx + 1:]
            else:
                break

        # Strip any whitespace after expressions
        group_str = group_str.strip()

        # Check for special cases
        if group_str == HOLD:
            note = Note(type=NoteType.HOLD, expressions=expressions)
            return [note]

        if group_str == REST_STAR:
            note = Note(type=NoteType.REST, expressions=expressions)
            return [note]

        if group_str == REST_DOUBLE_STAR:
            # Two-beat rest - return two rests
            return [Note(type=NoteType.REST), Note(type=NoteType.REST)]

        # Check for chord
        if group_str.startswith(CHORD_OPEN) and CHORD_CLOSE in group_str:
            chord_end = group_str.index(CHORD_CLOSE)
            chord_content = group_str[1:chord_end]
            chord_notes = []
            for note_str in chord_content.split('.'):
                if note_str:
                    n = self._parse_single_note(note_str)
                    if n:
                        chord_notes.append(n)
            note = Note(type=NoteType.CHORD, chord_notes=chord_notes, expressions=expressions)
            return [note]

        # Check for modulation (old_note/new_note)
        if MODULATION_SEPARATOR in group_str:
            parts = group_str.split(MODULATION_SEPARATOR)
            if len(parts) == 2:
                note = Note(
                    type=NoteType.MODULATION,
                    modulation_from=parts[0],
                    modulation_to=parts[1],
                    key_change=key_change,
                    expressions=expressions
                )
                # The modulation_to is also the played note
                played = self._parse_single_note(parts[1])
                if played:
                    note.solfa = played.solfa
                    note.octave_modifier = played.octave_modifier
                return [note]

        # Parse as regular note(s) - could be tuplet like "dms"
        remaining = group_str
        while remaining:
            # Check for melisma prefix
            is_melisma = False
            if remaining.startswith(NOTE_MELISMA_PREFIX):
                is_melisma = True
                remaining = remaining[1:]

            # Try to match a note
            note = self._parse_single_note_from_start(remaining)
            if note:
                note.is_melisma = is_melisma
                if is_staccato and len(notes) == 0:
                    note.is_staccato = True
                if expressions and len(notes) == 0:
                    note.expressions = expressions
                notes.append(note)
                # Consume the matched portion
                consumed = len(note.solfa) + len(note.octave_modifier)
                remaining = remaining[consumed:]
            else:
                # Couldn't parse - skip character
                if remaining:
                    remaining = remaining[1:]

        if not notes:
            return [Note(type=NoteType.REST)]

        return notes

    def _parse_single_note(self, note_str: str) -> Optional[Note]:
        """Parse a single note string completely"""
        note = self._parse_single_note_from_start(note_str)
        return note

    def _parse_single_note_from_start(self, text: str) -> Optional[Note]:
        """Parse a note from the start of text, return Note with solfa and octave_modifier"""
        if not text:
            return None

        # Try to match solfa tokens (longest first)
        matched_solfa = None
        for token in SOLFA_TOKENS_SORTED:
            if text.lower().startswith(token):
                matched_solfa = token
                break

        if not matched_solfa:
            return None

        # Get octave modifiers after the solfa
        remaining = text[len(matched_solfa):]
        octave_mod = ""
        while remaining and remaining[0] in (OCTAVE_UP_CHAR, OCTAVE_DOWN_CHAR):
            octave_mod += remaining[0]
            remaining = remaining[1:]

        return Note(type=NoteType.NOTE, solfa=matched_solfa, octave_modifier=octave_mod)

    def _parse_expression(self, content: str) -> Optional[Expression]:
        """Parse expression content inside parentheses"""
        if content in VALID_DYNAMICS:
            return Expression(type="dynamic", value=content)
        elif content == HAIRPIN_CRESC:
            return Expression(type="hairpin", value="cresc.")
        elif content == HAIRPIN_DIM:
            return Expression(type="hairpin", value="dim.")
        elif content == FERMATA:
            return Expression(type="fermata", value="fermata")
        elif content in NAVIGATION_MARKERS:
            return Expression(type="navigation", value=NAVIGATION_MARKERS[content])
        elif content in TEXT_EXPRESSIONS:
            return Expression(type="text", value=TEXT_EXPRESSIONS[content])
        else:
            # Check for numbered navigation markers (DS1, DS2, S1, S2, DSF1, etc.)
            import re
            # Match patterns like DS1, DS2, S1, S2, DSF1, DSC1, etc.
            match = re.match(r'^(DS|DSF|DSC|SEGNO|S|CODA|C|TC|DC|DCF|DCC|FINE)(\d+)$', content)
            if match:
                base_marker = match.group(1)
                number = match.group(2)
                if base_marker in NAVIGATION_MARKERS:
                    base_text = NAVIGATION_MARKERS[base_marker]
                    # For Segno symbol, append number directly
                    if base_text == SEGNO_SYMBOL:
                        display_text = f"{base_text}{number}"
                    elif base_text == CODA_SYMBOL:
                        display_text = f"{base_text}{number}"
                    else:
                        # For text markers like D.S., append number
                        display_text = f"{base_text} {number}"
                    return Expression(type="navigation", value=display_text)
        return None

    def _parse_lyric_line(self, line: str, available_voices: List[str]) -> Optional[LyricLine]:
        """Parse a lyrics line with optional prefix"""
        line = line.strip()
        if not line:
            return None

        # Patterns to match:
        # "S text..."      - verse 1, soprano
        # "SA text..."     - verse 1, soprano + alto
        # "SAT text..."    - verse 1, soprano + alto + tenor
        # "1SA text..."    - verse 1, soprano + alto
        # "1S1S2 text..."  - verse 1, soprano 1 + soprano 2
        # "RSA text..."    - refrain, soprano + alto
        # "1 text..."      - verse 1, all voices
        # "R text..."      - refrain, all voices
        # "text..."        - no prefix (verse 1, all voices)

        verse = "1"
        voices = list(available_voices) if available_voices else DEFAULT_VOICE_ORDER[:]
        display_prefix = ""
        text = line

        # Try to match prefix before the first space
        match = re.match(r'^(\S+)\s+(.*)$', line)
        if match:
            prefix = match.group(1)
            rest = match.group(2)
            parsed = False

            # Check for verse+voices (e.g. "1SA", "2B", "RS1S2", "1S1S2")
            # or verse only (e.g. "1", "2") or refrain (e.g. "R")
            v_part = ""
            voice_part = ""
            if prefix.startswith('R'):
                v_part = 'R'
                voice_part = prefix[1:]
            elif prefix[0].isdigit():
                # Extract leading digits as verse
                i = 0
                while i < len(prefix) and prefix[i].isdigit():
                    i += 1
                v_part = prefix[:i]
                voice_part = prefix[i:]

            if v_part:
                verse = v_part
                display_prefix = v_part

                if voice_part:
                    parsed_voices = self._parse_voice_labels(voice_part)
                    if parsed_voices:
                        voices = parsed_voices
                        if set(parsed_voices) != set(DEFAULT_VOICE_ORDER[:len(available_voices)]):
                            display_prefix += voice_part

                text = rest
                parsed = True

            # Check for voice-only prefix (e.g. "S", "SA", "SAT", "S1S2")
            if not parsed:
                parsed_voices = self._parse_voice_labels(prefix)
                if parsed_voices:
                    voices = parsed_voices
                    if set(parsed_voices) != set(DEFAULT_VOICE_ORDER[:len(available_voices)]):
                        display_prefix = prefix
                    text = rest
                    parsed = True

            # If prefix wasn't recognized, treat entire line as lyrics text
            if not parsed:
                text = line

        # Parse syllables
        syllables = self._parse_syllables(text)

        if not syllables:
            return None

        return LyricLine(
            verse=verse,
            voices=voices,
            syllables=syllables,
            display_prefix=display_prefix
        )

    def _parse_voice_labels(self, voice_str: str) -> List[str]:
        """Parse concatenated voice labels like 'SA', 'S1S2T' into a list"""
        labels = []
        i = 0
        while i < len(voice_str):
            if voice_str[i] in 'SATB':
                if i + 1 < len(voice_str) and voice_str[i + 1].isdigit():
                    labels.append(voice_str[i:i + 2])
                    i += 2
                else:
                    labels.append(voice_str[i])
                    i += 1
            else:
                break
        # Only valid if we consumed the entire string
        if i == len(voice_str) and labels:
            return labels
        return []

    def _parse_syllables(self, text: str) -> List[str]:
        """Parse lyrics text into syllables"""
        syllables = []

        # Replace joined syllables (^) with a special marker
        text = text.replace(LYRICS_JOIN, " ")

        # Split by spaces and hyphens
        words = text.split()

        for word in words:
            if word == LYRICS_REST_SKIP:
                syllables.append("*")
            elif LYRICS_HYPHEN in word:
                # Split hyphenated word
                parts = word.split(LYRICS_HYPHEN)
                for i, part in enumerate(parts):
                    if part:
                        if i < len(parts) - 1:
                            syllables.append(part + "-")
                        else:
                            syllables.append(part)
            else:
                syllables.append(word)

        return syllables
