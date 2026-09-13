# Utility Documentation: `app/utils/similarity.py`

## Overview
The `similarity.py` module provides pure-Python implementations of the Jaro and Jaro-Winkler string similarity algorithms.

### Architectural Rationale
- **Zero External Dependencies**: Avoids C/Rust-compiled packages (such as `jellyfish` or `Levenshtein`), ensuring complete cross-platform compatibility across Windows, Linux Alpine containers, and macOS without compilation toolchain requirements.
- **Optimized for Entity Names**: Jaro-Winkler is statistically proven to be the most effective edit-distance metric for short human names and corporate entities due to its prefix-weighting factor.

---

## Mathematical Formulation & Algorithm Details

### 1. `jaro_similarity(s1: str, s2: str) -> float`
Calculates standard Jaro similarity between two input strings, returning a score $0.0 \le S_j \le 1.0$:

$$S_j = \begin{cases} 
0 & \text{if } m = 0 \\ 
\frac{1}{3} \left( \frac{m}{|s_1|} + \frac{m}{|s_2|} + \frac{m - t}{m} \right) & \text{otherwise} 
\end{cases}$$

Where:
- $|s_1|$ and $|s_2|$ are the lengths of the respective strings.
- $m$ is the count of matching characters within a sliding window distance $\lfloor \frac{\max(|s_1|, |s_2|)}{2} \rfloor - 1$.
- $t$ is the number of half-transpositions (matching characters that appear in different relative sequences).

### 2. `jaro_winkler_similarity(s1: str, s2: str, p: float = 0.1, max_l: int = 4) -> float`
Extends Jaro similarity by applying a bonus for shared initial prefixes up to length $L \le \text{max\_l}$:

$$S_w = S_j + (L \cdot p \cdot (1 - S_j))$$

Where:
- $S_j$ is the base Jaro score.
- $L$ is the length of the common prefix between $s_1$ and $s_2$ (up to a standard maximum of 4 characters).
- $p$ is a constant scaling factor (standard default is $0.1$).
- **Threshold Gating**: The prefix boost is only applied if $S_j \ge 0.70$. If the base Jaro similarity is below $0.70$, the raw Jaro score is returned without amplification to guard against false inflation of completely distinct words.

---

## Performance & Edge Cases
- **Exact Matches**: Returns `1.0` immediately via identity check.
- **Empty Strings**: Returns `0.0` immediately if either string is empty.
- **Transposition Sensitivity**: Distinguishes between localized typographical errors (e.g., `"Arjun"` vs `"Arujn"`) and arbitrary substitutions.
