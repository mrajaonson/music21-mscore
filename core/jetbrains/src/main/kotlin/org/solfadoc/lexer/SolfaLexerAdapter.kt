package org.solfadoc.lexer

import com.intellij.lexer.LexerBase
import com.intellij.psi.tree.IElementType

class SolfaLexerAdapter : LexerBase() {
    private var buffer: CharSequence = ""
    private var startOffset = 0
    private var endOffset = 0
    private var currentOffset = 0
    private var tokenType: IElementType? = null
    private var tokenStart = 0
    private var tokenEnd = 0
    private var lineStart = true
    private var inHeader = true
    private var isLyricsLine = false

    companion object {
        // Natural solfa notes (single char)
        private val NATURAL_NOTES = setOf('d', 'r', 'm', 'f', 's', 'l', 't')

        // Two-char chromatic notes
        private val CHROMATIC_NOTES = setOf(
            "de", "di", "re", "ri", "fe", "fi", "se", "si", "le", "li",  // sharps
            "ra", "ma", "sa", "la", "ta"                                   // flats
        )

        // Voice labels
        private val VOICE_LABELS = setOf("S", "A", "T", "B", "PR", "PL")

        // Dynamics tokens
        private val DYNAMICS = setOf(
            "ppp", "pp", "mp", "mf", "ff", "fff", "sf", "sfz", "fp", "p", "f",
            "<", ">", "^", "cresc", "dim", "rit", "accel"
        )

        // Navigation markers
        private val NAVIGATION = setOf(
            "DC", "DCF", "DCC", "DS", "DSF", "DSC", "FINE", "TC", "CODA", "SEGNO"
        )
    }

    override fun start(buffer: CharSequence, startOffset: Int, endOffset: Int, initialState: Int) {
        this.buffer = buffer
        this.startOffset = startOffset
        this.endOffset = endOffset
        this.currentOffset = startOffset
        this.lineStart = true
        this.inHeader = true
        this.isLyricsLine = false
        advance()
    }

    override fun getState(): Int = 0
    override fun getTokenType(): IElementType? = tokenType
    override fun getTokenStart(): Int = tokenStart
    override fun getTokenEnd(): Int = tokenEnd
    override fun getBufferSequence(): CharSequence = buffer
    override fun getBufferEnd(): Int = endOffset

    private fun charAt(offset: Int): Char =
        if (offset < endOffset) buffer[offset] else '\u0000'

    private fun remaining(): CharSequence =
        buffer.subSequence(currentOffset, endOffset)

    private fun lookingAt(s: String): Boolean {
        if (currentOffset + s.length > endOffset) return false
        for (i in s.indices) {
            if (buffer[currentOffset + i] != s[i]) return false
        }
        return true
    }

    private fun isLineStart(): Boolean {
        if (currentOffset == startOffset) return true
        val prev = currentOffset - 1
        return prev >= startOffset && buffer[prev] == '\n'
    }

    override fun advance() {
        if (currentOffset >= endOffset) {
            tokenType = null
            return
        }

        tokenStart = currentOffset
        val c = charAt(currentOffset)
        lineStart = isLineStart()

        // Newline
        if (c == '\n') {
            currentOffset++
            tokenEnd = currentOffset
            tokenType = SolfaTokenTypes.NEWLINE
            isLyricsLine = false
            return
        }

        // At line start, determine line type
        if (lineStart) {
            // Skip leading whitespace for classification (but don't consume it yet)
            var probe = currentOffset
            while (probe < endOffset && buffer[probe] == ' ') probe++

            if (probe < endOffset) {
                val probeChar = buffer[probe]

                // Comment line
                if (probeChar == '#') {
                    currentOffset = consumeToEndOfLine()
                    tokenEnd = currentOffset
                    tokenType = SolfaTokenTypes.COMMENT
                    return
                }

                // Header line: starts with ':'
                if (probeChar == ':') {
                    inHeader = true
                    // Consume leading whitespace as whitespace
                    if (currentOffset < probe) {
                        currentOffset = probe
                        tokenEnd = currentOffset
                        tokenType = SolfaTokenTypes.WHITESPACE
                        return
                    }
                    // Consume the ':' prefix
                    currentOffset++
                    tokenEnd = currentOffset
                    tokenType = SolfaTokenTypes.HEADER_PREFIX
                    return
                }

                // After first blank line, we're past the header
                if (inHeader && probeChar == '\n') {
                    inHeader = false
                }

                // Lyrics line: starts with a digit, or "R " (refrain)
                if (!inHeader) {
                    val lineText = getRestOfLine(probe)
                    if (isLyricsLineStart(lineText, probe)) {
                        isLyricsLine = true
                    }
                }
            }
        }

        // Whitespace
        if (c == ' ' || c == '\t') {
            while (currentOffset < endOffset && (charAt(currentOffset) == ' ' || charAt(currentOffset) == '\t')) {
                currentOffset++
            }
            tokenEnd = currentOffset
            tokenType = SolfaTokenTypes.WHITESPACE
            return
        }

        // Inside header: parse key and value
        if (inHeader) {
            lexHeader(c)
            return
        }

        // Lyrics line content
        if (isLyricsLine) {
            lexLyricsLine(c)
            return
        }

        // Music line content
        lexMusicLine(c)
    }

