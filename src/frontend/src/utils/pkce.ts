/**
 * PKCE (Proof Key for Code Exchange) Utility
 *
 * REQ: REQ-F-A1-1, REQ-F-A1-2
 * Implements RFC 7636 for OAuth 2.0 public clients
 */

/**
 * Generate a cryptographically secure random string
 * @param length - Length of the random string (43-128 for PKCE)
 * @returns Base64URL-encoded random string
 */
function generateRandomString(length: number): string {
  const array = new Uint8Array(length)
  crypto.getRandomValues(array)
  return base64URLEncode(array)
}

/**
 * Base64URL encode (without padding)
 * @param buffer - Uint8Array to encode
 * @returns Base64URL-encoded string
 */
function base64URLEncode(buffer: Uint8Array): string {
  const base64 = btoa(String.fromCharCode(...buffer))
  return base64.replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '')
}

/**
 * Generate SHA-256 hash
 * @param plain - Plain text to hash
 * @returns Base64URL-encoded hash
 */
async function sha256(plain: string): Promise<string> {
  const encoder = new TextEncoder()
  const data = encoder.encode(plain)
  const hashBuffer = await crypto.subtle.digest('SHA-256', data)
  return base64URLEncode(new Uint8Array(hashBuffer))
}

/**
 * Generate PKCE code_verifier (43-128 characters)
 * @returns Random code_verifier string
 */
export function generateCodeVerifier(): string {
  return generateRandomString(64) // 64 bytes = ~86 characters after base64url
}

/**
 * Generate PKCE code_challenge from code_verifier
 * @param codeVerifier - Code verifier to hash
 * @returns Promise<code_challenge> (SHA-256 hash of verifier)
 */
export async function generateCodeChallenge(codeVerifier: string): Promise<string> {
  return sha256(codeVerifier)
}

/**
 * Generate random state for CSRF protection
 * @returns Random state string
 */
export function generateState(): string {
  return generateRandomString(32)
}

/**
 * Generate random nonce for replay attack protection
 * @returns Random nonce string
 */
export function generateNonce(): string {
  return generateRandomString(32)
}

/**
 * Generate all PKCE parameters at once
 * @returns Object with code_verifier, code_challenge, state, nonce
 */
export async function generatePKCEParams(): Promise<{
  codeVerifier: string
  codeChallenge: string
  state: string
  nonce: string
}> {
  const codeVerifier = generateCodeVerifier()
  const codeChallenge = await generateCodeChallenge(codeVerifier)
  const state = generateState()
  const nonce = generateNonce()

  return {
    codeVerifier,
    codeChallenge,
    state,
    nonce,
  }
}

/**
 * Store PKCE parameters in sessionStorage
 * @param params - PKCE parameters to store
 */
export function storePKCEParams(params: {
  codeVerifier: string
  state: string
  nonce: string
}): void {
  sessionStorage.setItem('pkce_code_verifier', params.codeVerifier)
  sessionStorage.setItem('pkce_state', params.state)
  sessionStorage.setItem('pkce_nonce', params.nonce)
}

/**
 * Retrieve stored PKCE parameters from sessionStorage
 * @returns Stored PKCE parameters or null if not found
 */
export function retrievePKCEParams(): {
  codeVerifier: string
  state: string
  nonce: string
} | null {
  const codeVerifier = sessionStorage.getItem('pkce_code_verifier')
  const state = sessionStorage.getItem('pkce_state')
  const nonce = sessionStorage.getItem('pkce_nonce')

  if (!codeVerifier || !state || !nonce) {
    return null
  }

  return { codeVerifier, state, nonce }
}

/**
 * Clear stored PKCE parameters from sessionStorage
 */
export function clearPKCEParams(): void {
  sessionStorage.removeItem('pkce_code_verifier')
  sessionStorage.removeItem('pkce_state')
  sessionStorage.removeItem('pkce_nonce')
}
