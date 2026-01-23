"""endless8 - Context-efficient task execution loop engine.

pydantic-ai と claudecode-model を使用したコンテキスト効率の良いタスク実行ループエンジン。
"""

__version__ = "0.1.0"

from endless8.config import EngineConfig
from endless8.engine import Engine
from endless8.models import (
    ExecutionResult,
    ExecutionSummary,
    IntakeResult,
    JudgmentResult,
    Knowledge,
    LoopResult,
    TaskInput,
)

__all__ = [
    "__version__",
    "Engine",
    "EngineConfig",
    "TaskInput",
    "IntakeResult",
    "ExecutionResult",
    "ExecutionSummary",
    "JudgmentResult",
    "LoopResult",
    "Knowledge",
]
