// REQ: REQ-F-A2-Signup-3, REQ-F-A2-Signup-4
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, test, expect, vi, beforeEach } from 'vitest'
import { BrowserRouter } from 'react-router-dom'
import SignupPage from '../SignupPage'
import * as transport from '../../lib/transport'

const mockNavigate = vi.fn()

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

// Mock transport
vi.mock('../../lib/transport', () => ({
  transport: {
    post: vi.fn(),
    get: vi.fn(),
  },
}))

// Mock auth utils
vi.mock('../../utils/auth', () => ({
  getToken: vi.fn(() => 'mock_token'),
}))

const renderWithRouter = (component: React.ReactElement) => {
  return render(<BrowserRouter>{component}</BrowserRouter>)
}

describe('SignupPage - REQ-F-A2-Signup-3 (Nickname Section)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockNavigate.mockReset()
  })

  // Test 1: Basic rendering
  test('renders nickname section with input field and check button', () => {
    // REQ: REQ-F-A2-Signup-3 - 닉네임 입력 필드 + "중복 확인" 버튼
    renderWithRouter(<SignupPage />)

    // Check page title
    expect(screen.getByRole('heading', { name: /회원가입/i })).toBeInTheDocument()

    // Check nickname section exists
    expect(screen.getByLabelText(/닉네임/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /중복 확인/i })).toBeInTheDocument()
    expect(
      screen.getByPlaceholderText(/영문자, 숫자, 언더스코어 \(3-30자\)/i)
    ).toBeInTheDocument()
  })

  // Test 2: Input validation - too short
  test('shows error message when nickname is less than 3 characters', async () => {
    // REQ: REQ-F-A2-Signup-3 - 실시간 유효성 검사
    const user = userEvent.setup()
    renderWithRouter(<SignupPage />)

    const input = screen.getByLabelText(/닉네임/i)
    const checkButton = screen.getByRole('button', { name: /중복 확인/i })

    await user.type(input, 'ab')
    await user.click(checkButton)

    await waitFor(() => {
      expect(screen.getByText(/닉네임은 3자 이상이어야 합니다/i)).toBeInTheDocument()
    })
  })

  // Test 3: Input field respects maxLength attribute
  test('input field prevents typing more than 30 characters', async () => {
    // REQ: REQ-F-A2-Signup-3 - 30자 제한 (HTML maxLength)
    const user = userEvent.setup()
    renderWithRouter(<SignupPage />)

    const input = screen.getByLabelText(/닉네임/i) as HTMLInputElement

    // Try to type 35 characters
    await user.type(input, 'a'.repeat(35))

    // Verify input value is capped at 30 characters
    expect(input.value).toHaveLength(30)
    expect(input.value).toBe('a'.repeat(30))
  })

  // Test 4: Input validation - invalid characters
  test('shows error message when nickname contains invalid characters', async () => {
    // REQ: REQ-F-A2-Signup-3 - 실시간 유효성 검사
    const user = userEvent.setup()
    renderWithRouter(<SignupPage />)

    const input = screen.getByLabelText(/닉네임/i)
    const checkButton = screen.getByRole('button', { name: /중복 확인/i })

    await user.type(input, 'john-doe!')
    await user.click(checkButton)

    await waitFor(() => {
      expect(
        screen.getByText(/영문자, 숫자, 언더스코어만 사용 가능합니다/i)
      ).toBeInTheDocument()
    })
  })

  // Test 5: Successful nickname check (available)
  test('shows success message when nickname is available', async () => {
    // REQ: REQ-F-A2-Signup-3 - 중복 확인 정상 작동
    const mockResponse = { available: true, suggestions: [] }
    vi.mocked(transport.transport.post).mockResolvedValueOnce(mockResponse)

    const user = userEvent.setup()
    renderWithRouter(<SignupPage />)

    const input = screen.getByLabelText(/닉네임/i)
    const checkButton = screen.getByRole('button', { name: /중복 확인/i })

    await user.type(input, 'john_doe')
    await user.click(checkButton)

    await waitFor(() => {
      expect(screen.getByText(/사용 가능한 닉네임입니다/i)).toBeInTheDocument()
    })

    // Verify API was called with correct data
    expect(transport.transport.post).toHaveBeenCalledWith(
      '/api/profile/nickname/check',
      { nickname: 'john_doe' }
    )
  })

  // Test 6: Nickname taken - shows suggestions
  test('shows error message and suggestions when nickname is taken', async () => {
    // REQ: REQ-F-A2-Signup-3 - 중복 시 대안 3개 제안
    const mockResponse = {
      available: false,
      suggestions: ['john_doe_1', 'john_doe_2', 'john_doe_3'],
    }
    vi.mocked(transport.transport.post).mockResolvedValueOnce(mockResponse)

    const user = userEvent.setup()
    renderWithRouter(<SignupPage />)

    const input = screen.getByLabelText(/닉네임/i)
    const checkButton = screen.getByRole('button', { name: /중복 확인/i })

    await user.type(input, 'john_doe')
    await user.click(checkButton)

    await waitFor(() => {
      expect(screen.getByText(/이미 사용 중인 닉네임입니다/i)).toBeInTheDocument()
    })

    // Check that all 3 suggestions are displayed
    expect(screen.getByText('john_doe_1')).toBeInTheDocument()
    expect(screen.getByText('john_doe_2')).toBeInTheDocument()
    expect(screen.getByText('john_doe_3')).toBeInTheDocument()
  })

  // Test 7: Clicking suggestion auto-fills input
  test('clicking a suggestion auto-fills the nickname input', async () => {
    // REQ: REQ-F-A2-Signup-3 - 대안 클릭 시 자동 입력
    const mockResponse = {
      available: false,
      suggestions: ['john_doe_1', 'john_doe_2', 'john_doe_3'],
    }
    vi.mocked(transport.transport.post).mockResolvedValueOnce(mockResponse)

    const user = userEvent.setup()
    renderWithRouter(<SignupPage />)

    const input = screen.getByLabelText(/닉네임/i) as HTMLInputElement
    const checkButton = screen.getByRole('button', { name: /중복 확인/i })

    await user.type(input, 'john_doe')
    await user.click(checkButton)

    await waitFor(() => {
      expect(screen.getByText('john_doe_1')).toBeInTheDocument()
    })

    // Click first suggestion
    const suggestionButton = screen.getByText('john_doe_1')
    await user.click(suggestionButton)

    // Verify input value changed
    expect(input.value).toBe('john_doe_1')

    // Verify suggestions and error message cleared
    expect(screen.queryByText(/이미 사용 중인 닉네임입니다/i)).not.toBeInTheDocument()
  })

  // Test 8: API error handling
  test('shows error message when nickname check API fails', async () => {
    // REQ: REQ-F-A2-Signup-3 - 에러 처리
    vi.mocked(transport.transport.post).mockRejectedValueOnce(
      new Error('Network error')
    )

    const user = userEvent.setup()
    renderWithRouter(<SignupPage />)

    const input = screen.getByLabelText(/닉네임/i)
    const checkButton = screen.getByRole('button', { name: /중복 확인/i })

    await user.type(input, 'john_doe')
    await user.click(checkButton)

    await waitFor(() => {
      expect(screen.getByText(/Network error/i)).toBeInTheDocument()
    })
  })

  // Test 9: Check button disabled when input is empty
  test('keeps check button disabled when input is empty', () => {
    // REQ: REQ-F-A2-Signup-3 - UX: 빈 입력 시 버튼 비활성화
    renderWithRouter(<SignupPage />)

    const checkButton = screen.getByRole('button', { name: /중복 확인/i })
    expect(checkButton).toBeDisabled()
  })

  // Test 10: Check button enabled when input has value
  test('enables check button when input has value', async () => {
    // REQ: REQ-F-A2-Signup-3 - UX: 입력 시 버튼 활성화
    const user = userEvent.setup()
    renderWithRouter(<SignupPage />)

    const input = screen.getByLabelText(/닉네임/i)
    const checkButton = screen.getByRole('button', { name: /중복 확인/i })

    expect(checkButton).toBeDisabled()

    await user.type(input, 'abc')

    expect(checkButton).not.toBeDisabled()
  })

  // Test 11: Shows "확인 중..." while checking
  test('shows loading state while checking nickname', async () => {
    // REQ: REQ-F-A2-Signup-3 - UX: 로딩 상태 표시
    const mockResponse = { available: true, suggestions: [] }
    vi.mocked(transport.transport.post).mockImplementation(
      () => new Promise((resolve) => setTimeout(() => resolve(mockResponse), 100))
    )

    const user = userEvent.setup()
    renderWithRouter(<SignupPage />)

    const input = screen.getByLabelText(/닉네임/i)
    const checkButton = screen.getByRole('button', { name: /중복 확인/i })

    await user.type(input, 'john_doe')
    await user.click(checkButton)

    // Should show loading state
    expect(screen.getByText(/확인 중/i)).toBeInTheDocument()

    // Wait for completion
    await waitFor(() => {
      expect(screen.queryByText(/확인 중/i)).not.toBeInTheDocument()
    })
  })
})

