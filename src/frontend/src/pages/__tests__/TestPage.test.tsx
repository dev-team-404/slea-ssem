// REQ: REQ-F-B2-1
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, test, expect, vi, beforeEach } from 'vitest'
import { BrowserRouter, MemoryRouter } from 'react-router-dom'
import TestPage from '../TestPage'
import * as transport from '../../lib/transport'

const mockNavigate = vi.fn()

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>(
    'react-router-dom'
  )
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useLocation: () => ({
      state: {
        surveyId: 'test-survey-123',
        round: 1,
      },
    }),
  }
})

// Mock transport
vi.mock('../../lib/transport', () => ({
  transport: {
    post: vi.fn(),
  },
}))

const renderWithRouter = (component: React.ReactElement) => {
  return render(<BrowserRouter>{component}</BrowserRouter>)
}

const mockQuestions = [
  {
    id: 'q1',
    item_type: 'multiple_choice',
    stem: 'What is AI?',
    choices: ['Option A', 'Option B', 'Option C'],
    difficulty: 5,
    category: 'AI Basics',
  },
  {
    id: 'q2',
    item_type: 'true_false',
    stem: 'Machine learning is a subset of AI',
    choices: null,
    difficulty: 3,
    category: 'AI Basics',
  },
  {
    id: 'q3',
    item_type: 'short_answer',
    stem: 'Explain neural networks',
    choices: null,
    difficulty: 7,
    category: 'Deep Learning',
  },
]

const mockGenerateResponse = {
  session_id: 'session-456',
  questions: mockQuestions,
}

