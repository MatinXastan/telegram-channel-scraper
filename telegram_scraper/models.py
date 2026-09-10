"""
Data models for Telegram posts, media, reactions, and channel information.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class PostReaction(BaseModel):
    """Represents an emoji reaction and its count on a message."""
    emoji: str
    count: int


class ForwardInfo(BaseModel):
    """Represents forwarded source details."""
    from_name: Optional[str] = None
    from_url: Optional[str] = None


class LinkPreview(BaseModel):
    """Represents an embedded web page preview inside a post."""
    title: Optional[str] = None
    site_name: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    url: Optional[str] = None


class PollOption(BaseModel):
    """Option inside a Telegram poll."""
    text: str
    percent: str


class PollInfo(BaseModel):
    """Represents an embedded poll."""
    question: str
    options: List[PollOption] = Field(default_factory=list)
    total_votes: Optional[str] = None


class MediaAttachment(BaseModel):
    """Represents an attached media item (photo, video, audio, voice, document, etc.)."""
    type: str = Field(..., description="photo, video, voice, audio, document, gif, sticker")
    url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    duration: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[str] = None
    local_path: Optional[str] = None


class TelegramPost(BaseModel):
    """Complete structure of a scraped Telegram post."""
    id: int
    channel: str
    url: str
    date_iso: Optional[str] = None
    date_formatted: Optional[str] = None
    text: str = ""
    raw_html: Optional[str] = None
    views: Optional[str] = None
    views_numeric: Optional[int] = None
    is_pinned: bool = False
    is_forwarded: bool = False
    forward_info: Optional[ForwardInfo] = None
    reply_to_post_id: Optional[int] = None
    reactions: List[PostReaction] = Field(default_factory=list)
    total_reactions_count: int = 0
    media: List[MediaAttachment] = Field(default_factory=list)
    link_preview: Optional[LinkPreview] = None
    poll: Optional[PollInfo] = None


class ChannelInfo(BaseModel):
    """Channel header and profile metadata."""
    username: str
    title: Optional[str] = None
    description: Optional[str] = None
    subscribers: Optional[str] = None
    subscribers_numeric: Optional[int] = None
    avatar_url: Optional[str] = None
    is_verified: bool = False


class ScrapeResult(BaseModel):
    """Overall result of a scraping session."""
    channel: ChannelInfo
    posts: List[TelegramPost] = Field(default_factory=list)
    total_scraped: int = 0
    scraped_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    engine_used: str = "unknown"
