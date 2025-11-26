// REQ: REQ-F-A1-4, REQ-F-A1-5
import { render, screen, waitFor } from '@testing-library/react'
import { BrowserRouter, useNavigate, useSearchParams } from 'react-router-dom'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import CallbackPage from '../CallbackPage'
import * as pkceUtils from '../../utils/pkce'

// Mock modules
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: vi.fn(),
    useSearchParams: vi.fn(),
  }
})
vi.mock('../../utils/pkce')

// Mock fetch globally
global.fetch = vi.fn()

describe('CallbackPage - OIDC Callback (REQ-F-A1-4, REQ-F-A1-5)', () => {
  let mockNavigate: ReturnType<typeof vi.fn>
  let mockSearchParams: URLSearchParams

  beforeEach(() => {
    // Mock navigate
    mockNavigate = vi.fn()
    vi.mocked(useNavigate).mockReturnValue(mockNavigate)

    // Mock sessionStorage
    vi.spyOn(Storage.prototype, 'getItem')
    vi.spyOn(Storage.prototype, 'setItem')
    vi.spyOn(Storage.prototype, 'removeItem')

    // Reset mocks
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  // Test 1: Happy Path - Successful OIDC callback (REQ-F-A1-4, REQ-F-A1-5)
  it('should handle successful OIDC callback and redirect to /home (REQ-F-A1-4, REQ-F-A1-5)', async () => {
    // Mock URL search params
    mockSearchParams = new URLSearchParams({
      code: 'mock-auth-code-12345',
      state: 'mock-state-abc',
    })
    vi.mocked(useSearchParams).mockReturnValue([mockSearchParams, vi.fn()])

    // Mock PKCE params from sessionStorage
    const mockPkceParams = {
      codeVerifier: 'mock-code-verifier',
      state: 'mock-state-abc',
      nonce: 'mock-nonce',
    }
    vi.mocked(pkceUtils.retrievePKCEParams).mockReturnValue(mockPkceParams)
    vi.mocked(pkceUtils.clearPKCEParams).mockImplementation(() => {})

    // Mock successful backend response
    vi.mocked(global.fetch).mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        user_id: 'test-user-123',
        is_new_user: false,
      }),
      headers: new Headers({
        'Set-Cookie': '__Host-session=jwt_token_here; HttpOnly; Secure',
      }),
    } as Response)

    render(
      <BrowserRouter>
        <CallbackPage />
      </BrowserRouter>
    )

    // Should show loading state
    expect(screen.getByText('로그인 처리 중입니다...')).toBeInTheDocument()

    // Wait for API call
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/auth/oidc/callback',
        expect.objectContaining({
          method: 'POST',
          credentials: 'include',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            code: 'mock-auth-code-12345',
            code_verifier: 'mock-code-verifier',
            nonce: 'mock-nonce',
          }),
        })
      )
    })

    // Should clear PKCE params from sessionStorage
    await waitFor(() => {
      expect(pkceUtils.clearPKCEParams).toHaveBeenCalled()
    })

    // Should redirect to /home
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/home', { replace: true })
    })
  })

  // Test 2: Input Validation - Missing authorization code
  it('should show error when authorization code is missing', async () => {
    // Mock URL without code
    mockSearchParams = new URLSearchParams({
      state: 'mock-state-abc',
    })
    vi.mocked(useSearchParams).mockReturnValue([mockSearchParams, vi.fn()])

    render(
      <BrowserRouter>
        <CallbackPage />
      </BrowserRouter>
    )

    // Should show error message
    await waitFor(() => {
      expect(screen.getByText('로그인 실패')).toBeInTheDocument()
      expect(screen.getByText(/인증 코드가 누락되었습니다/)).toBeInTheDocument()
    })

    // Should NOT call backend API
    expect(global.fetch).not.toHaveBeenCalled()

    // Should NOT redirect
    expect(mockNavigate).not.toHaveBeenCalled()
  })

  // Test 3: Security - State mismatch (CSRF protection)
  it('should show error when state does not match (CSRF protection)', async () => {
    // Mock URL with different state
    mockSearchParams = new URLSearchParams({
      code: 'mock-auth-code',
      state: 'different-state',
    })
    vi.mocked(useSearchParams).mockReturnValue([mockSearchParams, vi.fn()])

    // Mock PKCE params with different state
    vi.mocked(pkceUtils.retrievePKCEParams).mockReturnValue({
      codeVerifier: 'mock-verifier',
      state: 'original-state',
      nonce: 'mock-nonce',
    })

    render(
      <BrowserRouter>
        <CallbackPage />
      </BrowserRouter>
    )

    // Should show error message
    await waitFor(() => {
      expect(screen.getByText('로그인 실패')).toBeInTheDocument()
      expect(screen.getByText(/잘못된 요청입니다/)).toBeInTheDocument()
    })

    // Should NOT call backend API
    expect(global.fetch).not.toHaveBeenCalled()
  })

  // Test 4: Edge Case - Missing PKCE params in sessionStorage
  it('should show error when PKCE params are missing from sessionStorage', async () => {
    // Mock URL params
    mockSearchParams = new URLSearchParams({
      code: 'mock-auth-code',
      state: 'mock-state',
    })
    vi.mocked(useSearchParams).mockReturnValue([mockSearchParams, vi.fn()])

    // Mock missing PKCE params
    vi.mocked(pkceUtils.retrievePKCEParams).mockReturnValue(null)

    render(
      <BrowserRouter>
        <CallbackPage />
      </BrowserRouter>
    )

    // Should show error message
    await waitFor(() => {
      expect(screen.getByText('로그인 실패')).toBeInTheDocument()
      expect(screen.getByText(/인증 정보가 만료되었습니다/)).toBeInTheDocument()
    })

    // Should NOT call backend API
    expect(global.fetch).not.toHaveBeenCalled()
  })

  // Test 5: Edge Case - Backend API error
  it('should show error when backend API returns error', async () => {
    // Mock URL params
    mockSearchParams = new URLSearchParams({
      code: 'mock-auth-code',
      state: 'mock-state',
    })
    vi.mocked(useSearchParams).mockReturnValue([mockSearchParams, vi.fn()])

    // Mock PKCE params
    vi.mocked(pkceUtils.retrievePKCEParams).mockReturnValue({
      codeVerifier: 'mock-verifier',
      state: 'mock-state',
      nonce: 'mock-nonce',
    })

    // Mock backend error
    vi.mocked(global.fetch).mockResolvedValue({
      ok: false,
      status: 401,
      json: async () => ({
        detail: 'Invalid authorization code',
      }),
    } as Response)

    render(
      <BrowserRouter>
        <CallbackPage />
      </BrowserRouter>
    )

    // Should show error message
    await waitFor(() => {
      expect(screen.getByText('로그인 실패')).toBeInTheDocument()
    })

    // Should show help links
    expect(screen.getByText('계정 정보 확인')).toBeInTheDocument()
    expect(screen.getByText('관리자 문의')).toBeInTheDocument()

    // Should NOT redirect
    expect(mockNavigate).not.toHaveBeenCalled()
  })

  // Test 6: Verify error message includes help links
  it('should display help links when authentication fails', async () => {
    // Mock URL without code
    mockSearchParams = new URLSearchParams({
      state: 'mock-state',
    })
    vi.mocked(useSearchParams).mockReturnValue([mockSearchParams, vi.fn()])

    render(
      <BrowserRouter>
        <CallbackPage />
      </BrowserRouter>
    )

    // Should show help links
    await waitFor(() => {
      const accountLink = screen.getByText('계정 정보 확인')
      expect(accountLink).toBeInTheDocument()
      expect(accountLink.closest('a')).toHaveAttribute('href', 'https://account.samsung.com')

      const supportLink = screen.getByText('관리자 문의')
      expect(supportLink).toBeInTheDocument()
      expect(supportLink.closest('a')).toHaveAttribute('href', 'mailto:support@samsung.com')
    })
  })

  // Test 7: Verify HttpOnly cookie is automatically sent
  it('should send credentials: include for HttpOnly cookie', async () => {
    mockSearchParams = new URLSearchParams({
      code: 'code',
      state: 'state',
    })
    vi.mocked(useSearchParams).mockReturnValue([mockSearchParams, vi.fn()])

    vi.mocked(pkceUtils.retrievePKCEParams).mockReturnValue({
      codeVerifier: 'verifier',
      state: 'state',
      nonce: 'nonce',
    })
    vi.mocked(pkceUtils.clearPKCEParams).mockImplementation(() => {})

    vi.mocked(global.fetch).mockResolvedValue({
      ok: true,
      json: async () => ({ user_id: 'user', is_new_user: false }),
    } as Response)

    render(
      <BrowserRouter>
        <CallbackPage />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/auth/oidc/callback',
        expect.objectContaining({
          credentials: 'include', // REQ-F-A1-5: HttpOnly cookie
        })
      )
    })
  })
})
