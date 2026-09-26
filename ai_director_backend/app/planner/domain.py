"""UI domain wins; Auto infers from the prompt."""

KEYWORDS = (
    ("space", ("space", "orbit", "station", "planet", "nasa", "zero-g", "spaceship")),
    ("zoo", ("zoo", "safari", "enclosure", "habitat", "lion", "tiger")),
    ("forest", ("forest", "woods", "jungle", "clearing")),
    ("park", ("park", "playground", "garden", "pond", "bench")),
    ("city", ("city", "street", "downtown", "alley", "skyscraper")),
    ("beach", ("beach", "shore", "ocean", "sand", "umbrella")),
    ("interior", ("living room", "bedroom", "office", "kitchen", "interior", "apartment", "sofa")),
)

VALID = {row[0] for row in KEYWORDS} | {"generic"}


def infer_domain(prompt: str) -> str:
    text = (prompt or "").lower()
    for domain, keys in KEYWORDS:
        if any(k in text for k in keys):
            return domain
    return "generic"


def resolve_domain(ui_domain: str | None, prompt: str) -> str:
    if ui_domain and ui_domain != "auto" and ui_domain in VALID:
        return ui_domain
    return infer_domain(prompt)
