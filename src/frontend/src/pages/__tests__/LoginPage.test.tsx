// REQ: REQ-F-A1-1, REQ-F-A1-2, REQ-F-A1-3
import { render, screen, waitFor } from '@testing-library/react'
import { BrowserRouter, useNavigate } from 'react-router-dom'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import LoginPage from '../LoginPage'
import * as authUtils from '../../utils/auth'
import * as pkceUtils from '../../utils/pkce'

// Mock the auth and pkce modules
vi.mock('../../utils/auth')
vi.mock('../../utils/pkce')
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: vi.fn(),
  }
})

describe('LoginPage - Auto-redirect (REQ-F-A1-1, REQ-F-A1-2, REQ-F-A1-3)', () => {
  let originalLocation: Location
  let mockNavigate: ReturnType<typeof vi.fn>

  beforeEach(() => {
    // Mock window.location
    originalLocation = window.location
    // @ts-ignore
    delete window.location
    window.location = { href: '' } as Location

    // Mock navigate
    mockNavigate = vi.fn()
    vi.mocked(useNavigate).mockReturnValue(mockNavigate)

    // Mock sessionStorage
    vi.spyOn(Storage.prototype, 'setItem')
    vi.spyOn(Storage.prototype, 'getItem').mockReturnValue(null)

    // Mock environment variables
    vi.stubEnv('VITE_AZURE_AD_TENANT_ID', 'test-tenant-id')
    vi.stubEnv('VITE_AZURE_AD_CLIENT_ID', 'test-client-id')
  })

  afterEach(() => {
    window.location = originalLocation
    vi.clearAllMocks()
    vi.unstubAllEnvs()
  })

  // Test 1: REQ-F-A1-3 - Already authenticated → redirect to /home
  it('should redirect to /home if already authenticated (REQ-F-A1-3)', async () => {
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

    // Should NOT generate PKCE params
    expect(pkceUtils.generatePKCEParams).not.toHaveBeenCalled()
  })

  // Test 2: REQ-F-A1-1 - Not authenticated → Generate PKCE params
  it('should generate PKCE params when not authenticated (REQ-F-A1-1)', async () => {
    // Mock: User is NOT authenticated
    vi.mocked(authUtils.isAuthenticated).mockResolvedValue(false)

    // Mock: PKCE params generation
    const mockPkceParams = {
      codeVerifier: 'mock-code-verifier',
      codeChallenge: 'mock-code-challenge',
      state: 'mock-state',
      nonce: 'mock-nonce',
    }
    vi.mocked(pkceUtils.generatePKCEParams).mockResolvedValue(mockPkceParams)
    vi.mocked(pkceUtils.storePKCEParams).mockImplementation(() => {})

    render(
      <BrowserRouter>
        <LoginPage />
      </BrowserRouter>
    )

    // Should generate PKCE params
    await waitFor(() => {
      expect(pkceUtils.generatePKCEParams).toHaveBeenCalled()
    })

    // Should store PKCE params in sessionStorage
    await waitFor(() => {
      expect(pkceUtils.storePKCEParams).toHaveBeenCalledWith({
        codeVerifier: 'mock-code-verifier',
        state: 'mock-state',
        nonce: 'mock-nonce',
      })
    })
  })

  // Test 3: REQ-F-A1-2 - Redirect to Azure AD with PKCE
  it('should redirect to Azure AD with PKCE params (REQ-F-A1-2)', async () => {
    // Mock: User is NOT authenticated
    vi.mocked(authUtils.isAuthenticated).mockResolvedValue(false)

    // Mock: PKCE params generation
    const mockPkceParams = {
      codeVerifier: 'test-verifier',
      codeChallenge: 'test-challenge',
      state: 'test-state',
      nonce: 'test-nonce',
    }
    vi.mocked(pkceUtils.generatePKCEParams).mockResolvedValue(mockPkceParams)
    vi.mocked(pkceUtils.storePKCEParams).mockImplementation(() => {})

    render(
      <BrowserRouter>
        <LoginPage />
      </BrowserRouter>
    )

    // Should redirect to Azure AD
    await waitFor(() => {
      expect(window.location.href).toContain('https://login.microsoftonline.com')
    })

    // Verify URL contains required PKCE params
    const redirectUrl = new URL(window.location.href)
    expect(redirectUrl.searchParams.get('client_id')).toBe('test-client-id')
    expect(redirectUrl.searchParams.get('response_type')).toBe('code')
    expect(redirectUrl.searchParams.get('code_challenge')).toBe('test-challenge')
    expect(redirectUrl.searchParams.get('code_challenge_method')).toBe('S256')
    expect(redirectUrl.searchParams.get('state')).toBe('test-state')
    expect(redirectUrl.searchParams.get('nonce')).toBe('test-nonce')
    expect(redirectUrl.searchParams.get('scope')).toBe('openid profile email')
  })

  // Test 4: Verify redirect_uri contains /auth/callback
  it('should include correct redirect_uri in Azure AD URL', async () => {
    // Mock: User is NOT authenticated
    vi.mocked(authUtils.isAuthenticated).mockResolvedValue(false)

    // Mock: PKCE params generation
    vi.mocked(pkceUtils.generatePKCEParams).mockResolvedValue({
      codeVerifier: 'verifier',
      codeChallenge: 'challenge',
      state: 'state',
      nonce: 'nonce',
    })
    vi.mocked(pkceUtils.storePKCEParams).mockImplementation(() => {})

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
    expect(redirectUri).toContain('/auth/callback')
  })

  // Test 5: Error handling - Show error message
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

  // Test 6: Render loading state initially
  it('should render loading state initially', () => {
    vi.mocked(authUtils.isAuthenticated).mockResolvedValue(false)
    vi.mocked(pkceUtils.generatePKCEParams).mockResolvedValue({
      codeVerifier: 'v',
      codeChallenge: 'c',
      state: 's',
      nonce: 'n',
    })

    render(
      <BrowserRouter>
        <LoginPage />
      </BrowserRouter>
    )

    // Should show loading state
    expect(screen.getByText('인증 중...')).toBeInTheDocument()
    expect(screen.getByText('SLEA-SSEM')).toBeInTheDocument()
  })

  // Test 7: Uses correct tenant ID in URL
  it('should use correct tenant ID in authorization URL', async () => {
    vi.mocked(authUtils.isAuthenticated).mockResolvedValue(false)
    vi.mocked(pkceUtils.generatePKCEParams).mockResolvedValue({
      codeVerifier: 'v',
      codeChallenge: 'c',
      state: 's',
      nonce: 'n',
    })
    vi.mocked(pkceUtils.storePKCEParams).mockImplementation(() => {})

    render(
      <BrowserRouter>
        <LoginPage />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(window.location.href).toContain('test-tenant-id')
    })

    expect(window.location.href).toContain('https://login.microsoftonline.com/test-tenant-id/oauth2/v2.0/authorize')
  })
})