describe('TestPage - REQ-F-B2-1', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockNavigate.mockReset()
  })

  test('AC1: 문항이 1개씩 순차적으로 표시된다', async () => {
    // REQ: REQ-F-B2-1 - Acceptance Criteria 1
    const mockPost = vi.mocked(transport.transport.post)
    mockPost.mockResolvedValueOnce(mockGenerateResponse)

    renderWithRouter(<TestPage />)

    await waitFor(() => {
      expect(screen.getByText('What is AI?')).toBeInTheDocument()
    })

    // First question displayed
    expect(screen.getByText('문제 1')).toBeInTheDocument()
    expect(screen.queryByText('Machine learning is a subset of AI')).not.toBeInTheDocument()
  })

  test('AC2: 진행률이 실시간으로 업데이트된다', async () => {
    // REQ: REQ-F-B2-1 - Acceptance Criteria 2
    const mockPost = vi.mocked(transport.transport.post)
    mockPost.mockResolvedValueOnce(mockGenerateResponse)
    mockPost.mockResolvedValueOnce({ saved: true, session_id: 'session-456', question_id: 'q1', saved_at: '2025-11-12T00:00:00Z' })

    const user = userEvent.setup()
    renderWithRouter(<TestPage />)

    await waitFor(() => {
      expect(screen.getByText(/진행률: 1\/3/i)).toBeInTheDocument()
    })

    // Select answer and click next
    const optionA = screen.getByLabelText('Option A')
    await user.click(optionA)

    const nextButton = screen.getByRole('button', { name: /다음 문제/i })
    await user.click(nextButton)

    await waitFor(() => {
      expect(screen.getByText(/진행률: 2\/3/i)).toBeInTheDocument()
    })
  })

  test('Happy Path: multiple choice 답변 제출 성공', async () => {
    // REQ: REQ-F-B2-1 - Submit multiple choice answer
    const mockPost = vi.mocked(transport.transport.post)
    mockPost.mockResolvedValueOnce(mockGenerateResponse)
    mockPost.mockResolvedValueOnce({
      saved: true,
      session_id: 'session-456',
      question_id: 'q1',
      saved_at: '2025-11-12T00:00:00Z',
    })

    const user = userEvent.setup()
    renderWithRouter(<TestPage />)

    await waitFor(() => {
      expect(screen.getByText('What is AI?')).toBeInTheDocument()
    })

    // Select option B
    const optionB = screen.getByLabelText('Option B')
    await user.click(optionB)

    const nextButton = screen.getByRole('button', { name: /다음 문제/i })
    await user.click(nextButton)

    await waitFor(() => {
      expect(mockPost).toHaveBeenCalledWith('/questions/autosave', expect.objectContaining({
        session_id: 'session-456',
        question_id: 'q1',
        user_answer: { selected: 'Option B' },
        response_time_ms: expect.any(Number),
      }))
    })
  })

  test('Happy Path: short answer 답변 제출 성공', async () => {
    // REQ: REQ-F-B2-1 - Submit short answer
    const mockPost = vi.mocked(transport.transport.post)
    mockPost.mockResolvedValueOnce(mockGenerateResponse)
    // Skip to question 3 by mocking 2 autosaves
    mockPost.mockResolvedValueOnce({ saved: true, session_id: 'session-456', question_id: 'q1', saved_at: '2025-11-12T00:00:00Z' })
    mockPost.mockResolvedValueOnce({ saved: true, session_id: 'session-456', question_id: 'q2', saved_at: '2025-11-12T00:00:00Z' })
    mockPost.mockResolvedValueOnce({ saved: true, session_id: 'session-456', question_id: 'q3', saved_at: '2025-11-12T00:00:00Z' })

    const user = userEvent.setup()
    renderWithRouter(<TestPage />)

    await waitFor(() => {
      expect(screen.getByText('What is AI?')).toBeInTheDocument()
    })

    // Navigate to question 3 (short answer)
    await user.click(screen.getByLabelText('Option A'))
    await user.click(screen.getByRole('button', { name: /다음 문제/i }))

    await waitFor(() => {
      expect(screen.getByText('Machine learning is a subset of AI')).toBeInTheDocument()
    })

    await user.click(screen.getByLabelText(/참 \(True\)/i))
    await user.click(screen.getByRole('button', { name: /다음 문제/i }))

    await waitFor(() => {
      expect(screen.getByText('Explain neural networks')).toBeInTheDocument()
    })

    // Type short answer
    const textarea = screen.getByPlaceholderText(/답변을 입력하세요/i)
    await user.type(textarea, 'Neural networks are computing systems inspired by biological neural networks.')

    const completeButton = screen.getByRole('button', { name: /테스트 완료/i })
    await user.click(completeButton)

    await waitFor(() => {
      expect(mockPost).toHaveBeenCalledWith('/questions/autosave', expect.objectContaining({
        session_id: 'session-456',
        question_id: 'q3',
        user_answer: { text: 'Neural networks are computing systems inspired by biological neural networks.' },
        response_time_ms: expect.any(Number),
      }))
    })
  })

  test('Input Validation: 빈 답변 제출 방지', async () => {
    // REQ: REQ-F-B2-1 - Prevent empty answer submission
    const mockPost = vi.mocked(transport.transport.post)
    mockPost.mockResolvedValueOnce(mockGenerateResponse)

    renderWithRouter(<TestPage />)

    await waitFor(() => {
      expect(screen.getByText('What is AI?')).toBeInTheDocument()
    })

    const nextButton = screen.getByRole('button', { name: /다음 문제/i })
    expect(nextButton).toBeDisabled()

    // Verify autosave was NOT called
    expect(mockPost).toHaveBeenCalledTimes(1) // Only generate call
  })

  test('Edge Case: 마지막 문항 완료 시 results 페이지 이동', async () => {
    // REQ: REQ-F-B2-1 - Navigate to results after last question
    const mockPost = vi.mocked(transport.transport.post)
    const singleQuestion = {
      session_id: 'session-789',
      questions: [mockQuestions[0]],
    }
    mockPost.mockResolvedValueOnce(singleQuestion)
    mockPost.mockResolvedValueOnce({ saved: true, session_id: 'session-789', question_id: 'q1', saved_at: '2025-11-12T00:00:00Z' })

    const user = userEvent.setup()
    renderWithRouter(<TestPage />)

    await waitFor(() => {
      expect(screen.getByText('What is AI?')).toBeInTheDocument()
    })

    const optionA = screen.getByLabelText('Option A')
    await user.click(optionA)

    const completeButton = screen.getByRole('button', { name: /테스트 완료/i })
    await user.click(completeButton)

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/test-results', {
        state: { sessionId: 'session-789' },
      })
    })
  })

  test('Error Handling: API 실패 시 에러 메시지 표시', async () => {
    // REQ: REQ-F-B2-1 - Show error on API failure
    const mockPost = vi.mocked(transport.transport.post)
    mockPost.mockResolvedValueOnce(mockGenerateResponse)
    mockPost.mockRejectedValueOnce(new Error('Network error'))

    const user = userEvent.setup()
    renderWithRouter(<TestPage />)

    await waitFor(() => {
      expect(screen.getByText('What is AI?')).toBeInTheDocument()
    })

    const optionC = screen.getByLabelText('Option C')
    await user.click(optionC)

    const nextButton = screen.getByRole('button', { name: /다음 문제/i })
    await user.click(nextButton)

    await waitFor(() => {
      expect(screen.getByText(/Network error/i)).toBeInTheDocument()
    })

    // Should stay on current question
    expect(screen.getByText('What is AI?')).toBeInTheDocument()
  })

  test('Response Time Tracking: response_time_ms 정확히 측정', async () => {
    // REQ: REQ-F-B2-1 - Track response time accurately
    const mockPost = vi.mocked(transport.transport.post)
    mockPost.mockResolvedValueOnce(mockGenerateResponse)
    mockPost.mockResolvedValueOnce({ saved: true, session_id: 'session-456', question_id: 'q1', saved_at: '2025-11-12T00:00:00Z' })

    const user = userEvent.setup()
    renderWithRouter(<TestPage />)

    await waitFor(() => {
      expect(screen.getByText('What is AI?')).toBeInTheDocument()
    })

    // Wait at least 100ms before answering
    await new Promise(resolve => setTimeout(resolve, 100))

    const optionA = screen.getByLabelText('Option A')
    await user.click(optionA)

    const nextButton = screen.getByRole('button', { name: /다음 문제/i })
    await user.click(nextButton)

    await waitFor(() => {
      const autosaveCall = mockPost.mock.calls.find(call => call[0] === '/questions/autosave')
      expect(autosaveCall).toBeDefined()
      const payload = autosaveCall![1] as any
      expect(payload.response_time_ms).toBeGreaterThanOrEqual(100)
    })
  })

  test('Button State: 제출 중 버튼 비활성화', async () => {
    // REQ: REQ-F-B2-1 - Disable button during submission
    const mockPost = vi.mocked(transport.transport.post)
    mockPost.mockResolvedValueOnce(mockGenerateResponse)

    // Delay autosave response
    mockPost.mockImplementationOnce(() =>
      new Promise(resolve =>
        setTimeout(() => resolve({
          saved: true,
          session_id: 'session-456',
          question_id: 'q1',
          saved_at: '2025-11-12T00:00:00Z'
        }), 500)
      )
    )

    const user = userEvent.setup()
    renderWithRouter(<TestPage />)

    await waitFor(() => {
      expect(screen.getByText('What is AI?')).toBeInTheDocument()
    })

    const optionA = screen.getByLabelText('Option A')
    await user.click(optionA)

    const nextButton = screen.getByRole('button', { name: /다음 문제/i })
    await user.click(nextButton)

    // Button should be disabled during submission
    expect(nextButton).toBeDisabled()

    await waitFor(() => {
      expect(screen.getByText('Machine learning is a subset of AI')).toBeInTheDocument()
    }, { timeout: 1000 })
  })
})
