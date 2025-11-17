import { render, screen } from '@testing-library/react'
import { describe, test, expect, vi } from 'vitest'
import ProfileEditPage from '../ProfileEditPage'

const MockSelfAssessment = vi.fn(() => (
  <div data-testid="self-assessment-proxy">SelfAssessment</div>
))

vi.mock('../SelfAssessmentPage', () => ({
  __esModule: true,
  default: MockSelfAssessment,
}))

describe('ProfileEditPage', () => {
  test('reuses SelfAssessmentPage component', () => {
    render(<ProfileEditPage />)

    expect(screen.getByTestId('self-assessment-proxy')).toBeInTheDocument()
    expect(MockSelfAssessment).toHaveBeenCalledTimes(1)
  })
})
