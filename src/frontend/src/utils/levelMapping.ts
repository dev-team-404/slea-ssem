/**
 * Level Mapping Utilities
 *
 * ✅ Updated to match backend 1:1 mapping
 * Backend uses: 'beginner', 'intermediate', 'inter-advanced', 'advanced', 'elite'
 *
 * Converts between frontend (1-5 scale) and backend level strings
 */

export type BackendLevel = 'beginner' | 'intermediate' | 'inter-advanced' | 'advanced' | 'elite'
export type FrontendLevel = 1 | 2 | 3 | 4 | 5

/**
 * Frontend to Backend level mapping (1:1)
 * 1 → beginner
 * 2 → intermediate
 * 3 → inter-advanced
 * 4 → advanced
 * 5 → elite
 */
const LEVEL_TO_BACKEND: Record<number, BackendLevel> = {
  1: 'beginner',
  2: 'intermediate',
  3: 'inter-advanced',
  4: 'advanced',
  5: 'elite',
}

/**
 * Backend to Frontend level mapping (1:1 reverse)
 * beginner → 1
 * intermediate → 2
 * inter-advanced → 3
 * advanced → 4
 * elite → 5
 */
const BACKEND_TO_LEVEL: Record<BackendLevel, number> = {
  beginner: 1,
  intermediate: 2,
  'inter-advanced': 3,
  advanced: 4,
  elite: 5,
}

/**
 * Convert frontend level (1-5) to backend level string
 * @param level - Frontend level (1-5)
 * @returns Backend level string (beginner/intermediate/advanced)
 * @throws Error if level is not in valid range
 */
export function levelToBackend(level: number): BackendLevel {
  if (level < 1 || level > 5) {
    throw new Error(`Invalid level: ${level}. Must be between 1 and 5.`)
  }
  return LEVEL_TO_BACKEND[level]
}

/**
 * Convert backend level string to frontend level (1-5)
 * @param backendLevel - Backend level string (beginner/intermediate/advanced)
 * @returns Frontend level number (1-5)
 * @throws Error if backendLevel is not valid
 */
export function backendToLevel(backendLevel: string): number {
  const normalized = backendLevel.toLowerCase() as BackendLevel

  if (!BACKEND_TO_LEVEL[normalized]) {
    throw new Error(`Invalid backend level: ${backendLevel}. Must be one of: beginner, intermediate, advanced.`)
  }

  return BACKEND_TO_LEVEL[normalized]
}

/**
 * Safely convert backend level string to frontend level with fallback
 * @param backendLevel - Backend level string (can be null/undefined)
 * @returns Frontend level number (1-5) or null if invalid
 */
export function safeBackendToLevel(backendLevel: string | null | undefined): number | null {
  if (!backendLevel) {
    return null
  }

  try {
    return backendToLevel(backendLevel)
  } catch {
    return null
  }
}
