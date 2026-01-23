"""Knowledge models for endless8."""

from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, Field


class KnowledgeType(str, Enum):
    """ナレッジタイプ。"""

    DISCOVERY = "discovery"  # コードベースの事実
    LESSON = "lesson"  # 失敗から学んだ教訓
    PATTERN = "pattern"  # コーディング規約・慣習
    CONSTRAINT = "constraint"  # 技術的制約
    CODEBASE = "codebase"  # 構造的な知見


class KnowledgeConfidence(str, Enum):
    """信頼度。"""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


def _utc_now() -> datetime:
    """Return current UTC time."""
    return datetime.now(UTC)


class Knowledge(BaseModel):
    """ナレッジエントリ。"""

    type: KnowledgeType
    category: str = Field(..., description="カテゴリ（例: error_handling, testing）")
    content: str = Field(..., description="ナレッジの内容")
    example_file: str | None = Field(None, description="例となるファイルと行番号")
    source_task: str = Field(..., description="発見元のタスク")
    confidence: KnowledgeConfidence = Field(default=KnowledgeConfidence.MEDIUM)
    applied_count: int = Field(default=0, ge=0, description="適用された回数")
    created_at: datetime = Field(default_factory=_utc_now)
