# src/cli/config/loader.py
from src.cli.config.models import CommandConfig
from src.cli.config.command_layout import COMMAND_LAYOUT

def load_config() -> CommandConfig:
    """
    command_layout.py에서 COMMAND_LAYOUT 딕셔너리를 로드하고,
    Pydantic 모델(CommandConfig)을 사용하여 구조와 데이터 타입을 검증합니다.

    Returns:
        검증된 CommandConfig 객체.

    Raises:
        pydantic.ValidationError: 설정 파일의 구조가 모델과 일치하지 않을 경우.
    """
    return CommandConfig(commands=COMMAND_LAYOUT)
