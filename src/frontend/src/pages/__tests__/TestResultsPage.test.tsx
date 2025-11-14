// REQ: REQ-F-B4-1, REQ-F-B5-1, REQ-F-B5-3
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, test, expect, vi, beforeEach, afterEach } from 'vitest'
import { BrowserRouter } from 'react-router-dom'
import TestResultsPage from '../TestResultsPage'
import * as transport from '../../lib/transport'

const mockNavigate = vi.fn()
let mockLocationState: any = { sessionId: 'session_123' }

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>(
    'react-router-dom'
  )
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useLocation: () => ({
      state: mockLocationState,
    }),
  }
})

// Mock transport
vi.mock('../../lib/transport', () => ({
  transport: {
    get: vi.fn(),
  },
}))

const mockResultData = {
  user_id: 1,
  grade: 3,
  score: 75,
  rank: 150,
  total_cohort_size: 500,
  percentile: 70,
  percentile_confidence: 'high' as const,
  percentile_description: '상위 30%',
  grade_distribution: [
    { grade: 1, count: 50 },
    { grade: 2, count: 100 },
    { grade: 3, count: 150 },
    { grade: 4, count: 120 },
    { grade: 5, count: 80 },
  ],
}

const renderWithRouter = (component: React.ReactElement) => {
  return render(<BrowserRouter>{component}</BrowserRouter>)
}

describe('TestResultsPage - REQ-F-B5-3 (Retake)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockNavigate.mockReset()
    localStorage.clear()
    mockLocationState = { sessionId: 'session_123' }
  })

  afterEach(() => {
    localStorage.clear()
  })

  test('navigates to /profile-review when "재응시하기" button clicked', async () => {
    // REQ: REQ-F-B5-3
    mockLocationState = { sessionId: 'session_123', surveyId: 'survey_abc' }

    vi.mocked(transport.transport.get).mockResolvedValueOnce(mockResultData)

    const user = userEvent.setup()
    renderWithRouter(<TestResultsPage />)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /재응시하기/i })).toBeInTheDocument()
    })

    const retakeButton = screen.getByRole('button', { name: /재응시하기/i })
    await user.click(retakeButton)

    // Should save surveyId to localStorage
    expect(localStorage.getItem('lastSurveyId')).toBe('survey_abc')

    // Should navigate to profile-review
    expect(mockNavigate).toHaveBeenCalledWith('/profile-review')
  })

  test('saves surveyId from state to localStorage on retake', async () => {
    // REQ: REQ-F-B5-3
    mockLocationState = { sessionId: 'session_123', surveyId: 'survey_xyz' }

    vi.mocked(transport.transport.get).mockResolvedValueOnce(mockResultData)

    const user = userEvent.setup()
    renderWithRouter(<TestResultsPage />)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /재응시하기/i })).toBeInTheDocument()
    })

    const retakeButton = screen.getByRole('button', { name: /재응시하기/i })
    await user.click(retakeButton)

    // surveyId should be saved to localStorage
    expect(localStorage.getItem('lastSurveyId')).toBe('survey_xyz')
  })

  test('uses surveyId from localStorage when state has no surveyId', async () => {
    // REQ: REQ-F-B5-3 - Fallback to localStorage
    mockLocationState = { sessionId: 'session_123' } // No surveyId
    localStorage.setItem('lastSurveyId', 'saved_survey_123')

    vi.mocked(transport.transport.get).mockResolvedValueOnce(mockResultData)

    const user = userEvent.setup()
    renderWithRouter(<TestResultsPage />)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /재응시하기/i })).toBeInTheDocument()
    })

    const retakeButton = screen.getByRole('button', { name: /재응시하기/i })
    await user.click(retakeButton)

    // Should still navigate to profile-review (localStorage surveyId exists)
    expect(mockNavigate).toHaveBeenCalledWith('/profile-review')

    // localStorage should still have the surveyId
    expect(localStorage.getItem('lastSurveyId')).toBe('saved_survey_123')
  })

  test('navigates to profile-review even when no surveyId available', async () => {
    // REQ: REQ-F-B5-3 - Fallback case
    mockLocationState = { sessionId: 'session_123' } // No surveyId
    // localStorage is empty (cleared in beforeEach)

    vi.mocked(transport.transport.get).mockResolvedValueOnce(mockResultData)

    const user = userEvent.setup()
    renderWithRouter(<TestResultsPage />)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /재응시하기/i })).toBeInTheDocument()
    })

    const retakeButton = screen.getByRole('button', { name: /재응시하기/i })
    await user.click(retakeButton)

    // Should navigate to profile-review (fallback behavior)
    expect(mockNavigate).toHaveBeenCalledWith('/profile-review')
  })

  test('navigates to /home when "홈화면으로 이동" button clicked', async () => {
    // REQ: REQ-F-B4-1
    vi.mocked(transport.transport.get).mockResolvedValueOnce(mockResultData)
    vi.mocked(transport.transport.get).mockResolvedValueOnce(null) // previous result

    const user = userEvent.setup()
    renderWithRouter(<TestResultsPage />)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /홈화면으로 이동/i })).toBeInTheDocument()
    })

    const homeButton = screen.getByRole('button', { name: /홈화면으로 이동/i })
    await user.click(homeButton)

    expect(mockNavigate).toHaveBeenCalledWith('/home')
  })
})

