# src/cli/context.py
from dataclasses import dataclass
from logging import Logger
from rich.console import Console

@dataclass
class CLIContext:
    """
    CLI의 전역 상태와 공용 객체를 담는 데이터 클래스.
    이 컨텍스트는 모든 액션 함수에 주입되어 일관된 상태와 기능에 접근할 수 있도록 합니다.
    """
    console: Console
    logger: Logger
    # 향후 필요한 사용자 정보, 설정 객체 등을 여기에 추가할 수 있습니다.
