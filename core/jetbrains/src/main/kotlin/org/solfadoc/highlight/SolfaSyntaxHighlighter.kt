package org.solfadoc.highlight

import com.intellij.lexer.Lexer
import com.intellij.openapi.editor.DefaultLanguageHighlighterColors
import com.intellij.openapi.editor.HighlighterColors
import com.intellij.openapi.editor.colors.TextAttributesKey
import com.intellij.openapi.fileTypes.SyntaxHighlighterBase
import com.intellij.psi.tree.IElementType
import org.solfadoc.lexer.SolfaLexerAdapter
import org.solfadoc.lexer.SolfaTokenTypes

class SolfaSyntaxHighlighter : SyntaxHighlighterBase() {

    companion object {
        val COMMENT = TextAttributesKey.createTextAttributesKey("SOLFA_COMMENT", DefaultLanguageHighlighterColors.LINE_COMMENT)
        val HEADER_KEY = TextAttributesKey.createTextAttributesKey("SOLFA_HEADER_KEY", DefaultLanguageHighlighterColors.KEYWORD)
        val HEADER_DELIM = TextAttributesKey.createTextAttributesKey("SOLFA_HEADER_DELIM", DefaultLanguageHighlighterColors.KEYWORD)
        val HEADER_VALUE = TextAttributesKey.createTextAttributesKey("SOLFA_HEADER_VALUE", DefaultLanguageHighlighterColors.STRING)
        val VOICE_LABEL = TextAttributesKey.createTextAttributesKey("SOLFA_VOICE_LABEL", DefaultLanguageHighlighterColors.CONSTANT)
        val NOTE = TextAttributesKey.createTextAttributesKey("SOLFA_NOTE", DefaultLanguageHighlighterColors.NUMBER)
        val CHROMATIC_NOTE = TextAttributesKey.createTextAttributesKey("SOLFA_CHROMATIC_NOTE", DefaultLanguageHighlighterColors.NUMBER)
        val REST = TextAttributesKey.createTextAttributesKey("SOLFA_REST", DefaultLanguageHighlighterColors.PREDEFINED_SYMBOL)
        val HOLD = TextAttributesKey.createTextAttributesKey("SOLFA_HOLD", DefaultLanguageHighlighterColors.PREDEFINED_SYMBOL)
        val BARLINE = TextAttributesKey.createTextAttributesKey("SOLFA_BARLINE", DefaultLanguageHighlighterColors.OPERATION_SIGN)
        val BEAT_SEP = TextAttributesKey.createTextAttributesKey("SOLFA_BEAT_SEP", DefaultLanguageHighlighterColors.DOT)
        val SUBBEAT_SEP = TextAttributesKey.createTextAttributesKey("SOLFA_SUBBEAT_SEP", DefaultLanguageHighlighterColors.DOT)
        val OCTAVE = TextAttributesKey.createTextAttributesKey("SOLFA_OCTAVE", DefaultLanguageHighlighterColors.METADATA)
        val DYNAMICS = TextAttributesKey.createTextAttributesKey("SOLFA_DYNAMICS", DefaultLanguageHighlighterColors.METADATA)
        val NAVIGATION = TextAttributesKey.createTextAttributesKey("SOLFA_NAVIGATION", DefaultLanguageHighlighterColors.LABEL)
        val CHORD_BRACKET = TextAttributesKey.createTextAttributesKey("SOLFA_CHORD_BRACKET", DefaultLanguageHighlighterColors.BRACKETS)
        val LYRICS_PREFIX = TextAttributesKey.createTextAttributesKey("SOLFA_LYRICS_PREFIX", DefaultLanguageHighlighterColors.CONSTANT)
        val LYRICS_TEXT = TextAttributesKey.createTextAttributesKey("SOLFA_LYRICS_TEXT", DefaultLanguageHighlighterColors.STRING)
        val BAD_CHAR = TextAttributesKey.createTextAttributesKey("SOLFA_BAD_CHARACTER", HighlighterColors.BAD_CHARACTER)
    }

    override fun getHighlightingLexer(): Lexer = SolfaLexerAdapter()

    override fun getTokenHighlights(tokenType: IElementType?): Array<TextAttributesKey> {
        return when (tokenType) {
            SolfaTokenTypes.COMMENT -> arrayOf(COMMENT)
            SolfaTokenTypes.HEADER_PREFIX, SolfaTokenTypes.HEADER_SUFFIX -> arrayOf(HEADER_DELIM)
            SolfaTokenTypes.HEADER_KEY -> arrayOf(HEADER_KEY)
            SolfaTokenTypes.HEADER_VALUE -> arrayOf(HEADER_VALUE)
            SolfaTokenTypes.VOICE_LABEL -> arrayOf(VOICE_LABEL)
            SolfaTokenTypes.NOTE -> arrayOf(NOTE)
            SolfaTokenTypes.CHROMATIC_NOTE -> arrayOf(CHROMATIC_NOTE)
            SolfaTokenTypes.REST -> arrayOf(REST)
            SolfaTokenTypes.HOLD -> arrayOf(HOLD)
            SolfaTokenTypes.BARLINE, SolfaTokenTypes.DOUBLE_BARLINE, SolfaTokenTypes.SOFT_BARLINE -> arrayOf(BARLINE)
            SolfaTokenTypes.BEAT_SEPARATOR -> arrayOf(BEAT_SEP)
            SolfaTokenTypes.SUBBEAT_SEPARATOR -> arrayOf(SUBBEAT_SEP)
            SolfaTokenTypes.OCTAVE_UP, SolfaTokenTypes.OCTAVE_DOWN -> arrayOf(OCTAVE)
            SolfaTokenTypes.STACCATO, SolfaTokenTypes.MELISMA -> arrayOf(DYNAMICS)
            SolfaTokenTypes.DYNAMICS -> arrayOf(DYNAMICS)
            SolfaTokenTypes.NAVIGATION -> arrayOf(NAVIGATION)
            SolfaTokenTypes.CHORD_OPEN, SolfaTokenTypes.CHORD_CLOSE -> arrayOf(CHORD_BRACKET)
            SolfaTokenTypes.LYRICS_PREFIX -> arrayOf(LYRICS_PREFIX)
            SolfaTokenTypes.LYRICS_TEXT -> arrayOf(LYRICS_TEXT)
            SolfaTokenTypes.BAD_CHARACTER -> arrayOf(BAD_CHAR)
            else -> emptyArray()
        }
    }
}