describe('TestResultsPage - REQ-F-B5-1 (Comparison)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockNavigate.mockReset()
    localStorage.clear()
    mockLocationState = { sessionId: 'session_123' }
  })

  afterEach(() => {
    localStorage.clear()
  })

  test('이전 결과 로드 성공 및 ComparisonSection 렌더링', async () => {
    // REQ: REQ-F-B5-1
    const mockPreviousResult = {
      grade: 'Beginner',
      score: 65,
      test_date: '2025-01-10T10:00:00Z',
    }

    vi.mocked(transport.transport.get)
      .mockResolvedValueOnce(mockResultData) // current results
      .mockResolvedValueOnce(mockPreviousResult) // previous result

    renderWithRouter(<TestResultsPage />)

    await waitFor(() => {
      // ComparisonSection 렌더링 확인
      expect(screen.getByText(/성적 비교/i)).toBeInTheDocument()
    })

    // 이전 결과 데이터 표시 확인
    await waitFor(() => {
      expect(screen.getByText(/이전 테스트:/i)).toBeInTheDocument()
      expect(screen.getByText('Beginner')).toBeInTheDocument()
      expect(screen.getByText('65점')).toBeInTheDocument()
    })
  })

  test('이전 결과 없을 때 (첫 응시)', async () => {
    // REQ: REQ-F-B5-1
    vi.mocked(transport.transport.get)
      .mockResolvedValueOnce(mockResultData) // current results
      .mockResolvedValueOnce(null) // no previous result

    renderWithRouter(<TestResultsPage />)

    await waitFor(() => {
      // "첫 응시입니다" 메시지 확인
      expect(screen.getByText(/첫 응시입니다/i)).toBeInTheDocument()
    })

    // 현재 결과만 표시
    expect(screen.getByText(/현재 등급:/i)).toBeInTheDocument()
    expect(screen.getByText(/현재 점수:/i)).toBeInTheDocument()
  })

  test('이전 결과 API 에러 시 ComparisonSection 숨김', async () => {
    // REQ: REQ-F-B5-1 - Error handling
    vi.mocked(transport.transport.get)
      .mockResolvedValueOnce(mockResultData) // current results
      .mockRejectedValueOnce(new Error('API Error')) // previous result fails

    renderWithRouter(<TestResultsPage />)

    await waitFor(() => {
      // Main results are still displayed
      expect(screen.getByText(/테스트 결과/i)).toBeInTheDocument()
    })

    // ComparisonSection 렌더링됨 (null previousResult로)
    await waitFor(() => {
      expect(screen.getByText(/첫 응시입니다/i)).toBeInTheDocument()
    })
  })
})
