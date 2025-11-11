// REQ: REQ-F-A1-2
import React, { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { saveToken } from '../utils/auth'
import './CallbackPage.css'

interface UserData {
  knox_id: string
  name: string
  dept: string
  business_unit: string
  email: string
}

interface LoginResponse {
  access_token: string
  token_type: string
  user_id: string
  is_new_user: boolean
}

const CallbackPage: React.FC = () => {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const handleCallback = async () => {
      try {
        // Check for mock mode
        const isMock = searchParams.get('mock') === 'true'

        let data: LoginResponse

        if (isMock) {
          // Mock mode: 백엔드 없이 프론트엔드만 테스트할 때 사용
          // 실제 API 호출 없이 mock 응답 반환
          console.log('🎭 Mock mode: 백엔드 API 호출 생략')

          // Mock 응답 생성 (신규 사용자로 시뮬레이션)
          data = {
            access_token: 'mock_jwt_token_' + Date.now(),
            token_type: 'bearer',
            user_id: 'test_user_001',
            is_new_user: true, // 신규 사용자 시뮬레이션 (false로 변경하면 기존 사용자)
          }

          // 실제 API 호출처럼 약간의 딜레이 추가
          await new Promise((resolve) => setTimeout(resolve, 500))
        } else {
          // 실제 모드: 백엔드 API 호출
          // Extract user data from URL parameters
          const knox_id = searchParams.get('knox_id')
          const name = searchParams.get('name')
          const dept = searchParams.get('dept')
          const business_unit = searchParams.get('business_unit')
          const email = searchParams.get('email')

          // Validate required parameters
          if (!knox_id || !name || !dept || !business_unit || !email) {
            setError('필수 정보가 누락되었습니다.')
            setLoading(false)
            return
          }

          const userData: UserData = {
            knox_id,
            name,
            dept,
            business_unit,
            email,
          }

          // Call backend authentication API
          const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify(userData),
          })

          if (!response.ok) {
            const errorData = await response.json()
            throw new Error(errorData.detail || '로그인에 실패했습니다.')
          }

          data = await response.json()
        }

        // Save JWT token to localStorage
        saveToken(data.access_token)

        // REQ-F-A1-2: All users (new and existing) redirect to home screen
        navigate('/home')
      } catch (err) {
        console.error('Authentication error:', err)
        setError(
          err instanceof Error ? err.message : '로그인에 실패했습니다. 다시 시도해주세요.'
        )
        setLoading(false)
      }
    }

    handleCallback()
  }, [searchParams, navigate])

  if (loading && !error) {
    return (
      <div className="callback-page">
        <div className="callback-container">
          <div className="loading-spinner" />
          <p className="loading-text">로그인 처리 중입니다...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="callback-page">
        <div className="callback-container error-container">
          <h2 className="error-title">로그인 실패</h2>
          <p className="error-message">{error}</p>
          <div className="error-links">
            <a
              href="https://account.samsung.com"
              className="help-link"
              target="_blank"
              rel="noopener noreferrer"
            >
              계정 정보 확인
            </a>
            <a
              href="mailto:support@samsung.com"
              className="help-link"
              target="_blank"
              rel="noopener noreferrer"
            >
              관리자 문의
            </a>
          </div>
        </div>
      </div>
    )
  }

  return null
}

export default CallbackPage
