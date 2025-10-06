import { parseTimestamp, extractTimestamps, formatTimestamp, TIMESTAMP_REGEX } from '../timestampParser'

describe('timestampParser', () => {
  describe('parseTimestamp', () => {
    test('parses single-digit minutes and seconds', () => {
      expect(parseTimestamp('[0:0]')).toBe(0)
      expect(parseTimestamp('[1:5]')).toBe(65)
      expect(parseTimestamp('[9:9]')).toBe(549)
    })

    test('parses double-digit minutes and seconds', () => {
      expect(parseTimestamp('[10:7]')).toBe(607)
      expect(parseTimestamp('[12:34]')).toBe(754)
      expect(parseTimestamp('[59:59]')).toBe(3599)
    })

    test('parses hours format', () => {
      expect(parseTimestamp('[1:0:0]')).toBe(3600)
      expect(parseTimestamp('[1:30:0]')).toBe(5400)
      expect(parseTimestamp('[2:15:30]')).toBe(8130)
      expect(parseTimestamp('[12:34:56]')).toBe(45296)
    })

    test('handles timestamps without brackets', () => {
      expect(parseTimestamp('1:23')).toBe(83)
      expect(parseTimestamp('10:05')).toBe(605)
    })

    test('returns null for invalid formats', () => {
      expect(parseTimestamp('[invalid]')).toBe(null)
      expect(parseTimestamp('[1]')).toBe(null)
      expect(parseTimestamp('[1:2:3:4]')).toBe(null)
      expect(parseTimestamp('[]')).toBe(null)
    })

    test('handles negative numbers', () => {
      expect(parseTimestamp('[-1:30]')).toBe(null)
    })
  })

  describe('TIMESTAMP_REGEX', () => {
    test('matches various timestamp formats', () => {
      const text = 'Check [0:0], [1:5], [10:7], [12:34], [1:00:00], and [12:34:56]'
      const matches = text.match(new RegExp(TIMESTAMP_REGEX.source, 'g'))

      expect(matches).toHaveLength(6)
      expect(matches).toEqual(['[0:0]', '[1:5]', '[10:7]', '[12:34]', '[1:00:00]', '[12:34:56]'])
    })

    test('does not match invalid formats', () => {
      const text = '[123:456], [a:b], [], [1], [1:2:3:4]'
      const matches = text.match(new RegExp(TIMESTAMP_REGEX.source, 'g'))

      expect(matches).toBe(null)
    })
  })

  describe('extractTimestamps', () => {
    test('extracts all timestamps with correct positions', () => {
      const text = 'Start at [0:0], then [1:23], and finally [10:7]'
      const timestamps = extractTimestamps(text)

      expect(timestamps).toHaveLength(3)
      expect(timestamps[0]).toEqual({ original: '[0:0]', seconds: 0, index: 9 })
      expect(timestamps[1]).toEqual({ original: '[1:23]', seconds: 83, index: 21 })
      expect(timestamps[2]).toEqual({ original: '[10:7]', seconds: 607, index: 39 })
    })

    test('handles text with no timestamps', () => {
      const text = 'No timestamps here'
      const timestamps = extractTimestamps(text)

      expect(timestamps).toHaveLength(0)
    })
  })

  describe('formatTimestamp', () => {
    test('formats seconds into MM:SS', () => {
      expect(formatTimestamp(0)).toBe('[0:00]')
      expect(formatTimestamp(65)).toBe('[1:05]')
      expect(formatTimestamp(607)).toBe('[10:07]')
      expect(formatTimestamp(3599)).toBe('[59:59]')
    })

    test('formats seconds into H:MM:SS for hours', () => {
      expect(formatTimestamp(3600)).toBe('[1:00:00]')
      expect(formatTimestamp(5400)).toBe('[1:30:00]')
      expect(formatTimestamp(45296)).toBe('[12:34:56]')
    })
  })
})
