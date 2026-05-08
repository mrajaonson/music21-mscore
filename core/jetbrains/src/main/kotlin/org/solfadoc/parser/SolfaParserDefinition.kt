package org.solfadoc.parser

import com.intellij.lang.ASTNode
import com.intellij.lang.PsiBuilder
import com.intellij.lang.PsiParser
import com.intellij.lang.ParserDefinition
import com.intellij.lexer.Lexer
import com.intellij.openapi.project.Project
import com.intellij.psi.FileViewProvider
import com.intellij.psi.PsiElement
import com.intellij.psi.PsiFile
import com.intellij.psi.tree.IElementType
import com.intellij.psi.tree.IFileElementType
import com.intellij.psi.tree.TokenSet
import org.solfadoc.SolfaLanguage
import org.solfadoc.lexer.SolfaLexerAdapter
import org.solfadoc.lexer.SolfaTokenTypes
import org.solfadoc.psi.SolfaFile

class SolfaParserDefinition : ParserDefinition {
    companion object {
        val FILE = IFileElementType(SolfaLanguage)
    }

    override fun createLexer(project: Project?): Lexer = SolfaLexerAdapter()

    override fun createParser(project: Project?): PsiParser = SolfaParser()

    override fun getFileNodeType(): IFileElementType = FILE

    override fun getCommentTokens(): TokenSet = TokenSet.create(SolfaTokenTypes.COMMENT)

    override fun getStringLiteralElements(): TokenSet = TokenSet.EMPTY

    override fun createElement(node: ASTNode): PsiElement =
        com.intellij.psi.impl.source.tree.LeafPsiElement(node.elementType, node.text)

    override fun createFile(viewProvider: FileViewProvider): PsiFile = SolfaFile(viewProvider)
}

private class SolfaParser : PsiParser {
    override fun parse(root: IElementType, builder: PsiBuilder): ASTNode {
        val rootMarker = builder.mark()
        while (!builder.eof()) {
            builder.advanceLexer()
        }
        rootMarker.done(root)
        return builder.treeBuilt
    }
}
