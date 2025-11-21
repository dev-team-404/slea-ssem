// REQ: REQ-F-A1-2, REQ-F-A2-1, REQ-F-A3, REQ-F-A2-Signup-1
import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { PlayIcon, ExclamationTriangleIcon } from '@heroicons/react/24/outline'
import { getToken } from '../utils/auth'
import { useUserProfile } from '../hooks/useUserProfile'
import { profileService } from '../services/profileService'
import { PageLayout } from '../components'
import './HomePage.css'

type SurveyProgress = {
  surveyId: string | null
  level: number | null
}

const getSurveyProgress = (): SurveyProgress => {
  if (typeof window === 'undefined') {
    return { surveyId: null, level: null }
  }

  const surveyId = localStorage.getItem('lastSurveyId')
  const levelRaw = localStorage.getItem('lastSurveyLevel')

  return {
    surveyId,
    level: levelRaw ? Number(levelRaw) : null,
  }
}

const HomePage: React.FC = () => {
  const navigate = useNavigate()
  const { nickname, loading: nicknameLoading, checkNickname } = useUserProfile()
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  // REQ-F-A2-Signup-1: Load nickname on mount to determine if signup button should show
  useEffect(() => {
    const loadNickname = async () => {
      try {
        await checkNickname()
      } catch (err) {
        console.error('Failed to load nickname:', err)
        // Silently fail for nickname check, user can still use the page
      }
    }

    loadNickname()
  }, [checkNickname])

    const handleStart = async () => {
      try {
        // REQ-F-A3-5: Check consent status first
        const consentStatus = await profileService.getConsentStatus()

        if (!consentStatus.consented) {
          // User hasn't consented yet, redirect to consent page
          navigate('/consent')
          return
        }

        // REQ-F-A2-1: Check if user has set nickname before proceeding
        const currentNickname = await checkNickname()
        const { surveyId, level } = getSurveyProgress()

        if (currentNickname === null) {
          // User hasn't set nickname yet, redirect to nickname setup
          navigate('/nickname-setup')
        } else if (surveyId) {
          // User completed profile, show review page for final confirmation/test entry
          navigate('/profile-review', {
            state: {
              surveyId,
              level: level ?? undefined,
            },
          })
        } else {
          // User has nickname but no profile yet, proceed to career info
          navigate('/career-info')
        }
      } catch (err) {
        // Log detailed error for debugging
        console.error('Failed to check user profile:', err)

        // Show user-friendly error message with hint
        const errorMsg = err instanceof Error ? err.message : 'Unknown error'
        setErrorMessage(`프로필 정보를 불러오는데 실패했습니다: ${errorMsg}`)
      }
    }

  // Verify user is authenticated
  const token = getToken()
  if (!token) {
    navigate('/')
    return null
  }

  return (
    <PageLayout
      showHeader
      nickname={nickname}
      isNicknameLoading={nicknameLoading}
      mainClassName="home-page"
      containerClassName="home-container"
    >
      <div className="home-sections">
        {/* Section 1: 메인 CTA */}
        <section className="home-section">
          <div className="home-content">
            <p className="home-label">TODAY'S LEARNING TEST</p>
            <h1 className="home-title">
              오늘 당신의 AI 역량을<br/>
              정확하게 측정해보세요.
            </h1>
            <p className="home-description">
              개인 맞춤형 테스트로 당신의 실력을 객관적으로 측정해보세요.
            </p>

            {errorMessage && (
              <div className="error-message">
                <ExclamationTriangleIcon className="error-icon" />
                <span>{errorMessage}</span>
              </div>
            )}

            <div className="button-group">
              <button className="start-button" onClick={handleStart}>
                <PlayIcon className="button-icon" />
                레벨테스트 시작하기
              </button>
            </div>
          </div>

          <div className="info-card">
            <p className="info-card-title">나의 현재 레벨</p>
            <p className="info-card-value">-</p>
            <p className="home-description" style={{ fontSize: '0.875rem', marginTop: '0.5rem' }}>
              테스트를 완료하면<br/>당신의 레벨이 표시됩니다
            </p>
          </div>
        </section>
      </div>
    </PageLayout>
  )
}

export default HomePage
