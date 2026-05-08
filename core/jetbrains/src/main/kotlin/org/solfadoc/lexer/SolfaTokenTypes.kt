package org.solfadoc.lexer

import com.intellij.psi.tree.IElementType
import com.intellij.psi.TokenType
import org.solfadoc.SolfaLanguage

object SolfaTokenTypes {
    val COMMENT = IElementType("COMMENT", SolfaLanguage)
    val HEADER_PREFIX = IElementType("HEADER_PREFIX", SolfaLanguage)
    val HEADER_KEY = IElementType("HEADER_KEY", SolfaLanguage)
    val HEADER_SUFFIX = IElementType("HEADER_SUFFIX", SolfaLanguage)
    val HEADER_VALUE = IElementType("HEADER_VALUE", SolfaLanguage)
    val VOICE_LABEL = IElementType("VOICE_LABEL", SolfaLanguage)
    val NOTE = IElementType("NOTE", SolfaLanguage)
    val CHROMATIC_NOTE = IElementType("CHROMATIC_NOTE", SolfaLanguage)
    val REST = IElementType("REST", SolfaLanguage)
    val HOLD = IElementType("HOLD", SolfaLanguage)
    val BARLINE = IElementType("BARLINE", SolfaLanguage)
    val DOUBLE_BARLINE = IElementType("DOUBLE_BARLINE", SolfaLanguage)
    val SOFT_BARLINE = IElementType("SOFT_BARLINE", SolfaLanguage)
    val BEAT_SEPARATOR = IElementType("BEAT_SEPARATOR", SolfaLanguage)
    val SUBBEAT_SEPARATOR = IElementType("SUBBEAT_SEPARATOR", SolfaLanguage)
    val OCTAVE_UP = IElementType("OCTAVE_UP", SolfaLanguage)
    val OCTAVE_DOWN = IElementType("OCTAVE_DOWN", SolfaLanguage)
    val STACCATO = IElementType("STACCATO", SolfaLanguage)
    val MELISMA = IElementType("MELISMA", SolfaLanguage)
    val DYNAMICS = IElementType("DYNAMICS", SolfaLanguage)
    val NAVIGATION = IElementType("NAVIGATION", SolfaLanguage)
    val CHORD_OPEN = IElementType("CHORD_OPEN", SolfaLanguage)
    val CHORD_CLOSE = IElementType("CHORD_CLOSE", SolfaLanguage)
    val LYRICS_PREFIX = IElementType("LYRICS_PREFIX", SolfaLanguage)
    val LYRICS_TEXT = IElementType("LYRICS_TEXT", SolfaLanguage)
    val NEWLINE = IElementType("NEWLINE", SolfaLanguage)
    val WHITESPACE = TokenType.WHITE_SPACE
    val BAD_CHARACTER = TokenType.BAD_CHARACTER
}
