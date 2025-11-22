// REQ: REQ-F-B4-1, REQ-F-B4-2
import React from 'react'
import { TrophyIcon } from '@heroicons/react/24/solid'
import {
  getGradeKorean,
  getGradeClass,
  isEliteGrade,
  getLevelKorean,
  getLevelClass,
  getLevelGradeString,
} from '../../utils/gradeHelpers'
import { SpecialBadge } from './SpecialBadge'
import type { GradeBadgeVariant } from '../../types/grade'

interface GradeBadgeProps {
  /**
   * Grade value - accepts both string ("Elite", "Beginner") and number (1-5)
   * String: Used in TestResultsPage
   * Number: Used in HomePage, ProfileReviewPage
   */
  grade: string | number
  /**
   * Display variant
   * - default: Full badge with icon, korean, and english (TestResultsPage)
   * - compact: Smaller badge for inline display (HomePage)
   * - detailed: Full badge with additional description
   */
  variant?: GradeBadgeVariant
  /**
   * Show special badge for Elite grade
   * Default: true
   */
  showSpecialBadge?: boolean
}

/**
 * Unified Grade Badge Component
 *
 * REQ: REQ-F-B4-1 - Displays the user's grade with color-coded styling
 * REQ: REQ-F-B4-2 - Displays special badge for Elite grade users
 *
 * Features:
 * - Accepts both string grade ("Elite") and numeric level (1-5)
 * - Multiple display variants for different UI contexts
 * - Consistent styling using unified gradeConfig
 * - Automatic Elite badge detection
 */
export const GradeBadge: React.FC<GradeBadgeProps> = ({
  grade,
  variant = 'default',
  showSpecialBadge = true,
}) => {
  const isNumeric = typeof grade === 'number'
  const isElite = isEliteGrade(grade)

  // Determine display values based on grade type
  const korean = isNumeric ? getLevelKorean(grade) : getGradeKorean(grade as string)
  const cssClass = isNumeric ? getLevelClass(grade) : getGradeClass(grade as string)
  const displayGrade = isNumeric ? getLevelGradeString(grade) : grade

  return (
    <div className="grade-badge-container">
      <div className={`grade-badge ${cssClass} grade-badge-${variant}`}>
        <TrophyIcon className="grade-icon" />
        <div className="grade-info">
          <p className="grade-label">등급</p>
          <p className="grade-value">{korean}</p>
          {variant !== 'compact' && <p className="grade-english">{displayGrade}</p>}
        </div>
      </div>

      {/* REQ: REQ-F-B4-2 - Special badge for Elite grade */}
      {showSpecialBadge && isElite && (
        <div className="special-badges-container">
          <SpecialBadge badgeType="Agent Specialist" />
        </div>
      )}
    </div>
  )
}
