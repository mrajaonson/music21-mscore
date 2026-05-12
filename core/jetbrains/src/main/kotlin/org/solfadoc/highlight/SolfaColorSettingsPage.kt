package org.solfadoc.highlight

import com.intellij.openapi.editor.colors.TextAttributesKey
import com.intellij.openapi.fileTypes.SyntaxHighlighter
import com.intellij.openapi.options.colors.AttributesDescriptor
import com.intellij.openapi.options.colors.ColorDescriptor
import com.intellij.openapi.options.colors.ColorSettingsPage
import javax.swing.Icon

class SolfaColorSettingsPage : ColorSettingsPage {

    private val descriptors = arrayOf(
        AttributesDescriptor("Header//Key",                    SolfaSyntaxHighlighter.HEADER_KEY),
        AttributesDescriptor("Header//Delimiter (colons)",     SolfaSyntaxHighlighter.HEADER_DELIM),
        AttributesDescriptor("Header//Value",                  SolfaSyntaxHighlighter.HEADER_VALUE),
        AttributesDescriptor("Comment",                        SolfaSyntaxHighlighter.COMMENT),
        AttributesDescriptor("Voice label",                    SolfaSyntaxHighlighter.VOICE_LABEL),
        AttributesDescriptor("Note//Natural (d r m f s l t)", SolfaSyntaxHighlighter.NOTE),
        AttributesDescriptor("Note//Chromatic",                SolfaSyntaxHighlighter.CHROMATIC_NOTE),
        AttributesDescriptor("Note//Rest (*)",                 SolfaSyntaxHighlighter.REST),
        AttributesDescriptor("Note//Hold (-)",                 SolfaSyntaxHighlighter.HOLD),
        AttributesDescriptor("Note//Octave modifier (' ,)",    SolfaSyntaxHighlighter.OCTAVE),
        AttributesDescriptor("Note//Staccato (,)",             SolfaSyntaxHighlighter.DYNAMICS),
        AttributesDescriptor("Note//Melisma (_)",              SolfaSyntaxHighlighter.DYNAMICS),
        AttributesDescriptor("Rhythm//Barline (|)",            SolfaSyntaxHighlighter.BARLINE),
        AttributesDescriptor("Rhythm//Beat separator (:)",     SolfaSyntaxHighlighter.BEAT_SEP),
        AttributesDescriptor("Rhythm//Sub-beat separator (.)", SolfaSyntaxHighlighter.SUBBEAT_SEP),
        AttributesDescriptor("Rhythm//Modulation separator (/)", SolfaSyntaxHighlighter.MODULATION_SEP),
        AttributesDescriptor("Chord bracket (< >)",            SolfaSyntaxHighlighter.CHORD_BRACKET),
        AttributesDescriptor("Dynamics",                       SolfaSyntaxHighlighter.DYNAMICS),
        AttributesDescriptor("Navigation marker",              SolfaSyntaxHighlighter.NAVIGATION),
        AttributesDescriptor("Lyrics//Prefix (verse / voice)", SolfaSyntaxHighlighter.LYRICS_PREFIX),
        AttributesDescriptor("Lyrics//Text",                   SolfaSyntaxHighlighter.LYRICS_TEXT),
        AttributesDescriptor("Lyrics//Hyphen (-)",             SolfaSyntaxHighlighter.LYRICS_HYPHEN),
        AttributesDescriptor("Lyrics//Join (^)",               SolfaSyntaxHighlighter.LYRICS_JOIN),
        AttributesDescriptor("Lyrics//Rest skip (*)",          SolfaSyntaxHighlighter.LYRICS_REST_SKIP),
        AttributesDescriptor("Lyrics//Mute delimiter (__)",    SolfaSyntaxHighlighter.LYRICS_MUTE_DELIM),
        AttributesDescriptor("Notes section//Marker ([notes])", SolfaSyntaxHighlighter.NOTES_SECTION_MARKER),
        AttributesDescriptor("Notes section//Text",            SolfaSyntaxHighlighter.NOTES_SECTION_TEXT),
        AttributesDescriptor("Bad character",                  SolfaSyntaxHighlighter.BAD_CHAR),
    )

    override fun getIcon(): Icon? = null
    override fun getHighlighter(): SyntaxHighlighter = SolfaSyntaxHighlighter()
    override fun getAdditionalHighlightingTagToDescriptorMap(): Map<String, TextAttributesKey>? = null
    override fun getAttributeDescriptors(): Array<AttributesDescriptor> = descriptors
    override fun getColorDescriptors(): Array<ColorDescriptor> = ColorDescriptor.EMPTY_ARRAY
    override fun getDisplayName(): String = "Solfadoc"

    override fun getDemoText(): String = """
        // Header comment
        :title: Amazing Grace
        :author: John Newton, 1779
        :key: G
        :timesig: 3/4

        S | d'.d' : r' : m' | (ff)m'.r' : d' : (DC)m' ||
        A | s .s  : s  : s  | s .s      : s  : s      ||
        T | m .m  : f  : m  | m .m      : m  : m      ||
        B | d,.-  : d  : d  | ,d.d      : d  : d,     ||
        # Music comment
        S | <d m s> : fe/fi : s | d'' : le : ta ||
        1 A-ma-zing grace how sweet the sound
        R Praise^God ev__e__ry * day

        [notes]
        Traditional hymn. Public domain.
    """.trimIndent()
}
