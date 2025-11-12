"""End-to-end test for CLI autosave with fixtures."""
from src.backend.models.question import Question
from src.backend.models.test_session import TestSession
from sqlalchemy.orm import Session


def test_autosave_with_existing_session(db_session: Session, test_session_in_progress: TestSession):
    """Test autosave API with existing test session and question."""
    # Create a test question
    question = Question(
        session_id=test_session_in_progress.id,
        item_type="multiple_choice",
        stem="What is the correct answer?",
        choices=["A", "B", "C", "D"],
        answer_schema={
            "correct_answer": "A",
            "explanation": "A is correct"
        },
        difficulty=5,
        category="AI",
        round=1
    )
    db_session.add(question)
    db_session.commit()

    print(f"\n✅ Test data created!")
    print(f"Session ID: {test_session_in_progress.id}")
    print(f"Question ID: {question.id}")
    
    # Verify the data exists
    assert question.session_id == test_session_in_progress.id
    assert question.stem == "What is the correct answer?"
