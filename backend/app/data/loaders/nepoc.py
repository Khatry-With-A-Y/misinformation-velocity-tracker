"""
Loader: theonlysanjeev/nepal-ooc-misinformation (NepOOC)

Role: the ONLY real spread/date signal. Provides real `posted_date`
(velocity slice), fact-check `article_url` / `article_title` (verdict-card
evidence), `named_entities` + `categories` (routing). Rows sharing a
`post_id` are grouped as one claim with several real-world variants.
"""
from collections import defaultdict

from datasets import load_dataset

from app.data.loaders.common import first_present, normalize_domain

DATASET_ID = "theonlysanjeev/nepal-ooc-misinformation"


def _to_list(val):
    if val is None:
        return None
    if isinstance(val, list):
        return [str(v) for v in val]
    return [s.strip() for s in str(val).split(",") if s.strip()]


def load_claims_with_variants(limit_claims: int = None) -> list[dict]:
    """
    Return a list of claim groups:
      {
        "claim": {canonical, domain, language, label, source},
        "variants": [ {text, platform, author, ts, verdict, rationale,
                       evidence_url, evidence_title, entities, source}, ... ]
      }
    """
    ds = load_dataset(DATASET_ID, split="train")

    groups = defaultdict(list)
    for row in ds:
        pid = first_present(row, "post_id", "id") or str(len(groups))
        groups[pid].append(row)

    out = []
    for pid, rows in groups.items():
        head = rows[0]
        canonical = first_present(head, "caption", "article_title", "text")
        if not canonical:
            continue
        domain = normalize_domain(
            first_present(head, "categories", "category", "domain")
        )
        claim = {
            "canonical": str(canonical).strip()[:1000],
            "domain": domain,
            "language": first_present(head, "language") or "ne",
            "label": "FAKE",
            "verdict": "FAKE",
            "rationale": first_present(head, "misinformation_type"),
            "source": DATASET_ID,
        }
        variants = []
        for r in rows:
            text = first_present(r, "caption", "article_title", "text")
            if not text:
                continue
            variants.append({
                "text": str(text).strip()[:2000],
                "platform": "facebook",
                "author": first_present(r, "author"),
                "ts": first_present(r, "posted_date", "date"),
                "verdict": "FAKE",
                "rationale": first_present(r, "misinformation_type"),
                "evidence_url": first_present(r, "article_url"),
                "evidence_title": first_present(r, "article_title"),
                "entities": _to_list(first_present(r, "named_entities")),
                "language": first_present(r, "language") or claim["language"],
                "source": DATASET_ID,
            })
        if variants:
            out.append({"claim": claim, "variants": variants})

    if limit_claims:
        out = out[:limit_claims]
    print(f"[nepoc] loaded {len(out)} claim groups "
          f"({sum(len(g['variants']) for g in out)} variants)")
    return out
