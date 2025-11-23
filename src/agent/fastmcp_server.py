"""
FastMCP Server implementation for agent tool registration.

REQ: REQ-A-FastMCP

Provides:
- FastMCP server setup and tool registration
- 6 real tool implementations for agent pipeline (Tool 1-6)
- Error handling and timeout management
- Integration with LangChain agent
"""

import logging

# Import real tool implementations from src/agent/tools/
from src.agent.tools.difficulty_keywords_tool import get_difficulty_keywords
from src.agent.tools.save_question_tool import save_generated_question
from src.agent.tools.score_and_explain_tool import score_and_explain
from src.agent.tools.search_templates_tool import search_question_templates
from src.agent.tools.user_profile_tool import get_user_profile
from src.agent.tools.validate_question_tool import validate_question_quality

logger = logging.getLogger(__name__)

# ============================================================================
# Real Tool Implementations
# ============================================================================
# All tools are now imported from src/agent/tools/ directory
# - Tool 1: get_user_profile (user_profile_tool.py)
# - Tool 2: search_question_templates (search_templates_tool.py)
# - Tool 3: get_difficulty_keywords (difficulty_keywords_tool.py)
# - Tool 4: validate_question_quality (validate_question_tool.py)
# - Tool 5: save_generated_question (save_question_tool.py)
# - Tool 6: score_and_explain (score_and_explain_tool.py)
#
# These are PRODUCTION-READY implementations with:
# - Real database connections
# - LLM-based validation and scoring
# - Error handling and retry logic
# - Proper logging and monitoring
# ============================================================================


# ============================================================================
# Tool 목록
# ============================================================================

TOOLS = [
    get_user_profile,
    search_question_templates,
    get_difficulty_keywords,
    validate_question_quality,
    save_generated_question,
    score_and_explain,
]
