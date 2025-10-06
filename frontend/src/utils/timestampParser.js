/**
 * Parses timestamp strings in various formats and converts them to seconds
 * Supports formats: [M:S], [MM:SS], [H:MM:SS], [HH:MM:SS]
 * Examples: [0:0], [1:5], [10:7], [1:23], [59:59], [1:00:00], [12:34:56]
 *
 * @param {string} timestampStr - Timestamp string in format [H:MM:SS] or [MM:SS]
 * @returns {number|null} Total seconds, or null if invalid
 */
export function parseTimestamp(timestampStr) {
  // Remove brackets if present
  const cleaned = timestampStr.replace(/[\[\]]/g, '').trim()

  // Split by colon
  const parts = cleaned.split(':')

  if (parts.length < 2 || parts.length > 3) {
    return null
  }

  try {
    const numbers = parts.map(p => {
      const num = parseInt(p, 10)
      if (isNaN(num) || num < 0) {
        throw new Error('Invalid number')
      }
      return num
    })

    let hours = 0
    let minutes = 0
    let seconds = 0

    if (numbers.length === 2) {
      // MM:SS format
      [minutes, seconds] = numbers
    } else if (numbers.length === 3) {
      // HH:MM:SS format
      [hours, minutes, seconds] = numbers
    }

    // Validate ranges (allow flexible minutes/seconds for edge cases)
    if (seconds > 59 || minutes > 59) {
      console.warn(`Timestamp has unusual values: ${timestampStr}`)
      // Still allow it - could be malformed but user intent is clear
    }

    return hours * 3600 + minutes * 60 + seconds
  } catch (e) {
    console.error(`Failed to parse timestamp: ${timestampStr}`, e)
    return null
  }
}

/**
 * Comprehensive regex to match timestamp formats in text
 * Matches: [0:0], [1:5], [10:7], [1:23], [59:59], [1:00:00], [12:34:56]
 */
export const TIMESTAMP_REGEX = /\[(\d{1,2}):(\d{1,2})(?::(\d{1,2}))?\]/g

/**
 * Extracts all timestamps from text
 * @param {string} text - Text containing timestamps
 * @returns {Array<{original: string, seconds: number, index: number}>}
 */
export function extractTimestamps(text) {
  const timestamps = []
  let match

  const regex = new RegExp(TIMESTAMP_REGEX.source, 'g')

  while ((match = regex.exec(text)) !== null) {
    const seconds = parseTimestamp(match[0])
    if (seconds !== null) {
      timestamps.push({
        original: match[0],
        seconds: seconds,
        index: match.index
      })
    }
  }

  return timestamps
}

/**
 * Formats seconds into timestamp string
 * @param {number} seconds - Total seconds
 * @returns {string} Formatted timestamp [MM:SS] or [H:MM:SS]
 */
export function formatTimestamp(seconds) {
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const secs = Math.floor(seconds % 60)

  if (hours > 0) {
    return `[${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}]`
  }
  return `[${minutes}:${secs.toString().padStart(2, '0')}]`
}
