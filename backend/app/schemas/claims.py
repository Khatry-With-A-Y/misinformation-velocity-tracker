"""Pydantic schemas for the claims / mutation-tree API."""
from typing import List, Optional
from pydantic import BaseModel


class IngestRequest(BaseModel):
    text: str


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