describe('SignupPage - REQ-F-A2-Signup-4 (Level Slider)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockNavigate.mockReset()
  })

  // Test 1: Render level slider
  test('renders profile section with level slider', () => {
    // REQ: REQ-F-A2-Signup-4 - 수준 (1~5 슬라이더)
    renderWithRouter(<SignupPage />)

    // Check profile section title
    expect(screen.getByRole('heading', { name: /자기평가 정보/i })).toBeInTheDocument()

    // Check level slider exists
    const slider = screen.getByLabelText(/수준/i) as HTMLInputElement
    expect(slider).toBeInTheDocument()
    expect(slider.type).toBe('range')
    expect(slider.min).toBe('1')
    expect(slider.max).toBe('5')
  })

  // Test 2: Initial state shows placeholder
  test('shows placeholder when no level is selected', () => {
    // REQ: REQ-F-A2-Signup-4 - 초기 상태
    renderWithRouter(<SignupPage />)

    // Should show placeholder text
    expect(screen.getByText(/슬라이더를 움직여 수준을 선택하세요/i)).toBeInTheDocument()
    
    // Level value display should be empty (level is null initially)
    const valueDisplay = document.querySelector('.level-value')
    expect(valueDisplay).toBeNull()
  })

  // Test 3: Level 2 description (testing from initial state)
  test('shows correct description for level 2 when changed from initial state', async () => {
    // REQ: REQ-F-A2-Signup-4 - 레벨 설명 표시
    renderWithRouter(<SignupPage />)

    const slider = screen.getByLabelText(/수준/i) as HTMLInputElement
    
    // Change slider to level 2 (triggers onChange from null state)
    fireEvent.change(slider, { target: { value: '2' } })

    await waitFor(() => {
      expect(screen.getByText(/2 - 초급: 기본 업무 수행 가능/i)).toBeInTheDocument()
    })
    
    // Level value should be displayed
    expect(screen.getByText('2')).toBeInTheDocument()
  })

  // Test 4: Level 3 description
  test('shows correct description for level 3', async () => {
    // REQ: REQ-F-A2-Signup-4 - 레벨 설명 표시
    renderWithRouter(<SignupPage />)

    const slider = screen.getByLabelText(/수준/i) as HTMLInputElement
    
    fireEvent.change(slider, { target: { value: '3' } })

    await waitFor(() => {
      expect(screen.getByText(/3 - 중급: 독립적으로 업무 수행/i)).toBeInTheDocument()
    })
  })

  // Test 5: Level 4 description
  test('shows correct description for level 4', async () => {
    // REQ: REQ-F-A2-Signup-4 - 레벨 설명 표시
    renderWithRouter(<SignupPage />)

    const slider = screen.getByLabelText(/수준/i) as HTMLInputElement
    
    fireEvent.change(slider, { target: { value: '4' } })

    await waitFor(() => {
      expect(screen.getByText(/4 - 고급: 복잡한 문제 해결 가능/i)).toBeInTheDocument()
    })
  })

  // Test 6: Level 5 description
  test('shows correct description for level 5', async () => {
    // REQ: REQ-F-A2-Signup-4 - 레벨 설명 표시
    renderWithRouter(<SignupPage />)

    const slider = screen.getByLabelText(/수준/i) as HTMLInputElement
    
    fireEvent.change(slider, { target: { value: '5' } })

    await waitFor(() => {
      expect(screen.getByText(/5 - 전문가: 다른 사람을 지도 가능/i)).toBeInTheDocument()
    })
  })

  // Test 7: Level value updates on slider change
  test('updates level value when slider changes', async () => {
    // REQ: REQ-F-A2-Signup-4 - 슬라이더 상태 관리
    renderWithRouter(<SignupPage />)

    const slider = screen.getByLabelText(/수준/i) as HTMLInputElement
    
    // Initial value
    expect(slider.value).toBe('1')

    // Change to level 3
    fireEvent.change(slider, { target: { value: '3' } })
    
    await waitFor(() => {
      expect(slider.value).toBe('3')
    })
  })
})
