import { useState, useRef, useEffect } from 'react'
import axios from 'axios'

export default function ChatInterface({ videoId, onTimestampClick }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const sendMessage = async () => {
    if (!input.trim()) return
    
    const userMessage = input
    setInput('')
    setLoading(true)

    // Add user message
    setMessages(prev => [...prev, { type: 'user', text: userMessage }])

    try {
      const response = await axios.post('http://localhost:8000/chat', {
        video_id: videoId,
        question: userMessage
      })

      // Add AI response
      setMessages(prev => [...prev, {
        type: 'assistant',
        text: response.data.answer,
        timestamps: response.data.relevant_timestamps
      }])
    } catch (error) {
      setMessages(prev => [...prev, {
        type: 'error',
        text: 'Failed to get response. Please try again.'
      }])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const renderAnswerWithTimestamps = (text) => {
    // Parse [MM:SS] or [HH:MM:SS] timestamps and make them clickable
    const timestampRegex = /\[(\d{1,2}):(\d{2})(?::(\d{2}))?\]/g
    const parts = []
    let lastIndex = 0
    let match

    while ((match = timestampRegex.exec(text)) !== null) {
      // Add text before timestamp
      if (match.index > lastIndex) {
        parts.push(
          <span key={`text-${lastIndex}`}>
            {text.slice(lastIndex, match.index)}
          </span>
        )
      }

      // Calculate seconds
      const hours = match[3] ? parseInt(match[1]) : 0
      const mins = match[3] ? parseInt(match[2]) : parseInt(match[1])
      const secs = match[3] ? parseInt(match[3]) : parseInt(match[2])
      const totalSeconds = hours * 3600 + mins * 60 + secs

      // Add clickable timestamp HYPERLINK
      parts.push(
        <button
          key={`timestamp-${match.index}`}
          onClick={() => onTimestampClick(totalSeconds)}
          className="inline-flex items-center gap-1 text-blue-600 hover:text-blue-800 font-semibold hover:underline transition-colors mx-0.5"
        >
          <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
            <path d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z"/>
          </svg>
          {match[0]}
        </button>
      )

      lastIndex = match.index + match[0].length
    }

    // Add remaining text
    if (lastIndex < text.length) {
      parts.push(
        <span key={`text-${lastIndex}`}>
          {text.slice(lastIndex)}
        </span>
      )
    }

    return parts
  }

  return (
    <div className="bg-white rounded-lg shadow-lg flex flex-col h-[600px]">
      {/* Header */}
      <div className="p-4 border-b border-gray-200 bg-gradient-to-r from-purple-50 to-blue-50">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-blue-500 rounded-full flex items-center justify-center">
            <svg className="w-6 h-6 text-white" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M18 10c0 3.866-3.582 7-8 7a8.841 8.841 0 01-4.083-.98L2 17l1.338-3.123C2.493 12.767 2 11.434 2 10c0-3.866 3.582-7 8-7s8 3.134 8 7zM7 9H5v2h2V9zm8 0h-2v2h2V9zM9 9h2v2H9V9z" clipRule="evenodd"/>
            </svg>
          </div>
          <div>
            <h3 className="font-bold text-gray-900">Chat with Video</h3>
            <p className="text-xs text-gray-500">Ask questions about the content</p>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center px-4">
            <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mb-4">
              <svg className="w-8 h-8 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10c0 3.866-3.582 7-8 7a8.841 8.841 0 01-4.083-.98L2 17l1.338-3.123C2.493 12.767 2 11.434 2 10c0-3.866 3.582-7 8-7s8 3.134 8 7zM7 9H5v2h2V9zm8 0h-2v2h2V9zM9 9h2v2H9V9z" clipRule="evenodd"/>
              </svg>
            </div>
            <p className="text-gray-600 font-medium mb-2">Start a conversation</p>
            <p className="text-sm text-gray-400 max-w-xs">
              Ask questions about the video and get answers with clickable timestamp citations
            </p>
            <div className="mt-6 space-y-2 text-left">
              <p className="text-xs text-gray-500 font-semibold">Try asking:</p>
              <button
                onClick={() => setInput("What are the main topics covered?")}
                className="block w-full text-left text-sm text-blue-600 hover:text-blue-800 hover:bg-blue-50 px-3 py-2 rounded transition-colors"
              >
                "What are the main topics covered?"
              </button>
              <button
                onClick={() => setInput("Can you summarize the key points?")}
                className="block w-full text-left text-sm text-blue-600 hover:text-blue-800 hover:bg-blue-50 px-3 py-2 rounded transition-colors"
              >
                "Can you summarize the key points?"
              </button>
            </div>
          </div>
        ) : (
          <>
            {messages.map((msg, i) => (
              <div key={i} className={`flex ${msg.type === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[80%] rounded-lg p-3 ${
                  msg.type === 'user' 
                    ? 'bg-blue-600 text-white' 
                    : msg.type === 'error'
                    ? 'bg-red-50 text-red-700 border border-red-200'
                    : 'bg-gray-100 text-gray-900'
                }`}>
                  {msg.type === 'assistant' ? (
                    <div className="text-sm leading-relaxed">
                      {renderAnswerWithTimestamps(msg.text)}
                    </div>
                  ) : (
                    <p className="text-sm">{msg.text}</p>
                  )}
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex justify-start">
                <div className="bg-gray-100 rounded-lg p-3">
                  <div className="flex items-center gap-2 text-sm text-gray-500">
                    <div className="flex gap-1">
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                    </div>
                    <span>Thinking...</span>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Input */}
      <div className="p-4 border-t border-gray-200 bg-gray-50">
        <div className="flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            className="flex-1 border-2 border-gray-300 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
            placeholder="Ask about the video..."
            disabled={loading}
          />
          <button
            onClick={sendMessage}
            disabled={loading || !input.trim()}
            className="bg-blue-600 text-white px-6 py-2 rounded-lg text-sm font-semibold hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow hover:shadow-md"
          >
            {loading ? (
              <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
            ) : (
              'Send'
            )}
          </button>
        </div>
        <p className="text-xs text-gray-500 mt-2">
          💡 Click any [MM:SS] timestamp in responses to jump to that moment
        </p>
      </div>
    </div>
  )
}
