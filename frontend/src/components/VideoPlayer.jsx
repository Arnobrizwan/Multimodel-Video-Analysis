import ReactPlayer from 'react-player/youtube'
import { useRef, useEffect } from 'react'

export default function VideoPlayer({ videoId, seekTime }) {
  const playerRef = useRef(null)
  
  useEffect(() => {
    if (seekTime !== undefined && seekTime !== null && playerRef.current) {
      playerRef.current.seekTo(seekTime, 'seconds')
    }
  }, [seekTime])
  
  return (
    <div className="bg-white rounded-lg shadow-lg overflow-hidden">
      <div className="aspect-video">
        <ReactPlayer
          ref={playerRef}
          url={`https://www.youtube.com/watch?v=${videoId}`}
          controls
          width="100%"
          height="100%"
          config={{
            youtube: {
              playerVars: { 
                modestbranding: 1,
                rel: 0,
                iv_load_policy: 3
              }
            }
          }}
        />
      </div>
    </div>
  )
}
