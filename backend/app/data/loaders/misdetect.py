"""
Loader: cair-nepal/MisDetect-CAIR (MIT licensed)

Role: ready-made explainable VERDICTS. We take a small labeled slice per
domain and use the `rationale` / `claim_type` / `annotation_confidence`
fields to power the verdict card and sanity-check domain routing.
Each row becomes a standalone claim + single variant carrying the verdict.
"""
from huggingface_hub import hf_hub_download
import pandas as pd

from app.config import get_settings
from app.data.loaders.common import first_present, normalize_domain, normalize_label

settings = get_settings()

DATASET_ID = "cair-nepal/MisDetect-CAIR"

# The dataset currently exposes Croissant metadata through the default HF
# builder, while the actual examples live in repository CSV files.
FILES = {
    "data/educational_reddit.csv": ("education", "reddit"),
    "data/healthcare_x.csv": ("health", "x"),
    "data/political_reddit.csv": ("government", "reddit"),
    "data/political_x.csv": ("government", "x"),
}


def _iter_file_rows(filename: str, rows_per_domain: int):
    path = hf_hub_download(repo_id=DATASET_ID, filename=filename, repo_type="dataset")
    frame = pd.read_csv(path, nrows=rows_per_domain * 5)
    for row in frame.fillna("").to_dict(orient="records"):
        yield row


def load_verdict_slice(rows_per_domain: int = None) -> list[dict]:
    """
    Return a flat list of claim groups (each with one variant) carrying
    the pre-built verdict/rationale so the verdict card needs no extra AI call.
    """
    rows_per_domain = rows_per_domain or settings.MISDETECT_ROWS_PER_DOMAIN
    out = []

    for filename, (domain_hint, platform) in FILES.items():
        try:
            rows = _iter_file_rows(filename, rows_per_domain)
        except Exception as e:
            print(f"[misdetect] skip file {filename}: {e}")
            continue

        count = 0
        for row in rows:
            if count >= rows_per_domain:
                break
            text = first_present(row, "text", "tweet", "content", "post", "body", "Body")
            title = first_present(row, "title", "Title")
            if title and text:
                text = f"{title}. {text}"
            elif title:
                text = title
            if not text:
                continue
            label = normalize_label(
                first_present(row, "is_misinformation", "label_value", "label")
            )
            claim = {
                "canonical": str(text).strip()[:1000],
                "domain": normalize_domain(
                    first_present(row, "domain", "Domain", "category") or domain_hint
                ),
                "language": "en",
                "label": label,
                "verdict": label,
                "rationale": first_present(row, "rationale"),
                "source": DATASET_ID,
            }
            variant = {
                "text": str(text).strip()[:2000],
                "platform": platform,
                "author": None,
                "ts": None,  # no usable timestamps in this corpus
                "verdict": label,
                "rationale": first_present(row, "rationale"),
                "confidence": first_present(row, "annotation_confidence"),
                "entities": None,
                "language": "en",
                "source": DATASET_ID,
            }
            out.append({"claim": claim, "variants": [variant]})
            count += 1
        print(f"[misdetect] {filename}: took {count} rows")

    print(f"[misdetect] total {len(out)} verdict rows")
    return out
