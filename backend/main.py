from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, validator
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
import os
import json
import re
import numpy as np
import time
import tempfile
from pathlib import Path
from typing import List, Dict, Optional
from dotenv import load_dotenv
import yt_dlp
import cv2
import base64
import hashlib
from functools import lru_cache
from collections import OrderedDict
from datetime import timedelta
import logging
import traceback

# Import custom modules
from exceptions import (
    TranscriptNotAvailableError,
    VideoDownloadError,
    GeminiAPIError,
    EmbeddingGenerationError,
    VideoProcessingError,
    FrameExtractionError,
    InvalidVideoIDError,
    ChunkCreationError,
    create_error_response
)
from logging_config import setup_logging, app_logger, log_error, log_info, log_warning

# Import authentication
from auth import (
    get_current_user,
    get_current_user_optional,
    create_access_token,
    create_user,
    authenticate_user,
    create_demo_session,
    User,
    UserCreate,
    Token,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from access_control import check_video_access, associate_video_with_user
from rate_limiting import check_rate_limit

# Load environment variables
load_dotenv()

# Setup logging
log_level = os.getenv("LOG_LEVEL", "INFO")
structured_logging = os.getenv("STRUCTURED_LOGGING", "false").lower() == "true"
setup_logging(log_level, structured_logging)

log_info(app_logger, "Starting Multimodal Video Analysis API", log_level=log_level)

# Initialize FastAPI
app = FastAPI(title="Multimodal Video Analysis API")

# Configure CORS based on environment
def get_cors_origins():
    """Get allowed CORS origins from environment or use defaults"""
    origins_env = os.getenv("CORS_ORIGINS", "")

    if origins_env:
        # Production: Use comma-separated list from environment
        origins = [origin.strip() for origin in origins_env.split(",")]
        print(f"CORS: Using configured origins: {origins}")
        return origins
    else:
        # Development: Allow localhost variants
        dev_origins = [
            "http://localhost:5173",
            "http://localhost:3000",
            "http://localhost:3001",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:3001"
        ]
        print(f"CORS: Development mode - allowing localhost origins: {dev_origins}")
        return dev_origins

allowed_origins = get_cors_origins()

# Enable CORS with secure configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
    max_age=600,  # Cache preflight requests for 10 minutes
)

# Health check endpoint (must be defined before GEMINI_API_KEY check)
@app.get("/health")
async def health_check():
    """Health check endpoint for Docker and monitoring"""
    return {
        "status": "healthy",
        "service": "multimodal-video-analysis-api",
        "gemini_configured": bool(os.getenv("GEMINI_API_KEY"))
    }

# Initialize Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables")

genai.configure(api_key=GEMINI_API_KEY)

# Store video data in memory (for demo purposes)
# Structure: {video_id: {user_id: str, ...video_data}}
video_store = {}

# User-to-videos mapping for efficient lookup
user_videos = {}  # {user_id: [video_id1, video_id2, ...]}

# ==================== Embedding Cache ====================
class EmbeddingCache:
    """LRU cache for Gemini embeddings to reduce API calls and latency"""

    def __init__(self, maxsize=1000):
        self.cache = OrderedDict()
        self.maxsize = maxsize
        self.hits = 0
        self.misses = 0

    def _hash_content(self, content: str, task_type: str) -> str:
        """Create hash key from content and task type"""
        key = f"{task_type}:{content}"
        return hashlib.sha256(key.encode()).hexdigest()

    def get(self, content: str, task_type: str) -> Optional[Dict]:
        """Retrieve cached embedding if available"""
        key = self._hash_content(content, task_type)
        if key in self.cache:
            self.hits += 1
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            return self.cache[key]
        self.misses += 1
        return None

    def set(self, content: str, task_type: str, embedding: Dict):
        """Store embedding in cache"""
        key = self._hash_content(content, task_type)

        # Remove oldest if at capacity
        if len(self.cache) >= self.maxsize:
            self.cache.popitem(last=False)

        self.cache[key] = embedding

    def stats(self) -> Dict:
        """Get cache statistics"""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        return {
            "size": len(self.cache),
            "maxsize": self.maxsize,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": f"{hit_rate:.2f}%"
        }

    def clear(self):
        """Clear cache"""
        self.cache.clear()
        self.hits = 0
        self.misses = 0

# Initialize embedding cache
embedding_cache = EmbeddingCache(maxsize=1000)


