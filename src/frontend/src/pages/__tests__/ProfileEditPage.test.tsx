import { describe, test, expect } from 'vitest'
import ProfileEditPage from '../ProfileEditPage'
import SelfAssessmentPage from '../SelfAssessmentPage'

describe('ProfileEditPage', () => {
  test('reuses SelfAssessmentPage component', () => {
    expect(ProfileEditPage).toBe(SelfAssessmentPage)
  })
})
