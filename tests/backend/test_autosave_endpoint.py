"""Integration test for autosave endpoint."""
from src.backend.models.question import Question
from src.backend.models.test_session import TestSession
from sqlalchemy.orm import Session


def test_autosave_endpoint_success(db_session: Session, test_session_in_progress: TestSession) -> None:
    """REQ-B-B2-Plus-1: Test autosave endpoint saves answer successfully."""
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

    # Test via HTTP endpoint
    client_response = None
    try:
        from fastapi.testclient import TestClient
        from src.backend.main import app
        
        client = TestClient(app)
        response = client.post(
            "/questions/autosave",
            json={
                "session_id": str(test_session_in_progress.id),
                "question_id": str(question.id),
                "user_answer": {"answer": "B"},
                "response_time_ms": 3000,
            }
        )
        
        assert response.status_code == 200
        client_response = response.json()
        assert client_response["saved"] is True
        assert client_response["session_id"] == str(test_session_in_progress.id)
        assert client_response["question_id"] == str(question.id)
        assert client_response["saved_at"] is not None
        
        print(f"✅ Autosave endpoint test passed!")
        print(f"   Response: {client_response}")
    except Exception as e:
        print(f"❌ Autosave endpoint test error: {e}")
        raise
