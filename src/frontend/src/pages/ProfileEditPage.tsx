// REQ: REQ-F-A2-Edit-2, REQ-F-A2-Profile-Access-5
import React from 'react'
import SelfAssessmentPage from './SelfAssessmentPage'

/**
 * Profile Edit Page Component
 *
 * This page shares the same UI/logic as the SelfAssessmentPage
 * until dedicated profile editing fields (nickname, career, etc.)
 * are implemented.
 *
 * Route: /profile/edit
 */
const ProfileEditPage: React.FC = () => {
  return <SelfAssessmentPage />
}

export default ProfileEditPage
