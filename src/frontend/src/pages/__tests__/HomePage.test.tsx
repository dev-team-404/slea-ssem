// REQ: REQ-F-A2-1, REQ-F-A2-Signup-1
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import HomePage from '../HomePage'
import * as authUtils from '../../utils/auth'
import { profileService } from '../../services'

// Mock useNavigate
const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

// Mock auth utils
vi.mock('../../utils/auth', () => ({
  getToken: vi.fn(() => 'mock_jwt_token'),
}))

// Mock profileService
vi.mock('../../services', () => ({
  profileService: {
    getNickname: vi.fn(),
  },
}))

describe('HomePage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.spyOn(authUtils, 'getToken').mockReturnValue('mock_jwt_token')
  })

  it('should redirect to login if no token is present', () => {
    vi.spyOn(authUtils, 'getToken').mockReturnValue(null)

    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>
    )

    expect(mockNavigate).toHaveBeenCalledWith('/')
  })

  it('should display welcome message when authenticated', async () => {
    vi.mocked(profileService.getNickname).mockResolvedValue({
      user_id: 'test@samsung.com',
      nickname: null,
      registered_at: null,
      updated_at: null,
    })

    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>
    )

    // Wait for component to mount
    await waitFor(() => {
      // Header와 본문 둘 다 플랫폼 이름이 있으므로 getAllByText 사용
      const platformTitles = screen.getAllByText('S.LSI Learning Platform')
      expect(platformTitles.length).toBeGreaterThanOrEqual(1)
    })

    expect(screen.getByText(/AI 기반 학습 플랫폼/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /시작하기/i})).toBeInTheDocument()
  })

  it('should call API to check nickname when "시작하기" is clicked', async () => {
    // Mock profileService to return testuser
    vi.mocked(profileService.getNickname).mockResolvedValue({
      user_id: 'test@samsung.com',
      nickname: 'testuser',
      registered_at: '2025-11-10T12:00:00Z',
      updated_at: '2025-11-10T12:00:00Z',
    })

    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>
    )

    const startButton = screen.getByRole('button', { name: /시작하기/i })
    fireEvent.click(startButton)

    await waitFor(() => {
      // getNickname이 2번 호출되어야 함 (mount + 버튼 클릭)
      expect(profileService.getNickname).toHaveBeenCalledTimes(2)
    })
  })

  it('should redirect to /nickname-setup when nickname is null', async () => {
    // REQ: REQ-F-A2-1
    vi.mocked(profileService.getNickname).mockResolvedValue({
      user_id: 'test@samsung.com',
      nickname: null,  // ✅ REQ-F-A2-1: nickname is NULL
      registered_at: null,
      updated_at: null,
    })

    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>
    )

    const startButton = screen.getByRole('button', { name: /시작하기/i })
    fireEvent.click(startButton)

    await waitFor(() => {
      // REQ-F-A2-1: Navigate to nickname-setup when nickname is null
      expect(mockNavigate).toHaveBeenCalledWith('/nickname-setup')
    })
  })

  it('should navigate to self-assessment when nickname exists', async () => {
    // REQ: REQ-F-A2-2-1
    vi.mocked(profileService.getNickname).mockResolvedValue({
      user_id: 'test@samsung.com',
      nickname: 'testuser',  // ✅ nickname is set
      registered_at: '2025-11-10T12:00:00Z',
      updated_at: '2025-11-10T12:00:00Z',
    })

    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>
    )

    const startButton = screen.getByRole('button', { name: /시작하기/i })
    fireEvent.click(startButton)

    await waitFor(() => {
      // REQ-F-A2-2-1: Navigate to self-assessment when nickname exists
      expect(mockNavigate).toHaveBeenCalledWith('/self-assessment')
    })
  })

  it('should display error message when API call fails', async () => {
    // Mount 시 성공, 버튼 클릭 시 실패
    vi.mocked(profileService.getNickname)
      .mockResolvedValueOnce({
        user_id: 'test@samsung.com',
        nickname: null,
        registered_at: null,
        updated_at: null,
      })
      .mockRejectedValueOnce(new Error('Unauthorized'))

    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>
    )

    const startButton = screen.getByRole('button', { name: /시작하기/i })
    fireEvent.click(startButton)

    await waitFor(() => {
      // Error handling - show error message to user
      const errorElement = screen.queryByText(/프로필 정보를 불러오는데 실패했습니다/i)
      expect(errorElement).toBeInTheDocument()
    })
  })

  it('should handle network errors gracefully', async () => {
    // Mount 시 성공, 버튼 클릭 시 네트워크 에러
    vi.mocked(profileService.getNickname)
      .mockResolvedValueOnce({
        user_id: 'test@samsung.com',
        nickname: null,
        registered_at: null,
        updated_at: null,
      })
      .mockRejectedValueOnce(new Error('Network error'))

    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>
    )

    const startButton = screen.getByRole('button', { name: /시작하기/i })
    fireEvent.click(startButton)

    await waitFor(() => {
      // Should show error message or handle gracefully
      const errorElement = screen.queryByText(/프로필 정보를 불러오는데 실패했습니다/i)
      expect(errorElement).toBeInTheDocument()
    })
  })
})

describe('HomePage - REQ-F-A2-Signup-1 (Header Integration)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.spyOn(authUtils, 'getToken').mockReturnValue('mock_jwt_token')
  })

  it('nickname이 null일 때 헤더에 "회원가입" 버튼 표시', async () => {
    // REQ: REQ-F-A2-Signup-1
    // Given: User has no nickname (initial load returns null)
    vi.mocked(profileService.getNickname).mockResolvedValue({
      user_id: 'test@samsung.com',
      nickname: null,
      registered_at: null,
      updated_at: null,
    })

    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>
    )

    // Then: "회원가입" button should appear in header after nickname is loaded
    await waitFor(() => {
      const signupButton = screen.getByRole('button', { name: /회원가입/i })
      expect(signupButton).toBeInTheDocument()
    })
  })

  it('nickname이 존재할 때 헤더에 "회원가입" 버튼 숨김', async () => {
    // REQ: REQ-F-A2-Signup-1
    // Given: User already has nickname
    vi.mocked(profileService.getNickname).mockResolvedValue({
      user_id: 'test@samsung.com',
      nickname: 'existing_user',
      registered_at: '2025-11-10T12:00:00Z',
      updated_at: '2025-11-10T12:00:00Z',
    })

    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>
    )

    // Wait for nickname to load
    await waitFor(() => {
      expect(profileService.getNickname).toHaveBeenCalled()
    })

    // Then: "회원가입" button should NOT be visible
    const signupButton = screen.queryByRole('button', { name: /회원가입/i })
    expect(signupButton).not.toBeInTheDocument()
  })

  it('헤더에 플랫폼 이름이 표시됨', async () => {
    // REQ: General header functionality
    vi.mocked(profileService.getNickname).mockResolvedValue({
      user_id: 'test@samsung.com',
      nickname: null,
      registered_at: null,
      updated_at: null,
    })

    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>
    )

    // Wait for mount
    await waitFor(() => {
      // Then: Platform name should appear twice (header + main content)
      const platformNames = screen.getAllByText(/S\.LSI Learning Platform/i)
      expect(platformNames.length).toBeGreaterThanOrEqual(1)
    })
  })
})
