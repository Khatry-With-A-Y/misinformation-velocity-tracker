"""Idempotent multilingual demo seeder.

Populates the wiped database with curated claim groups that showcase
cross-language chaining (English, Romanized Nepali, Devanagari) and
believable mutation trees — without any Gemini generation calls
(canonicals are hand-written in English; only embeddings hit the API).

Idempotency: every row is tagged source='seed_demo'. On start the seeder
deletes all claims with that source (the FK cascade clears their variants),
then reinserts. User submissions (source='submission') and news rows are
never touched.

Usage (from backend/):
    python -m scripts.seed_demo

Or via Docker:
    docker compose exec backend python -m scripts.seed_demo
"""
import sys
from datetime import UTC, datetime, timedelta

# Ensure app modules are importable inside the container
sys.path.insert(0, "/app")

from app.core import supabase as db
from app.services import embeddings
from app.services.tree import reconstruct_parents

SEED_SOURCE = "seed_demo"

# Each group: one claim (known English canonical, no Gemini needed) plus
# 2-3 variants spanning English / Romanized Nepali / Devanagari across
# varied platforms. "_hours" staggers variant timestamps inside the group.
SEED_GROUPS = [
    {
        "claim": {
            "canonical": "Drinking hot water cures dengue fever",
            "domain": "health",
            "language": "mixed",
            "label": "FAKE",
            "verdict": "FAKE",
            "rationale": (
                "There is no cure for dengue; treatment is supportive "
                "(fluids, rest, fever management). Hot water does not kill "
                "the dengue virus."
            ),
        },
        "variants": [
            {
                "text": "Drinking hot water cures dengue fever, no medicine needed!",
                "platform": "facebook",
                "language": "en",
                "mutation_type": "original",
                "_hours": 0,
            },
            {
                "text": "Tato pani le dengue niko hunchha, aushadi nachahine ho re",
                "platform": "whatsapp",
                "language": "romanized",
                "mutation_type": "translation",
                "_hours": 22,
            },
            {
                "text": "तातो पानी पिएर डेङ्गु पूरै निको हुन्छ, अस्पताल जानु पर्दैन",
                "platform": "x",
                "language": "ne",
                "mutation_type": "translation",
                "_hours": 51,
            },
        ],
    },
    {
        "claim": {
            "canonical": "COVID-19 vaccines contain microchips to track citizens",
            "domain": "health",
            "language": "mixed",
            "label": "FAKE",
            "verdict": "FAKE",
            "rationale": (
                "Vaccine vials contain no electronics. This claim has been "
                "debunked repeatedly by independent fact-checkers worldwide."
            ),
        },
        "variants": [
            {
                "text": "BREAKING: Covid vaccines have microchips so the government can track everyone",
                "platform": "facebook",
                "language": "en",
                "mutation_type": "original",
                "_hours": 0,
            },
            {
                "text": "Covid khop ma microchip cha re, sarkar le sabai lai track garcha",
                "platform": "whatsapp",
                "language": "romanized",
                "mutation_type": "translation",
                "_hours": 30,
            },
            {
                "text": "कोभिड खोपमा माइक्रोचिप छ, सरकारले नागरिकलाई ट्र्याक गर्दैछ",
                "platform": "tiktok",
                "language": "ne",
                "mutation_type": "translation",
                "_hours": 68,
            },
        ],
    },
    {
        "claim": {
            "canonical": "Ballot boxes from Kathmandu were found dumped in the Bagmati river",
            "domain": "election",
            "language": "mixed",
            "label": "UNVERIFIED",
            "verdict": "UNVERIFIED",
            "rationale": (
                "No credible outlet or the Election Commission has confirmed "
                "any ballot boxes recovered from the Bagmati; verification is "
                "required before amplification."
            ),
        },
        "variants": [
            {
                "text": "Ballot boxes from Kathmandu found dumped in the Bagmati river before counting!!",
                "platform": "x",
                "language": "en",
                "mutation_type": "original",
                "_hours": 0,
            },
            {
                "text": "Kathmandu ka matpeti Bagmati ma phaliyeko bhetiyo re, chunav dhandali!",
                "platform": "facebook",
                "language": "romanized",
                "mutation_type": "translation",
                "_hours": 14,
            },
            {
                "text": "काठमाडौंका मतपेटिका बागमती नदीमा फालिएको भेटियो, गणनाअघि नै!",
                "platform": "tiktok",
                "language": "ne",
                "mutation_type": "translation",
                "_hours": 40,
            },
        ],
    },
    {
        "claim": {
            "canonical": "The government will deduct Rs 500 monthly from every bank account as a digital tax",
            "domain": "government",
            "language": "mixed",
            "label": "FAKE",
            "verdict": "FAKE",
            "rationale": (
                "Neither the Ministry of Finance nor Nepal Rastra Bank has "
                "announced any such deduction; no gazette or circular exists."
            ),
        },
        "variants": [
            {
                "text": "New rule: government will cut Rs 500 every month from all bank accounts as digital tax",
                "platform": "facebook",
                "language": "en",
                "mutation_type": "original",
                "_hours": 0,
            },
            {
                "text": "Sarkar le digital tax bhandai sabai bank khata bata mahina ko Rs 500 katne bhayo re",
                "platform": "whatsapp",
                "language": "romanized",
                "mutation_type": "translation",
                "_hours": 26,
            },
            {
                "text": "सरकारले डिजिटल करका नाममा हरेक बैंक खाताबाट मासिक रु ५०० काट्ने भयो",
                "platform": "x",
                "language": "ne",
                "mutation_type": "translation",
                "_hours": 55,
            },
        ],
    },
    {
        "claim": {
            "canonical": "Voter ID cards issued after 2015 will not be valid in the upcoming election",
            "domain": "election",
            "language": "mixed",
            "label": "FAKE",
            "verdict": "FAKE",
            "rationale": (
                "The Election Commission has issued no such invalidation; "
                "voter rolls are based on the registered voter list, not the "
                "card's issue date."
            ),
        },
        "variants": [
            {
                "text": "Voter ID cards made after 2015 will NOT work in the upcoming election, get a new one now",
                "platform": "whatsapp",
                "language": "en",
                "mutation_type": "original",
                "_hours": 0,
            },
            {
                "text": "2015 pachi baneko voter card aba ko chunav ma chaldaina re, naya banauna paryo",
                "platform": "facebook",
                "language": "romanized",
                "mutation_type": "translation",
                "_hours": 19,
            },
        ],
    },
    {
        "claim": {
            "canonical": "The government is giving Rs 10,000 to every citizen who registers on a new relief portal",
            "domain": "government",
            "language": "mixed",
            "label": "FAKE",
            "verdict": "FAKE",
            "rationale": (
                "No such relief portal exists; circulating links are phishing "
                "pages harvesting citizenship and bank details."
            ),
        },
        "variants": [
            {
                "text": "Register on the new govt relief portal and get Rs 10,000 directly in your account. Link inside!",
                "platform": "facebook",
                "language": "en",
                "mutation_type": "original",
                "_hours": 0,
            },
            {
                "text": "Sarkar le naya rahat portal ma register garne sabai lai Rs 10,000 dine bhayo, link share gara",
                "platform": "whatsapp",
                "language": "romanized",
                "mutation_type": "translation",
                "_hours": 12,
            },
            {
                "text": "सरकारले नयाँ राहत पोर्टलमा दर्ता गर्ने हरेक नागरिकलाई रु १०,००० दिने भयो",
                "platform": "tiktok",
                "language": "ne",
                "mutation_type": "translation",
                "_hours": 44,
            },
        ],
    },
]


