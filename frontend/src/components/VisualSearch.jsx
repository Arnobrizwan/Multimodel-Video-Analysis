import { useState } from 'react'
import axios from 'axios'

export default function VisualSearch({ videoId, onTimestampClick }) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [searched, setSearched] = useState(false)

  const searchVisual = async () => {
    if (!query.trim()) return

    setLoading(true)
    setSearched(true)
    
    try {
      const response = await axios.post('http://localhost:8000/visual_search', {
        video_id: videoId,
        query: query
      })
      
      setResults(response.data.matches)
    } catch (error) {
      console.error('Visual search failed:', error)
      setResults([])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      searchVisual()
    }
  }

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const getClipDuration = (start, end) => {
    const duration = Math.round(end - start)
    return `${duration}s`
  }

  const exampleQueries = [
    "show me charts or graphs",
    "person speaking to camera",
    "code on screen",
    "text slides or bullet points"
  ]

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <div className="mb-4">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-pink-500 rounded-full flex items-center justify-center">
            <svg className="w-6 h-6 text-white" fill="currentColor" viewBox="0 0 20 20">
              <path d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z"/>
            </svg>
          </div>
          <div>
            <h3 className="font-bold text-gray-900">Visual Frame Search</h3>
            <p className="text-xs text-gray-500">Find specific visual content</p>
          </div>
        </div>
      </div>

      <div className="mb-4">
        <div className="flex gap-2">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="e.g., 'show me charts' or 'person speaking'"
            className="flex-1 border-2 border-gray-300 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-purple-500 focus:border-transparent"
            disabled={loading}
          />
          <button
            onClick={searchVisual}
            disabled={loading || !query.trim()}
            className="bg-gradient-to-r from-purple-600 to-pink-600 text-white px-6 py-2 rounded-lg text-sm font-semibold hover:from-purple-700 hover:to-pink-700 disabled:opacity-50"
          >
            {loading ? '...' : 'Search'}
          </button>
        </div>
      </div>

      {loading && (
        <div className="flex justify-center py-8">
          <div className="text-center">
            <svg className="animate-spin h-8 w-8 text-purple-600 mx-auto mb-2" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
            <p className="text-sm text-gray-600">Analyzing frames...</p>
          </div>
        </div>
      )}

      {!loading && searched && results.length > 0 && (
        <div className="space-y-3 max-h-96 overflow-y-auto">
          <p className="text-sm font-semibold text-gray-700 mb-2">
            Found {results.length} matching clip{results.length !== 1 ? 's' : ''}:
          </p>
          {results.map((result, i) => (
            <button
              key={i}
              onClick={() => onTimestampClick(result.timestamp)}
              className="w-full text-left p-4 border-2 border-gray-200 rounded-lg hover:bg-purple-50 hover:border-purple-300 transition-all group"
            >
              <div className="flex items-center gap-3 mb-2">
                <svg className="w-5 h-5 text-purple-600" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z"/>
                </svg>
                <span className="text-purple-600 font-bold text-lg group-hover:underline">
                  [{formatTime(result.timestamp)}]
                </span>
                <span className="text-xs bg-purple-100 text-purple-700 px-2 py-1 rounded-full">
                  {getClipDuration(result.timestamp, result.end_timestamp)} clip
                </span>
              </div>
              <p className="text-sm text-gray-700 leading-relaxed pl-8">
                {result.description}
              </p>
            </button>
          ))}
        </div>
      )}

      {!loading && searched && results.length === 0 && (
        <div className="text-center py-8">
          <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-3">
            <svg className="w-8 h-8 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clipRule="evenodd"/>
            </svg>
          </div>
          <p className="text-sm text-gray-500">No matches found</p>
          <p className="text-xs text-gray-400 mt-1">Try a different search query</p>
        </div>
      )}

      {!searched && (
        <div className="mt-4 p-4 bg-purple-50 rounded-lg border border-purple-100">
          <p className="text-xs font-semibold text-purple-900 mb-2">Try searching for:</p>
          <div className="space-y-1">
            {exampleQueries.map((example, i) => (
              <button
                key={i}
                onClick={() => setQuery(example)}
                className="block w-full text-left text-xs text-purple-700 hover:text-purple-900 hover:bg-purple-100 px-2 py-1 rounded"
              >
                • "{example}"
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
