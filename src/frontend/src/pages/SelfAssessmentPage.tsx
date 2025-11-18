// REQ: REQ-F-A2-2-2
import React, { useCallback, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { submitProfileSurvey } from '../features/profile/profileSubmission'
import LevelSelector from '../components/LevelSelector'
import NumberInput from '../components/NumberInput'
import RadioGroup, { type RadioOption } from '../components/RadioGroup'
import TextAreaInput from '../components/TextAreaInput'
import InfoBox, { InfoBoxIcons } from '../components/InfoBox'
import './SelfAssessmentPage.css'

/**
 * Self Assessment Page Component
 *
 * REQ: REQ-F-A2-2-2 - 자기평가 정보(수준) 입력
 * REQ: REQ-F-A2-2-3 - 필수 필드 입력 시 "완료" 버튼 활성화
 * REQ: REQ-F-A2-2-4 - "완료" 버튼 클릭 시 user_profile 저장 및 리다이렉트
 *
 * Features:
 * - Level selection (shared LevelSelector component)
 * - Complete button (enabled when level is selected)
 * - API integration with LEVEL_MAPPING conversion
 *
 * Route: /self-assessment
 *
 * Shared Components:
 * - LevelSelector: Reused with REQ-F-A2-Signup-4
 * - NumberInput: Reusable number input field
 * - RadioGroup: Reusable radio button group
 * - TextAreaInput: Reusable textarea with character counter
 * - LEVEL_MAPPING: Centralized level conversion
 * - InfoBox: Consistent info display
 */

// Radio options for Job Role field
const JOB_ROLE_OPTIONS: RadioOption[] = [
  { value: 'S', label: 'Software' },
  { value: 'E', label: 'Engineering' },
  { value: 'M', label: 'Marketing' },
  { value: 'G', label: '기획' },
  { value: 'F', label: 'Finance/인사' },
]

// Radio options for Interests field
const INTERESTS_OPTIONS: RadioOption[] = [
  { value: 'AI', label: 'AI' },
  { value: 'ML', label: 'ML' },
  { value: 'Backend', label: 'Backend' },
  { value: 'Frontend', label: 'Frontend' },
]

const SelfAssessmentPage: React.FC = () => {
  const [level, setLevel] = useState<number | null>(null)
  const [career, setCareer] = useState<number>(0)
  const [jobRole, setJobRole] = useState<string>('')
  const [duty, setDuty] = useState<string>('')
  const [interests, setInterests] = useState<string>('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const navigate = useNavigate()

  const handleLevelChange = useCallback((selectedLevel: number) => {
    setLevel(selectedLevel)
    setErrorMessage(null)
  }, [])

  const handleCareerChange = useCallback((value: number) => {
    setCareer(value)
    setErrorMessage(null)
  }, [])

  const handleJobRoleChange = useCallback((value: string) => {
    setJobRole(value)
    setErrorMessage(null)
  }, [])

  const handleDutyChange = useCallback((value: string) => {
    setDuty(value)
    setErrorMessage(null)
  }, [])

  const handleInterestsChange = useCallback((value: string) => {
    setInterests(value)
    setErrorMessage(null)
  }, [])

  const handleCompleteClick = useCallback(async () => {
    if (level === null || isSubmitting) {
      return
    }

    // Validate career range (0-50)
    if (career < 0 || career > 50) {
      setErrorMessage('경력은 0~50 사이의 값을 입력해주세요.')
      return
    }

    setIsSubmitting(true)
    setErrorMessage(null)

    try {
      const response = await submitProfileSurvey({
        level,
        career,
        jobRole,
        duty,
        interests,
      })

      setIsSubmitting(false)
      navigate('/profile-review', {
        replace: true,
        state: { level, surveyId: response.surveyId },
      })
    } catch (error) {
      const message =
        error instanceof Error ? error.message : '자기평가 정보 저장에 실패했습니다.'
      setErrorMessage(message)
      setIsSubmitting(false)
    }
  }, [level, career, jobRole, duty, interests, isSubmitting, navigate])

  const isCompleteEnabled = level !== null && !isSubmitting

  return (
    <main className="self-assessment-page">
      <div className="self-assessment-container">
        <h1 className="page-title">자기평가 입력</h1>
        <p className="page-description">
          현재 본인의 기술 수준과 경력 정보를 입력해주세요. 이 정보는 맞춤형 테스트 생성에 활용됩니다.
        </p>

        <div className="form-section">
          {/* 1. 수준 (1-5 슬라이더) */}
          <LevelSelector
            value={level}
            onChange={handleLevelChange}
            disabled={isSubmitting}
            showTitle={true}
          />

          {/* 2. 경력(연차) - 숫자 입력 */}
          <NumberInput
            id="career"
            label="경력(연차)"
            value={career}
            onChange={handleCareerChange}
            min={0}
            max={50}
            disabled={isSubmitting}
            placeholder="0"
          />

          {/* 3. 직군 - 라디오버튼 */}
          <RadioGroup
            name="jobRole"
            legend="직군"
            options={JOB_ROLE_OPTIONS}
            value={jobRole}
            onChange={handleJobRoleChange}
            disabled={isSubmitting}
          />

          {/* 4. 담당 업무 - 텍스트 입력 */}
          <TextAreaInput
            id="duty"
            label="담당 업무"
            value={duty}
            onChange={handleDutyChange}
            disabled={isSubmitting}
            maxLength={500}
            placeholder="담당하고 있는 주요 업무를 입력해주세요"
            rows={3}
          />

          {/* 5. 관심분야 - 라디오버튼 */}
          <RadioGroup
            name="interests"
            legend="관심분야"
            options={INTERESTS_OPTIONS}
            value={interests}
            onChange={handleInterestsChange}
            disabled={isSubmitting}
          />
        </div>

        {errorMessage && <p className="error-message">{errorMessage}</p>}

        <div className="form-actions">
          <button
            type="button"
            className="complete-button"
            onClick={handleCompleteClick}
            disabled={!isCompleteEnabled}
          >
            {isSubmitting ? '제출 중...' : '완료'}
          </button>
        </div>

        <InfoBox title="자기평가 가이드" icon={InfoBoxIcons.check}>
          <ul className="info-list">
            <li>본인의 현재 기술 수준을 솔직하게 평가해주세요</li>
            <li>선택한 수준에 맞춰 테스트 난이도가 조정됩니다</li>
            <li>모든 필드는 선택사항입니다 (수준 필드 제외)</li>
            <li>나중에 프로필 수정에서 변경할 수 있습니다</li>
          </ul>
        </InfoBox>
      </div>
    </main>
  )
}

export default SelfAssessmentPage
