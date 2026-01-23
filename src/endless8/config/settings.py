"""Configuration models for endless8."""

from pydantic import BaseModel, Field


class ClaudeOptions(BaseModel):
    """claude CLI オプション。"""

    allowed_tools: list[str] = Field(
        default=["Read", "Edit", "Write", "Bash"],
        description="許可するツール",
    )
    model: str = Field(default="sonnet", description="使用するモデル")
    output_format: str = Field(default="stream-json", description="出力形式")
    verbose: bool = Field(default=True, description="詳細出力")
    timeout: float = Field(
        default=300.0,
        ge=30.0,
        le=3600.0,
        description="SDK クエリのタイムアウト（秒）",
    )


class LoggingOptions(BaseModel):
    """ロギングオプション。"""

    raw_log: bool = Field(default=False, description="生ログを保存するか")
    raw_log_dir: str = Field(default=".e8/logs", description="生ログ保存先")


class PromptsConfig(BaseModel):
    """プロンプト設定。"""

    judgment: str | None = Field(None, description="判定エージェントのプロンプト")
    append_system_prompt: str | None = Field(
        None,
        description="実行エージェントに追加するシステムプロンプト",
    )


class EngineConfig(BaseModel):
    """エンジン設定。"""

    task: str = Field(..., description="タスクの説明")
    criteria: list[str] = Field(..., min_length=1, description="完了条件")
    agent_model: str = Field(
        default="anthropic:claude-sonnet-4-5",
        description="エージェントが使用するモデル",
    )
    max_iterations: int = Field(
        default=10, ge=1, le=100, description="最大イテレーション数"
    )
    persist: str | None = Field(None, description="履歴ファイルパス")
    knowledge: str = Field(
        default=".e8/knowledge.jsonl", description="ナレッジファイルパス"
    )
    history_context_size: int = Field(
        default=5, ge=1, le=20, description="履歴参照件数"
    )
    knowledge_context_size: int = Field(
        default=10, ge=1, le=50, description="ナレッジ参照件数"
    )
    logging: LoggingOptions = Field(default_factory=LoggingOptions)
    claude_options: ClaudeOptions = Field(default_factory=ClaudeOptions)
    prompts: PromptsConfig = Field(default_factory=PromptsConfig)
