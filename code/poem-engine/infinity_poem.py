#!/usr/bin/env python3
"""
∞ Poem Engine — Generative poetry from mathematical constants.

Each constant's digits are mapped to phonemes, syllables, and line breaks,
producing verse that is structurally determined by the fabric of mathematics.
"""

import math
import sys
from dataclasses import dataclass
from typing import List


# ─── Phoneme mapping: digit → (syllable, stress_pattern) ───
PHONEME_MAP = {
    0: ("void",   False),
    1: ("one",    True),
    2: ("twin",   True),
    3: ("tri",    False),
    4: ("quar",   True),
    5: ("pen",    False),
    6: ("hex",    True),
    7: ("sep",    False),
    8: ("oc",     True),
    9: ("nov",    False),
}

# Word pools indexed by stress (stressed/unstressed)
STRESSED_WORDS = [
    "light", "dream", "fire", "stone", "breath", "night", "deep",
    "fall", "rise", "wave", "dark", "star", "bone", "time",
    "truth", "mind", "soul", "veil", "form", "void", "pulse",
    "edge", "core", "seed", "ash", "blade", "fate", "call",
]

UNSTRESSED_WORDS = [
    "the", "of", "in", "and", "a", "to", "from", "with", "on",
    "through", "by", "as", "at", "for", "but", "or", "yet",
    "so", "if", "when", "where", "how", "all", "each", "every",
    "some", "any", "no", "not", "still", "only", "even",
]

END_WORDS = [
    "remains", "unfolds", "dissolves", "emerges", "converges",
    "fractures", "remembers", "forgets", "becomes", "returns",
    "lingers", "vanishes", "persists", "awakens", "transforms",
    "oscillates", "reverberates", "echoes", "subsides", "endures",
]


@dataclass
class PoemLine:
    words: List[str]
    digit_source: List[int]
    is_end: bool = False

    def __str__(self):
        return " ".join(self.words).capitalize() + ("." if self.is_end else ",")


def extract_digits(value: float, count: int = 200) -> List[int]:
    """Extract decimal digits from a mathematical constant."""
    s = f"{value:.{count}f}"
    after_decimal = s.split(".")[1] if "." in s else ""
    return [int(d) for d in after_decimal[:count]]


def digit_to_word(digit: int, position: int, line_length: int) -> str:
    """Map a digit to a word based on its phoneme properties and position."""
    syllable, stressed = PHONEME_MAP[digit]
    
    # Position-aware word selection
    if position == line_length - 1:
        # Last word in line — use an "end word" seeded by digit
        return END_WORDS[digit * 2 % len(END_WORDS)]
    elif stressed:
        # Stressed syllable — content word
        return STRESSED_WORDS[(digit * 7 + position * 3) % len(STRESSED_WORDS)]
    else:
        # Unstressed — function word
        return UNSTRESSED_WORDS[(digit * 5 + position * 2) % len(UNSTRESSED_WORDS)]


def digits_to_poem(digits: List[int], lines: int = 8, words_per_line: int = 6) -> List[PoemLine]:
    """Transform a sequence of digits into a poem."""
    poem_lines = []
    idx = 0
    
    for line_num in range(lines):
        words = []
        digit_src = []
        
        # Vary line length slightly based on digits
        actual_length = words_per_line + (digits[idx % len(digits)] % 3 - 1)
        actual_length = max(3, actual_length)
        
        for pos in range(actual_length):
            if idx >= len(digits):
                idx = 0  # wrap around
            d = digits[idx]
            words.append(digit_to_word(d, pos, actual_length))
            digit_src.append(d)
            idx += 1
        
        is_end = (line_num == lines - 1) or (line_num % 4 == 3)
        poem_lines.append(PoemLine(words=words, digit_source=digit_src, is_end=is_end))
    
    return poem_lines


def format_poem(lines: List[PoemLine], title: str = "", source: str = "") -> str:
    """Format poem lines into a readable string."""
    parts = []
    if title:
        parts.append(f"  {title}")
        parts.append(f"  {'─' * len(title)}")
        if source:
            parts.append(f"  (from {source})")
        parts.append("")
    
    for line in lines:
        parts.append(f"  {line}")
    
    return "\n".join(parts)


def generate_from_constant(name: str, value: float, lines: int = 8, words: int = 6) -> str:
    """Generate a poem from a mathematical constant."""
    digits = extract_digits(value, count=300)
    poem = digits_to_poem(digits, lines=lines, words_per_line=words)
    return format_poem(poem, title=f"Poem of {name}", source=f"the digits of {name} ≈ {value:.10f}...")


# ─── Main ───

CONSTANTS = {
    "π":  math.pi,
    "e":  math.e,
    "φ":  (1 + math.sqrt(5)) / 2,  # golden ratio
    "√2": math.sqrt(2),
    "euler-mascheroni γ": 0.5772156649,
    "apéry's ζ(3)": 1.2020569032,
    "feigenbaum δ": 4.6692016091,
    "feigenbaum α": 2.5029078750,
}


if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    
    if count == 0 or count > len(CONSTANTS):
        names = list(CONSTANTS.keys())
    else:
        names = list(CONSTANTS.keys())[:count]
    
    for name in names:
        value = CONSTANTS[name]
        print(generate_from_constant(name, value, lines=10, words=5))
        print()