    private fun lexHeader(c: Char) {
        // After HEADER_PREFIX, we expect the key name until next ':'
        if (c == ':') {
            currentOffset++
            tokenEnd = currentOffset
            tokenType = SolfaTokenTypes.HEADER_SUFFIX
            return
        }

        // Try to read header key (alpha + underscore chars)
        if (c.isLetter() || c == '_') {
            while (currentOffset < endOffset) {
                val ch = charAt(currentOffset)
                if (ch.isLetterOrDigit() || ch == '_') currentOffset++
                else break
            }
            tokenEnd = currentOffset
            // Check if next char is ':' — then this is a key
            if (charAt(currentOffset) == ':') {
                tokenType = SolfaTokenTypes.HEADER_KEY
            } else {
                tokenType = SolfaTokenTypes.HEADER_VALUE
            }
            return
        }

        // Everything else on a header line after the suffix ':' is the value
        currentOffset = consumeToEndOfLine()
        tokenEnd = currentOffset
        tokenType = SolfaTokenTypes.HEADER_VALUE
    }

    private fun lexMusicLine(c: Char) {
        // Voice label at start of music content (after optional whitespace)
        if (lineStart || isAfterNewlineAndWhitespace()) {
            val label = tryMatchVoiceLabel()
            if (label != null) {
                currentOffset += label.length
                tokenEnd = currentOffset
                tokenType = SolfaTokenTypes.VOICE_LABEL
                return
            }
        }

        // Double barline ||
        if (c == '|' && charAt(currentOffset + 1) == '|') {
            currentOffset += 2
            tokenEnd = currentOffset
            tokenType = SolfaTokenTypes.DOUBLE_BARLINE
            return
        }

        // Single barline |
        if (c == '|') {
            currentOffset++
            tokenEnd = currentOffset
            tokenType = SolfaTokenTypes.BARLINE
            return
        }

        // Soft barline !
        if (c == '!') {
            currentOffset++
            tokenEnd = currentOffset
            tokenType = SolfaTokenTypes.SOFT_BARLINE
            return
        }

        // Beat separator :
        if (c == ':') {
            currentOffset++
            tokenEnd = currentOffset
            tokenType = SolfaTokenTypes.BEAT_SEPARATOR
            return
        }

        // Subbeat separator .
        if (c == '.') {
            currentOffset++
            tokenEnd = currentOffset
            tokenType = SolfaTokenTypes.SUBBEAT_SEPARATOR
            return
        }

        // Rest *
        if (c == '*') {
            currentOffset++
            tokenEnd = currentOffset
            tokenType = SolfaTokenTypes.REST
            return
        }

        // Hold -
        if (c == '-') {
            currentOffset++
            tokenEnd = currentOffset
            tokenType = SolfaTokenTypes.HOLD
            return
        }

        // Octave up '
        if (c == '\'') {
            currentOffset++
            tokenEnd = currentOffset
            tokenType = SolfaTokenTypes.OCTAVE_UP
            return
        }

        // Staccato , (before a note) or Octave down , (after a note)
        if (c == ',') {
            currentOffset++
            tokenEnd = currentOffset
            // Determine by context: if previous token was a note or octave mark, it's octave down
            tokenType = SolfaTokenTypes.OCTAVE_DOWN
            return
        }

        // Melisma prefix _
        if (c == '_') {
            currentOffset++
            tokenEnd = currentOffset
            tokenType = SolfaTokenTypes.MELISMA
            return
        }

        // Chord brackets
        if (c == '<') {
            currentOffset++
            tokenEnd = currentOffset
            tokenType = SolfaTokenTypes.CHORD_OPEN
            return
        }
        if (c == '>') {
            currentOffset++
            tokenEnd = currentOffset
            tokenType = SolfaTokenTypes.CHORD_CLOSE
            return
        }

        // Parenthesized expressions: dynamics, navigation, modulation hints
        if (c == '(') {
            val closeIdx = buffer.indexOf(')', currentOffset + 1)
            if (closeIdx != -1 && closeIdx < endOffset) {
                val content = buffer.subSequence(currentOffset + 1, closeIdx).toString()
                currentOffset = closeIdx + 1
                tokenEnd = currentOffset
                tokenType = when {
                    NAVIGATION.any { content.startsWith(it) } -> SolfaTokenTypes.NAVIGATION
                    else -> SolfaTokenTypes.DYNAMICS
                }
                return
            }
        }

        // Chromatic notes (2-char, must check before single-char natural notes)
        if (currentOffset + 1 < endOffset) {
            val twoChar = buffer.subSequence(currentOffset, currentOffset + 2).toString()
            if (CHROMATIC_NOTES.contains(twoChar)) {
                currentOffset += 2
                tokenEnd = currentOffset
                tokenType = SolfaTokenTypes.CHROMATIC_NOTE
                return
            }
        }

        // Natural notes (single char)
        if (c in NATURAL_NOTES) {
            currentOffset++
            tokenEnd = currentOffset
            tokenType = SolfaTokenTypes.NOTE
            return
        }

        // Modulation separator /
        if (c == '/') {
            currentOffset++
            tokenEnd = currentOffset
            tokenType = SolfaTokenTypes.BEAT_SEPARATOR
            return
        }

        // Comment mid-line (shouldn't happen per spec, but handle gracefully)
        if (c == '#') {
            currentOffset = consumeToEndOfLine()
            tokenEnd = currentOffset
            tokenType = SolfaTokenTypes.COMMENT
            return
        }

        // Fallback: bad character
        currentOffset++
        tokenEnd = currentOffset
        tokenType = SolfaTokenTypes.BAD_CHARACTER
    }

