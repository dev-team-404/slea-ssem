import '@testing-library/jest-dom'
import { vi } from 'vitest'
import { webcrypto } from 'node:crypto'

// Force Vitest to use frontend mock mode by default so transport
// never attempts to call the real backend during unit tests.
vi.stubEnv('VITE_MOCK_API', 'true')
vi.stubEnv('VITE_MOCK_SSO', 'true')

// Provide Web Crypto API for PKCE tests (REQ-F-A1-1)
if (!globalThis.crypto) {
  Object.defineProperty(globalThis, 'crypto', {
    value: webcrypto,
  })
}

// Provide a minimal matchMedia implementation for components that expect it.
if (!window.matchMedia) {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation(query => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: vi.fn(), // deprecated
      removeListener: vi.fn(), // deprecated
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  })
}