# ==================== Pydantic Models ====================
class VideoRequest(BaseModel):
    youtube_url: str

    @validator('youtube_url')
    def validate_youtube_url(cls, v):
        """Validate YouTube URL format and whitelist domains"""
        import re
        from urllib.parse import urlparse

        # Length check
        if len(v) > 500:
            raise ValueError("URL too long (max 500 characters)")

        # Parse URL
        try:
            parsed = urlparse(v)
        except Exception:
            raise ValueError("Invalid URL format")

        # Whitelist YouTube domains only (SSRF protection)
        allowed_hosts = {
            'youtube.com',
            'www.youtube.com',
            'youtu.be',
            'm.youtube.com'
        }

        if parsed.hostname not in allowed_hosts:
            raise ValueError(
                f"Only YouTube URLs are allowed. Got hostname: {parsed.hostname}"
            )

        # Validate URL scheme
        if parsed.scheme not in ['http', 'https']:
            raise ValueError("Only HTTP/HTTPS URLs are allowed")

        # Validate YouTube URL format (support videos, shorts, and playlists)
        youtube_regex = r'^(https?://)?(www\.)?(youtube\.com/(watch\?v=|embed/|v/|shorts/|playlist\?list=)|youtu\.be/)[\w-]+.*$'
        if not re.match(youtube_regex, v):
            raise ValueError(
                "Invalid YouTube URL format. Expected format: "
                "https://www.youtube.com/watch?v=VIDEO_ID, playlist, or shorts"
            )

        return v


class ChatRequest(BaseModel):
    video_id: str
    question: str

    @validator('video_id')
    def validate_video_id(cls, v):
        """Validate video ID format"""
        import re

        # Length check
        if len(v) > 100:
            raise ValueError("Video ID too long (max 100 characters)")

        # Alphanumeric, hyphens, underscores only
        if not re.match(r'^[\w-]+$', v):
            raise ValueError("Video ID contains invalid characters")

        return v

    @validator('question')
    def validate_question(cls, v):
        """Validate question content"""
        # Length check
        if len(v) < 1:
            raise ValueError("Question cannot be empty")
        if len(v) > 2000:
            raise ValueError("Question too long (max 2000 characters)")

        # Strip whitespace
        v = v.strip()

        # Check not just whitespace
        if not v:
            raise ValueError("Question cannot be only whitespace")

        return v


class VisualSearchRequest(BaseModel):
    video_id: str
    query: str

    @validator('video_id')
    def validate_video_id(cls, v):
        """Validate video ID format"""
        import re

        if len(v) > 100:
            raise ValueError("Video ID too long (max 100 characters)")

        if not re.match(r'^[\w-]+$', v):
            raise ValueError("Video ID contains invalid characters")

        return v

    @validator('query')
    def validate_query(cls, v):
        """Validate search query"""
        # Length check
        if len(v) < 1:
            raise ValueError("Query cannot be empty")
        if len(v) > 500:
            raise ValueError("Query too long (max 500 characters)")

        # Strip whitespace
        v = v.strip()

        if not v:
            raise ValueError("Query cannot be only whitespace")

        return v


class Section(BaseModel):
    title: str
    start_time: float
    end_time: float
    summary: str


# ==================== Helper Functions ====================
def embedding_to_array(embedding) -> np.ndarray:
    """Normalize embedding object into numpy array."""
    if embedding is None:
        return np.array([])
    if isinstance(embedding, dict):
        values = embedding.get('values', [])
        return np.array(values, dtype=float)
    return np.array(embedding, dtype=float)


def get_cached_embedding(content: str, task_type: str):
    """Get embedding with caching to reduce API calls"""
    # Check cache first
    cached = embedding_cache.get(content, task_type)
    if cached is not None:
        return cached

    # Cache miss - call API
    result = genai.embed_content(
        model="models/text-embedding-004",
        content=content,
        task_type=task_type
    )

    # Store in cache
    embedding_cache.set(content, task_type, result['embedding'])

    return result['embedding']


def extract_video_id(url: str) -> str:
    """Extract YouTube video ID from various URL formats including Shorts"""
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&\n?#]+)',
        r'youtube\.com\/embed\/([^&\n?#]+)',
        r'youtube\.com\/v\/([^&\n?#]+)',
        r'youtube\.com\/shorts\/([^&\n?#]+)',  # YouTube Shorts
        r'youtu\.be\/shorts\/([^&\n?#]+)'      # Short youtu.be links
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    raise ValueError("Invalid YouTube URL format. Supported formats: youtube.com/watch?v=, youtu.be/, youtube.com/shorts/, youtube.com/embed/")


def get_playlist_video_ids(playlist_url: str) -> List[str]:
    """Extract all video IDs from a YouTube playlist"""
    import re

    # Extract playlist ID from URL
    playlist_id_match = re.search(r'list=([\w-]+)', playlist_url)
    if not playlist_id_match:
        raise ValueError("Invalid playlist URL")

    playlist_id = playlist_id_match.group(1)

    # Use yt-dlp to get playlist info
    ydl_opts = {
        'extract_flat': True,  # Don't download, just extract info
        'quiet': True,
        'no_warnings': True,
    }

    video_ids = []
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        playlist_info = ydl.extract_info(f'https://www.youtube.com/playlist?list={playlist_id}', download=False)

        if 'entries' in playlist_info:
            for entry in playlist_info['entries']:
                if entry and 'id' in entry:
                    video_ids.append(entry['id'])

    return video_ids


