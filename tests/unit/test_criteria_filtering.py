"""Tests for criteria filtering."""

from endless8.models.criteria import CommandCriterion, filter_semantic_criteria


class TestFilterSemanticCriteria:
    """Tests for filter_semantic_criteria function."""

    def test_filters_out_command_criteria(self) -> None:
        """CommandCriterion がフィルタされること。"""
        criteria = [
            "テストカバレッジが90%以上",
            CommandCriterion(
                type="command",
                command="pytest --cov",
                description="テスト全パス",
            ),
            "コードレビュー完了",
        ]
        result = filter_semantic_criteria(criteria)
        assert result == ["テストカバレッジが90%以上", "コードレビュー完了"]

    def test_returns_empty_when_only_commands(self) -> None:
        """コマンド条件のみの場合は空リストを返すこと。"""
        criteria = [
            CommandCriterion(
                type="command",
                command="pytest",
                description="テスト",
            ),
        ]
        result = filter_semantic_criteria(criteria)
        assert result == []

    def test_returns_all_when_no_commands(self) -> None:
        """セマンティック条件のみの場合は全て返すこと。"""
        criteria = ["条件A", "条件B"]
        result = filter_semantic_criteria(criteria)
        assert result == ["条件A", "条件B"]

    def test_preserves_order(self) -> None:
        """セマンティック条件の順序が保持されること。"""
        criteria = [
            "条件1",
            CommandCriterion(type="command", command="cmd1"),
            "条件2",
            CommandCriterion(type="command", command="cmd2"),
            "条件3",
        ]
        result = filter_semantic_criteria(criteria)
        assert result == ["条件1", "条件2", "条件3"]
