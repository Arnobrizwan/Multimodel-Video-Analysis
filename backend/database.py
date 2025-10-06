"""Database models and connection management"""
from sqlalchemy import create_engine, Column, String, Text, Integer, Float, DateTime, Boolean, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.pool import StaticPool
from datetime import datetime
from typing import Optional, List, Dict
import os
import json

# Database URL from environment or default to SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./video_analysis.db")

# Create engine
# For SQLite, use check_same_thread=False to allow usage across threads
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
else:
    # PostgreSQL or other databases
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


# ==================== Models ====================

class User(Base):
    """User model for authentication"""
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    username = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=True)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    # Relationships
    videos = relationship("Video", back_populates="owner", cascade="all, delete-orphan")


class Video(Base):
    """Video processing record"""
    __tablename__ = "videos"

    video_id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    youtube_url = Column(String, nullable=False)
    transcript = Column(Text, nullable=True)
    processing_mode = Column(String, nullable=False)  # "transcript" or "video_analysis"
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    owner = relationship("User", back_populates="videos")
    sections = relationship("Section", back_populates="video", cascade="all, delete-orphan")
    chunks = relationship("Chunk", back_populates="video", cascade="all, delete-orphan")
    visual_frames = relationship("VisualFrame", back_populates="video", cascade="all, delete-orphan")


class Section(Base):
    """Video section/chapter"""
    __tablename__ = "sections"

    id = Column(Integer, primary_key=True, autoincrement=True)
    video_id = Column(String, ForeignKey("videos.video_id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    summary = Column(Text, nullable=True)
    order = Column(Integer, nullable=False)  # Section order

    # Relationships
    video = relationship("Video", back_populates="sections")


class Chunk(Base):
    """Text chunk with embeddings for RAG"""
    __tablename__ = "chunks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    video_id = Column(String, ForeignKey("videos.video_id"), nullable=False, index=True)
    text = Column(Text, nullable=False)
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    embedding = Column(JSON, nullable=False)  # Store as JSON array
    order = Column(Integer, nullable=False)  # Chunk order

    # Relationships
    video = relationship("Video", back_populates="chunks")


class VisualFrame(Base):
    """Visual frame index with descriptions and embeddings"""
    __tablename__ = "visual_frames"

    id = Column(Integer, primary_key=True, autoincrement=True)
    video_id = Column(String, ForeignKey("videos.video_id"), nullable=False, index=True)
    timestamp = Column(Float, nullable=False)
    end_timestamp = Column(Float, nullable=True)
    description = Column(Text, nullable=False)
    image_base64 = Column(Text, nullable=False)
    embedding = Column(JSON, nullable=False)  # Store as JSON array

    # Relationships
    video = relationship("Video", back_populates="visual_frames")


class CacheEntry(Base):
    """Embedding cache for reuse"""
    __tablename__ = "cache_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    content_hash = Column(String, unique=True, nullable=False, index=True)
    task_type = Column(String, nullable=False)
    embedding = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    hit_count = Column(Integer, default=0)
    last_accessed = Column(DateTime, default=datetime.utcnow)


# ==================== Database Functions ====================

def create_tables():
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)


def get_db():
    """
    Dependency for getting database session.
    Use with FastAPI's Depends()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database (create tables)"""
    print("Initializing database...")
    create_tables()
    print("Database initialized successfully")


# ==================== Data Access Layer ====================

class VideoRepository:
    """Repository pattern for video operations"""

    def __init__(self, db: Session):
        self.db = db

    def create_video(
        self,
        video_id: str,
        user_id: str,
        youtube_url: str,
        transcript: Optional[str],
        processing_mode: str
    ) -> Video:
        """Create new video record"""
        video = Video(
            video_id=video_id,
            user_id=user_id,
            youtube_url=youtube_url,
            transcript=transcript,
            processing_mode=processing_mode
        )
        self.db.add(video)
        self.db.commit()
        self.db.refresh(video)
        return video

    def get_video(self, video_id: str) -> Optional[Video]:
        """Get video by ID"""
        return self.db.query(Video).filter(Video.video_id == video_id).first()

    def get_user_videos(self, user_id: str) -> List[Video]:
        """Get all videos for a user"""
        return self.db.query(Video).filter(Video.user_id == user_id).all()

    def delete_video(self, video_id: str) -> bool:
        """Delete video and related data"""
        video = self.get_video(video_id)
        if video:
            self.db.delete(video)
            self.db.commit()
            return True
        return False

    def add_sections(self, video_id: str, sections: List[Dict]):
        """Add sections to video"""
        for idx, section_data in enumerate(sections):
            section = Section(
                video_id=video_id,
                title=section_data["title"],
                start_time=section_data.get("start_time", 0.0),
                end_time=section_data.get("end_time", 0.0),
                summary=section_data.get("summary", ""),
                order=idx
            )
            self.db.add(section)
        self.db.commit()

    def add_chunks(self, video_id: str, chunks: List[Dict]):
        """Add text chunks to video"""
        for idx, chunk_data in enumerate(chunks):
            chunk = Chunk(
                video_id=video_id,
                text=chunk_data["text"],
                start_time=chunk_data.get("start", 0.0),
                end_time=chunk_data.get("end", 0.0),
                embedding=chunk_data.get("embedding", []),
                order=idx
            )
            self.db.add(chunk)
        self.db.commit()

    def add_visual_frames(self, video_id: str, frames: List[Dict]):
        """Add visual frames to video"""
        for frame_data in frames:
            frame = VisualFrame(
                video_id=video_id,
                timestamp=frame_data["timestamp"],
                end_timestamp=frame_data.get("end_timestamp"),
                description=frame_data["description"],
                image_base64=frame_data["image_base64"],
                embedding=frame_data.get("embedding", [])
            )
            self.db.add(frame)
        self.db.commit()

    def get_chunks(self, video_id: str) -> List[Chunk]:
        """Get all chunks for a video"""
        return self.db.query(Chunk).filter(
            Chunk.video_id == video_id
        ).order_by(Chunk.order).all()

    def get_visual_frames(self, video_id: str) -> List[VisualFrame]:
        """Get all visual frames for a video"""
        return self.db.query(VisualFrame).filter(
            VisualFrame.video_id == video_id
        ).all()


class CacheRepository:
    """Repository for embedding cache"""

    def __init__(self, db: Session):
        self.db = db

    def get(self, content_hash: str) -> Optional[CacheEntry]:
        """Get cache entry and update access stats"""
        entry = self.db.query(CacheEntry).filter(
            CacheEntry.content_hash == content_hash
        ).first()

        if entry:
            # Update stats
            entry.hit_count += 1
            entry.last_accessed = datetime.utcnow()
            self.db.commit()

        return entry

    def set(self, content_hash: str, task_type: str, embedding: Dict):
        """Store embedding in cache"""
        entry = CacheEntry(
            content_hash=content_hash,
            task_type=task_type,
            embedding=embedding
        )
        self.db.add(entry)
        self.db.commit()

    def clear_old_entries(self, days: int = 30):
        """Clear cache entries older than specified days"""
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(days=days)

        self.db.query(CacheEntry).filter(
            CacheEntry.last_accessed < cutoff
        ).delete()
        self.db.commit()

    def get_stats(self) -> Dict:
        """Get cache statistics"""
        total = self.db.query(CacheEntry).count()
        total_hits = self.db.query(CacheEntry).with_entities(
            CacheEntry.hit_count
        ).all()

        return {
            "total_entries": total,
            "total_hits": sum(h[0] for h in total_hits),
            "avg_hits_per_entry": sum(h[0] for h in total_hits) / total if total > 0 else 0
        }