def get_transcript(video_id: str) -> Optional[List[Dict]]:
    """Fetch transcript from YouTube video - returns None if not available"""
    try:
        # Initialize the API
        ytt_api = YouTubeTranscriptApi()
        
        # Try to get transcript in multiple languages
        fetched_transcript = ytt_api.fetch(video_id, languages=['en', 'en-US', 'en-GB'])
        
        # Convert to raw data (list of dictionaries)
        return fetched_transcript.to_raw_data()
        
    except Exception as e:
        # Try to get any available transcript
        try:
            ytt_api = YouTubeTranscriptApi()
            transcript_list = ytt_api.list(video_id)
            
            # Get the first available transcript
            for transcript in transcript_list:
                fetched = transcript.fetch()
                return fetched.to_raw_data()
        except:
            pass
        
        # Return None if no transcript is available
        print(f"No transcript available for video {video_id}. Will use video analysis.")
        return None


def download_youtube_video(video_id: str, output_path: str) -> str:
    """Download YouTube video for Gemini analysis"""
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',  # Most flexible
        'outtmpl': output_path,
        'quiet': True,
        'no_warnings': True,
        'merge_output_format': 'mp4',  # Force MP4 output
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',
        }],
    }
    
    url = f'https://www.youtube.com/watch?v={video_id}'
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    
    return output_path


