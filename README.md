# 🎬 Multimodal Video Analysis System

A powerful video analysis platform powered by **Gemini 2.5 Pro** that enables intelligent interaction with YouTube videos - works with **OR without** transcripts using native video understanding!

![Tech Stack](https://img.shields.io/badge/Python-3.11+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115.0-green)
![React](https://img.shields.io/badge/React-18.2.0-cyan)
![Gemini](https://img.shields.io/badge/Gemini-2.5%20Pro-orange)

## 🎯 What Makes This Special

- **🎥 Works with ANY YouTube video** - Transcript OR native video analysis
- **⚡ Gemini-powered embeddings** - Fast, no slow model downloads
- **🤖 True multimodal AI** - Analyzes actual video frames when needed
- **💬 Smart chat with citations** - Every answer includes clickable timestamps
- **🔍 Visual search** - Find moments by describing what you see

---

## 🆕 Recent Updates

✅ **Dual-Mode Processing** - Automatically detects and uses best approach (transcript vs video analysis)  
✅ **No ChromaDB Required** - Switched to Gemini embeddings for faster processing  
✅ **Video Download & Analysis** - Full support for videos without transcripts using yt-dlp  
✅ **In-Memory Vector Storage** - NumPy-based cosine similarity for chat/search  
✅ **Latest APIs** - Updated to youtube-transcript-api 1.2.2 with new interface  

---

## ✨ Features

### 📹 **Dual-Mode Video Processing**

**🎯 Mode 1: Transcript-Based (Fast)**
- Extracts existing YouTube captions
- Processes in ~10-15 seconds
- Perfect for videos with transcripts

**🎥 Mode 2: Video Analysis (Smart)**
- Downloads and analyzes actual video
- Uses Gemini's native video understanding
- Sees frames, actions, scenes, text
- Works when NO transcript is available

### 🎬 **Auto Section Breakdown**
- AI-generated chapter divisions
- **Clickable timestamp hyperlinks** that jump directly to video moments
- Comprehensive summaries for each section
- Works regardless of transcript availability

### 💬 **Chat with Video**
- Ask questions about video content
- Get AI-powered answers with context
- **Automatic timestamp citations** - Every reference includes clickable [MM:SS] hyperlinks
- RAG-powered responses using Gemini embeddings

### 🔍 **Visual Frame Search**
- Natural language queries for visual content
- Find specific moments by describing what you see
- Search for charts, graphs, people, code, text, and more
- Results show clip duration and precise timestamps
- Examples:
  - "show me charts or graphs"
  - "person speaking to camera"
  - "code on screen"
  - "text slides with bullet points"

### ⏱️ **Smart Navigation**
Three ways to navigate video content:
1. **Section timestamps** - Pre-generated chapter links
2. **Chat citations** - AI-referenced moments in responses
3. **Visual search results** - Content-matched clips

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (React)                      │
│  - Video Upload UI    - Chat Interface                  │
│  - Video Player       - Visual Search                   │
│  - Section List       - Timestamp Navigation            │
└─────────────────────────────────────────────────────────┘
                           │
                    HTTP REST API
                           │
┌─────────────────────────────────────────────────────────┐
│                  Backend (FastAPI)                       │
│                                                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Dual-Path Video Processing                     │   │
│  │                                                  │   │
│  │  PATH A (Transcript):    PATH B (Video):        │   │
│  │  ✓ Extract transcript    ✓ Download video      │   │
│  │  ✓ Parse text            ✓ Upload to Gemini    │   │
│  │  ✓ Generate sections     ✓ AI video analysis   │   │
│  │                          ✓ Extract scenes       │   │
│  │                                                  │   │
│  │  Both paths converge to:                        │   │
│  │  ✓ Create embeddings (Gemini API)              │   │
│  │  ✓ Store in memory with timestamps             │   │
│  └─────────────────────────────────────────────────┘   │
│                                                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │  RAG Chat System                                │   │
│  │  1. Generate query embedding (Gemini API)       │   │
│  │  2. Cosine similarity search (NumPy)            │   │
│  │  3. Retrieve top-k chunks with timestamps       │   │
│  │  4. Generate answer with Gemini                 │   │
│  │  5. Return response with [MM:SS] citations      │   │
│  └─────────────────────────────────────────────────┘   │
│                                                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Visual Search                                  │   │
│  │  1. Analyze content for visual cues             │   │
│  │  2. Match query to descriptions                 │   │
│  │  3. Return clips with timestamps                │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                           │
                ┌──────────┴──────────┐
                │                     │
        ┌───────▼──────────┐  ┌──────▼───────────┐
        │  Gemini 2.5 Pro  │  │  YouTube / Web   │
        │  - Text Gen      │  │  - Transcripts   │
        │  - Embeddings    │  │  - Video Files   │
        │  - Video Vision  │  │                  │
        └──────────────────┘  └──────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **Gemini API Key** (from Google AI Studio)

### 1. Clone Repository

```bash
git clone <repository-url>
cd Multimodel-Video-Analysis
```

### 2. Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env

# Edit .env and add your Gemini API key
# GEMINI_API_KEY=your_actual_api_key_here
```

**Get your Gemini API Key:**
1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Copy and paste it into `.env`

### 3. Frontend Setup

```bash
# Open a new terminal and navigate to frontend directory
cd frontend

# Install dependencies
npm install
```

### 4. Run the Application

**Terminal 1 - Backend:**
```bash
cd backend
source venv/bin/activate  # or venv\Scripts\activate on Windows
python main.py
# Server will start on http://localhost:8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
# App will open on http://localhost:3000
```

### 5. Start Analyzing Videos! 🎉

1. Open http://localhost:3000 in your browser
2. Paste **ANY** YouTube URL (works with OR without transcripts!)
3. Click "Analyze Video"
4. Explore sections, chat, and search features

**Note:** Videos without transcripts will be downloaded and analyzed by Gemini - this takes longer (~2-5 minutes) but works on ANY video!

## 📖 User Guide

### How to Use Each Feature

#### 1. **Uploading a Video**
- Paste **ANY** YouTube URL
- Click "Analyze Video"
- Processing time:
  - **With transcript:** 10-30 seconds ⚡
  - **Without transcript:** 2-5 minutes (downloads & analyzes video) 🎥

#### 2. **Navigating with Section Timestamps**
- View auto-generated sections below the video
- Click any blue **[MM:SS]** timestamp
- Video immediately jumps to that moment

#### 3. **Chatting with the Video**
- Type questions in the chat interface
- Examples:
  - "What are the main topics covered?"
  - "Summarize the key points"
  - "What is explained at the beginning?"
- AI responds with answers containing **clickable [MM:SS] timestamps**
- Click any timestamp in the response to jump to that moment

#### 4. **Visual Frame Search**
- Describe visual content you're looking for
- Examples:
  - "show me charts or graphs"
  - "find moments with a person speaking"
  - "when is code shown on screen"
- Get a list of matching clips with timestamps
- Click any result to jump to that visual content

## 🎯 Demo Script

### Recommended Demo Video Criteria
- **Duration:** 5-10 minutes (optimal for demo)
- **Content:** Educational, tech talks, tutorials
- **For fastest demo:** Use videos with captions/transcripts
- **To show video analysis:** Use videos WITHOUT transcripts
- **Suggestions:**
  - TED Talks (have transcripts)
  - Conference presentations
  - Tutorial videos
  - User-generated content (often no transcripts)

### Demo Flow (5 minutes)

**[0:00 - 0:30] Introduction**
- "I built a multimodal video analysis system using Gemini 2.5 Pro"
- Show landing page

**[0:30 - 1:30] Feature 1: Video Processing & Section Breakdown**
- Paste YouTube URL
- Mention: "Works with OR without transcripts - uses AI to analyze actual video"
- Show processing animation
- Display generated sections
- **Demo clickable timestamps:**
  - Click [0:00] → Video jumps to start
  - Click [2:30] → Video jumps to middle
  - Emphasize: "Every timestamp is a hyperlink"

**[1:30 - 3:00] Feature 2: Chat with Timestamp Citations**
- Ask: "What topics are covered?"
- Show AI response with multiple **[MM:SS]** citations
- **Demo clicking timestamps in chat:**
  - Click [0:15] → Video seeks to 15 seconds
  - Click [2:45] → Video seeks to 2:45
  - Highlight: "AI gives you direct links to exact moments"
- Ask follow-up: "Tell me more about [specific topic]"
- Show contextual response with more citations

**[3:00 - 4:30] Feature 3: Visual Frame Search**
- Type query: "show me charts or graphs"
- Display matching clips with durations
- Click first result → Video jumps to that chart
- Try another: "person speaking to camera"
- Show multiple results, click through 2-3
- Emphasize: "Search ANY visual content with natural language"

**[4:30 - 5:00] Conclusion**
- Recap: "Three ways to navigate - sections, chat, visual search"
- Mention tech stack: React, FastAPI, Gemini 2.5 Pro
- Show code snippet (optional)

## 📦 Tech Stack Details

### Backend
| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.11+ | Main language |
| FastAPI | 0.115.0 | REST API framework |
| Gemini 2.5 Pro | Latest | Multimodal AI (text, embeddings, video) |
| youtube-transcript-api | 1.2.2 | Extract transcripts |
| yt-dlp | Latest | Download YouTube videos |
| NumPy | 2.3.3 | Vector similarity calculations |
| Pydantic | 2.10.4 | Data validation |

### Frontend
| Technology | Version | Purpose |
|------------|---------|---------|
| React | 18.2.0 | UI framework |
| Vite | 5.0.8 | Build tool |
| Tailwind CSS | 3.4.1 | Styling |
| React Player | 2.14.1 | YouTube video player |
| Axios | 1.6.5 | HTTP client |

## 🔧 API Endpoints

### `POST /process_video`
Process a YouTube video and generate sections.

**Request:**
```json
{
  "youtube_url": "https://www.youtube.com/watch?v=VIDEO_ID"
}
```

**Response:**
```json
{
  "video_id": "VIDEO_ID",
  "sections": [
    {
      "title": "Introduction",
      "start_time": 0.0,
      "end_time": 45.0,
      "summary": "Welcome and overview"
    }
  ],
  "transcript_length": 150,
  "chunks_created": 10
}
```

### `POST /chat`
Chat with video content using RAG.

**Request:**
```json
{
  "video_id": "VIDEO_ID",
  "question": "What are the main topics?"
}
```

**Response:**
```json
{
  "answer": "The video covers three main topics: Introduction at [0:15], core concepts at [2:30], and examples at [4:45].",
  "relevant_timestamps": [...],
  "sources_count": 5
}
```

### `POST /visual_search`
Search for visual content in video frames.

**Request:**
```json
{
  "video_id": "VIDEO_ID",
  "query": "show me charts or graphs"
}
```

**Response:**
```json
{
  "matches": [
    {
      "timestamp": 45.5,
      "end_timestamp": 52.0,
      "description": "Bar chart showing quarterly results",
      "confidence": "high"
    }
  ],
  "total_matches": 3
}
```

## ✅ Requirements Coverage

| Requirement | Implementation | Status |
|------------|----------------|--------|
| YouTube Video Upload UI | `VideoUpload.jsx` with URL validation | ✅ Complete |
| Section Breakdown with Hyperlinked Timestamps | `SectionList.jsx` - clickable [MM:SS] links | ✅ Complete |
| Chat with Timestamp Citations | `ChatInterface.jsx` - AI responses with [MM:SS] hyperlinks | ✅ Complete |
| Visual Frame Search | `VisualSearch.jsx` - natural language queries | ✅ Complete |
| Smart Video Navigation | Three navigation methods integrated | ✅ Complete |

## 🎨 Key UI/UX Features

- **Gradient backgrounds** for modern aesthetic
- **Hover effects** on all interactive elements
- **Loading states** with animations
- **Responsive design** for all screen sizes
- **Color-coded sections:**
  - Blue: Section timestamps & chat
  - Purple/Pink: Visual search
- **Smooth scrolling** in chat and results
- **Visual feedback** for all actions

## 🐛 Troubleshooting

### Backend Issues

**Problem:** `GEMINI_API_KEY not found`
- **Solution:** Ensure `.env` file exists in `backend/` directory with `GEMINI_API_KEY=your_key`

**Problem:** `Import errors`
- **Solution:** Ensure virtual environment is activated and dependencies installed:
  ```bash
  source venv/bin/activate
  pip install -r requirements.txt
  ```

**Problem:** Video download fails
- **Solution:** Ensure `yt-dlp` is installed correctly. Some videos may be restricted or unavailable.

**Problem:** Gemini video upload fails
- **Solution:** Check video file size (max ~2GB). Large videos may need lower quality settings.

**Problem:** Processing takes too long
- **Solution:** 
  - Videos WITH transcripts: ~10-30 seconds
  - Videos WITHOUT transcripts: ~2-5 minutes (normal)
  - Check console for progress messages

### Frontend Issues

**Problem:** `Cannot connect to backend`
- **Solution:** Ensure backend is running on `http://localhost:8000`
- Check CORS settings in `main.py`

**Problem:** Video player not loading
- **Solution:** Check YouTube video ID is valid and video is not restricted

**Problem:** `npm install` fails
- **Solution:** Delete `node_modules` and `package-lock.json`, then run `npm install` again

## 🚧 Future Enhancements

- [x] **Native video understanding** - ✅ Implemented with Gemini 2.5 Pro!
- [x] **Works without transcripts** - ✅ Downloads and analyzes video frames!
- [ ] **Multiple language support** - Transcripts in various languages
- [ ] **Video summarization** - AI-generated video summaries
- [ ] **Bookmark moments** - Save favorite timestamps
- [ ] **Export transcripts** - Download formatted transcripts
- [ ] **Batch processing** - Analyze multiple videos
- [ ] **User authentication** - Save analysis history
- [ ] **Advanced search filters** - Filter by section, duration, confidence
- [ ] **Live stream support** - Analyze live YouTube streams
- [ ] **Playlist processing** - Analyze entire YouTube playlists

## 📄 License

MIT License - Feel free to use and modify!

## 🙏 Acknowledgments

- **Google Gemini 2.5 Pro** for powerful multimodal AI (text, embeddings, video understanding)
- **FastAPI** for elegant API framework
- **React** for robust UI framework
- **yt-dlp** for reliable YouTube video downloading
- **NumPy** for fast vector similarity calculations
- **YouTube Transcript API** for transcript extraction

## 📞 Support

For issues or questions:
1. Check troubleshooting section above
2. Review API documentation
3. Ensure all dependencies are correctly installed
4. Verify Gemini API key is valid

---

**Built with ❤️ using Gemini 2.5 Pro, FastAPI, and React**

Happy Video Analyzing! 🎬✨
