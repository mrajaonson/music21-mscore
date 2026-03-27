from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.units import mm, cm
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from config import *
from s2p_data_structures import (Song)
from datetime import datetime
from typing import List, Dict, Tuple
from s2p_data_structures import (NoteType, Measure, Beat, Note)

class TonicSolfaPDFRenderer:
    """Renders a parsed Song to PDF in traditional hymnal style"""

    def __init__(self, song: Song, output_path: str):
        self.song = song
        self.output_path = output_path

        # Page settings
        self.page_size = A4
        self.page_width, self.page_height = self.page_size
        self.margin_left = 15 * mm
        self.margin_right = 15 * mm
        self.margin_top = 20 * mm
        self.margin_bottom = 20 * mm

        # Content area
        self.content_width = self.page_width - self.margin_left - self.margin_right
        self.content_height = self.page_height - self.margin_top - self.margin_bottom

        # Font settings
        self.title_font_size = 14
        self.subtitle_font_size = 10
        self.header_font_size = 9
        self.note_font_size = 9
        self.lyric_font_size = 8
        self.small_font_size = 7

        # Layout settings
        self.voice_row_height = 12  # Height per voice row
        self.lyric_row_height = 9  # Height per lyric row (reduced from 10)
        self.block_spacing = 12  # Space between blocks (increased from 6)
        self.lyric_top_margin = 6  # Space above lyrics (increased)
        self.lyric_bottom_margin = 2  # Space below lyrics (reduced)
        self.measure_padding = 2  # Padding inside measure cells

        # Calculate measures per line based on time signature
        beats_per_measure = song.time_sig[0]
        if beats_per_measure <= 3:
            self.measures_per_line = 5
        elif beats_per_measure <= 4:
            self.measures_per_line = 4
        else:
            self.measures_per_line = 3

        # Track state
        self.current_page = 1
        self.y_position = self.page_height - self.margin_top

    def render(self):
        """Render the complete PDF"""
        self.c = canvas.Canvas(self.output_path, pagesize=self.page_size)

        # Draw first page header
        self._draw_page_header()

        # Draw song header (title, composer, etc.)
        self._draw_song_header()

        # Draw all blocks
        self._draw_all_blocks()

        # Draw footer on last page
        self._draw_page_footer()

        self.c.save()

    def _draw_page_header(self):
        """Draw page header with measure numbers indicator"""
        pass  # Header info is in song header for first page

    def _draw_page_footer(self):
        """Draw page footer with page number and generation date"""
        self.c.setFont("Helvetica", self.small_font_size)

        # Page number
        page_text = f"Page {self.current_page}"
        self.c.drawCentredString(self.page_width / 2, self.margin_bottom - 8 * mm, page_text)

        # Generation date
        date_text = f"Generated on {datetime.now().strftime('%Y-%m-%d')}"
        self.c.drawRightString(self.page_width - self.margin_right, self.margin_bottom - 8 * mm, date_text)

    def _new_page(self):
        """Start a new page"""
        self._draw_page_footer()
        self.c.showPage()
        self.current_page += 1
        self.y_position = self.page_height - self.margin_top

        # Draw key/time signature reminder at top of new page
        self.c.setFont("Helvetica", self.small_font_size)
        reminder = f"{self.song.title}  —  Key: {self.song.key}    Time: {self.song.time_sig[0]}/{self.song.time_sig[1]}"
        self.c.drawString(self.margin_left, self.y_position, reminder)
        self.y_position -= 10

    def _check_page_space(self, needed_height: float) -> bool:
        """Check if there's enough space on current page, start new page if not"""
        if self.y_position - needed_height < self.margin_bottom + 12 * mm:
            self._new_page()
            return True
        return False

    def _draw_song_header(self):
        """Draw the song header (title, composer, key, etc.)"""
        # Title
        if self.song.title:
            self.c.setFont("Helvetica-Bold", self.title_font_size)
            self.c.drawCentredString(self.page_width / 2, self.y_position, self.song.title)
            self.y_position -= self.title_font_size + 3

        # Composer/Author
        if self.song.composer or self.song.author:
            self.c.setFont("Helvetica-Oblique", self.subtitle_font_size)
            text = self.song.composer if self.song.composer else self.song.author
            self.c.drawCentredString(self.page_width / 2, self.y_position, text)
            self.y_position -= self.subtitle_font_size + 3

        # Comments (e.g., scripture reference)
        if self.song.comments:
            self.c.setFont("Helvetica-Oblique", self.small_font_size)
            self.c.drawCentredString(self.page_width / 2, self.y_position, self.song.comments)
            self.y_position -= self.small_font_size + 3

        # Key, Tempo, Time Signature line
        self.c.setFont("Helvetica", self.header_font_size)
        info_parts = []
        info_parts.append(f"Key: {self.song.key}")
        info_parts.append(f"Time: {self.song.time_sig[0]}/{self.song.time_sig[1]}")
        if self.song.tempo:
            info_parts.append(f"Tempo: {self.song.tempo}")

        info_text = "    ".join(info_parts)
        self.c.drawString(self.margin_left, self.y_position, info_text)
        self.y_position -= self.header_font_size + 8

    def _draw_all_blocks(self):
        """Draw all blocks of the song"""
        # Collect all measures across all voices
        all_voice_data = {}  # voice_label -> list of all measures

        for block in self.song.blocks:
            for voice_line in block.voice_lines:
                if voice_line.voice_label not in all_voice_data:
                    all_voice_data[voice_line.voice_label] = []
                all_voice_data[voice_line.voice_label].extend(voice_line.measures)

        # Determine voice order
        voice_order = []
        for v in DEFAULT_VOICE_ORDER:
            if v in all_voice_data:
                voice_order.append(v)
        # Add any other voices
        for v in all_voice_data:
            if v not in voice_order:
                voice_order.append(v)

        if not voice_order:
            return

        total_measures = max(len(all_voice_data[v]) for v in voice_order)

        # Collect lyrics per block
        block_lyrics = []
        measure_offset = 0
        for block in self.song.blocks:
            if block.voice_lines:
                num_measures = len(block.voice_lines[0].measures)
                block_lyrics.append({
                    'start': measure_offset,
                    'end': measure_offset + num_measures,
                    'lyrics': block.lyric_lines
                })
                measure_offset += num_measures

        # Draw measures in groups (lines)
        measure_idx = 0
        while measure_idx < total_measures:
            end_idx = min(measure_idx + self.measures_per_line, total_measures)

            # Skip lines of entirely empty measures at the end
            all_empty = True
            for v in voice_order:
                measures = all_voice_data.get(v, [])
                for m_idx in range(measure_idx, min(end_idx, len(measures))):
                    if not measures[m_idx].is_empty:
                        all_empty = False
                        break
                if not all_empty:
                    break

            # Check if there are any lyrics for these measures
            has_lyrics = False
            for bl in block_lyrics:
                if bl['start'] < end_idx and bl['end'] > measure_idx and bl['lyrics']:
                    has_lyrics = True
                    break

            if all_empty and not has_lyrics and measure_idx > 0:
                # Skip drawing empty measure lines
                measure_idx = end_idx
                continue

            # Calculate height needed for this line
            num_voices = len(voice_order)
            line_height = (num_voices * self.voice_row_height +
                           2 * self.lyric_row_height +  # Space for lyrics
                           self.block_spacing)

            self._check_page_space(line_height)

            # Draw this group of measures
            self._draw_measure_group(
                all_voice_data, voice_order,
                measure_idx, end_idx,
                block_lyrics
            )

            measure_idx = end_idx

    def _draw_measure_group(self, all_voice_data: Dict, voice_order: List[str],
                            start_idx: int, end_idx: int, block_lyrics: List[Dict]):
        """Draw a group of measures (one line of the score) with lyrics under target voices"""
        num_measures = end_idx - start_idx

        # Check if we have all 4 standard SATB voices - if so, don't show labels
        show_voice_labels = not (set(voice_order) == set(DEFAULT_VOICE_ORDER) and len(voice_order) == 4)

        # Calculate column widths
        voice_label_width = 8 * mm if show_voice_labels else 0
        available_width = self.content_width - voice_label_width
        measure_width = available_width / num_measures

        # Starting position
        start_x = self.margin_left
        start_y = self.y_position

        # Collect navigation markers from all voices for these measures
        nav_markers = self._collect_navigation_markers(all_voice_data, voice_order, start_idx, end_idx)

        # If there are navigation markers, reserve space at the top for them
        if nav_markers:
            # Draw navigation markers at the very top
            self._draw_navigation_markers(nav_markers, start_x, start_y, voice_label_width, measure_width, start_idx)
            start_y -= 12  # Add space below navigation markers for measure numbers

        # Collect fermatas from first voice only
        fermatas = self._collect_fermatas(all_voice_data, voice_order, start_idx, end_idx)

        # If there are fermatas, reserve space and draw them
        if fermatas:
            self._draw_fermatas(fermatas, start_x, start_y, voice_label_width, measure_width, start_idx)
            start_y -= 10  # Add space below fermatas

        # Collect key changes from all voices for these measures
        key_changes = self._collect_key_changes(all_voice_data, voice_order, start_idx, end_idx)

        # If there are key changes, reserve space and draw them
        if key_changes:
            self._draw_key_changes(key_changes, start_x, start_y, voice_label_width, measure_width, start_idx)
            start_y -= 10  # Add space below key changes

        # Draw measure numbers above first voice
        self.c.setFont("Helvetica", self.small_font_size)
        self.c.setFillColor(colors.Color(0.4, 0.4, 0.4))
        x = start_x + voice_label_width
        for m_idx in range(start_idx, end_idx):
            measure_num = m_idx + 1
            self.c.drawString(x + 1, start_y + 1, str(measure_num))
            x += measure_width
        self.c.setFillColor(colors.black)
        start_y -= 2

        # Organize lyrics by their target voice (last voice in prefix)
        lyrics_by_target_voice = self._organize_lyrics_by_target_voice(block_lyrics, start_idx, end_idx, voice_order)

        # Draw each voice with its lyrics underneath
        y = start_y
        for voice_idx, voice_label in enumerate(voice_order):
            measures = all_voice_data.get(voice_label, [])

            # Draw voice label only if not standard SATB
            if show_voice_labels:
                self.c.setFont("Helvetica-Bold", self.note_font_size)
                self.c.drawString(start_x, y - self.voice_row_height + 3, voice_label)

            # Draw barline at start
            x = start_x + voice_label_width
            self.c.setStrokeColor(colors.black)
            self.c.setLineWidth(0.5)
            self.c.line(x, y, x, y - self.voice_row_height)

            # Draw measures for this voice
            for m_idx in range(start_idx, end_idx):
                if m_idx < len(measures):
                    measure = measures[m_idx]
                    self._draw_measure_content(measure, x, y, measure_width, self.voice_row_height)

                # Draw barline after measure
                x += measure_width

                # Check if this is the last measure of the piece
                is_last_measure = (m_idx == len(measures) - 1) or (m_idx == end_idx - 1 and end_idx >= len(measures))

                if is_last_measure and m_idx == len(measures) - 1:
                    # Double barline at end
                    self.c.setLineWidth(0.5)
                    self.c.line(x - 2, y, x - 2, y - self.voice_row_height)
                    self.c.setLineWidth(1.5)
                    self.c.line(x, y, x, y - self.voice_row_height)
                    self.c.setLineWidth(0.5)
                else:
                    self.c.line(x, y, x, y - self.voice_row_height)

            y -= self.voice_row_height

            # Draw lyrics for this voice if any
            if voice_label in lyrics_by_target_voice:
                for lyric_info in lyrics_by_target_voice[voice_label]:
                    self._draw_single_lyric_line(start_x, y, voice_label_width, measure_width,
                                                 start_idx, end_idx, lyric_info, all_voice_data, voice_order)
                    y -= (self.lyric_row_height + self.lyric_bottom_margin)

        # Update y position with block spacing
        self.y_position = y - self.block_spacing

    def _organize_lyrics_by_target_voice(self, block_lyrics: List[Dict], start_idx: int,
                                         end_idx: int, voice_order: List[str]) -> Dict[str, List]:
        """Organize lyrics by their target voice (last voice in prefix)"""
        result = {}

        for bl in block_lyrics:
            if bl['start'] < end_idx and bl['end'] > start_idx:
                for lyric in bl['lyrics']:
                    # Determine target voice (last voice in the prefix)
                    target_voice = self._get_target_voice(lyric.voices, voice_order)

                    if target_voice not in result:
                        result[target_voice] = []

                    result[target_voice].append({
                        'lyric': lyric,
                        'block_start': bl['start'],
                        'block_end': bl['end']
                    })

        return result

    def _get_target_voice(self, voices: List[str], voice_order: List[str]) -> str:
        """Get the last voice from the voices list (where lyrics should be placed)"""
        if not voices:
            # No prefix means all voices, so put under the last voice (B)
            return voice_order[-1] if voice_order else "B"

        # Find the last voice in the voices list that exists in voice_order
        for v in reversed(voices):
            if v in voice_order:
                return v

        # Fallback to last voice in voice_order
        return voice_order[-1] if voice_order else "B"

    def _collect_key_changes(self, all_voice_data: Dict, voice_order: List[str],
                             start_idx: int, end_idx: int) -> List[Dict]:
        """Collect key changes from the first voice (key changes appear only on first voice line)"""
        key_changes = []
        seen = set()

        if not voice_order:
            return key_changes

        # Only check first voice for key changes
        first_voice = voice_order[0]
        measures = all_voice_data.get(first_voice, [])

        for m_idx in range(start_idx, min(end_idx, len(measures))):
            measure = measures[m_idx]
            num_beats = len(measure.beats)
            beat_width_fraction = 1.0 / num_beats if num_beats > 0 else 1.0

            for beat_idx, beat in enumerate(measure.beats):
                all_notes = beat.all_notes()

                for note_idx, note in enumerate(all_notes):
                    if note.type == NoteType.MODULATION and note.key_change:
                        pos = beat_idx * beat_width_fraction
                        key = (m_idx, round(pos, 3))
                        if key not in seen:
                            seen.add(key)
                            key_changes.append({
                                'measure': m_idx,
                                'position': pos,
                                'key': note.key_change
                            })

        return key_changes

    def _draw_key_changes(self, key_changes: List[Dict], start_x: float, start_y: float,
                          label_width: float, measure_width: float, start_idx: int):
        """Draw key changes above the staff"""
        self.c.setFont("Helvetica-Bold", self.small_font_size + 2)
        self.c.setFillColor(colors.black)

        for kc in key_changes:
            rel_m = kc['measure'] - start_idx
            x = start_x + label_width + rel_m * measure_width + kc['position'] * measure_width

            text = kc['key']
            text_width = self.c.stringWidth(text, "Helvetica-Bold", self.small_font_size + 2)
            draw_x = x

            self.c.drawString(draw_x, start_y + 2, text)

    def _collect_fermatas(self, all_voice_data: Dict, voice_order: List[str],
                          start_idx: int, end_idx: int) -> List[Dict]:
        """Collect fermatas from the first voice only"""
        fermatas = []
        seen = set()

        if not voice_order:
            return fermatas

        # Only check first voice for fermatas
        first_voice = voice_order[0]
        measures = all_voice_data.get(first_voice, [])

        for m_idx in range(start_idx, min(end_idx, len(measures))):
            measure = measures[m_idx]
            num_beats = len(measure.beats)
            beat_width_fraction = 1.0 / num_beats if num_beats > 0 else 1.0

            for beat_idx, beat in enumerate(measure.beats):
                all_notes = beat.all_notes()
                num_notes = len(all_notes)

                for note_idx, note in enumerate(all_notes):
                    for expr in note.expressions:
                        if expr.type == "fermata":
                            # Calculate position within measure
                            if beat.is_subdivided:
                                if note in beat.first_half:
                                    half_idx = beat.first_half.index(note)
                                    half_notes = len(beat.first_half)
                                    pos = beat_idx * beat_width_fraction + (
                                                half_idx / half_notes) * beat_width_fraction * 0.5
                                else:
                                    half_idx = beat.second_half.index(note) if note in beat.second_half else 0
                                    half_notes = len(beat.second_half)
                                    pos = beat_idx * beat_width_fraction + 0.5 * beat_width_fraction + (
                                                half_idx / half_notes) * beat_width_fraction * 0.5
                            else:
                                pos = beat_idx * beat_width_fraction + (
                                            note_idx / num_notes) * beat_width_fraction if num_notes > 0 else beat_idx * beat_width_fraction

                            key = (m_idx, round(pos, 3))
                            if key not in seen:
                                seen.add(key)
                                fermatas.append({
                                    'measure': m_idx,
                                    'position': pos
                                })

        return fermatas

    def _draw_fermatas(self, fermatas: List[Dict], start_x: float, start_y: float,
                       label_width: float, measure_width: float, start_idx: int):
        """Draw fermata symbols above the staff"""
        # Use FreeSerif for the fermata symbol
        self.c.setFont(MUSIC_SYMBOL_FONT, self.small_font_size + 6)
        self.c.setFillColor(colors.black)

        for fermata in fermatas:
            rel_m = fermata['measure'] - start_idx
            x = start_x + label_width + rel_m * measure_width + fermata['position'] * measure_width

            text = FERMATA_SYMBOL
            text_width = self.c.stringWidth(text, MUSIC_SYMBOL_FONT, self.small_font_size + 6)
            draw_x = x - text_width / 2  # Center the fermata

            self.c.drawString(draw_x, start_y + 2, text)

    def _collect_navigation_markers(self, all_voice_data: Dict, voice_order: List[str],
                                    start_idx: int, end_idx: int) -> List[Dict]:
        """Collect all navigation markers from all voices for the given measure range"""
        markers = []
        seen = set()  # Avoid duplicates (same marker at same position)

        for voice_label in voice_order:
            measures = all_voice_data.get(voice_label, [])
            for m_idx in range(start_idx, min(end_idx, len(measures))):
                measure = measures[m_idx]
                num_beats = len(measure.beats)
                beat_width_fraction = 1.0 / num_beats if num_beats > 0 else 1.0

                for beat_idx, beat in enumerate(measure.beats):
                    all_notes = beat.all_notes()
                    num_notes = len(all_notes)

                    for note_idx, note in enumerate(all_notes):
                        for expr in note.expressions:
                            if expr.type == "navigation":
                                # Calculate position within measure (0.0 to 1.0)
                                if beat.is_subdivided:
                                    if note in beat.first_half:
                                        half_idx = beat.first_half.index(note)
                                        half_notes = len(beat.first_half)
                                        pos = beat_idx * beat_width_fraction + (
                                                    half_idx / half_notes) * beat_width_fraction * 0.5
                                    else:
                                        half_idx = beat.second_half.index(note) if note in beat.second_half else 0
                                        half_notes = len(beat.second_half)
                                        pos = beat_idx * beat_width_fraction + 0.5 * beat_width_fraction + (
                                                    half_idx / half_notes) * beat_width_fraction * 0.5
                                else:
                                    pos = beat_idx * beat_width_fraction + (note_idx / num_notes) * beat_width_fraction

                                key = (m_idx, round(pos, 3), expr.value)
                                if key not in seen:
                                    seen.add(key)
                                    markers.append({
                                        'measure': m_idx,
                                        'position': pos,
                                        'text': expr.value
                                    })

        return markers

    def _draw_navigation_markers(self, markers: List[Dict], start_x: float, start_y: float,
                                 label_width: float, measure_width: float, start_idx: int):
        """Draw navigation markers above the staff (above measure numbers)"""
        self.c.setFillColor(colors.black)

        for marker in markers:
            rel_m = marker['measure'] - start_idx
            # Calculate x position
            x = start_x + label_width + rel_m * measure_width + marker['position'] * measure_width

            text = marker['text']

            # Check if this contains a musical symbol (Coda or Segno), possibly with number
            contains_music_symbol = CODA_SYMBOL in text or SEGNO_SYMBOL in text

            if contains_music_symbol:
                # Use FreeSerif font with bigger size for musical symbols
                font_name = MUSIC_SYMBOL_FONT
                font_size = self.small_font_size + 6  # Bigger for symbols
            else:
                # Use Helvetica-Bold for text markers
                font_name = "Helvetica-Bold"
                font_size = self.small_font_size + 1

            self.c.setFont(font_name, font_size)
            text_width = self.c.stringWidth(text, font_name, font_size)

            # Center the marker above the beat
            draw_x = x - text_width / 2

            # Draw above measure numbers (start_y + offset)
            # Navigation markers should be at the very top
            draw_y = start_y + 2
            self.c.drawString(draw_x, draw_y, text)

    def _draw_measure_content(self, measure: Measure, x: float, y: float,
                              width: float, height: float):
        """Draw the content of a single measure"""
        if measure.is_empty:
            # Draw empty measure with just beat separators
            num_beats = len(measure.beats) if measure.beats else 4
            beat_width = width / num_beats
            self.c.setFont("Helvetica", self.note_font_size)
            text_y = y - height + 3
            for beat_idx in range(num_beats - 1):
                sep_x = x + (beat_idx + 1) * beat_width
                self.c.drawCentredString(sep_x, text_y, ":")
            return

        # Calculate beat positions
        num_beats = len(measure.beats)
        if num_beats == 0:
            return

        beat_width = width / num_beats

        # Draw each beat and collect melisma positions
        self.c.setFont("Helvetica", self.note_font_size)
        text_y = y - height + 3
        underline_y = text_y - 2

        # Collect melisma ranges across beats
        melisma_ranges = []  # List of (start_x, end_x) tuples
        current_melisma_start = None
        current_melisma_end = None

        for beat_idx, beat in enumerate(measure.beats):
            beat_x = x + beat_idx * beat_width

            # Draw beat content and get melisma info
            beat_melisma_info = self._draw_beat_content_with_positions(beat, beat_x, y, beat_width, height)

            if beat_melisma_info['has_melisma']:
                if current_melisma_start is None:
                    current_melisma_start = beat_melisma_info['start_x']
                current_melisma_end = beat_melisma_info['end_x']
            else:
                # No melisma in this beat - close any open range
                if current_melisma_start is not None:
                    melisma_ranges.append((current_melisma_start, current_melisma_end))
                    current_melisma_start = None
                    current_melisma_end = None

            # Draw ":" beat separator between beats
            if beat_idx < num_beats - 1:
                sep_x = beat_x + beat_width
                self.c.drawCentredString(sep_x, text_y, ":")

        # Close any remaining melisma range
        if current_melisma_start is not None:
            melisma_ranges.append((current_melisma_start, current_melisma_end))

        # Draw all melisma underlines (continuous across beats)
        for start_x, end_x in melisma_ranges:
            self._draw_melisma_underline(start_x, underline_y, end_x - start_x)

    def _draw_beat_content_with_positions(self, beat: Beat, x: float, y: float,
                                          width: float, height: float) -> Dict:
        """Draw the content of a single beat and return melisma position info"""
        self.c.setFont("Helvetica", self.note_font_size)

        text_y = y - height + 3
        above_y = y + 2  # Position for key change above the note line

        result = {
            'has_melisma': False,
            'start_x': None,
            'end_x': None,
            'key_changes': []  # List of (x, key) for drawing above
        }

        if beat.is_subdivided:
            # Draw first half and second half with dot separator
            half_width = width / 2

            # Check if any note in either half has melisma
            first_text, first_has_melisma, first_mods = self._notes_to_display_text_with_melisma(beat.first_half)
            second_text, second_has_melisma, second_mods = self._notes_to_display_text_with_melisma(beat.second_half)

            # First half
            first_draw_x = None
            first_text_width = 0
            if first_text:
                first_text_width = self._calc_text_width_with_mods(first_text, first_mods)
                first_draw_x = x + (half_width - first_text_width) / 2
                self._draw_text_with_modulation(first_text, first_mods, first_draw_x, text_y, x, above_y)
                # Collect key changes
                for mod in first_mods:
                    if mod.get('key_change'):
                        result['key_changes'].append((first_draw_x, mod['key_change']))

            # Dot separator - draw centered
            dot_x = x + half_width - 1
            dot_width = self.c.stringWidth(".", "Helvetica", self.note_font_size)
            self.c.setFont("Helvetica", self.note_font_size)
            self.c.drawString(dot_x, text_y, ".")

            # Second half
            second_draw_x = None
            second_text_width = 0
            if second_text:
                second_text_width = self._calc_text_width_with_mods(second_text, second_mods)
                second_draw_x = x + half_width + (half_width - second_text_width) / 2
                self._draw_text_with_modulation(second_text, second_mods, second_draw_x, text_y, x + half_width,
                                                above_y)
                # Collect key changes
                for mod in second_mods:
                    if mod.get('key_change'):
                        result['key_changes'].append((second_draw_x, mod['key_change']))

            # Calculate melisma range for this beat
            if first_has_melisma or second_has_melisma:
                result['has_melisma'] = True
                # Start from first text or dot
                if first_draw_x is not None:
                    result['start_x'] = first_draw_x
                else:
                    result['start_x'] = dot_x
                # End at second text end or dot end
                if second_draw_x is not None:
                    result['end_x'] = second_draw_x + second_text_width
                elif first_draw_x is not None:
                    result['end_x'] = first_draw_x + first_text_width
                else:
                    result['end_x'] = dot_x + dot_width
        else:
            # Single group of notes (or tuplet)
            text, has_melisma, mods = self._notes_to_display_text_with_melisma(beat.notes)
            if text:
                # Center the text in the beat
                text_width = self._calc_text_width_with_mods(text, mods)
                draw_x = x + (width - text_width) / 2
                self._draw_text_with_modulation(text, mods, draw_x, text_y, x, above_y)

                # Collect key changes
                for mod in mods:
                    if mod.get('key_change'):
                        result['key_changes'].append((draw_x, mod['key_change']))

                if has_melisma:
                    result['has_melisma'] = True
                    result['start_x'] = draw_x
                    result['end_x'] = draw_x + text_width

        return result

    def _calc_text_width_with_mods(self, text: str, modulations: List[Dict]) -> float:
        """Calculate total width of text including modulation superscripts"""
        if not modulations:
            return self.c.stringWidth(text, "Helvetica", self.note_font_size)

        total_width = 0
        superscript_size = self.note_font_size - 1

        # Add width of superscripts
        for mod in modulations:
            old_note_width = self.c.stringWidth(mod['old_note'], "Helvetica", superscript_size)
            total_width += old_note_width

        # Add width of main text
        total_width += self.c.stringWidth(text, "Helvetica", self.note_font_size)

        return total_width

    def _draw_melisma_underline(self, x: float, y: float, width: float):
        """Draw underline for melisma notes"""
        self.c.setStrokeColor(colors.black)
        self.c.setLineWidth(0.5)
        self.c.line(x, y, x + width, y)

    def _notes_to_display_text_with_melisma(self, notes: List[Note]) -> Tuple[str, bool, List[Dict]]:
        """Convert notes to display text, indicate if any are melisma, and return modulation info"""
        parts = []
        has_melisma = False
        modulations = []  # List of {old_note, position} for superscript rendering

        for note in notes:
            # Track melisma
            if note.is_melisma:
                has_melisma = True

            # Add expression markers EXCEPT navigation and fermata (those go above the staff)
            for expr in note.expressions:
                if expr.type == "dynamic":
                    parts.append(f"({expr.value})")
                elif expr.type == "hairpin":
                    if "cresc" in expr.value.lower():
                        parts.append("(<)")
                    else:
                        parts.append("(>)")
                # Skip navigation markers and fermata - they are drawn above the staff

            # Track modulation for superscript rendering
            if note.type == NoteType.MODULATION and note.modulation_from:
                modulations.append({
                    'old_note': note.modulation_from,
                    'position': len("".join(parts)),  # Position before the new note
                    'key_change': note.key_change
                })

            parts.append(note.display_text())

        return "".join(parts), has_melisma, modulations

    def _draw_text_with_modulation(self, text: str, modulations: List[Dict],
                                   x: float, y: float, beat_x: float, above_y: float):
        """Draw text with modulation superscripts (key changes are drawn separately above measure numbers)"""
        if not modulations:
            # Simple case - just draw the text
            self.c.setFont("Helvetica", self.note_font_size)
            self.c.drawString(x, y, text)
            return

        # Draw with modulation superscripts
        self.c.setFont("Helvetica", self.note_font_size)
        current_x = x
        text_idx = 0

        for mod in modulations:
            # Draw text before this modulation
            if mod['position'] > text_idx:
                pre_text = text[text_idx:mod['position']]
                self.c.setFont("Helvetica", self.note_font_size)
                self.c.drawString(current_x, y, pre_text)
                current_x += self.c.stringWidth(pre_text, "Helvetica", self.note_font_size)
                text_idx = mod['position']

            # Key change is drawn separately by _draw_key_changes above measure numbers
            # So we don't draw it here anymore

            # Draw old_note as superscript (slightly bigger than typical superscript)
            superscript_size = self.note_font_size - 1  # Only 1pt smaller for readability
            self.c.setFont("Helvetica", superscript_size)
            old_note_text = mod['old_note']
            self.c.drawString(current_x, y + 4, old_note_text)  # Raised position
            current_x += self.c.stringWidth(old_note_text, "Helvetica", superscript_size)

        # Draw remaining text
        if text_idx < len(text):
            remaining = text[text_idx:]
            self.c.setFont("Helvetica", self.note_font_size)
            self.c.drawString(current_x, y, remaining)

    def _short_nav(self, nav_text: str) -> str:
        """Get short form of navigation marker for display"""
        reverse_map = {v: k for k, v in NAVIGATION_MARKERS.items()}
        return reverse_map.get(nav_text, nav_text)

    def _draw_lyrics_for_measures(self, start_x: float, y: float,
                                  label_width: float, measure_width: float,
                                  start_idx: int, end_idx: int,
                                  block_lyrics: List[Dict],
                                  all_voice_data: Dict, voice_order: List[str]):
        """Draw lyrics aligned under the measures - NO barlines in lyrics area"""
        # Find lyrics that apply to these measures
        relevant_lyrics = []
        for bl in block_lyrics:
            if bl['start'] < end_idx and bl['end'] > start_idx:
                for lyric in bl['lyrics']:
                    relevant_lyrics.append({
                        'lyric': lyric,
                        'block_start': bl['start'],
                        'block_end': bl['end']
                    })

        if not relevant_lyrics:
            return

        # Get reference voice for note positions (usually Soprano)
        ref_voice = voice_order[0] if voice_order else "S"
        ref_measures = all_voice_data.get(ref_voice, [])

        # More space between notes and lyrics
        lyric_y = y - 6

        # Collect syllable positions
        all_syllable_positions = []

        for rl in relevant_lyrics:
            lyric = rl['lyric']
            syllable_idx = 0
            block_start = rl['block_start']

            for m_offset in range(rl['block_end'] - rl['block_start']):
                m_idx = block_start + m_offset
                if m_idx >= len(ref_measures):
                    continue
                if m_idx < start_idx or m_idx >= end_idx:
                    # Count syllables for measures not being displayed
                    measure = ref_measures[m_idx]
                    for beat in measure.beats:
                        for note in beat.all_notes():
                            if note.type == NoteType.NOTE and not note.is_melisma:
                                syllable_idx += 1
                            elif note.type == NoteType.MODULATION:
                                syllable_idx += 1
                    continue

                measure = ref_measures[m_idx]
                num_beats = len(measure.beats)
                beat_width = measure_width / num_beats if num_beats > 0 else measure_width

                for beat_idx, beat in enumerate(measure.beats):
                    all_notes = beat.all_notes()
                    num_notes_in_beat = len(all_notes)

                    # Calculate positions for notes in this beat
                    if beat.is_subdivided:
                        first_half_notes = beat.first_half
                        second_half_notes = beat.second_half
                        half_width = beat_width / 2

                        # First half notes
                        for note_idx, note in enumerate(first_half_notes):
                            if note.type == NoteType.NOTE and not note.is_melisma:
                                if syllable_idx < len(lyric.syllables):
                                    syl = lyric.syllables[syllable_idx]
                                    if syl != "*":
                                        rel_m = m_idx - start_idx
                                        # Center within first half
                                        note_width = half_width / len(
                                            first_half_notes) if first_half_notes else half_width
                                        note_center_x = (start_x + label_width +
                                                         rel_m * measure_width +
                                                         beat_idx * beat_width +
                                                         note_idx * note_width +
                                                         note_width / 2)
                                        all_syllable_positions.append({
                                            'text': syl,
                                            'center_x': note_center_x,
                                            'prefix': lyric.display_prefix
                                        })
                                    syllable_idx += 1
                            elif note.type == NoteType.MODULATION:
                                if syllable_idx < len(lyric.syllables):
                                    syl = lyric.syllables[syllable_idx]
                                    if syl != "*":
                                        rel_m = m_idx - start_idx
                                        note_width = half_width / len(
                                            first_half_notes) if first_half_notes else half_width
                                        note_center_x = (start_x + label_width +
                                                         rel_m * measure_width +
                                                         beat_idx * beat_width +
                                                         note_idx * note_width +
                                                         note_width / 2)
                                        all_syllable_positions.append({
                                            'text': syl,
                                            'center_x': note_center_x,
                                            'prefix': lyric.display_prefix
                                        })
                                    syllable_idx += 1

                        # Second half notes
                        for note_idx, note in enumerate(second_half_notes):
                            if note.type == NoteType.NOTE and not note.is_melisma:
                                if syllable_idx < len(lyric.syllables):
                                    syl = lyric.syllables[syllable_idx]
                                    if syl != "*":
                                        rel_m = m_idx - start_idx
                                        note_width = half_width / len(
                                            second_half_notes) if second_half_notes else half_width
                                        note_center_x = (start_x + label_width +
                                                         rel_m * measure_width +
                                                         beat_idx * beat_width +
                                                         half_width +  # offset for second half
                                                         note_idx * note_width +
                                                         note_width / 2)
                                        all_syllable_positions.append({
                                            'text': syl,
                                            'center_x': note_center_x,
                                            'prefix': lyric.display_prefix
                                        })
                                    syllable_idx += 1
                            elif note.type == NoteType.MODULATION:
                                if syllable_idx < len(lyric.syllables):
                                    syl = lyric.syllables[syllable_idx]
                                    if syl != "*":
                                        rel_m = m_idx - start_idx
                                        note_width = half_width / len(
                                            second_half_notes) if second_half_notes else half_width
                                        note_center_x = (start_x + label_width +
                                                         rel_m * measure_width +
                                                         beat_idx * beat_width +
                                                         half_width +
                                                         note_idx * note_width +
                                                         note_width / 2)
                                        all_syllable_positions.append({
                                            'text': syl,
                                            'center_x': note_center_x,
                                            'prefix': lyric.display_prefix
                                        })
                                    syllable_idx += 1
                    else:
                        # Non-subdivided beat
                        for note_idx, note in enumerate(all_notes):
                            if note.type == NoteType.NOTE and not note.is_melisma:
                                if syllable_idx < len(lyric.syllables):
                                    syl = lyric.syllables[syllable_idx]
                                    if syl != "*":
                                        rel_m = m_idx - start_idx
                                        # Center within this note's portion of the beat
                                        note_width = beat_width / num_notes_in_beat
                                        note_center_x = (start_x + label_width +
                                                         rel_m * measure_width +
                                                         beat_idx * beat_width +
                                                         note_idx * note_width +
                                                         note_width / 2)
                                        all_syllable_positions.append({
                                            'text': syl,
                                            'center_x': note_center_x,
                                            'prefix': lyric.display_prefix
                                        })
                                    syllable_idx += 1
                            elif note.type == NoteType.MODULATION:
                                if syllable_idx < len(lyric.syllables):
                                    syl = lyric.syllables[syllable_idx]
                                    if syl != "*":
                                        rel_m = m_idx - start_idx
                                        note_width = beat_width / num_notes_in_beat
                                        note_center_x = (start_x + label_width +
                                                         rel_m * measure_width +
                                                         beat_idx * beat_width +
                                                         note_idx * note_width +
                                                         note_width / 2)
                                        all_syllable_positions.append({
                                            'text': syl,
                                            'center_x': note_center_x,
                                            'prefix': lyric.display_prefix
                                        })
                                    syllable_idx += 1

        if not all_syllable_positions:
            return

        # Draw syllables centered under their notes
        self.c.setFont("Helvetica", self.lyric_font_size)

        for syl_info in all_syllable_positions:
            text = syl_info['text']
            center_x = syl_info['center_x']

            # Center the syllable text
            text_width = self.c.stringWidth(text, "Helvetica", self.lyric_font_size)
            draw_x = center_x - text_width / 2

            self.c.drawString(draw_x, lyric_y, text)

    def _draw_single_lyric_line(self, start_x: float, y: float,
                                label_width: float, measure_width: float,
                                start_idx: int, end_idx: int,
                                lyric_info: Dict,
                                all_voice_data: Dict, voice_order: List[str]):
        """Draw a single lyric line under the notes, synced to the target voice"""
        lyric = lyric_info['lyric']
        block_start = lyric_info['block_start']
        block_end = lyric_info['block_end']

        # Get the target voice for this lyric (the voice it's placed under)
        target_voice = self._get_target_voice(lyric.voices, voice_order)

        # Use the target voice's notes for lyric positioning
        ref_measures = all_voice_data.get(target_voice, [])

        # If target voice not found, fall back to first voice
        if not ref_measures and voice_order:
            ref_measures = all_voice_data.get(voice_order[0], [])

        # Position for lyrics - use lyric_top_margin for more space above
        lyric_y = y - self.lyric_top_margin

        # Collect syllable positions
        syllable_positions = []
        syllable_idx = 0

        for m_offset in range(block_end - block_start):
            m_idx = block_start + m_offset
            if m_idx >= len(ref_measures):
                continue
            if m_idx < start_idx or m_idx >= end_idx:
                # Count syllables for measures not being displayed
                # Only count actual notes (not rests/holds)
                measure = ref_measures[m_idx]
                for beat in measure.beats:
                    for note in beat.all_notes():
                        if note.type == NoteType.NOTE and not note.is_melisma:
                            syllable_idx += 1
                        elif note.type == NoteType.MODULATION:
                            syllable_idx += 1
                        # Skip REST and HOLD - they don't consume syllables
                continue

            measure = ref_measures[m_idx]
            num_beats = len(measure.beats)
            beat_width = measure_width / num_beats if num_beats > 0 else measure_width

            for beat_idx, beat in enumerate(measure.beats):
                all_notes = beat.all_notes()
                num_notes_in_beat = len(all_notes)

                if beat.is_subdivided:
                    first_half_notes = beat.first_half
                    second_half_notes = beat.second_half
                    half_width = beat_width / 2

                    # First half notes
                    for note_idx, note in enumerate(first_half_notes):
                        # Only actual notes get syllables (not rests, not holds, not melisma)
                        if note.type == NoteType.NOTE and not note.is_melisma:
                            if syllable_idx < len(lyric.syllables):
                                syl = lyric.syllables[syllable_idx]
                                if syl != "*":
                                    rel_m = m_idx - start_idx
                                    note_width = half_width / len(first_half_notes) if first_half_notes else half_width
                                    note_center_x = (start_x + label_width +
                                                     rel_m * measure_width +
                                                     beat_idx * beat_width +
                                                     note_idx * note_width +
                                                     note_width / 2)
                                    syllable_positions.append({
                                        'text': syl,
                                        'center_x': note_center_x
                                    })
                                syllable_idx += 1
                        elif note.type == NoteType.MODULATION:
                            if syllable_idx < len(lyric.syllables):
                                syl = lyric.syllables[syllable_idx]
                                if syl != "*":
                                    rel_m = m_idx - start_idx
                                    note_width = half_width / len(first_half_notes) if first_half_notes else half_width
                                    note_center_x = (start_x + label_width +
                                                     rel_m * measure_width +
                                                     beat_idx * beat_width +
                                                     note_idx * note_width +
                                                     note_width / 2)
                                    syllable_positions.append({
                                        'text': syl,
                                        'center_x': note_center_x
                                    })
                                syllable_idx += 1
                        # REST and HOLD don't consume syllables

                    # Second half notes
                    for note_idx, note in enumerate(second_half_notes):
                        if note.type == NoteType.NOTE and not note.is_melisma:
                            if syllable_idx < len(lyric.syllables):
                                syl = lyric.syllables[syllable_idx]
                                if syl != "*":
                                    rel_m = m_idx - start_idx
                                    note_width = half_width / len(
                                        second_half_notes) if second_half_notes else half_width
                                    note_center_x = (start_x + label_width +
                                                     rel_m * measure_width +
                                                     beat_idx * beat_width +
                                                     half_width +
                                                     note_idx * note_width +
                                                     note_width / 2)
                                    syllable_positions.append({
                                        'text': syl,
                                        'center_x': note_center_x
                                    })
                                syllable_idx += 1
                        elif note.type == NoteType.MODULATION:
                            if syllable_idx < len(lyric.syllables):
                                syl = lyric.syllables[syllable_idx]
                                if syl != "*":
                                    rel_m = m_idx - start_idx
                                    note_width = half_width / len(
                                        second_half_notes) if second_half_notes else half_width
                                    note_center_x = (start_x + label_width +
                                                     rel_m * measure_width +
                                                     beat_idx * beat_width +
                                                     half_width +
                                                     note_idx * note_width +
                                                     note_width / 2)
                                    syllable_positions.append({
                                        'text': syl,
                                        'center_x': note_center_x
                                    })
                                syllable_idx += 1
                        # REST and HOLD don't consume syllables
                else:
                    # Non-subdivided beat
                    for note_idx, note in enumerate(all_notes):
                        if note.type == NoteType.NOTE and not note.is_melisma:
                            if syllable_idx < len(lyric.syllables):
                                syl = lyric.syllables[syllable_idx]
                                if syl != "*":
                                    rel_m = m_idx - start_idx
                                    note_width = beat_width / num_notes_in_beat
                                    note_center_x = (start_x + label_width +
                                                     rel_m * measure_width +
                                                     beat_idx * beat_width +
                                                     note_idx * note_width +
                                                     note_width / 2)
                                    syllable_positions.append({
                                        'text': syl,
                                        'center_x': note_center_x
                                    })
                                syllable_idx += 1
                        elif note.type == NoteType.MODULATION:
                            if syllable_idx < len(lyric.syllables):
                                syl = lyric.syllables[syllable_idx]
                                if syl != "*":
                                    rel_m = m_idx - start_idx
                                    note_width = beat_width / num_notes_in_beat
                                    note_center_x = (start_x + label_width +
                                                     rel_m * measure_width +
                                                     beat_idx * beat_width +
                                                     note_idx * note_width +
                                                     note_width / 2)
                                    syllable_positions.append({
                                        'text': syl,
                                        'center_x': note_center_x
                                    })
                                syllable_idx += 1
                        # REST and HOLD don't consume syllables

        if not syllable_positions:
            return

        # Draw syllables centered under their notes
        self.c.setFont("Helvetica", self.lyric_font_size)

        for syl_info in syllable_positions:
            text = syl_info['text']
            center_x = syl_info['center_x']

            # Center the syllable text
            text_width = self.c.stringWidth(text, "Helvetica", self.lyric_font_size)
            draw_x = center_x - text_width / 2

            self.c.drawString(draw_x, lyric_y, text)
