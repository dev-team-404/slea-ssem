// REQ: REQ-F-A1-1, REQ-F-A1-3, REQ-B-A1-9
/**
 * Authentication utility functions for HttpOnly cookie-based auth.
 *
 * MIGRATION NOTE (2025-01):
 * - Removed: saveToken, getToken, removeToken (localStorage 방식)
 * - Migrated to HttpOnly cookie (XSS 방어)
 * - JWT는 서버에서 Set-Cookie로 관리
 * - 브라우저가 자동으로 모든 요청에 쿠키 포함
 */

/**
 * Check if user is authenticated via GET /api/auth/status
 * (HttpOnly cookie is automatically included by browser)
 *
 * REQ: REQ-F-A1-3, REQ-B-A1-9
 *
 * @returns Promise<boolean> - true if authenticated (200 OK), false otherwise
 */
export const isAuthenticated = async (): Promise<boolean> => {
  try {
    const response = await fetch('/api/auth/status', {
      credentials: 'include', // Include HttpOnly cookies
      method: 'GET',
    })
    return response.ok // 200 OK = authenticated, 401 = not authenticated
  } catch {
    return false
  }
}
