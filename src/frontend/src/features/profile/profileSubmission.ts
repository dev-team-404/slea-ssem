import { LEVEL_MAPPING } from '../../constants/profileLevels'
import { profileService } from '../../services'
import { setCachedNickname } from '../../utils/nicknameCache'

type BaseProfileInput = {
  level: number
  career?: number
  interests?: string[]
}

type CompleteSignupInput = BaseProfileInput & {
  nickname: string
}

export async function submitProfileSurvey(input: BaseProfileInput) {
  const payload = {
    level: LEVEL_MAPPING[input.level],
    career: input.career ?? 0,
    interests: input.interests ?? [],
  }

  const response = await profileService.updateSurvey(payload)
  return {
    surveyId: response.survey_id,
    level: payload.level,
  }
}

export async function completeProfileSignup(input: CompleteSignupInput) {
  await profileService.registerNickname(input.nickname)
  const surveyResult = await submitProfileSurvey(input)
  setCachedNickname(input.nickname)

  return {
    nickname: input.nickname,
    surveyId: surveyResult.surveyId,
  }
}
