export default function SectionList({ sections, onTimestampClick }) {
  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-xl font-bold text-gray-900">Video Sections</h3>
        <span className="text-sm text-gray-500">{sections.length} sections</span>
      </div>
      
      <div className="space-y-4">
        {sections.map((section, i) => (
          <div 
            key={i} 
            className="group border-l-4 border-blue-500 pl-4 py-3 hover:bg-blue-50 transition-all rounded-r-lg cursor-pointer"
            onClick={() => onTimestampClick(section.start_time)}
          >
            {/* HYPERLINKED TIMESTAMP - Clicking jumps video to this time */}
            <button
              className="text-left w-full"
              onClick={(e) => {
                e.stopPropagation()
                onTimestampClick(section.start_time)
              }}
            >
              <div className="flex items-center gap-2 mb-2">
                <svg 
                  className="w-5 h-5 text-blue-600 group-hover:text-blue-700 transition-colors" 
                  fill="currentColor" 
                  viewBox="0 0 20 20"
                >
                  <path d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z"/>
                </svg>
                <span className="text-blue-600 hover:text-blue-800 font-bold text-lg group-hover:underline transition-all">
                  [{formatTime(section.start_time)}]
                </span>
                <span className="font-semibold text-gray-900 group-hover:text-blue-900 transition-colors">
                  {section.title}
                </span>
              </div>
              
              <p className="text-sm text-gray-600 leading-relaxed">
                {section.summary}
              </p>
              
              <div className="flex items-center gap-2 mt-2 text-xs text-gray-400">
                <span>Duration: {formatTime(section.end_time - section.start_time)}</span>
                <span>•</span>
                <span>Ends at {formatTime(section.end_time)}</span>
              </div>
            </button>
          </div>
        ))}
      </div>
      
      <div className="mt-6 p-4 bg-blue-50 rounded-lg border border-blue-100">
        <p className="text-sm text-blue-800">
          <span className="font-semibold">💡 Tip:</span> Click any timestamp to jump directly to that moment in the video!
        </p>
      </div>
    </div>
  )
}
