import { useState } from 'react'
import VideoUpload from './components/VideoUpload'
import VideoPlayer from './components/VideoPlayer'
import SectionList from './components/SectionList'
import ChatInterface from './components/ChatInterface'
import VisualSearch from './components/VisualSearch'

export default function App() {
  const [videoData, setVideoData] = useState(null)
  const [currentTime, setCurrentTime] = useState(0)

  const handleVideoProcessed = (data) => {
    setVideoData(data)
  }

  const handleTimestampClick = (seconds) => {
    setCurrentTime(seconds)
    // Force re-render by setting a unique value
    setTimeout(() => setCurrentTime(seconds + 0.001), 10)
  }

  if (!videoData) {
    return <VideoUpload onVideoProcessed={handleVideoProcessed} />
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-lg flex items-center justify-center">
              <svg className="w-6 h-6 text-white" fill="currentColor" viewBox="0 0 20 20">
                <path d="M2 6a2 2 0 012-2h6a2 2 0 012 2v8a2 2 0 01-2 2H4a2 2 0 01-2-2V6zM14.553 7.106A1 1 0 0014 8v4a1 1 0 00.553.894l2 1A1 1 0 0018 13V7a1 1 0 00-1.447-.894l-2 1z"/>
              </svg>
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900">Video Analysis</h1>
              <p className="text-xs text-gray-500">Powered by Gemini 2.5 Pro</p>
            </div>
          </div>
          <button
            onClick={() => setVideoData(null)}
            className="flex items-center gap-2 text-blue-600 hover:text-blue-800 font-medium px-4 py-2 rounded-lg hover:bg-blue-50 transition-all"
          >
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M9.707 16.707a1 1 0 01-1.414 0l-6-6a1 1 0 010-1.414l6-6a1 1 0 011.414 1.414L5.414 9H17a1 1 0 110 2H5.414l4.293 4.293a1 1 0 010 1.414z" clipRule="evenodd"/>
            </svg>
            Analyze New Video
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* Left Column - Video Player & Sections */}
          <div className="lg:col-span-2 space-y-6">
            <VideoPlayer
              videoId={videoData.video_id}
              seekTime={currentTime}
            />
            
            <SectionList
              sections={videoData.sections}
              onTimestampClick={handleTimestampClick}
            />
          </div>

          {/* Right Column - Chat & Visual Search */}
          <div className="space-y-6">
            <ChatInterface
              videoId={videoData.video_id}
              onTimestampClick={handleTimestampClick}
            />

            <VisualSearch
              videoId={videoData.video_id}
              onTimestampClick={handleTimestampClick}
            />
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="bg-white border-t mt-12">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <div className="flex flex-col md:flex-row justify-between items-center gap-4">
            <div className="text-sm text-gray-600">
              <p className="font-semibold">Features:</p>
              <ul className="mt-1 space-y-1 text-xs">
                <li>✅ Auto section breakdown with clickable timestamps</li>
                <li>✅ Chat with AI-powered timestamp citations</li>
                <li>✅ Visual frame search for specific content</li>
              </ul>
            </div>
            <div className="text-sm text-gray-500">
              Built with React + FastAPI + Gemini 2.5 Pro
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
