// REQ: REQ-F-A2-Signup-3, REQ-F-A2-Signup-4, REQ-F-A2-Signup-5
import React, { useMemo, useState } from 'react'
import { useNicknameCheck } from '../hooks/useNicknameCheck'
import NicknameInputSection from '../components/NicknameInputSection'
import LevelSelector from '../components/LevelSelector'
import InfoBox, { InfoBoxIcons } from '../components/InfoBox'
import './SignupPage.css'

/**
 * Unified Signup Page Component
 *
 * REQ: REQ-F-A2-Signup-3 - 통합 회원가입 페이지에 닉네임 입력 섹션 표시
 * REQ: REQ-F-A2-Signup-4 - 통합 회원가입 페이지에 자기평가 입력 섹션 표시 (수준만)
 * REQ: REQ-F-A2-Signup-5 - 닉네임 중복 확인 완료 + 모든 필수 필드 입력 시 "가입 완료" 버튼 활성화
 *
 * Features:
 * - Nickname input section (REQ-F-A2-Signup-3)
 *   - Input field (3-30 characters)
 *   - Duplicate check button
 *   - Real-time validation
 *   - Suggestions on duplicate (up to 3)
 * - Profile input section (REQ-F-A2-Signup-4)
 *   - Level slider (1-5)
 * - Submit button activation (REQ-F-A2-Signup-5)
 *   - Enabled when: checkStatus === 'available' AND level !== null
 *   - Disabled otherwise
 *
 * Route: /signup
 */

const SignupPage: React.FC = () => {
  // REQ-F-A2-Signup-3: Nickname state (from useNicknameCheck hook)
  const {
    nickname,
    setNickname,
    checkStatus,
    errorMessage,
    suggestions,
    checkNickname,
  } = useNicknameCheck()

  // REQ-F-A2-Signup-4: Level state
  const [level, setLevel] = useState<number | null>(null)

  // REQ-F-A2-Signup-5: Submit button activation logic
  // Enable when: nickname is available AND level is selected
  const isSubmitDisabled = useMemo(() => {
    return checkStatus !== 'available' || level === null
  }, [checkStatus, level])

  return (
    <main className="signup-page">
      <div className="signup-container">
        <h1 className="page-title">회원가입</h1>
        <p className="page-description">
          닉네임과 자기평가 정보를 입력하여 가입을 완료하세요.
        </p>

        {/* REQ-F-A2-Signup-3: Nickname Section */}
        <NicknameInputSection
          nickname={nickname}
          setNickname={setNickname}
          checkStatus={checkStatus}
          errorMessage={errorMessage}
          suggestions={suggestions}
          onCheckClick={checkNickname}
          disabled={false}
          showInfoBox={true}
        />

        {/* REQ-F-A2-Signup-4: Profile Section (Level only) */}
        <LevelSelector
          value={level}
          onChange={setLevel}
          disabled={false}
          showTitle={true}
        />

        <InfoBox title="향후 추가 예정" icon={InfoBoxIcons.clock}>
          <ul className="info-list">
            <li>경력(연차) 입력</li>
            <li>직군 선택</li>
            <li>담당 업무 입력</li>
            <li>관심분야 다중 선택</li>
          </ul>
        </InfoBox>

        {/* REQ-F-A2-Signup-5/6: Submit Button */}
        <div className="form-actions">
          <button
            type="button"
            className="submit-button"
            disabled={isSubmitDisabled}
          >
            가입 완료
          </button>
        </div>
      </div>
    </main>
  )
}

export default SignupPage
