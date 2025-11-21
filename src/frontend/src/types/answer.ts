/**
 * Shared Answer Types
 *
 * Centralized type definitions for user answers across UI and service layers.
 * These types match the backend API contract and prevent type drift between:
 * - AutosaveRequest (questionService.ts)
 * - QuestionExplanation (ExplanationPage.tsx)
 * - Any future components handling user answers
 */

/**
 * Multiple choice answer format
 * User selects one option from available choices
 */
export interface MultipleChoiceAnswer {
  selected_key: string
}

/**
 * True/False answer format
 * User selects true or false
 */
export interface TrueFalseAnswer {
  answer: string | boolean
}

/**
 * Short answer format
 * User provides free-form text response
 */
export interface ShortAnswer {
  text: string
}

/**
 * Union type representing all possible user answer formats
 *
 * Backend contract: Answer structure depends on question type (item_type):
 * - multiple_choice → MultipleChoiceAnswer
 * - true_false → TrueFalseAnswer
 * - short_answer → ShortAnswer
 */
export type UserAnswer = MultipleChoiceAnswer | TrueFalseAnswer | ShortAnswer

/**
 * Type guard: Check if answer is MultipleChoiceAnswer
 */
export function isMultipleChoiceAnswer(answer: UserAnswer): answer is MultipleChoiceAnswer {
  return 'selected_key' in answer
}

/**
 * Type guard: Check if answer is TrueFalseAnswer
 */
export function isTrueFalseAnswer(answer: UserAnswer): answer is TrueFalseAnswer {
  return 'answer' in answer
}

/**
 * Type guard: Check if answer is ShortAnswer
 */
export function isShortAnswer(answer: UserAnswer): answer is ShortAnswer {
  return 'text' in answer
}

/**
 * Format UserAnswer to display string
 * Handles all answer types and gracefully degrades to string representation
 */
export function formatUserAnswer(answer: UserAnswer | string | null | undefined): string {
  // Handle null/undefined
  if (!answer) return ''

  // Already a string (e.g., from serialized backend response)
  if (typeof answer === 'string') return answer

  // Handle structured answer types
  if (isMultipleChoiceAnswer(answer)) {
    return answer.selected_key
  }

  if (isTrueFalseAnswer(answer)) {
    return String(answer.answer)
  }

  if (isShortAnswer(answer)) {
    return answer.text
  }

  // Fallback: stringify unknown structure
  return JSON.stringify(answer)
}
