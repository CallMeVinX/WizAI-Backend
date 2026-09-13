"""Pure Python string similarity algorithms (Jaro-Winkler, Levenshtein).
Eliminates external C/Rust dependencies for cross-platform compatibility.
"""

def jaro_similarity(s1: str, s2: str) -> float:
    """Calculate Jaro similarity between two strings."""
    if s1 == s2:
        return 1.0

    len1, len2 = len(s1), len(s2)
    if len1 == 0 or len2 == 0:
        return 0.0

    match_distance = max(len1, len2) // 2 - 1
    if match_distance < 0:
        match_distance = 0

    s1_matches = [False] * len1
    s2_matches = [False] * len2

    matches = 0
    for i in range(len1):
        start = max(0, i - match_distance)
        end = min(i + match_distance + 1, len2)

        for j in range(start, end):
            if s2_matches[j]:
                continue
            if s1[i] != s2[j]:
                continue
            s1_matches[i] = True
            s2_matches[j] = True
            matches += 1
            break

    if matches == 0:
        return 0.0

    k = 0
    transpositions = 0
    for i in range(len1):
        if not s1_matches[i]:
            continue
        while not s2_matches[k]:
            k += 1
        if s1[i] != s2[k]:
            transpositions += 1
        k += 1

    t = transpositions / 2.0
    return (matches / len1 + matches / len2 + (matches - t) / matches) / 3.0


def jaro_winkler_similarity(s1: str, s2: str, p: float = 0.1, max_l: int = 4) -> float:
    """Calculate Jaro-Winkler similarity between two strings.
    
    Args:
        s1: First string
        s2: Second string
        p: Scaling factor (standard is 0.1)
        max_l: Maximum common prefix length to consider (standard is 4)
    """
    jaro_sim = jaro_similarity(s1, s2)
    if jaro_sim < 0.7:
        return jaro_sim

    # Find common prefix length
    l = 0
    for c1, c2 in zip(s1[:max_l], s2[:max_l]):
        if c1 == c2:
            l += 1
        else:
            break

    return jaro_sim + (l * p * (1.0 - jaro_sim))
