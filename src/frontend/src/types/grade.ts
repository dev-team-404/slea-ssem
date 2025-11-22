/**
 * Common Grade and Level Type Definitions
 *
 * Centralized type definitions for grade and level system to ensure consistency
 * across the application.
 */

/**
 * Frontend Level (1-5 scale)
 * Used in: Profile setup, Self-assessment, HomePage, ProfileReviewPage
 */
export type FrontendLevel = 1 | 2 | 3 | 4 | 5

/**
 * Backend Level (string enum)
 * Used in: API communication with backend
 * Maps 1:1 with frontend levels and grade strings
 */
export type BackendLevel = 'beginner' | 'intermediate' | 'inter-advanced' | 'advanced' | 'elite'

/**
 * Grade String (TestResults system)
 * Used in: TestResultsPage, GradeBadge
 */
export type GradeString =
  | 'Beginner'
  | 'Intermediate'
  | 'Inter-Advanced'
  | 'Advanced'
  | 'Elite'

/**
 * Grade Configuration
 * Complete information about a grade/level
 */
export type GradeInfo = {
  /** Frontend numeric level (1-5) */
  level: FrontendLevel
  /** Backend level string */
  backendLevel: BackendLevel
  /** Grade display string */
  gradeString: GradeString
  /** Korean translation */
  korean: string
  /** CSS class name */
  cssClass: string
  /** Short description */
  description: string
}

/**
 * Grade Badge Variant
 * Different visual styles for displaying grades
 */
export type GradeBadgeVariant = 'default' | 'compact' | 'detailed'
