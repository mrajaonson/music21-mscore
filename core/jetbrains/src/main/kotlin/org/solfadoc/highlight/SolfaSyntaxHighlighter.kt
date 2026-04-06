package org.solfadoc.highlight

import com.intellij.lexer.Lexer
import com.intellij.openapi.editor.DefaultLanguageHighlighterColors
import com.intellij.openapi.editor.colors.TextAttributesKey
import com.intellij.openapi.fileTypes.SyntaxHighlighterBase
import com.intellij.psi.tree.IElementType
import org.solfadoc.lexer.SolfaLexerAdapter
import org.solfadoc.lexer.SolfaTokenTypes

class SolfaSyntaxHighlighter : SyntaxHighlighterBase() {

    companion object {
        val COMMENT = TextAttributesKey.createTextAttributesKey("SOLFA_COMMENT", DefaultLanguageHighlighterColors.LINE_COMMENT)
        val HEADER_KEY = TextAttributesKey.createTextAttributesKey("SOLFA_HEADER_KEY", DefaultLanguageHighlighterColors.KEYWORD)
        val HEADER_VALUE = TextAttributesKey.createTextAttributesKey("SOLFA_HEADER_VALUE", DefaultLanguageHighlighterColors.STRING)
        val NOTE = TextAttributesKey.createTextAttributesKey("SOLFA_NOTE", DefaultLanguageHighlighterColors.NUMBER)
        val BARLINE = TextAttributesKey.createTextAttributesKey("SOLFA_BARLINE", DefaultLanguageHighlighterColors.OPERATION_SIGN)
        val LYRICS = TextAttributesKey.createTextAttributesKey("SOLFA_LYRICS", DefaultLanguageHighlighterColors.STRING)
        val BAD_CHAR = TextAttributesKey.createTextAttributesKey("SOLFA_BAD_CHARACTER", DefaultLanguageHighlighterColors.INVALID_STRING_ESCAPE)
    }

    override fun getHighlightingLexer(): Lexer = SolfaLexerAdapter()

    override fun getTokenHighlights(tokenType: IElementType?): Array<TextAttributesKey> {
        return when (tokenType) {
            SolfaTokenTypes.COMMENT -> arrayOf(COMMENT)
            SolfaTokenTypes.HEADER_KEY -> arrayOf(HEADER_KEY)
            SolfaTokenTypes.HEADER_VALUE -> arrayOf(HEADER_VALUE)
            SolfaTokenTypes.NOTE -> arrayOf(NOTE)
            SolfaTokenTypes.BARLINE -> arrayOf(BARLINE)
            SolfaTokenTypes.LYRICS -> arrayOf(LYRICS)
            SolfaTokenTypes.BAD_CHARACTER -> arrayOf(BAD_CHAR)
            else -> emptyArray()
        }
    }
}