def extract_frames(video_path: str, max_frames: int = 12) -> List[Dict]:
    """Extract evenly spaced frames from the video and return base64 encoded images."""
    frames = []
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        print(f"Failed to open video for frame extraction: {video_path}")
        return frames

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

    if total_frames == 0:
        cap.release()
        return frames

    interval = max(1, total_frames // max_frames)
    frame_idx = 0

    while len(frames) < max_frames and frame_idx < total_frames:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        success, frame = cap.read()
        if not success:
            frame_idx += interval
            continue

        timestamp = frame_idx / fps
        success, buffer = cv2.imencode('.jpg', frame)
        if not success:
            frame_idx += interval
            continue

        image_base64 = base64.b64encode(buffer).decode('utf-8')
        frames.append({
            "timestamp": timestamp,
            "image_base64": image_base64
        })

        frame_idx += interval

    cap.release()
    return frames


def build_visual_index(frames: List[Dict]) -> List[Dict]:
    """Create visual index by describing frames with Gemini and generating embeddings."""
    if not frames:
        return []

    model = genai.GenerativeModel('gemini-2.5-pro')
    descriptions = []
    visual_index: List[Dict] = []

    for frame in frames:
        image_bytes = base64.b64decode(frame['image_base64'])
        prompt = "Describe this video frame in one concise sentence highlighting visible elements, people, actions, and any on-screen text. Respond with plain text only."
        response = model.generate_content([
            {"mime_type": "image/jpeg", "data": image_bytes},
            {"text": prompt}
        ])

        description = response.text.strip()
        descriptions.append(description)
        visual_index.append({
            "timestamp": frame['timestamp'],
            "description": description,
            "image_base64": frame['image_base64']
        })

    embed_result = genai.embed_content(
        model="models/text-embedding-004",
        content=descriptions,
        task_type="retrieval_document"
    )

    embeddings = embed_result['embedding']

    # When a single item is provided, embedding may not be a list
    if isinstance(embeddings, dict):
        embeddings = [embeddings]

    # CRITICAL: Validate embedding count matches frame count
    frames_count = len(visual_index)
    embeddings_count = len(embeddings)

    print(f"Visual index validation: {frames_count} frames -> {embeddings_count} embeddings")

    if embeddings_count != frames_count:
        error_msg = (
            f"Visual embedding count mismatch! Expected {frames_count} embeddings "
            f"for {frames_count} frames, but received {embeddings_count}. "
            f"Frame descriptions sample: {descriptions[:2] if len(descriptions) > 1 else descriptions}"
        )
        print(f"ERROR: {error_msg}")
        raise ValueError(error_msg)

    # Map embeddings to visual index with validation
    for idx in range(frames_count):
        try:
            emb_array = embedding_to_array(embeddings[idx])
            if emb_array.size == 0:
                print(f"WARNING: Empty embedding at frame index {idx}")
                raise ValueError(f"Empty embedding for frame {idx}")
            visual_index[idx]["embedding"] = emb_array.tolist()
        except (IndexError, KeyError) as e:
            error_msg = (
                f"Failed to map embedding to frame {idx}: {str(e)}. "
                f"Frames: {frames_count}, Embeddings: {embeddings_count}"
            )
            print(f"ERROR: {error_msg}")
            raise ValueError(error_msg)

    print(f"✓ Successfully mapped {frames_count} embeddings to visual frames")
    return visual_index


def upload_to_gemini(path: str, mime_type: str = "video/mp4"):
    """Uploads the given file to Gemini."""
    file = genai.upload_file(path, mime_type=mime_type)
    print(f"Uploaded file '{file.display_name}' as: {file.uri}")
    return file


def wait_for_files_active(files):
    """Waits for the given files to be active."""
    print("Waiting for file processing...")
    for name in (file.name for file in files):
        file = genai.get_file(name)
        while file.state.name == "PROCESSING":
            print(".", end="", flush=True)
            time.sleep(10)
            file = genai.get_file(name)
        if file.state.name != "ACTIVE":
            raise Exception(f"File {file.name} failed to process")
    print("...all files ready")
    print()


def analyze_video_with_gemini(video_file) -> Dict:
    """Analyze video using Gemini's native video understanding"""
    model = genai.GenerativeModel('gemini-2.5-pro')
    
    prompt = """Analyze this video and provide a detailed breakdown with timestamps.

Return ONLY a valid JSON object (no markdown formatting) in this exact format:
{
    "sections": [
        {
            "title": "Section Title",
            "start_time": 0.0,
            "end_time": 45.0,
            "summary": "Brief summary of what's covered in this section"
        }
    ],
    "transcript": "Full transcript or detailed description of the video content with approximate timestamps"
}

Create 3-7 logical sections based on the video content. Make timestamps precise and summaries concise (1-2 sentences).
For the transcript field, provide a detailed play-by-play description of what happens in the video with approximate timestamps."""
    
    response = model.generate_content([video_file, prompt])
    return parse_json_from_response(response.text)


def format_transcript_for_gemini(transcript: List[Dict]) -> str:
    """Format transcript with timestamps for Gemini"""
    formatted_lines = []
    for entry in transcript:
        timestamp = entry['start']
        text = entry['text']
        mins = int(timestamp // 60)
        secs = int(timestamp % 60)
        formatted_lines.append(f"[{mins:02d}:{secs:02d}] {text}")
    
    return "\n".join(formatted_lines)


def parse_json_from_response(text: str) -> Dict:
    """Extract and parse JSON from Gemini response"""
    # Try to find JSON in code blocks
    json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
    else:
        # Try to find JSON directly
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
        else:
            json_str = text
    
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse JSON response: {str(e)}\nResponse: {text[:500]}")


def create_chunks(transcript: List[Dict], chunk_duration: int = 30) -> List[Dict]:
    """Split transcript into chunks with timestamps"""
    chunks = []
    current_chunk = []
    chunk_start = 0
    
    for i, entry in enumerate(transcript):
        current_chunk.append(entry['text'])
        
        # Check if we should create a new chunk
        if i == len(transcript) - 1 or transcript[i + 1]['start'] - chunk_start >= chunk_duration:
            chunk_text = " ".join(current_chunk)
            chunk_end = entry['start'] + entry.get('duration', 3)
            
            chunks.append({
                "text": chunk_text,
                "start": chunk_start,
                "end": chunk_end
            })
            
            current_chunk = []
            if i < len(transcript) - 1:
                chunk_start = transcript[i + 1]['start']
    
    return chunks


# ==================== API Endpoints ====================
@app.get("/")
async def root():
    return {
        "message": "Multimodal Video Analysis API",
        "version": "1.0.0",
        "endpoints": {
            "POST /auth/register": "Register new user account",
            "POST /auth/login": "Login and get access token",
            "POST /auth/demo": "Get demo session token",
            "POST /process_video": "Process a YouTube video (requires auth)",
            "POST /chat": "Chat with video content (requires auth)",
            "POST /visual_search": "Search for visual content (requires auth)",
            "GET /videos": "List user's videos (requires auth)"
        }
    }


# ==================== Auth Endpoints ====================
@app.post("/auth/register", response_model=Token)
async def register(user_create: UserCreate):
    """Register new user account"""
    try:
        user = create_user(
            username=user_create.username,
            password=user_create.password,
            email=user_create.email
        )

        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user["user_id"]}, expires_delta=access_token_expires
        )

        return Token(
            access_token=access_token,
            token_type="bearer",
            user_id=user["user_id"]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/auth/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Login with username and password"""
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password"
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["user_id"]}, expires_delta=access_token_expires
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        user_id=user["user_id"]
    )


@app.post("/auth/demo", response_model=Token)
async def demo_session():
    """Create anonymous demo session (no registration required)"""
    access_token, user_id = create_demo_session()
    return Token(
        access_token=access_token,
        token_type="bearer",
        user_id=user_id
    )


@app.get("/auth/me", response_model=User)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return current_user


@app.post("/process_video", dependencies=[Depends(check_rate_limit)])
async def process_video(request: VideoRequest, current_user: User = Depends(get_current_user)):
    """
    Process a YouTube video or playlist:
    1. Check if URL is a playlist - if so, extract first video
    2. Extract video ID
    3. Try to get transcript OR download and analyze video with Gemini
    4. Generate section breakdown
    5. Create embeddings
    """
    try:
        # Check if this is a playlist URL
        is_playlist = 'list=' in request.youtube_url and 'playlist?' in request.youtube_url

        if is_playlist:
            print(f"Detected playlist URL, extracting videos...")
            video_ids = get_playlist_video_ids(request.youtube_url)

            if not video_ids:
                raise HTTPException(status_code=400, detail="Playlist is empty or invalid")

            # For now, process only the first video
            # TODO: Allow user to select which video or process all
            video_id = video_ids[0]
            print(f"Processing first video from playlist: {video_id} (total: {len(video_ids)} videos)")
        else:
            # Step 1: Extract video ID
            video_id = extract_video_id(request.youtube_url)
            print(f"Processing video: {video_id}")
        
        # Step 2: Try to get transcript
        transcript = get_transcript(video_id)
        
        sections = []
        chunks = []
        visual_index: List[Dict] = []
        video_file_path = None
        temp_dir = None
        
        if transcript:
            # PATH A: Video has transcript
            print(f"✓ Transcript available: {len(transcript)} entries")
            
            # Format transcript for Gemini
            formatted_transcript = format_transcript_for_gemini(transcript)
            
            # Generate section breakdown with Gemini
            model = genai.GenerativeModel('gemini-2.5-pro')
            
            prompt = f"""Analyze this video transcript and create a section breakdown.
Each section should have a clear title, start time (in seconds), end time (in seconds), and brief summary.

Transcript with timestamps:
{formatted_transcript}

Return ONLY a valid JSON object (no markdown formatting) in this exact format:
{{
    "sections": [
        {{
            "title": "Introduction",
            "start_time": 0.0,
            "end_time": 45.0,
            "summary": "Brief summary of what's covered in this section"
        }}
    ]
}}

Create 3-7 logical sections based on the content. Make timestamps precise and summaries concise (1-2 sentences)."""
            
            response = model.generate_content(prompt)
            print(f"Gemini response received: {response.text[:200]}...")
            
            section_data = parse_json_from_response(response.text)
            sections = section_data.get('sections', [])
            
            # Create chunks from transcript
            chunks = create_chunks(transcript)
            print(f"Created {len(chunks)} chunks for embeddings")

            # Download video to support visual indexing
            temp_dir = tempfile.mkdtemp()
            video_file_path = os.path.join(temp_dir, f"{video_id}.mp4")
            print("Downloading video for visual indexing...")
            download_youtube_video(video_id, video_file_path)
            print(f"✓ Video downloaded for visual indexing: {video_file_path}")
            
        else:
            # PATH B: No transcript - use Gemini video analysis
            print("✗ No transcript available - using Gemini video analysis")
            
            # Download video to temporary location
            temp_dir = tempfile.mkdtemp()
            video_file_path = os.path.join(temp_dir, f"{video_id}.mp4")
            
            print(f"Downloading video...")
            download_youtube_video(video_id, video_file_path)
            print(f"✓ Video downloaded: {video_file_path}")
            
            # Upload to Gemini
            print("Uploading video to Gemini...")
            video_file = upload_to_gemini(video_file_path)
            
            # Wait for processing
            wait_for_files_active([video_file])
            
            # Analyze video with Gemini
            print("Analyzing video with Gemini...")
            analysis_result = analyze_video_with_gemini(video_file)
            
            sections = analysis_result.get('sections', [])
            video_content = analysis_result.get('transcript', '')
            
            print(f"✓ Video analyzed: {len(sections)} sections generated")
            
            # Create chunks from video content description
            # Split video content into ~30 second chunks based on sections
            for i, section in enumerate(sections):
                chunks.append({
                    "text": f"{section['title']}: {section['summary']}",
                    "start": section['start_time'],
                    "end": section['end_time'],
                })
            
            # Keep video file for visual indexing; cleanup deferred below
            try:
                genai.delete_file(video_file.name)
            except:
                pass
        
        # Step 3: Create embeddings with Gemini API
        print(f"Created {len(chunks)} chunks for embeddings")
        
        # Generate embeddings using Gemini API
        chunk_texts = [chunk['text'] for chunk in chunks]

        print("Generating embeddings with Gemini...")
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=chunk_texts,
            task_type="retrieval_document"
        )

        embeddings = result['embedding']

        # Ensure embeddings iterable
        if isinstance(embeddings, dict):
            embeddings = [embeddings]

        # CRITICAL: Validate embedding count matches chunk count
        chunks_count = len(chunks)
        embeddings_count = len(embeddings)

        print(f"Validation: {chunks_count} chunks -> {embeddings_count} embeddings")

        if embeddings_count != chunks_count:
            error_msg = (
                f"Embedding count mismatch! Expected {chunks_count} embeddings "
                f"for {chunks_count} chunks, but received {embeddings_count}. "
                f"This may indicate API filtering, batch size limits, or content issues. "
                f"Chunk details: first={chunk_texts[0][:50]}..., last={chunk_texts[-1][:50]}..."
            )
            print(f"ERROR: {error_msg}")
            raise HTTPException(
                status_code=500,
                detail=error_msg
            )

        # Store embeddings with chunks
        for i, chunk in enumerate(chunks):
            try:
                emb_array = embedding_to_array(embeddings[i])
                if emb_array.size == 0:
                    print(f"WARNING: Empty embedding at index {i} for chunk: {chunk['text'][:50]}...")
                    raise ValueError(f"Empty embedding returned for chunk {i}")
                chunk['embedding'] = emb_array.tolist()
            except (IndexError, KeyError) as e:
                error_msg = (
                    f"Failed to process embedding at index {i}: {str(e)}. "
                    f"Chunks count: {chunks_count}, Embeddings count: {embeddings_count}"
                )
                print(f"ERROR: {error_msg}")
                raise HTTPException(status_code=500, detail=error_msg)

        print(f"✓ Successfully mapped {chunks_count} embeddings to chunks")

        # Build visual index from video frames
        if video_file_path and os.path.exists(video_file_path):
            try:
                frames = extract_frames(video_file_path)
                visual_index = build_visual_index(frames)
                print(f"Created visual index with {len(visual_index)} frames")
            except Exception as visual_error:
                print(f"Warning: Failed to build visual index: {visual_error}")
                visual_index = []
        else:
            print("No video file available for visual indexing.")
            visual_index = []

        # Cleanup temporary video files
        if temp_dir:
            try:
                if video_file_path and os.path.exists(video_file_path):
                    os.remove(video_file_path)
                os.rmdir(temp_dir)
            except Exception as cleanup_error:
                print(f"Warning: Failed to clean up temp video files: {cleanup_error}")
        
        # Store video data
        video_data = {
            "video_id": video_id,
            "youtube_url": request.youtube_url,
            "transcript": transcript,
            "sections": sections,
            "chunks": chunks,
            "visual_index": visual_index
        }

        # Associate video with user
        associate_video_with_user(video_data, current_user, user_videos)
        video_store[video_id] = video_data

        return {
            "video_id": video_id,
            "youtube_url": request.youtube_url,
            "sections": sections,
            "transcript_length": len(transcript) if transcript else 0,
            "chunks_created": len(chunks),
            "processing_mode": "transcript" if transcript else "video_analysis",
            "visual_frames_indexed": len(visual_index)
        }
        
    except InvalidVideoIDError as e:
        log_error(app_logger, "InvalidVideoID", f"Invalid video ID: {e.message}",
                 exc_info=e, youtube_url=request.youtube_url, user_id=current_user.user_id)
        raise create_error_response(
            status_code=400,
            error_type="InvalidVideoID",
            message=e.message,
            details=e.details
        )
    except TranscriptNotAvailableError as e:
        log_warning(app_logger, f"Transcript not available for video: {video_id}",
                   video_id=video_id, user_id=current_user.user_id)
        raise create_error_response(
            status_code=404,
            error_type="TranscriptNotAvailable",
            message="Video transcript is not available",
            details={"video_id": video_id}
        )
    except VideoDownloadError as e:
        log_error(app_logger, "VideoDownloadError", f"Failed to download video: {e.message}",
                 exc_info=e, video_id=video_id, user_id=current_user.user_id)
        raise create_error_response(
            status_code=500,
            error_type="VideoDownloadError",
            message="Failed to download video for processing",
            details=e.details
        )
    except GeminiAPIError as e:
        log_error(app_logger, "GeminiAPIError", f"Gemini API error: {e.message}",
                 exc_info=e, video_id=video_id, user_id=current_user.user_id)
        raise create_error_response(
            status_code=503,
            error_type="GeminiAPIError",
            message="AI service temporarily unavailable",
            details=e.details
        )
    except EmbeddingGenerationError as e:
        log_error(app_logger, "EmbeddingError", f"Embedding generation failed: {e.message}",
                 exc_info=e, video_id=video_id, user_id=current_user.user_id)
        raise create_error_response(
            status_code=500,
            error_type="EmbeddingGenerationError",
            message="Failed to generate embeddings",
            details=e.details
        )
    except FrameExtractionError as e:
        log_error(app_logger, "FrameExtractionError", f"Frame extraction failed: {e.message}",
                 exc_info=e, video_id=video_id, user_id=current_user.user_id)
        # Don't fail entire process, continue without visual index
        log_warning(app_logger, "Continuing without visual index", video_id=video_id)
    except ValueError as e:
        log_error(app_logger, "ValueError", f"Validation error: {str(e)}",
                 exc_info=e, user_id=current_user.user_id)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Log unexpected errors with full traceback
        log_error(
            app_logger,
            "UnexpectedError",
            f"Unexpected error processing video: {str(e)}",
            exc_info=e,
            video_id=video_id if 'video_id' in locals() else 'unknown',
            user_id=current_user.user_id,
            traceback_str=traceback.format_exc()
        )
        raise create_error_response(
            status_code=500,
            error_type="UnexpectedError",
            message="An unexpected error occurred while processing the video",
            details={"error": str(e)} if log_level == "DEBUG" else None
        )


@app.post("/chat", dependencies=[Depends(check_rate_limit)])
async def chat_with_video(request: ChatRequest, current_user: User = Depends(get_current_user)):
    """
    Chat with video using RAG:
    1. Retrieve relevant chunks using Gemini embeddings
    2. Query Gemini with context
    3. Return answer with timestamp citations
    """
    try:
        video_id = request.video_id
        question = request.question

        if video_id not in video_store:
            raise HTTPException(status_code=404, detail="Video not found. Please process the video first.")

        video_data = video_store[video_id]

        # Check access permission
        check_video_access(video_data, current_user)

        chunks = video_data['chunks']
        
        if not chunks:
            raise HTTPException(status_code=400, detail="No transcript chunks available for this video")

        # Generate embedding for the question (with caching)
        query_embedding_result = get_cached_embedding(question, "retrieval_query")
        query_embedding = embedding_to_array(query_embedding_result)
        if query_embedding.size == 0:
            raise HTTPException(status_code=500, detail="Failed to generate embedding for question")
        
        # Calculate cosine similarity with all chunks
        similarities = []
        for chunk in chunks:
            chunk_embedding = embedding_to_array(chunk['embedding'])
            if chunk_embedding.size == 0:
                similarities.append(-1)
                continue
            norm_product = np.linalg.norm(query_embedding) * np.linalg.norm(chunk_embedding)
            if norm_product == 0:
                similarities.append(-1)
                continue
            similarity = float(np.dot(query_embedding, chunk_embedding) / norm_product)
            similarities.append(similarity)
        
        top_indices = np.argsort(similarities)[-5:][::-1]
        context_parts = []
        relevant_timestamps = []
        
        for idx in top_indices:
            if idx < 0 or similarities[idx] < 0:
                continue
            chunk = chunks[idx]
            start = chunk['start']
            start_mins = int(start // 60)
            start_secs = int(start % 60)
            text = chunk['text']
            context_parts.append(f"[{start_mins:02d}:{start_secs:02d}] {text}")
            relevant_timestamps.append({
                "timestamp": start,
                "text": text[:100] + "..."
            })
        
        context = "\n\n".join(context_parts)
        model = genai.GenerativeModel('gemini-2.5-pro')
        
        prompt = f"""You are a helpful video analysis assistant. Answer the user's question based on the video transcript context provided.

Context from video (with timestamps):
{context}

Question: {question}

IMPORTANT INSTRUCTIONS:
1. Include timestamp citations in [MM:SS] format for any specific portions you reference.
2. Use timestamps from the context above.
3. Make timestamps clickable hyperlinks by wrapping them in square brackets like [MM:SS].
4. Cite multiple timestamps when relevant.

Answer naturally and conversationally, but include timestamp citations for accuracy."""
        
        response = model.generate_content(prompt)
        answer = response.text
        
        return {
            "answer": answer,
            "relevant_timestamps": relevant_timestamps,
            "sources_count": len([idx for idx in top_indices if idx >= 0 and similarities[idx] >= 0])
        }
        
    except HTTPException:
        raise
    except GeminiAPIError as e:
        log_error(app_logger, "GeminiAPIError", f"Gemini API error in chat: {e.message}",
                 exc_info=e, video_id=request.video_id, user_id=current_user.user_id)
        raise create_error_response(
            status_code=503,
            error_type="GeminiAPIError",
            message="AI service temporarily unavailable for chat",
            details=e.details
        )
    except EmbeddingGenerationError as e:
        log_error(app_logger, "EmbeddingError", f"Failed to generate query embedding: {e.message}",
                 exc_info=e, video_id=request.video_id, user_id=current_user.user_id)
        raise create_error_response(
            status_code=500,
            error_type="EmbeddingGenerationError",
            message="Failed to process your question",
            details=e.details
        )
    except Exception as e:
        log_error(
            app_logger,
            "UnexpectedError",
            f"Unexpected error in chat: {str(e)}",
            exc_info=e,
            video_id=request.video_id,
            user_id=current_user.user_id,
            question_preview=request.question[:100],
            traceback_str=traceback.format_exc()
        )
        raise create_error_response(
            status_code=500,
            error_type="UnexpectedError",
            message="An unexpected error occurred while processing your question",
            details={"error": str(e)} if log_level == "DEBUG" else None
        )


@app.post("/visual_search", dependencies=[Depends(check_rate_limit)])
async def visual_search(request: VisualSearchRequest, current_user: User = Depends(get_current_user)):
    """Search for visual content using frame embeddings or transcript fallback."""
    try:
        video_id = request.video_id
        query = request.query

        if video_id not in video_store:
            raise HTTPException(status_code=404, detail="Video not found. Please process the video first.")

        video_data = video_store[video_id]

        # Check access permission
        check_video_access(video_data, current_user)
        transcript = video_data['transcript']
        sections = video_data['sections']
        visual_index = video_data.get('visual_index', [])

        matches = []

        if visual_index:
            # Generate embedding for visual search query (with caching)
            query_embedding_result = get_cached_embedding(query, "retrieval_query")
            query_embedding = embedding_to_array(query_embedding_result)
            if query_embedding.size == 0:
                raise HTTPException(status_code=500, detail="Failed to generate embedding for query")

            scored = []
            for frame in visual_index:
                frame_embedding = embedding_to_array(frame.get('embedding'))
                if frame_embedding.size == 0:
                    continue
                norm_product = np.linalg.norm(query_embedding) * np.linalg.norm(frame_embedding)
                if norm_product == 0:
                    continue
                similarity = float(np.dot(query_embedding, frame_embedding) / norm_product)
                if np.isnan(similarity):
                    continue
                scored.append((similarity, frame))

            scored.sort(key=lambda x: x[0], reverse=True)
            for similarity, frame in scored[:8]:
                confidence = "low"
                if similarity >= 0.80:
                    confidence = "high"
                elif similarity >= 0.60:
                    confidence = "medium"
                matches.append({
                    "timestamp": frame['timestamp'],
                    "end_timestamp": frame['timestamp'] + 5,
                    "description": frame['description'],
                    "confidence": confidence,
                    "similarity": similarity,
                    "preview_image_base64": frame.get('image_base64')
                })

            source = "visual_index"

        else:
            if transcript:
                formatted_transcript = format_transcript_for_gemini(transcript)
            else:
                formatted_transcript = "\n\n".join([
                    f"[{int(s['start_time']//60):02d}:{int(s['start_time']%60):02d}] {s['title']}: {s['summary']}"
                    for s in sections
                ])

            model = genai.GenerativeModel('gemini-2.5-pro')
            prompt = f"""Analyze this video content and find moments that match the visual query: "{query}"

Context with timestamps:
{formatted_transcript}

Infer which moments likely contain the requested visual content. Return ONLY JSON in format:
{{"matches": [{{"timestamp": number, "end_timestamp": number, "description": string, "confidence": "low"|"medium"|"high"}}]}}. Include up to 5 matches."""
            response = model.generate_content(prompt)
            result = parse_json_from_response(response.text)
            matches = result.get('matches', [])
            source = "transcript_inference"

        return {
            "query": query,
            "matches": matches,
            "total_matches": len(matches),
            "source": source
        }

    except HTTPException:
        raise
    except EmbeddingGenerationError as e:
        log_error(app_logger, "EmbeddingError", f"Failed to generate search embedding: {e.message}",
                 exc_info=e, video_id=request.video_id, user_id=current_user.user_id)
        raise create_error_response(
            status_code=500,
            error_type="EmbeddingGenerationError",
            message="Failed to process your search query",
            details=e.details
        )
    except Exception as e:
        log_error(
            app_logger,
            "UnexpectedError",
            f"Unexpected error in visual search: {str(e)}",
            exc_info=e,
            video_id=request.video_id,
            user_id=current_user.user_id,
            query=request.query,
            traceback_str=traceback.format_exc()
        )
        raise create_error_response(
            status_code=500,
            error_type="UnexpectedError",
            message="An unexpected error occurred during visual search",
            details={"error": str(e)} if log_level == "DEBUG" else None
        )


@app.get("/video/{video_id}")
async def get_video_info(video_id: str, current_user: User = Depends(get_current_user)):
    """Get information about a processed video"""
    if video_id not in video_store:
        raise HTTPException(status_code=404, detail="Video not found")

    video_data = video_store[video_id]

    # Check access permission
    check_video_access(video_data, current_user)
    transcript = video_data['transcript']
    return {
        "video_id": video_data['video_id'],
        "youtube_url": video_data['youtube_url'],
        "sections": video_data['sections'],
        "transcript_length": len(transcript) if transcript else 0,
        "visual_frames_indexed": len(video_data.get('visual_index', []))
    }


@app.get("/cache/stats")
async def get_cache_stats():
    """Get embedding cache statistics for monitoring"""
    return {
        "embedding_cache": embedding_cache.stats(),
        "videos_cached": len(video_store)
    }


@app.get("/videos")
async def list_user_videos(current_user: User = Depends(get_current_user)):
    """List all videos belonging to current user"""
    user_video_ids = user_videos.get(current_user.user_id, [])

    videos = []
    for video_id in user_video_ids:
        if video_id in video_store:
            video_data = video_store[video_id]
            videos.append({
                "video_id": video_data["video_id"],
                "youtube_url": video_data["youtube_url"],
                "sections_count": len(video_data.get("sections", [])),
                "has_visual_index": len(video_data.get("visual_index", [])) > 0
            })

    return {
        "count": len(videos),
        "videos": videos
    }


@app.post("/cache/clear")
async def clear_cache():
    """Clear embedding cache (admin endpoint)"""
    embedding_cache.clear()
    return {
        "status": "success",
        "message": "Embedding cache cleared"
    }


# ==================== Run Server ====================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
