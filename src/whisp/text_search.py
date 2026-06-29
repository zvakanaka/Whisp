def iter_body_match_offsets(text, term, low=None):
    """Yield case-insensitive offsets of term in text, skipping the first (title)
    line. Pass low=text.lower() to reuse an already-lowercased copy."""
    if not term:
        return
    if low is None:
        low = text.lower()
    t = term.lower()
    nl = low.find('\n')
    start = nl + 1 if nl != -1 else len(low)
    i = low.find(t, start)
    while i != -1:
        yield i
        i = low.find(t, i + len(t))


def body_match_offsets(text, term, low=None):
    """Case-insensitive offsets of term in text, skipping the first (title) line."""
    return list(iter_body_match_offsets(text, term, low))
