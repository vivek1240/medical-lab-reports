def to_float(value: str | None) -> float | None:
    if value is None:
        return None
    cleaned = "".join(ch for ch in value if ch.isdigit() or ch in {".", "-"})
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def compute_delta(prev: float | None, curr: float | None) -> float | None:
    if prev is None or curr is None or prev == 0:
        return None
    return ((curr - prev) / abs(prev)) * 100.0
