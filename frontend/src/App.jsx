import { useState, useEffect } from 'react'
import { VideoProvider, useVideo } from './context/VideoContext'
import AuthForm from './components/AuthForm'
import VideoUpload from './components/VideoUpload'
import VideoPlayer from './components/VideoPlayer'
import SectionList from './components/SectionList'
import ChatInterface from './components/ChatInterface'
import VisualSearch from './components/VisualSearch'

function AppContent() {
  const { videoData, currentTime, handleVideoProcessed, handleTimestampClick, resetVideo } = useVideo()
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [user, setUser] = useState(null)

  useEffect(() => {
    // Check if user is already logged in
    const token = localStorage.getItem('access_token')
    const userId = localStorage.getItem('user_id')
    if (token && userId) {
      setIsAuthenticated(true)
      setUser({ user_id: userId })
    }
  }, [])

  const handleAuthSuccess = (authData) => {
    setIsAuthenticated(true)
    setUser({ user_id: authData.user_id })
  }

  const handleLogout = () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('user_id')
    setIsAuthenticated(false)
    setUser(null)
    resetVideo()
  }

  if (!isAuthenticated) {
    return <AuthForm onAuthSuccess={handleAuthSuccess} />
  }

  if (!videoData) {
    return <VideoUpload onVideoProcessed={handleVideoProcessed} onLogout={handleLogout} />
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
          <div className="flex items-center gap-3">
            <button
              onClick={resetVideo}
              className="flex items-center gap-2 text-blue-600 hover:text-blue-800 font-medium px-4 py-2 rounded-lg hover:bg-blue-50 transition-all"
            >
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M9.707 16.707a1 1 0 01-1.414 0l-6-6a1 1 0 010-1.414l6-6a1 1 0 011.414 1.414L5.414 9H17a1 1 0 110 2H5.414l4.293 4.293a1 1 0 010 1.414z" clipRule="evenodd"/>
              </svg>
              Analyze New Video
            </button>
            <button
              onClick={handleLogout}
              className="flex items-center gap-2 text-gray-600 hover:text-gray-800 font-medium px-4 py-2 rounded-lg hover:bg-gray-50 transition-all"
            >
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M3 3a1 1 0 00-1 1v12a1 1 0 102 0V4a1 1 0 00-1-1zm10.293 9.293a1 1 0 001.414 1.414l3-3a1 1 0 000-1.414l-3-3a1 1 0 10-1.414 1.414L14.586 9H7a1 1 0 100 2h7.586l-1.293 1.293z" clipRule="evenodd"/>
              </svg>
              Logout
            </button>
          </div>
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

export default function App() {
  return (
    <VideoProvider>
      <AppContent />
    </VideoProvider>
  )
}
