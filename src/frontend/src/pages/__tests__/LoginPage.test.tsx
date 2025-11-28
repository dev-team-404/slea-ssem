// REQ: REQ-F-A1-1, REQ-F-A1-2
import { render, screen, waitFor } from '@testing-library/react'
import { BrowserRouter, useNavigate } from 'react-router-dom'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import LoginPage from '../LoginPage'
import * as authUtils from '../../utils/auth'

// Mock the auth module
vi.mock('../../utils/auth')
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: vi.fn(),
  }
})

describe('LoginPage - Auto-redirect (REQ-F-A1-1, REQ-F-A1-2)', () => {
  let originalLocation: Location
  let mockNavigate: ReturnType<typeof vi.fn>

  beforeEach(() => {
    // Mock window.location
    originalLocation = window.location
    // @ts-ignore
    delete window.location
    window.location = { href: '', origin: 'http://localhost:3000' } as Location

    // Mock navigate
    mockNavigate = vi.fn()
    vi.mocked(useNavigate).mockReturnValue(mockNavigate)

    // Mock environment variables
    vi.stubEnv('VITE_IDP_BASE_URL', 'https://idp.test.com')
    vi.stubEnv('VITE_IDP_CLIENT_ID', 'test-client-id')
    vi.stubEnv('VITE_API_BASE_URL', 'http://localhost:8000')
  })

  afterEach(() => {
    window.location = originalLocation
    vi.clearAllMocks()
    vi.unstubAllEnvs()
  })

  // Test 1: REQ-F-A1-2 - Already authenticated → redirect to /home
  it('should redirect to /home if already authenticated (REQ-F-A1-2)', async () => {
    // Mock: User is already authenticated
    vi.mocked(authUtils.isAuthenticated).mockResolvedValue(true)

    render(
      <BrowserRouter>
        <LoginPage />
      </BrowserRouter>
    )

    // Should show loading state first
    expect(screen.getByText('인증 중...')).toBeInTheDocument()

    // Should redirect to /home
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/home', { replace: true })
    })
  })

  // Test 2: REQ-F-A1-1 - Not authenticated → Redirect to IDP
  it('should redirect to IDP when not authenticated (REQ-F-A1-1)', async () => {
    // Mock: User is NOT authenticated
    vi.mocked(authUtils.isAuthenticated).mockResolvedValue(false)

    render(
      <BrowserRouter>
        <LoginPage />
      </BrowserRouter>
    )

    // Should redirect to IDP
    await waitFor(() => {
      expect(window.location.href).toContain('https://idp.test.com')
    })

    // Verify URL contains required params
    const redirectUrl = new URL(window.location.href)
    expect(redirectUrl.searchParams.get('client_id')).toBe('test-client-id')
    expect(redirectUrl.searchParams.get('response_type')).toBe('code')
    expect(redirectUrl.searchParams.get('response_mode')).toBe('form_post')
    expect(redirectUrl.searchParams.get('scope')).toBe('openid profile email')
  })

  // Test 3: Verify redirect_uri points to backend /auth/oidc/callback
  it('should include correct redirect_uri pointing to backend', async () => {
    // Mock: User is NOT authenticated
    vi.mocked(authUtils.isAuthenticated).mockResolvedValue(false)

    render(
      <BrowserRouter>
        <LoginPage />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(window.location.href).toContain('redirect_uri')
    })

    const redirectUrl = new URL(window.location.href)
    const redirectUri = redirectUrl.searchParams.get('redirect_uri')
    expect(redirectUri).toBe('http://localhost:8000/auth/oidc/callback')
  })

  // Test 4: Error handling - Show error message
  it('should show error message when auto-redirect fails', async () => {
    // Mock: isAuthenticated throws error
    vi.mocked(authUtils.isAuthenticated).mockRejectedValue(new Error('Network error'))

    render(
      <BrowserRouter>
        <LoginPage />
      </BrowserRouter>
    )

    // Should show error message
    await waitFor(() => {
      expect(screen.getByText('로그인 처리 중 오류가 발생했습니다.')).toBeInTheDocument()
    })

    // Should NOT redirect
    expect(mockNavigate).not.toHaveBeenCalled()
    expect(window.location.href).toBe('')
  })

  // Test 5: Render loading state initially
  it('should render loading state initially', () => {
    vi.mocked(authUtils.isAuthenticated).mockResolvedValue(false)

    render(
      <BrowserRouter>
        <LoginPage />
      </BrowserRouter>
    )

    // Should show loading state
    expect(screen.getByText('인증 중...')).toBeInTheDocument()
    expect(screen.getByText('SLEA-SSEM')).toBeInTheDocument()
  })
})
