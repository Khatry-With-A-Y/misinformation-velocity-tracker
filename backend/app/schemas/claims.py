"""Pydantic schemas for the claims / mutation-tree API."""
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

Period = Literal["day", "week", "month", "year"]
TrustTier = Literal["VERIFIED_FALSE", "AI_FLAGGED", "UNVERIFIED"]


class IngestRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)

    @field_validator("text")
    @classmethod
    def text_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("text must not be blank")
        return value


class ResearchResource(BaseModel):
    name: str
    url: str
    advisory: str


class IngestResponse(BaseModel):
    id: str
    variant_id: str
    parent_id: Optional[str] = None
    matched: bool
    similarity: Optional[float] = Field(default=None, ge=-1, le=1)
    canonical: str
    domain: Literal["health", "election", "government", "finance", "education", "other"]
    language: Literal["en", "ne", "romanized", "mixed"]
    label: Literal["UNVERIFIED"]
    verdict: Literal["UNVERIFIED"]
    rationale: str
    research_resources: List[ResearchResource]
    variant_count: int = Field(ge=1)


class ClaimSummary(BaseModel):
    id: str
    canonical: str
    domain: Optional[str] = None
    language: Optional[str] = None
    label: Optional[str] = None
    source: Optional[str] = None
    verdict: Optional[str] = None
    rationale: Optional[str] = None
    variant_count: Optional[int] = None
    created_at: Optional[str] = None
    tier: TrustTier = "UNVERIFIED"
    confidence: Optional[float] = None
    assessed_at: Optional[str] = None
    evidence_url: Optional[str] = None
    evidence_title: Optional[str] = None
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None
    current_count: int = 0
    previous_count: int = 0
    top_platform: Optional[str] = None


class ClaimPage(BaseModel):
    items: List[ClaimSummary]
    total: int = Field(ge=0)
    next_cursor: Optional[str] = None


class RankingItem(BaseModel):
    id: str
    canonical: str
    domain: Optional[str] = None
    language: Optional[str] = None
    source: Optional[str] = None
    tier: str
    verdict: str
    confidence: Optional[float] = None
    rationale: Optional[str] = None
    model: Optional[str] = None
    assessed_at: Optional[str] = None
    evidence_url: Optional[str] = None
    evidence_title: Optional[str] = None
    current_count: int
    previous_count: int
    percent_change: Optional[float] = None
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None


class DistributionItem(BaseModel):
    label: str
    count: int


class TimelinePoint(BaseModel):
    date: str
    count: int
    cumulative: int


class ClaimAnalytics(BaseModel):
    summary: dict
    timeline: List[TimelinePoint]
    platforms: List[DistributionItem]
    languages: List[DistributionItem]
    mutations: List[DistributionItem]
    top_variants: List[dict]


class TreeNode(BaseModel):
    id: str
    label: str
    text: Optional[str] = None
    platform: Optional[str] = None
    ts: Optional[str] = None
    mutation_type: Optional[str] = None
    language: Optional[str] = None
    source: Optional[str] = None
    confidence: Optional[float] = None
    evidence_url: Optional[str] = None
    evidence_title: Optional[str] = None


class TreeEdge(BaseModel):
    source: str
    target: str


class TreeResponse(BaseModel):
    nodes: List[TreeNode]
    edges: List[TreeEdge]


class VelocityPoint(BaseModel):
    bucket: str
    count: int


class PlatformCount(BaseModel):
    platform: str
    count: int
