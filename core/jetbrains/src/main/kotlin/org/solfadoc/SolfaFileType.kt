package org.solfadoc

import com.intellij.openapi.fileTypes.LanguageFileType
import javax.swing.Icon

object SolfaFileType : LanguageFileType(SolfaLanguage) {
    override fun getName(): String = "Solfadoc"
    override fun getDescription(): String = "Solfadoc notation file"
    override fun getDefaultExtension(): String = "solfa"
    override fun getIcon(): Icon = SolfaIcons.FILE
}
