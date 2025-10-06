from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
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

# Load environment variables
load_dotenv()

# Initialize FastAPI
app = FastAPI(title="Multimodal Video Analysis API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables")

genai.configure(api_key=GEMINI_API_KEY)

# Store video data in memory (for demo purposes)
video_store = {}


# ==================== Pydantic Models ====================
class VideoRequest(BaseModel):
    youtube_url: str


class ChatRequest(BaseModel):
    video_id: str
    question: str


class VisualSearchRequest(BaseModel):
    video_id: str
    query: str


class Section(BaseModel):
    title: str
    start_time: float
    end_time: float
    summary: str


# ==================== Helper Functions ====================
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
        'format': 'best[ext=mp4][height<=720]/best[ext=mp4]/best',  # Prefer MP4, max 720p
        'outtmpl': output_path,
        'quiet': True,
        'no_warnings': True,
    }
    
    url = f'https://www.youtube.com/watch?v={video_id}'
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    
    return output_path


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
            "POST /process_video": "Process a YouTube video and generate sections",
            "POST /chat": "Chat with video content using RAG",
            "POST /visual_search": "Search for visual content in video frames"
        }
    }


@app.post("/process_video")
async def process_video(request: VideoRequest):
    """
    Process a YouTube video:
    1. Extract video ID
    2. Try to get transcript OR download and analyze video with Gemini
    3. Generate section breakdown
    4. Create embeddings
    """
    try:
        # Step 1: Extract video ID
        video_id = extract_video_id(request.youtube_url)
        print(f"Processing video: {video_id}")
        
        # Step 2: Try to get transcript
        transcript = get_transcript(video_id)
        
        sections = []
        chunks = []
        video_file_path = None
        
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
            
            # Clean up video file
            try:
                genai.delete_file(video_file.name)
                os.remove(video_file_path)
                os.rmdir(temp_dir)
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
        print(f"Generated {len(embeddings)} embeddings")
        
        # Store embeddings with chunks
        for i, chunk in enumerate(chunks):
            chunk['embedding'] = embeddings[i]
        
        # Store video data
        video_store[video_id] = {
            "video_id": video_id,
            "youtube_url": request.youtube_url,
            "transcript": transcript,
            "sections": sections,
            "chunks": chunks
        }
        
        return {
            "video_id": video_id,
            "youtube_url": request.youtube_url,
            "sections": sections,
            "transcript_length": len(transcript) if transcript else 0,
            "chunks_created": len(chunks),
            "processing_mode": "transcript" if transcript else "video_analysis"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing video: {str(e)}")


@app.post("/chat")
async def chat_with_video(request: ChatRequest):
    """
    Chat with video using RAG:
    1. Retrieve relevant chunks using Gemini embeddings
    2. Query Gemini with context
    3. Return answer with timestamp citations
    """
    try:
        video_id = request.video_id
        question = request.question
        
        # Check if video exists
        if video_id not in video_store:
            raise HTTPException(status_code=404, detail="Video not found. Please process the video first.")
        
        video_data = video_store[video_id]
        chunks = video_data['chunks']
        
        # Generate embedding for the question
        query_result = genai.embed_content(
            model="models/text-embedding-004",
            content=question,
            task_type="retrieval_query"
        )
        query_embedding = np.array(query_result['embedding'])
        
        # Calculate cosine similarity with all chunks
        similarities = []
        for chunk in chunks:
            chunk_embedding = np.array(chunk['embedding'])
            similarity = np.dot(query_embedding, chunk_embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(chunk_embedding)
            )
            similarities.append(similarity)
        
        # Get top 5 most similar chunks
        top_indices = np.argsort(similarities)[-5:][::-1]
        
        # Build context with timestamps
        context_parts = []
        relevant_timestamps = []
        
        for idx in top_indices:
            chunk = chunks[idx]
            start = chunk['start']
            end = chunk['end']
            text = chunk['text']
            start_mins = int(start // 60)
            start_secs = int(start % 60)
            
            context_parts.append(f"[{start_mins:02d}:{start_secs:02d}] {text}")
            relevant_timestamps.append({
                "timestamp": start,
                "text": text[:100] + "..."
            })
        
        context = "\n\n".join(context_parts)
        
        # Query Gemini with instruction to include timestamp citations
        model = genai.GenerativeModel('gemini-2.5-pro')
        
        prompt = f"""You are a helpful video analysis assistant. Answer the user's question based on the video transcript context provided.

Context from video (with timestamps):
{context}

Question: {question}

IMPORTANT INSTRUCTIONS:
1. In your answer, include timestamp citations in [MM:SS] format for any specific portions of the video you reference
2. Use timestamps from the context provided above
3. Make timestamps clickable hyperlinks by wrapping them in square brackets like [MM:SS]
4. Be specific and cite multiple timestamps when relevant

Examples of good responses:
- "The introduction starts at [00:00] and covers the main topics."
- "The concept is explained at [02:30], with examples shown at [03:45] and [05:15]."
- "You can see the demo starting at [04:00] which continues until around [06:30]."

Answer naturally and conversationally, but include timestamp citations for accuracy."""
        
        response = model.generate_content(prompt)
        answer = response.text
        
        return {
            "answer": answer,
            "relevant_timestamps": relevant_timestamps,
            "sources_count": len(top_indices)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in chat: {str(e)}")


@app.post("/visual_search")
async def visual_search(request: VisualSearchRequest):
    """
    Search for visual content in video frames using natural language.
    
    NOTE: This is a simplified implementation that uses transcript-based search.
    For true frame-by-frame analysis, you would need to:
    1. Download video frames at regular intervals
    2. Upload frames to Gemini Vision API
    3. Analyze each frame for visual content
    
    This implementation provides a working demo using transcript context.
    """
    try:
        video_id = request.video_id
        query = request.query
        
        # Check if video exists
        if video_id not in video_store:
            raise HTTPException(status_code=404, detail="Video not found. Please process the video first.")
        
        video_data = video_store[video_id]
        transcript = video_data['transcript']
        sections = video_data['sections']
        
        # Prepare content for search
        if transcript:
            # Use Gemini to find relevant moments based on transcript
            formatted_transcript = format_transcript_for_gemini(transcript)
        else:
            # For videos without transcripts, use sections as content
            formatted_transcript = "\n\n".join([
                f"[{int(s['start_time']//60):02d}:{int(s['start_time']%60):02d}] {s['title']}: {s['summary']}"
                for s in sections
            ])
        
        model = genai.GenerativeModel('gemini-2.5-pro')
        
        prompt = f"""Analyze this video transcript and find moments that match the visual query: "{query}"

Transcript with timestamps:
{formatted_transcript}

Based on the transcript content, infer which moments likely contain the visual content described.
For example:
- "charts" or "graphs" → Look for mentions of data, statistics, visualizations
- "person speaking" → Look for direct speech, "I", "we", presenter dialogue
- "code" → Look for technical terms, programming concepts, code examples
- "text slides" → Look for bullet points, lists, structured information

Return ONLY a valid JSON object (no markdown) in this exact format:
{{
    "matches": [
        {{
            "timestamp": 45.0,
            "end_timestamp": 52.0,
            "description": "Description of what's shown at this moment",
            "confidence": "high"
        }}
    ]
}}

Find 3-8 relevant moments. Be specific with timestamps (use exact times from transcript).
If no matches found, return an empty matches array."""
        
        response = model.generate_content(prompt)
        result = parse_json_from_response(response.text)
        
        matches = result.get('matches', [])
        
        return {
            "query": query,
            "matches": matches,
            "total_matches": len(matches)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in visual search: {str(e)}")


@app.get("/video/{video_id}")
async def get_video_info(video_id: str):
    """Get information about a processed video"""
    if video_id not in video_store:
        raise HTTPException(status_code=404, detail="Video not found")
    
    video_data = video_store[video_id]
    return {
        "video_id": video_data['video_id'],
        "youtube_url": video_data['youtube_url'],
        "sections": video_data['sections'],
        "transcript_length": len(video_data['transcript'])
    }


# ==================== Run Server ====================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
