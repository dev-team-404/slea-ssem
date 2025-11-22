// REQ: REQ-F-B4-1, REQ-F-B4-7, REQ-F-B5-Retake-4
import React from 'react'
import { HomeIcon, ArrowPathIcon, DocumentTextIcon } from '@heroicons/react/24/outline'

interface ActionButtonsProps {
  round: number  // REQ-F-B5-Retake-4: Hide retake button for Round 2
  onGoHome: () => void
  onRetake: () => void
  onViewExplanations?: () => void // REQ: REQ-F-B4-7
}

/**
 * Action Buttons Component
 * Displays navigation buttons for home, retake, and explanations
 *
 * REQ: REQ-F-B4-7 - Added "해설 보기" button
 * REQ: REQ-F-B5-Retake-4 - Hide "재응시하기" button after Round 2
 */
export const ActionButtons: React.FC<ActionButtonsProps> = ({
  round,
  onGoHome,
  onRetake,
  onViewExplanations,
}) => {
  return (
    <div className="action-buttons">
      {/* REQ: REQ-F-B4-7 - View Explanations Button */}
      {onViewExplanations && (
        <button type="button" className="explanation-button" onClick={onViewExplanations}>
          <DocumentTextIcon className="button-icon" />
          문항별 해설 보기
        </button>
      )}

      <button type="button" className="primary-button" onClick={onGoHome}>
        <HomeIcon className="button-icon" />
        홈화면으로 이동
      </button>

      {/* REQ-F-B5-Retake-4: Only show retake button for Round 1 */}
      {round === 1 && (
        <button type="button" className="secondary-button" onClick={onRetake}>
          <ArrowPathIcon className="button-icon" />
          2차 진행
        </button>
      )}
    </div>
  )
}
