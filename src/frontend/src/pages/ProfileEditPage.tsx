// REQ: REQ-F-A2-Edit
import React, { useState, useEffect, useCallback } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { profileService } from '../services/profileService'
import { useNicknameCheck } from '../hooks/useNicknameCheck'
import { useUserProfile } from '../hooks/useUserProfile'
import { PageLayout } from '../components'
import LevelSelector from '../components/LevelSelector'
import CareerInfoSection from '../components/CareerInfoSection'
import RadioButtonGrid, { type RadioButtonOption } from '../components/RadioButtonGrid'
import InfoBox, { InfoBoxIcons } from '../components/InfoBox'
import { safeBackendToLevel } from '../utils/levelMapping'
import {
  shouldValidateNickname as shouldCheckNickname,
} from '../utils/profileValidation'
import { executeProfileUpdate, type UpdateHandlerContext } from '../utils/profileUpdateHandler'
import './ProfileEditPage.css'

/**
 * Profile Edit Page Component
 *
 * REQ: REQ-F-A2-Edit - 프로필 수정 (닉네임/자기평가 변경)
 *
 * Features:
 * - Load existing profile data on mount
 * - Edit all profile fields in one page:
 *   - Nickname (with duplicate check, excluding self)
 *   - Level (1-5 slider)
 *   - Career (0-50 number input)
 *   - Job role (radio button grid 3 columns)
 *   - Duty (textarea with character counter)
 *   - Interests (radio button grid 3 columns)
 * - Conditional save (only call APIs for changed fields)
 * - Redirect to /profile-review after save
 *
 * Route: /profile/edit
 *
 * Access:
 * - Header nickname → dropdown → "프로필 수정"
 * - ProfileReviewPage → "수정" button
 */

// Radio button grid options for Interests field
const INTERESTS_OPTIONS: RadioButtonOption[] = [
  { value: 'AI', label: 'AI' },
  { value: 'ML', label: 'ML' },
  { value: 'Backend', label: 'Backend' },
  { value: 'Frontend', label: 'Frontend' },
]

