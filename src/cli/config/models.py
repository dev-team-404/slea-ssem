# src/cli/config/models.py
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

class Command(BaseModel):
    description: str = Field(..., description="명령어에 대한 설명 (help 메시지에 사용)")
    target: Optional[str] = Field(None, min_length=1, description="'module.function' 형태의 실행 함수 경로")
    sub_commands: Optional[Dict[str, 'Command']] = Field(None, description="하위 명령어 딕셔너리")

class CommandConfig(BaseModel):
    commands: Dict[str, Command]
