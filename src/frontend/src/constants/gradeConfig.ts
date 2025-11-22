/**
 * Unified Grade Configuration
 *
 * Single source of truth for all grade/level mappings.
 * This configuration ensures consistency across:
 * - HomePage (numeric grades 1-5)
 * - TestResultsPage (string grades like "Elite", "Beginner")
 * - ProfileReviewPage (level descriptions)
 * - API communication (backend level strings)
 */

import type { FrontendLevel, BackendLevel, GradeString, GradeInfo } from '../types/grade'

/**
 * Complete Grade Configuration
 *
 * IMPORTANT: This is now aligned 1:1 with backend enum values
 * Backend uses: 'beginner', 'intermediate', 'inter-advanced', 'advanced', 'elite'
 * (stored as capitalized in PostgreSQL: 'Beginner', 'Intermediate', 'Inter-Advanced', 'Advanced', 'Elite')
 */
export const GRADE_CONFIG: Record<FrontendLevel, GradeInfo> = {
  1: {
    level: 1,
    backendLevel: 'beginner',
    gradeString: 'Beginner',
    korean: '입문',
    cssClass: 'grade-beginner',
    description: '기초 개념 학습 중',
  },
  2: {
    level: 2,
    backendLevel: 'intermediate',
    gradeString: 'Intermediate',
    korean: '초급',
    cssClass: 'grade-intermediate',
    description: '기본 업무 수행 가능',
  },
  3: {
    level: 3,
    backendLevel: 'inter-advanced', // ✅ Fixed: was 'intermediate'
    gradeString: 'Inter-Advanced',
    korean: '중급',
    cssClass: 'grade-Inter-Advanced',
    description: '독립적으로 업무 수행',
  },
  4: {
    level: 4,
    backendLevel: 'advanced',
    gradeString: 'Advanced',
    korean: '고급',
    cssClass: 'grade-advanced',
    description: '복잡한 문제 해결 가능',
  },
  5: {
    level: 5,
    backendLevel: 'elite', // ✅ Fixed: was 'advanced'
    gradeString: 'Elite',
    korean: '전문가',
    cssClass: 'grade-elite',
    description: '다른 사람을 지도 가능',
  },
}

/**
 * Reverse mapping: String Grade → Frontend Level
 */
export const GRADE_STRING_TO_LEVEL: Record<GradeString, FrontendLevel> = {
  Beginner: 1,
  Intermediate: 2,
  'Inter-Advanced': 3,
  Advanced: 4,
  Elite: 5,
}

/**
 * Reverse mapping: Backend Level → Frontend Level
 * Now 1:1 mapping with no ambiguity
 */
export const BACKEND_TO_LEVEL: Record<BackendLevel, FrontendLevel> = {
  beginner: 1,
  intermediate: 2,
  'inter-advanced': 3, // ✅ Added
  advanced: 4,
  elite: 5, // ✅ Added
}

/**
 * Elite grade threshold
 */
export const ELITE_GRADE_LEVEL = 5
