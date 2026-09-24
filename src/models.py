"""Data models and schemas for Mansam AI Concierge."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


@dataclass
class Chunk:
    """Represents a single RAG knowledge chunk."""

    chunk_id: str
    source: str
    type: str
    text: str
    location: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ChatMessage(BaseModel):
    """Single message in a conversational session."""

    role: str = Field(..., description="'user', 'assistant', or 'system'")
    content: str


class ChatRequest(BaseModel):
    """Incoming user query request."""

    message: str = Field(..., min_length=1)
    history: List[ChatMessage] = Field(default_factory=list)
    language: Optional[str] = Field(default="auto", description="'auto', 'ar', or 'en'")
    mode: Optional[str] = Field(default="concierge", description="'concierge', 'heritage', 'galaxy', 'support'")


class ProductCard(BaseModel):
    """Structured product preview card."""

    name: str
    collection: str
    price_sar: float
    size: str
    notes: List[str] = Field(default_factory=list)
    mood: Optional[str] = None
    url: Optional[str] = None


class ChatResponse(BaseModel):
    """Concierge response payload."""

    reply: str
    language: str
    sources: List[str] = Field(default_factory=list)
    products: List[ProductCard] = Field(default_factory=list)
    suggested_product_url: Optional[str] = None
    ticket_id: Optional[str] = None
    whatsapp_link: Optional[str] = None


class GalaxyCategory(BaseModel):
    """The Galaxy 7-mood emotional classification."""

    id: str
    name_en: str
    name_ar: str
    description_en: str
    description_ar: str
    fragrances: List[str]
    olfactive_profile: str


class TicketRequest(BaseModel):
    """Request to create a concierge follow-up ticket."""

    customer_name: str
    phone: str
    preferred_fragrance: Optional[str] = None
    city: Optional[str] = None
    notes: Optional[str] = None
