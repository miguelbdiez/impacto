"""Text normalisation shared by training and inference.

The OpenNN word tokenizer only keeps ASCII letters, digits and punctuation. The bytes of accented
letters are dropped and split the word ("más" -> "m", "s"; "pequeño" -> "peque", "o"). Every text is
therefore transliterated to ASCII before it reaches the model, both when building the training file
and when predicting, so both sides see exactly the same tokens.
"""

import re
import unicodedata

WHITESPACE = re.compile(r"\s+")

# Double quotes become single quotes because OpenNN switches to quoted-field parsing as soon as a
# data file contains one. Opening ¿ and ¡ carry no meaning once the closing sign is kept.
REPLACEMENTS = str.maketrans({
    '"': "'", "“": "'", "”": "'", "«": "'", "»": "'", "‘": "'", "’": "'",
    "¿": " ", "¡": " ", "…": "...", "–": "-", "—": "-",
})


def normalize_text(text: str) -> str:
    """Transliterate to ASCII ("pequeño" -> "pequeno") and collapse whitespace into single spaces."""
    # NFKD splits accented letters into base letter + combining mark, and the mark is dropped.
    # Any other non-ASCII character (emoji, symbols) becomes a space so it never glues two words.
    decomposed = unicodedata.normalize("NFKD", text.translate(REPLACEMENTS))
    ascii_text = "".join("" if unicodedata.combining(character)
                         else character if character.isascii()
                         else " "
                         for character in decomposed)

    return WHITESPACE.sub(" ", ascii_text).strip()
