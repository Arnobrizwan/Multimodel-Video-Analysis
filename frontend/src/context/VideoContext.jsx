import { createContext, useContext, useState } from 'react'

const VideoContext = createContext(null)

export function VideoProvider({ children }) {
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

  const resetVideo = () => {
    setVideoData(null)
    setCurrentTime(0)
  }

  const value = {
    videoData,
    currentTime,
    handleVideoProcessed,
    handleTimestampClick,
    resetVideo
  }

  return (
    <VideoContext.Provider value={value}>
      {children}
    </VideoContext.Provider>
  )
}

export function useVideo() {
  const context = useContext(VideoContext)
  if (!context) {
    throw new Error('useVideo must be used within a VideoProvider')
  }
  return context
}