def clear_previous_seed() -> None:
    """Delete only prior seed rows. Claims cascade to their variants; an
    extra variants pass catches any stragglers. User submissions survive."""
    client = db.get_client()
    res = client.table("claims").delete().eq("source", SEED_SOURCE).execute()
    removed = len(res.data or [])
    client.table("variants").delete().eq("source", SEED_SOURCE).execute()
    print(f"[seed_demo] removed {removed} previous seed claims")


def seed() -> None:
    clear_previous_seed()

    # Stagger groups across the past ~14 days so velocity charts look alive.
    base = datetime.now(UTC) - timedelta(days=14)
    for i, group in enumerate(SEED_GROUPS):
        claim = dict(group["claim"])
        claim["source"] = SEED_SOURCE
        claim_id = db.insert_claim(**claim)

        group_base = base + timedelta(days=i * 2, hours=i * 5)
        variants = []
        for v in group["variants"]:
            variants.append({
                "text": v["text"],
                "platform": v["platform"],
                "language": v["language"],
                "mutation_type": v["mutation_type"],
                "ts": (group_base + timedelta(hours=v["_hours"])).isoformat(),
                "verdict": claim["verdict"],
                "rationale": claim["rationale"],
                "source": SEED_SOURCE,
            })

        texts = [v["text"] for v in variants]
        vecs = embeddings.embed_batch(texts)
        for v, vec in zip(variants, vecs):
            v["embedding"] = vec
            v["claim_id"] = claim_id

        inserted = db.insert_variants(variants)

        # Re-attach locally computed embeddings + ts (insert preserves order),
        # since Supabase returns the vector column as a string, not a float list.
        for r, v, vec in zip(inserted, variants, vecs):
            r["embedding"] = vec
            r["ts"] = v["ts"]

        reconstruct_parents(inserted)
        print(
            f"[seed_demo] claim {i + 1}/{len(SEED_GROUPS)} "
            f"({claim['domain']}) -> {len(inserted)} variants"
        )

    print("[seed_demo] done")


if __name__ == "__main__":
    seed()