    private fun lexLyricsLine(c: Char) {
        // Lyrics prefix: digits, R, or voice labels at the very start
        if (lineStart || isAfterNewlineAndWhitespace()) {
            // Check for digit prefix (verse number)
            if (c.isDigit()) {
                while (currentOffset < endOffset && charAt(currentOffset).isDigit()) {
                    currentOffset++
                }
                tokenEnd = currentOffset
                tokenType = SolfaTokenTypes.LYRICS_PREFIX
                return
            }
            // Check for "R" refrain prefix
            if (c == 'R' && (currentOffset + 1 >= endOffset || charAt(currentOffset + 1) == ' ')) {
                currentOffset++
                tokenEnd = currentOffset
                tokenType = SolfaTokenTypes.LYRICS_PREFIX
                return
            }
            // Voice labels in lyrics prefix (e.g. "SA", "1SA")
            val label = tryMatchVoiceLabel()
            if (label != null) {
                currentOffset += label.length
                tokenEnd = currentOffset
                tokenType = SolfaTokenTypes.LYRICS_PREFIX
                return
            }
        }

        // Rest of lyrics line is text
        currentOffset = consumeToEndOfLine()
        tokenEnd = currentOffset
        tokenType = SolfaTokenTypes.LYRICS_TEXT
    }

    private fun consumeToEndOfLine(): Int {
        var i = currentOffset
        while (i < endOffset && buffer[i] != '\n') i++
        return i
    }

    private fun getRestOfLine(from: Int): String {
        var i = from
        while (i < endOffset && buffer[i] != '\n') i++
        return buffer.subSequence(from, i).toString()
    }

    private fun isLyricsLineStart(lineText: String, probeOffset: Int): Boolean {
        if (lineText.isEmpty()) return false
        val first = lineText[0]
        // Starts with digit → lyrics (verse number)
        if (first.isDigit()) return true
        // Starts with "R " → refrain
        if (first == 'R' && lineText.length > 1 && lineText[1] == ' ') return true
        // Doesn't start with voice label followed by | or space-| → lyrics
        // Music lines typically have: VOICE_LABEL <space> | or just |
        // If line has no | or : it's likely lyrics
        if (!lineText.contains('|') && !lineText.contains(':')) return true
        return false
    }

    private fun isAfterNewlineAndWhitespace(): Boolean {
        var i = currentOffset - 1
        while (i >= startOffset && (buffer[i] == ' ' || buffer[i] == '\t')) i--
        return i >= startOffset && buffer[i] == '\n'
    }

    private fun tryMatchVoiceLabel(): String? {
        // Try longest match first: PR, PL, then S, A, T, B (optionally followed by digits)
        for (label in listOf("PR", "PL")) {
            if (lookingAt(label)) {
                var end = currentOffset + label.length
                // Check it's followed by space or |
                if (end < endOffset && (charAt(end) == ' ' || charAt(end) == '|')) {
                    return label
                }
            }
        }
        for (base in listOf("S", "A", "T", "B")) {
            if (lookingAt(base)) {
                var end = currentOffset + base.length
                // Optionally followed by digit (S1, A2, etc.)
                while (end < endOffset && charAt(end).isDigit()) end++
                val candidate = buffer.subSequence(currentOffset, end).toString()
                // Must be followed by space or |
                if (end < endOffset && (charAt(end) == ' ' || charAt(end) == '|')) {
                    return candidate
                }
            }
        }
        return null
    }
}
