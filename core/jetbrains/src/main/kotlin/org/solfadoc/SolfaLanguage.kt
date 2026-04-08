package org.solfadoc

import com.intellij.lang.Language

object SolfaLanguage : Language("Solfadoc") {
    private fun readResolve(): Any = SolfaLanguage
}
