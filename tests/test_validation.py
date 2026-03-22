"""Tests for Pydantic model validation rules."""

import pytest
from pydantic import ValidationError

from src.server import (
    TodoistCreateTaskInput,
    TodoistUpdateTaskInput,
    TodoistListCommentsInput,
    TodoistCreateCommentInput,
)


class TestTaskDueDateExclusivity:
    """Only one of due_string, due_date, due_datetime allowed."""

    def test_due_string_alone_ok(self):
        t = TodoistCreateTaskInput(content="test", due_string="tomorrow")
        assert t.due_string == "tomorrow"

    def test_due_date_alone_ok(self):
        t = TodoistCreateTaskInput(content="test", due_date="2026-04-01")
        assert t.due_date == "2026-04-01"

    def test_due_string_and_due_date_rejected(self):
        with pytest.raises(ValidationError, match="Only one of"):
            TodoistCreateTaskInput(
                content="test", due_string="tomorrow", due_date="2026-04-01"
            )

    def test_all_three_rejected(self):
        with pytest.raises(ValidationError, match="Only one of"):
            TodoistCreateTaskInput(
                content="test",
                due_string="tomorrow",
                due_date="2026-04-01",
                due_datetime="2026-04-01T10:00:00Z",
            )

    def test_update_due_string_and_date_rejected(self):
        with pytest.raises(ValidationError, match="Only one of"):
            TodoistUpdateTaskInput(
                task_id="123", due_string="tomorrow", due_date="2026-04-01"
            )


class TestDurationUnit:
    """duration_unit must be 'minute' or 'day'."""

    def test_valid_minute(self):
        t = TodoistCreateTaskInput(content="test", duration=30, duration_unit="minute")
        assert t.duration_unit == "minute"

    def test_valid_day(self):
        t = TodoistCreateTaskInput(content="test", duration=1, duration_unit="day")
        assert t.duration_unit == "day"

    def test_invalid_unit_rejected(self):
        with pytest.raises(ValidationError, match="duration_unit"):
            TodoistCreateTaskInput(content="test", duration=30, duration_unit="hour")


class TestCommentIdExclusivity:
    """Exactly one of task_id or project_id required."""

    def test_task_id_alone_ok(self):
        c = TodoistListCommentsInput(task_id="123")
        assert c.task_id == "123"

    def test_both_rejected(self):
        with pytest.raises(ValidationError, match="exactly one"):
            TodoistListCommentsInput(task_id="123", project_id="456")

    def test_neither_rejected(self):
        with pytest.raises(ValidationError):
            TodoistListCommentsInput()

    def test_create_both_rejected(self):
        with pytest.raises(ValidationError, match="exactly one"):
            TodoistCreateCommentInput(content="hi", task_id="123", project_id="456")
