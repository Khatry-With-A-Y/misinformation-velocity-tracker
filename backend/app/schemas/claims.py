"""Pydantic schemas for the claims / mutation-tree API."""
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


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


class TreeNode(BaseModel):
    id: str
    label: str
    platform: Optional[str] = None
    ts: Optional[str] = None
    mutation_type: Optional[str] = None


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
