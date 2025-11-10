// REQ: REQ-F-A1-1
import React from 'react'
import './LoginPage.css'

const LoginPage: React.FC = () => {
  const handleLogin = () => {
    window.location.href = '/api/auth/login'
  }

  return (
    <main className="login-page">
      <div className="login-container" data-testid="login-container">
        <h1 className="login-title">SLEA-SSEM</h1>
        <button
          type="button"
          className="login-button"
          onClick={handleLogin}
          aria-label="Samsung AD로 로그인"
        >
          Samsung AD로 로그인
        </button>
      </div>
    </main>
  )
}

export default LoginPage
