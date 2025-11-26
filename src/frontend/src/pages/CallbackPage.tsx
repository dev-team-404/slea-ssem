// REQ: REQ-F-A1-4, REQ-F-A1-5
import React from 'react'
import { useSearchParams } from 'react-router-dom'
import { PageLayout } from '../components'
import { useAuthCallback } from '../hooks/useAuthCallback'
import { LoadingSpinner } from '../components/LoadingSpinner'
import { ErrorMessage } from '../components/ErrorMessage'
import './CallbackPage.css'

/**
 * OIDC callback page for handling authentication with PKCE
 *
 * REQ-F-A1-4: Receives authorization code and sends it with code_verifier to backend
 * REQ-F-A1-5: Receives HttpOnly JWT cookie and redirects to /home
 *
 * Flow:
 * 1. Extract code and state from URL (?code=xxx&state=xxx)
 * 2. Retrieve PKCE params from sessionStorage
 * 3. Verify state (CSRF protection)
 * 4. Call POST /api/auth/oidc/callback with { code, code_verifier, nonce }
 * 5. Receive HttpOnly cookie with JWT
 * 6. Clear PKCE params from sessionStorage
 * 7. Redirect to /home
 */
const CallbackPage: React.FC = () => {
  const [searchParams] = useSearchParams()
  const { loading, error } = useAuthCallback(searchParams)

  if (loading && !error) {
    return (
      <PageLayout mainClassName="callback-page" containerClassName="callback-container">
        <LoadingSpinner message="로그인 처리 중입니다..." />
      </PageLayout>
    )
  }

  if (error) {
    return (
      <PageLayout mainClassName="callback-page" containerClassName="callback-container">
        <ErrorMessage
          title="로그인 실패"
          message={error}
          helpLinks={[
            {
              text: '계정 정보 확인',
              href: 'https://account.samsung.com',
            },
            {
              text: '관리자 문의',
              href: 'mailto:support@samsung.com',
            },
          ]}
        />
      </PageLayout>
    )
  }

  return null
}

export default CallbackPage
