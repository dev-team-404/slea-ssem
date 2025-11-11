// REQ: REQ-F-A1-2, REQ-F-A3
import React from 'react'
import { useNavigate } from 'react-router-dom'
import { getToken } from '../utils/auth'
import './HomePage.css'

const HomePage: React.FC = () => {
  const navigate = useNavigate()

  const handleStart = () => {
    // REQ-F-A3: When user clicks "Start", check if nickname/profile exists
    // For now, navigate to signup (nickname setup)
    // This will be enhanced when REQ-F-A2, REQ-F-A4 are implemented
    navigate('/signup')
  }

  // Verify user is authenticated
  const token = getToken()
  if (!token) {
    navigate('/')
    return null
  }

  return (
    <main className="home-page">
      <div className="home-container">
        <h1 className="home-title">S.LSI Learning Platform</h1>
        <p className="home-description">
          AI 기반 학습 플랫폼에 오신 것을 환영합니다.
        </p>
        <p className="home-subtitle">
          개인 맞춤형 레벨 테스트로 학습을 시작하세요.
        </p>
        <button className="start-button" onClick={handleStart}>
          시작하기
        </button>
      </div>
    </main>
  )
}

export default HomePage
