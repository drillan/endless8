"""Data models for endless8."""

from endless8.models.criteria import (
    CommandCriterion,
    CriterionInput,
    CriterionType,
    criteria_to_str_list,
    filter_semantic_criteria,
)
from endless8.models.knowledge import Knowledge, KnowledgeConfidence, KnowledgeType
from endless8.models.progress import ProgressEvent, ProgressEventType
from endless8.models.results import (
    CommandResult,
    CriteriaEvaluation,
    ExecutionResult,
    ExecutionStatus,
    IntakeResult,
    IntakeStatus,
    JudgmentResult,
    LoopResult,
    LoopStatus,
    SemanticMetadata,
)
from endless8.models.state import StateTransition, TaskPhase
from endless8.models.summary import (
    ExecutionSummary,
    KnowledgeEntry,
    NextAction,
    SummaryLLMOutput,
    SummaryMetadata,
)
from endless8.models.task import TaskInput

__all__ = [
    # Task
    "TaskInput",
    # Criteria
    "CriterionType",
    "CommandCriterion",
    "CriterionInput",
    "criteria_to_str_list",
    "filter_semantic_criteria",
    # Results
    "IntakeStatus",
    "IntakeResult",
    "ExecutionStatus",
    "ExecutionResult",
    "SemanticMetadata",
    "CommandResult",
    "CriteriaEvaluation",
    "JudgmentResult",
    "LoopStatus",
    "LoopResult",
    # State
    "TaskPhase",
    "StateTransition",
    # Summary
    "KnowledgeEntry",
    "SummaryLLMOutput",
    "SummaryMetadata",
    "NextAction",
    "ExecutionSummary",
    # Knowledge
    "KnowledgeType",
    "KnowledgeConfidence",
    "Knowledge",
    # Progress
    "ProgressEventType",
    "ProgressEvent",
]