const ProfileEditPage: React.FC = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const { checkNickname } = useUserProfile()

  // Get returnTo path from navigation state (default to /profile-review)
  const returnTo = (location.state as { returnTo?: string })?.returnTo || '/profile-review'

  // Original values (for change detection)
  const [originalNickname, setOriginalNickname] = useState<string>('')
  const [originalLevel, setOriginalLevel] = useState<number | null>(null)
  const [originalCareer, setOriginalCareer] = useState<number>(0)
  const [originalJobRole, setOriginalJobRole] = useState<string>('')
  const [originalDuty, setOriginalDuty] = useState<string>('')
  const [originalInterests, setOriginalInterests] = useState<string>('')

  // Current form values
  const [level, setLevel] = useState<number | null>(null)
  const [career, setCareer] = useState<number>(0)
  const [jobRole, setJobRole] = useState<string>('')
  const [duty, setDuty] = useState<string>('')
  const [interests, setInterests] = useState<string>('')

  const [isLoading, setIsLoading] = useState(true)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  // Nickname validation using useNicknameCheck hook
  const {
    nickname,
    setNickname,
    checkStatus,
    errorMessage: nicknameErrorMessage,
    checkNickname: validateNickname,
    setManualError,
  } = useNicknameCheck()

  // Load existing profile data on mount
  useEffect(() => {
    const loadProfile = async () => {
      try {
        setIsLoading(true)
        setErrorMessage(null)

        // Load nickname
        const currentNickname = await checkNickname()
        if (currentNickname) {
          setNickname(currentNickname) // This will use the hook's setNickname
          setOriginalNickname(currentNickname)
        }

        // Load profile survey data
        const surveyData = await profileService.getSurvey()

        // Convert level string to number for LevelSelector using utility
        const levelNum = safeBackendToLevel(surveyData.level)

        // Extract first interest from array (since we only support single selection)
        const interestsStr =
          surveyData.interests && surveyData.interests.length > 0
            ? surveyData.interests[0]
            : ''

        // Set form values
        setLevel(levelNum)
        setOriginalLevel(levelNum)

        setCareer(surveyData.career ?? 0)
        setOriginalCareer(surveyData.career ?? 0)

        setJobRole(surveyData.job_role ?? '')
        setOriginalJobRole(surveyData.job_role ?? '')

        setDuty(surveyData.duty ?? '')
        setOriginalDuty(surveyData.duty ?? '')

        setInterests(interestsStr)
        setOriginalInterests(interestsStr)

        setIsLoading(false)
      } catch (error) {
        console.error('Failed to load profile:', error)
        setErrorMessage('프로필 정보를 불러오는데 실패했습니다.')
        setIsLoading(false)
      }
    }

    loadProfile()
  }, [checkNickname])

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

  const handleNicknameChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      setNickname(e.target.value) // This will use the hook's setNickname
      setErrorMessage(null)
    },
    [setNickname]
  )

  const handleCheckNickname = useCallback(async () => {
    // If nickname hasn't changed, skip validation using utility
    if (!shouldCheckNickname(nickname, originalNickname)) {
      setManualError('현재 사용 중인 닉네임입니다.')
      return
    }

    await validateNickname()
  }, [nickname, originalNickname, validateNickname, setManualError])

  const handleSave = useCallback(async () => {
    if (isSubmitting) return

    // Basic client-side checks only
    if (!nickname || !nickname.trim()) {
      setErrorMessage('닉네임을 입력해주세요.')
      return
    }

    if (level === null) {
      setErrorMessage('기술 수준을 선택해주세요.')
      return
    }

    // Check if nickname changed and needs validation
    const nicknameChanged = shouldCheckNickname(nickname, originalNickname)
    if (nicknameChanged && checkStatus !== 'available') {
      setErrorMessage('닉네임 중복 확인을 완료해주세요.')
      return
    }

    setIsSubmitting(true)
    setErrorMessage(null)
    setSuccessMessage(null)

    try {
      // Prepare update context for handler map
      const updateContext: UpdateHandlerContext = {
        current: {
          nickname,
          level,
          career,
          jobRole,
          duty,
          interests,
        },
        original: {
          nickname: originalNickname,
          level: originalLevel,
          career: originalCareer,
          jobRole: originalJobRole,
          duty: originalDuty,
          interests: originalInterests,
        },
      }

      // Execute update handlers using handler map pattern
      const executedHandlers = await executeProfileUpdate(updateContext)

      if (executedHandlers.length === 0) {
        setErrorMessage('변경된 항목이 없습니다.')
        setIsSubmitting(false)
        return
      }

      // Show success message
      setSuccessMessage('저장되었습니다')
      setIsSubmitting(false)

      // Redirect to returnTo path after 1 second
      setTimeout(() => {
        navigate(returnTo, { replace: true })
      }, 1000)
    } catch (error) {
      const message =
        error instanceof Error ? error.message : '프로필 저장에 실패했습니다.'
      setErrorMessage(message)
      setIsSubmitting(false)
    }
  }, [
    nickname,
    level,
    career,
    jobRole,
    duty,
    interests,
    originalNickname,
    originalLevel,
    originalCareer,
    originalJobRole,
    originalDuty,
    originalInterests,
    checkStatus,
    isSubmitting,
    navigate,
    returnTo,
  ])

  const isSaveEnabled = level !== null && !isSubmitting && !isLoading

  if (isLoading) {
    return (
      <PageLayout mainClassName="profile-edit-page" containerClassName="profile-edit-container">
        <p className="loading-message">프로필 정보를 불러오는 중...</p>
      </PageLayout>
    )
  }

  return (
    <PageLayout mainClassName="profile-edit-page" containerClassName="profile-edit-container">
        <h1 className="page-title">프로필 수정</h1>
        <p className="page-description">
          닉네임과 자기평가 정보를 수정할 수 있습니다. 기술 수준은 필수 항목입니다.
        </p>

        <div className="form-section">
          {/* 1. 닉네임 입력 + 중복 확인 */}
          <div className="nickname-input-field">
            <label htmlFor="nickname" className="nickname-label">
              닉네임
            </label>
            <div className="nickname-input-group">
              <input
                id="nickname"
                type="text"
                className="nickname-input"
                value={nickname}
                onChange={handleNicknameChange}
                disabled={isSubmitting}
                placeholder="닉네임을 입력하세요"
              />
              <button
                type="button"
                className="check-button"
                onClick={handleCheckNickname}
                disabled={isSubmitting || !nickname.trim()}
              >
                중복 확인
              </button>
            </div>
            {checkStatus === 'checking' && (
              <p className="status-message checking">확인 중...</p>
            )}
            {checkStatus === 'available' && (
              <p className="status-message available">사용 가능한 닉네임입니다</p>
            )}
            {checkStatus === 'taken' && (
              <p className="status-message taken">이미 사용 중인 닉네임입니다</p>
            )}
            {checkStatus === 'error' && nicknameErrorMessage && (
              <p className="status-message error">
                {nicknameErrorMessage}
              </p>
            )}
          </div>
        </div>

        {/* 경력 정보 섹션 */}
        <div className="form-section">
          <h2 className="section-title">경력 정보</h2>
          <CareerInfoSection
            career={career}
            jobRole={jobRole}
            duty={duty}
            onCareerChange={handleCareerChange}
            onJobRoleChange={handleJobRoleChange}
            onDutyChange={handleDutyChange}
            disabled={isSubmitting}
            showTitle={false}
          />
        </div>

        {/* 관심분야 및 기술 수준 섹션 */}
        <div className="form-section">
          <h2 className="section-title">관심분야 및 기술 수준</h2>

          {/* 관심분야 */}
          <RadioButtonGrid
            name="interests"
            legend="관심분야"
            options={INTERESTS_OPTIONS}
            value={interests}
            onChange={handleInterestsChange}
            disabled={isSubmitting}
          />

          {/* 기술 수준 */}
          <LevelSelector
            value={level}
            onChange={handleLevelChange}
            disabled={isSubmitting}
            showTitle={false}
          />
        </div>

        {errorMessage && <p className="error-message">{errorMessage}</p>}
        {successMessage && <p className="success-message">{successMessage}</p>}

        <div className="form-actions">
          <button
            type="button"
            className="save-button"
            onClick={handleSave}
            disabled={!isSaveEnabled}
          >
            {isSubmitting ? '저장 중...' : '저장'}
          </button>
        </div>

        <InfoBox title="프로필 수정 안내" icon={InfoBoxIcons.check}>
          <ul className="info-list">
            <li>닉네임 변경 시 중복 확인이 필요합니다</li>
            <li>기술 수준은 필수 항목입니다 (1~5 중 선택)</li>
            <li>경력은 0~50년 사이로 입력해주세요</li>
            <li>직군: S(Software), E(Engineering), M(Marketing), G(기획), F(Finance/인사)</li>
            <li>변경 사항이 없으면 API 호출을 생략합니다</li>
            <li>저장 후 프로필 리뷰 페이지로 이동합니다</li>
          </ul>
        </InfoBox>
    </PageLayout>
  )
}

export default ProfileEditPage
