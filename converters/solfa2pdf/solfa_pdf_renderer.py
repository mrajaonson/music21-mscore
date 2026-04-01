from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.units import mm, cm
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from ..shared import spec
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

def _resolve_music_font() -> str:
    pref = spec["export"]["music_symbol_font_preference"]
    fallback = spec["export"]["music_symbol_font_fallback"]
    try:
        pdfmetrics.registerFont(TTFont(pref, f'/Library/Fonts/{pref}.ttf'))
        return pref
    except Exception:
        return fallback

MUSIC_SYMBOL_FONT = _resolve_music_font()
from .data_structures import (Song)
from datetime import datetime
from typing import List, Dict, Tuple
from .data_structures import (NoteType, Measure, Beat, Note)

class TonicSolfaPDFRenderer:
    """Renders a parsed Song to PDF in traditional hymnal style"""

    def __init__(self, song: Song, output_path: str):
        self.c = None
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
        self.notation_font = spec["export"]["notation_font"]
        self.title_font_size = 14
        self.subtitle_font_size = 10
        self.header_font_size = 9
        self.note_font_size = 9
        self.lyric_font_size = 8
        self.small_font_size = 7

        # Layout settings
        self.voice_row_height = 12  # Height per voice row
        self.lyric_row_height = 9  # Height per lyric row
        self.block_spacing = 12  # Space between blocks
        self.lyric_top_margin = 6  # Space above lyrics
        self.lyric_bottom_margin = 2  # Space below lyrics
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
        page_text = f"-{self.current_page}-"
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

        # Author (left) and Composer (right) on the same line
        has_author = bool(self.song.author)
        has_composer = bool(self.song.composer)
        if has_author or has_composer:
            self.c.setFont("Helvetica-Oblique", self.subtitle_font_size)
            if has_author:
                self.c.drawString(self.margin_left, self.y_position, self.song.author)
            if has_composer:
                self.c.drawRightString(self.page_width - self.margin_left, self.y_position, self.song.composer)
            self.y_position -= self.subtitle_font_size + 3

        # Comments (right-aligned, under composer)
        if self.song.comments:
            self.c.setFont("Helvetica-Oblique", self.small_font_size)
            self.c.drawRightString(self.page_width - self.margin_left, self.y_position, self.song.comments)
            self.y_position -= self.small_font_size + 3

        # Key, Tempo, Time Signature line
        self.c.setFont("Helvetica", self.header_font_size)
        info_parts = [f"Key: {self.song.key}", f"Time: {self.song.time_sig[0]}/{self.song.time_sig[1]}"]
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
        for v in spec["voices"]["default_order"]:
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
                measure_idx = end_idx
                continue

            # Calculate height needed for this line
            num_voices = len(voice_order)
            line_height = (num_voices * self.voice_row_height +
                           2 * self.lyric_row_height +
                           self.block_spacing)

            self._check_page_space(line_height)

            # Draw this group of measures
            self._draw_measure_group(
                all_voice_data, voice_order,
                measure_idx, end_idx,
                block_lyrics
            )

            measure_idx = end_idx

    # ─────────────────────────────────────────────────────────────────
    # Note center X computation (shared by fermatas, key changes, lyrics)
    # ─────────────────────────────────────────────────────────────────

    def _compute_note_center_x_full(self, m_idx: int, start_idx: int,
                                    beat_idx: int, note_idx: int, note: Note,
                                    beat: Beat, num_beats: int,
                                    start_x: float, label_width: float,
                                    measure_width: float) -> float:
        """Compute the center X for a specific note in a measure.
        Uses the same centering logic as lyric syllable placement so that
        fermatas, key changes, etc. are centered exactly over their note."""
        rel_m = m_idx - start_idx
        beat_width = measure_width / num_beats if num_beats > 0 else measure_width

        if beat.is_subdivided:
            half_width = beat_width / 2
            if note in beat.first_half:
                idx_in_half = beat.first_half.index(note)
                num_in_half = len(beat.first_half)
                note_width = half_width / num_in_half if num_in_half > 0 else half_width
                center_x = (start_x + label_width +
                            rel_m * measure_width +
                            beat_idx * beat_width +
                            idx_in_half * note_width +
                            note_width / 2)
            elif note in beat.second_half:
                idx_in_half = beat.second_half.index(note)
                num_in_half = len(beat.second_half)
                note_width = half_width / num_in_half if num_in_half > 0 else half_width
                center_x = (start_x + label_width +
                            rel_m * measure_width +
                            beat_idx * beat_width +
                            half_width +
                            idx_in_half * note_width +
                            note_width / 2)
            else:
                # Fallback: center of beat
                center_x = (start_x + label_width +
                            rel_m * measure_width +
                            beat_idx * beat_width +
                            beat_width / 2)
        else:
            all_notes = beat.all_notes()
            num_notes = len(all_notes)
            note_width = beat_width / num_notes if num_notes > 0 else beat_width
            center_x = (start_x + label_width +
                        rel_m * measure_width +
                        beat_idx * beat_width +
                        note_idx * note_width +
                        note_width / 2)

        return center_x

    # ─────────────────────────────────────────────────────────────────
    # Draw a group of measures (one line of the score)
    # ─────────────────────────────────────────────────────────────────

    def _draw_measure_group(self, all_voice_data: Dict, voice_order: List[str],
                            start_idx: int, end_idx: int, block_lyrics: List[Dict]):
        """Draw a group of measures (one line of the score) with lyrics under target voices"""
        num_measures = end_idx - start_idx

        # Check if we have all 4 standard SATB voices - if so, don't show labels
        show_voice_labels = not (set(voice_order) == set(spec["voices"]["default_order"]) and len(voice_order) == 4)

        # Calculate column widths — use consistent measure width based on measures_per_line
        voice_label_width = 8 * mm if show_voice_labels else 0
        available_width = self.content_width - voice_label_width
        measure_width = available_width / self.measures_per_line

        # Starting position
        start_x = self.margin_left
        start_y = self.y_position

        # ── Collect ALL above-staff markers into a unified list ──
        above_staff_items = self._collect_all_above_staff_items(
            all_voice_data, voice_order, start_idx, end_idx,
            start_x, voice_label_width, measure_width
        )

        # Draw all above-staff markers on the SAME line if any exist
        if above_staff_items:
            self._draw_above_staff_line(above_staff_items, start_y)
            start_y -= 12  # Single vertical offset for the combined row

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

        # Organize lyrics by their target voice
        lyrics_by_target_voice = self._organize_lyrics_by_target_voice(block_lyrics, start_idx, end_idx, voice_order)

        # Pre-compute total barline height: from top of first voice to bottom of last voice's note row
        # (including lyrics rows between voices, but NOT the last voice's lyrics)
        total_barline_height = 0
        for voice_idx, voice_label in enumerate(voice_order):
            total_barline_height += self.voice_row_height
            # Add lyrics height for all voices except the last one
            if voice_idx < len(voice_order) - 1 and voice_label in lyrics_by_target_voice:
                num_lyric_lines = len(lyrics_by_target_voice[voice_label])
                total_barline_height += num_lyric_lines * (self.lyric_row_height + self.lyric_bottom_margin)

        # Draw barlines first (full height from first voice to bottom of last voice's notes)
        barline_top_y = start_y
        barline_bottom_y = start_y - total_barline_height
        self.c.setStrokeColor(colors.black)

        x = start_x + voice_label_width
        # Left barline
        self.c.setLineWidth(0.5)
        self.c.line(x, barline_top_y, x, barline_bottom_y)

        # Barlines after each measure
        bx = x
        total_voice_measures = max(len(all_voice_data.get(v, [])) for v in voice_order) if voice_order else 0
        for m_idx in range(start_idx, end_idx):
            bx += measure_width
            is_last_measure = (m_idx == total_voice_measures - 1)

            if is_last_measure:
                # Double barline at end
                self.c.setLineWidth(0.5)
                self.c.line(bx - 2, barline_top_y, bx - 2, barline_bottom_y)
                self.c.setLineWidth(1.5)
                self.c.line(bx, barline_top_y, bx, barline_bottom_y)
                self.c.setLineWidth(0.5)
            else:
                self.c.setLineWidth(0.5)
                self.c.line(bx, barline_top_y, bx, barline_bottom_y)

        # Draw each voice with its lyrics underneath
        y = start_y
        for voice_idx, voice_label in enumerate(voice_order):
            measures = all_voice_data.get(voice_label, [])

            # Draw voice label only if not standard SATB
            if show_voice_labels:
                self.c.setFont("Helvetica-Bold", self.note_font_size)
                self.c.drawString(start_x, y - self.voice_row_height + 3, voice_label)

            # Draw measures for this voice (content only, no barlines)
            x = start_x + voice_label_width
            for m_idx in range(start_idx, end_idx):
                if m_idx < len(measures):
                    measure = measures[m_idx]
                    self._draw_measure_content(measure, x, y, measure_width, self.voice_row_height)
                x += measure_width

            y -= self.voice_row_height

            # Draw lyrics for this voice if any
            if voice_label in lyrics_by_target_voice:
                for lyric_info in lyrics_by_target_voice[voice_label]:
                    self._draw_single_lyric_line(start_x, y, voice_label_width, measure_width,
                                                 start_idx, end_idx, lyric_info, all_voice_data, voice_order)
                    y -= (self.lyric_row_height + self.lyric_bottom_margin)

        # Update y position with block spacing
        self.y_position = y - self.block_spacing

    # ─────────────────────────────────────────────────────────────────
    # Draw above-staff markers (nav + fermata + key changes on ONE line)
    # ─────────────────────────────────────────────────────────────────

    def _collect_all_above_staff_items(self, all_voice_data: Dict, voice_order: List[str],
                                       start_idx: int, end_idx: int,
                                       start_x: float, label_width: float,
                                       measure_width: float) -> List[Dict]:
        """Collect ALL above-staff items (dynamics, hairpins, text expressions, fermatas,
        navigation markers, key changes) from the first voice, grouped by note position.
        Each item has 'center_x', 'order' (notation order), and 'texts' (list of display strings)."""
        if not voice_order:
            return []

        # Collect items with their center_x and a global ordering index
        items_by_position = {}  # key: (m_idx, beat_idx, note_idx) -> list of texts in order
        order_counter = [0]

        def add_item(key, center_x, text):
            if key not in items_by_position:
                items_by_position[key] = {'center_x': center_x, 'texts': [], 'order': order_counter[0]}
            items_by_position[key]['texts'].append(text)
            order_counter[0] += 1

        # Use first voice for center_x computation, but collect marks from ALL voices
        first_voice = voice_order[0]
        first_measures = all_voice_data.get(first_voice, [])
        seen_texts = set()  # (key, text) to avoid duplicates across voices

        for voice_label in voice_order:
            measures = all_voice_data.get(voice_label, [])

            for m_idx in range(start_idx, min(end_idx, len(measures))):
                measure = measures[m_idx]
                # Use first voice's beat structure for center_x
                ref_measure = first_measures[m_idx] if m_idx < len(first_measures) else measure
                num_beats = len(ref_measure.beats)

                for beat_idx, beat in enumerate(measure.beats):
                    all_notes = beat.all_notes()
                    ref_beat = ref_measure.beats[beat_idx] if beat_idx < len(ref_measure.beats) else beat

                    for note_idx, note in enumerate(all_notes):
                        # Compute center_x using first voice's beat for consistent alignment
                        ref_notes = ref_beat.all_notes()
                        ref_note = ref_notes[note_idx] if note_idx < len(ref_notes) else note
                        center_x = self._compute_note_center_x_full(
                            m_idx, start_idx, beat_idx, note_idx, ref_note,
                            ref_beat, num_beats, start_x, label_width, measure_width
                        )
                        key = (m_idx, beat_idx, note_idx)

                        for expr in note.expressions:
                            dedup = (key, expr.type, expr.value)
                            if dedup in seen_texts:
                                continue
                            seen_texts.add(dedup)

                            if expr.type == "dynamic":
                                add_item(key, center_x, expr.value)
                            elif expr.type == "hairpin":
                                add_item(key, center_x, expr.value)
                            elif expr.type == "text":
                                add_item(key, center_x, expr.value)
                            elif expr.type == "fermata":
                                add_item(key, center_x, spec["navigation"]["fermata_symbol"])
                            elif expr.type == "navigation":
                                add_item(key, center_x, expr.value)

                        if note.type == NoteType.MODULATION and note.key_change:
                            dedup = (key, "key_change", note.key_change)
                            if dedup not in seen_texts:
                                seen_texts.add(dedup)
                                add_item(key, center_x, f"Key: {note.key_change}")

        # Convert to sorted list
        result = sorted(items_by_position.values(), key=lambda x: x['order'])
        return result

    def _draw_above_staff_line(self, items: List[Dict], start_y: float):
        """Draw all above-staff items on ONE line. Each item's texts are joined by spaces
        and centered over the note's center_x."""
        self.c.setFillColor(colors.black)
        draw_y = start_y + 2

        for item in items:
            center_x = item['center_x']
            texts = item['texts']

            # Build combined display, handling music symbols specially
            self._draw_combined_above_text(texts, center_x, draw_y)

    def _draw_combined_above_text(self, texts: List[str], center_x: float, draw_y: float):
        """Draw a list of above-staff text items centered over center_x, separated by spaces.
        Music symbols (Coda, Segno, Fermata) use MUSIC_SYMBOL_FONT, others use Helvetica-Bold."""
        # Build segments: list of (text, font_name, font_size)
        segments = []
        music_symbols = {spec["navigation"]["coda_symbol"], spec["navigation"]["segno_symbol"], spec["navigation"]["fermata_symbol"]}

        for i, text in enumerate(texts):
            if i > 0:
                segments.append((" ", "Helvetica-Bold", self.small_font_size + 1))

            # Check if text contains music symbols
            contains_music = any(sym in text for sym in music_symbols)
            if contains_music:
                # Split symbol from number suffix
                idx = len(text) - 1
                while idx >= 0 and text[idx].isdigit():
                    idx -= 1
                symbol_part = text[:idx + 1]
                number_suffix = text[idx + 1:]

                segments.append((symbol_part, MUSIC_SYMBOL_FONT, self.small_font_size + 6))
                if number_suffix:
                    segments.append((number_suffix, "Helvetica-Bold", self.small_font_size + 2))
            else:
                segments.append((text, "Helvetica-Bold", self.small_font_size + 1))

        # Calculate total width
        total_width = 0
        for seg_text, seg_font, seg_size in segments:
            total_width += self.c.stringWidth(seg_text, seg_font, seg_size)

        # Draw centered
        draw_x = center_x - total_width / 2
        for seg_text, seg_font, seg_size in segments:
            self.c.setFont(seg_font, seg_size)
            self.c.drawString(draw_x, draw_y, seg_text)
            draw_x += self.c.stringWidth(seg_text, seg_font, seg_size)

    # ─────────────────────────────────────────────────────────────────
    # Lyric organization helpers
    # ─────────────────────────────────────────────────────────────────

    def _organize_lyrics_by_target_voice(self, block_lyrics: List[Dict], start_idx: int,
                                         end_idx: int, voice_order: List[str]) -> Dict[str, List]:
        """Organize lyrics by their target voice (last voice in prefix)"""
        result = {}

        for bl in block_lyrics:
            if bl['start'] < end_idx and bl['end'] > start_idx:
                for lyric in bl['lyrics']:
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
            return voice_order[-1] if voice_order else "B"

        for v in reversed(voices):
            if v in voice_order:
                return v

        return voice_order[-1] if voice_order else "B"

    # ─────────────────────────────────────────────────────────────────
    # Collect above-staff markers with precise center_x
    # ─────────────────────────────────────────────────────────────────


    # ─────────────────────────────────────────────────────────────────
    # Measure and beat content rendering
    # ─────────────────────────────────────────────────────────────────

    def _draw_measure_content(self, measure: Measure, x: float, y: float,
                              width: float, height: float):
        """Draw the content of a single measure"""
        if measure.is_empty:
            num_beats = len(measure.beats) if measure.beats else 4
            beat_width = width / num_beats
            self.c.setFont(self.notation_font, self.note_font_size)
            text_y = y - height + 3
            for beat_idx in range(num_beats - 1):
                sep_x = x + (beat_idx + 1) * beat_width
                if measure.soft_barline_after_beat == beat_idx:
                    self.c.drawCentredString(sep_x, text_y, "|")
                else:
                    self.c.drawCentredString(sep_x, text_y, ":")
            return

        num_beats = len(measure.beats)
        if num_beats == 0:
            return

        beat_width = width / num_beats

        self.c.setFont(self.notation_font, self.note_font_size)
        text_y = y - height + 3
        underline_y = text_y - 2

        # Collect per-note positions across all beats for melisma underlines
        all_note_positions = []  # list of {x, end_x, is_melisma, is_note}

        for beat_idx, beat in enumerate(measure.beats):
            beat_x = x + beat_idx * beat_width

            beat_result = self._draw_beat_content_with_positions(beat, beat_x, y, beat_width, height)
            all_note_positions.extend(beat_result.get('note_positions', []))

            if beat_idx < num_beats - 1:
                sep_x = beat_x + beat_width
                if measure.soft_barline_after_beat == beat_idx:
                    self.c.drawCentredString(sep_x, text_y, "|")
                else:
                    self.c.drawCentredString(sep_x, text_y, ":")

        # Build melisma underline ranges: include the note before the melisma chain
        melisma_ranges = []
        i = 0
        while i < len(all_note_positions):
            pos = all_note_positions[i]
            if pos['is_melisma'] and pos['is_note']:
                # Find the start: include preceding note
                start_x_m = pos['x']
                if i > 0 and all_note_positions[i - 1]['is_note']:
                    start_x_m = all_note_positions[i - 1]['x']
                # Extend through consecutive melisma notes
                end_x_m = pos['end_x']
                while i < len(all_note_positions) and all_note_positions[i]['is_melisma'] and all_note_positions[i]['is_note']:
                    end_x_m = all_note_positions[i]['end_x']
                    i += 1
                melisma_ranges.append((start_x_m, end_x_m))
            else:
                i += 1

        for start_x_m, end_x_m in melisma_ranges:
            self._draw_melisma_underline(start_x_m, underline_y, end_x_m - start_x_m)

    def _draw_beat_content_with_positions(self, beat: Beat, x: float, y: float,
                                          width: float, height: float) -> Dict:
        """Draw the content of a single beat and return per-note position info"""
        self.c.setFont(self.notation_font, self.note_font_size)

        text_y = y - height + 3
        above_y = y + 2

        result = {
            'note_positions': [],  # list of {x, end_x, is_melisma, is_note}
            'key_changes': []
        }

        if beat.is_subdivided:
            half_width = width / 2

            first_text, first_mods = self._notes_to_display_text(beat.first_half)
            second_text, second_mods = self._notes_to_display_text(beat.second_half)

            first_draw_x = None
            first_text_width = 0
            if first_text:
                first_text_width = self._calc_text_width_with_mods(first_text, first_mods)
                first_draw_x = x + (half_width - first_text_width) / 2
                self._draw_text_with_modulation(first_text, first_mods, first_draw_x, text_y, x, above_y)
                for mod in first_mods:
                    if mod.get('key_change'):
                        result['key_changes'].append((first_draw_x, mod['key_change']))

            # Per-note positions for first half
            self._add_note_positions(beat.first_half, x, half_width, first_draw_x, first_text_width, result)

            dot_x = x + half_width - 1
            self.c.setFont(self.notation_font, self.note_font_size)
            self.c.drawString(dot_x, text_y, ".")

            second_draw_x = None
            second_text_width = 0
            if second_text:
                second_text_width = self._calc_text_width_with_mods(second_text, second_mods)
                second_draw_x = x + half_width + (half_width - second_text_width) / 2
                self._draw_text_with_modulation(second_text, second_mods, second_draw_x, text_y, x + half_width,
                                                above_y)
                for mod in second_mods:
                    if mod.get('key_change'):
                        result['key_changes'].append((second_draw_x, mod['key_change']))

            # Per-note positions for second half
            self._add_note_positions(beat.second_half, x + half_width, half_width, second_draw_x, second_text_width, result)

        else:
            text, mods = self._notes_to_display_text(beat.notes)
            if text:
                text_width = self._calc_text_width_with_mods(text, mods)
                draw_x = x + (width - text_width) / 2
                self._draw_text_with_modulation(text, mods, draw_x, text_y, x, above_y)

                for mod in mods:
                    if mod.get('key_change'):
                        result['key_changes'].append((draw_x, mod['key_change']))

            # Per-note positions
            draw_x_val = x + (width - self._calc_text_width_with_mods(text, mods)) / 2 if text else x
            self._add_note_positions(beat.notes, x, width, draw_x_val if text else None, self._calc_text_width_with_mods(text, mods) if text else 0, result)

        return result

    def _add_note_positions(self, notes: List[Note], half_x: float, half_width: float,
                            draw_x: float, text_width: float, result: Dict):
        """Add per-note position info for melisma underline computation."""
        if not notes:
            return
        num_notes = len(notes)
        note_width = half_width / num_notes if num_notes > 0 else half_width
        for i, note in enumerate(notes):
            is_real_note = note.type in (NoteType.NOTE, NoteType.MODULATION, NoteType.CHORD)
            # Approximate each note's drawn x range within the half
            note_x = half_x + i * note_width
            note_end_x = note_x + note_width
            # If we have actual draw coordinates, use proportional mapping
            if draw_x is not None and text_width > 0 and num_notes > 0:
                per_note_w = text_width / num_notes
                note_x = draw_x + i * per_note_w
                note_end_x = note_x + per_note_w
            result['note_positions'].append({
                'x': note_x,
                'end_x': note_end_x,
                'is_melisma': note.is_melisma,
                'is_note': is_real_note
            })

    def _calc_text_width_with_mods(self, text: str, modulations: List[Dict]) -> float:
        """Calculate total width of text including modulation superscripts"""
        if not modulations:
            return self.c.stringWidth(text, self.notation_font, self.note_font_size)

        total_width = 0
        superscript_size = self.note_font_size - 1

        for mod in modulations:
            old_note_width = self.c.stringWidth(mod['old_note'], self.notation_font, superscript_size)
            total_width += old_note_width

        total_width += self.c.stringWidth(text, self.notation_font, self.note_font_size)

        return total_width

    def _draw_melisma_underline(self, x: float, y: float, width: float):
        """Draw underline for melisma notes"""
        self.c.setStrokeColor(colors.black)
        self.c.setLineWidth(0.5)
        self.c.line(x, y, x + width, y)

    def _notes_to_display_text(self, notes: List[Note]) -> Tuple[str, List[Dict]]:
        """Convert notes to display text and return modulation info"""
        parts = []
        modulations = []

        for note in notes:
            # Dynamics, hairpins, text expressions are rendered above staff, not inline

            if note.type == NoteType.MODULATION and note.modulation_from:
                modulations.append({
                    'old_note': note.modulation_from,
                    'position': len("".join(parts)),
                    'key_change': note.key_change
                })

            parts.append(note.display_text())

        return "".join(parts), modulations

    def _draw_text_with_modulation(self, text: str, modulations: List[Dict],
                                   x: float, y: float, beat_x: float, above_y: float):
        """Draw text with modulation superscripts"""
        if not modulations:
            self.c.setFont(self.notation_font, self.note_font_size)
            self.c.drawString(x, y, text)
            return

        self.c.setFont(self.notation_font, self.note_font_size)
        current_x = x
        text_idx = 0

        for mod in modulations:
            if mod['position'] > text_idx:
                pre_text = text[text_idx:mod['position']]
                self.c.setFont(self.notation_font, self.note_font_size)
                self.c.drawString(current_x, y, pre_text)
                current_x += self.c.stringWidth(pre_text, self.notation_font, self.note_font_size)
                text_idx = mod['position']

            superscript_size = self.note_font_size - 1
            self.c.setFont(self.notation_font, superscript_size)
            old_note_text = mod['old_note']
            self.c.drawString(current_x, y + 4, old_note_text)
            current_x += self.c.stringWidth(old_note_text, self.notation_font, superscript_size)

        if text_idx < len(text):
            remaining = text[text_idx:]
            self.c.setFont(self.notation_font, self.note_font_size)
            self.c.drawString(current_x, y, remaining)

    def _short_nav(self, nav_text: str) -> str:
        """Get short form of navigation marker for display"""
        reverse_map = {v: k for k, v in spec["navigation"]["markers"].items()}
        return reverse_map.get(nav_text, nav_text)

    # ─────────────────────────────────────────────────────────────────
    # Lyric rendering
    # ─────────────────────────────────────────────────────────────────

    def _draw_single_lyric_line(self, start_x: float, y: float,
                                label_width: float, measure_width: float,
                                start_idx: int, end_idx: int,
                                lyric_info: Dict,
                                all_voice_data: Dict, voice_order: List[str]):
        """Draw a single lyric line under the notes, synced to the target voice"""
        lyric = lyric_info['lyric']
        block_start = lyric_info['block_start']
        block_end = lyric_info['block_end']

        target_voice = self._get_target_voice(lyric.voices, voice_order)
        ref_measures = all_voice_data.get(target_voice, [])

        if not ref_measures and voice_order:
            ref_measures = all_voice_data.get(voice_order[0], [])

        lyric_y = y - self.lyric_top_margin

        syllable_positions = []
        syllable_idx = 0

        for m_offset in range(block_end - block_start):
            m_idx = block_start + m_offset
            if m_idx >= len(ref_measures):
                continue
            if m_idx < start_idx or m_idx >= end_idx:
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

                if beat.is_subdivided:
                    first_half_notes = beat.first_half
                    second_half_notes = beat.second_half
                    half_width = beat_width / 2

                    for note_idx, note in enumerate(first_half_notes):
                        if (note.type == NoteType.NOTE and not note.is_melisma) or note.type == NoteType.MODULATION:
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

                    for note_idx, note in enumerate(second_half_notes):
                        if (note.type == NoteType.NOTE and not note.is_melisma) or note.type == NoteType.MODULATION:
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
                else:
                    for note_idx, note in enumerate(all_notes):
                        if (note.type == NoteType.NOTE and not note.is_melisma) or note.type == NoteType.MODULATION:
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

        if not syllable_positions:
            return

        self.c.setFont(self.notation_font, self.lyric_font_size)

        for syl_info in syllable_positions:
            text = syl_info['text']
            center_x = syl_info['center_x']

            text_width = self.c.stringWidth(text, self.notation_font, self.lyric_font_size)
            draw_x = center_x - text_width / 2

            self.c.drawString(draw_x, lyric_y, text)
