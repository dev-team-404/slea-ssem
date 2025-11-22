// REQ: REQ-F-B4-1, REQ-F-B4-2
/**
 * Unified Grade utility functions
 *
 * Provides conversion and utility functions for all grade/level representations:
 * - Frontend Level (1-5 numeric)
 * - Backend Level ("beginner", "intermediate", "advanced")
 * - Grade String ("Beginner", "Elite", etc.)
 * - Korean translations
 * - CSS classes
 */

import { GRADE_CONFIG, GRADE_STRING_TO_LEVEL, ELITE_GRADE_LEVEL } from '../constants/gradeConfig'
import type { FrontendLevel, GradeString } from '../types/grade'

/**
 * ============================================================================
 * Level → Other conversions (from numeric level 1-5)
 * ============================================================================
 */

/**
 * Convert frontend level (1-5) to Korean text
 * @param level - Frontend level (1-5) or null/undefined
 * @returns Korean text representation or fallback
 */
export const getLevelKorean = (level: FrontendLevel | number | null | undefined): string => {
  if (!level || level < 1 || level > 5) return '정보 없음'
  return GRADE_CONFIG[level as FrontendLevel].korean
}

/**
 * Convert frontend level (1-5) to grade string
 * @param level - Frontend level (1-5) or null/undefined
 * @returns Grade string (e.g., "Elite", "Beginner") or fallback
 */
export const getLevelGradeString = (level: FrontendLevel | number | null | undefined): string => {
  if (!level || level < 1 || level > 5) return 'Unknown'
  return GRADE_CONFIG[level as FrontendLevel].gradeString
}

/**
 * Convert frontend level (1-5) to CSS class
 * @param level - Frontend level (1-5) or null/undefined
 * @returns CSS class name
 */
export const getLevelClass = (level: FrontendLevel | number | null | undefined): string => {
  if (!level || level < 1 || level > 5) return 'grade-default'
  return GRADE_CONFIG[level as FrontendLevel].cssClass
}

/**
 * Convert frontend level (1-5) to description text
 * @param level - Frontend level (1-5) or null/undefined
 * @returns Description text
 */
export const getLevelDescription = (level: FrontendLevel | number | null | undefined): string => {
  if (!level || level < 1 || level > 5) return '정보 없음'
  return GRADE_CONFIG[level as FrontendLevel].description
}

/**
 * ============================================================================
 * Grade String → Other conversions (from "Elite", "Beginner", etc.)
 * ============================================================================
 */

/**
 * Convert English grade to Korean
 * @param grade - Grade string (e.g., "Elite", "Beginner")
 * @returns Korean text
 */
export const getGradeKorean = (grade: string): string => {
  const level = GRADE_STRING_TO_LEVEL[grade as GradeString]
  if (!level) return grade
  return GRADE_CONFIG[level].korean
}

/**
 * Get grade CSS class for color coding
 * @param grade - Grade string (e.g., "Elite", "Beginner")
 * @returns CSS class name
 */
export const getGradeClass = (grade: string): string => {
  const level = GRADE_STRING_TO_LEVEL[grade as GradeString]
  if (!level) return 'grade-default'
  return GRADE_CONFIG[level].cssClass
}

/**
 * Convert grade string to frontend level
 * @param grade - Grade string (e.g., "Elite", "Beginner")
 * @returns Frontend level (1-5) or null
 */
export const getGradeLevel = (grade: string): number | null => {
  return GRADE_STRING_TO_LEVEL[grade as GradeString] || null
}

/**
 * ============================================================================
 * Special checks
 * ============================================================================
 */

/**
 * Check if grade is Elite
 *
 * REQ: REQ-F-B4-2 - Elite 등급 확인하여 특수 배지 표시
 * @param grade - Grade string OR numeric level
 * @returns true if Elite grade
 */
export const isEliteGrade = (grade: string | number): boolean => {
  if (typeof grade === 'number') {
    return grade === ELITE_GRADE_LEVEL
  }
  return grade === 'Elite'
}

/**
 * ============================================================================
 * Utility functions
 * ============================================================================
 */

/**
 * Format decimal - remove trailing zero for integers
 * Examples: 85.0 -> "85", 87.5 -> "87.5"
 * @param value - Numeric value
 * @returns Formatted string
 */
export const formatDecimal = (value: number): string => {
  return Number(value.toFixed(1)).toString()
}
