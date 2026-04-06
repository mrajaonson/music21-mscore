package org.solfadoc.psi

import com.intellij.extapi.psi.PsiFileBase
import com.intellij.openapi.fileTypes.FileType
import com.intellij.psi.FileViewProvider
import org.solfadoc.SolfaFileType
import org.solfadoc.SolfaLanguage

class SolfaFile(viewProvider: FileViewProvider) : PsiFileBase(viewProvider, SolfaLanguage) {
    override fun getFileType(): FileType = SolfaFileType
    override fun toString(): String = "Solfadoc File"
}
