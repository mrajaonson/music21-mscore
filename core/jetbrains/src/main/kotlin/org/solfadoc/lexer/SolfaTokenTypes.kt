package org.solfadoc.lexer

import com.intellij.psi.tree.IElementType
import org.solfadoc.SolfaLanguage

object SolfaTokenTypes {
    val COMMENT = IElementType("COMMENT", SolfaLanguage)
    val HEADER_KEY = IElementType("HEADER_KEY", SolfaLanguage)
    val HEADER_VALUE = IElementType("HEADER_VALUE", SolfaLanguage)
    val NOTE = IElementType("NOTE", SolfaLanguage)
    val BARLINE = IElementType("BARLINE", SolfaLanguage)
    val LYRICS = IElementType("LYRICS", SolfaLanguage)
    val WHITESPACE = IElementType("WHITESPACE", SolfaLanguage)
    val BAD_CHARACTER = IElementType("BAD_CHARACTER", SolfaLanguage)
}
