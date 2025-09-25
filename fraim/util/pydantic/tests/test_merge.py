# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Resourcely Inc.

"""Tests for pydantic model merging functionality."""

import pytest
from pydantic import BaseModel, Field

from fraim.util.pydantic.merge import merge_models

from .conftest import DynamicModule


# Test Models - defined at module level for reuse
class BaseUser(BaseModel):
    name: str = "default"
    role: str = "user"


class OverlayUser(BaseModel):
    name: str = "override"
    role: str = "admin"


class BaseMessage(BaseModel):
    text: str


class OverlayMessage(BaseModel):
    text: str
    urgency: str = "normal"


class BaseResult(BaseModel):
    message: str = Field(description="Base message")


class OverlayResult(BaseModel):
    message: str = Field(description="Overlay message description")


class BaseScore(BaseModel):
    value: int = 0


class OverlayScore(BaseModel):
    value: int = Field(ge=1, le=10, description="Score from 1 to 10")


class BaseConfig(BaseModel):
    level: str = "info"


class OverlayConfig(BaseModel):
    level: str = Field(examples=["debug", "info", "error"])


class BaseTask(BaseModel):
    name: str


class OverlayTask(BaseModel):
    name: str
    priority: int = Field(default=1, description="Task priority")
    completed: bool = False


class BaseItem(BaseModel):
    name: str


class OverlayItem(BaseModel):
    name: str
    category: str = "default"


class BaseContainer(BaseModel):
    items: list[BaseItem] = []


class BaseError(BaseModel):
    code: str


class OverlayError(BaseModel):
    code: str
    severity: int = 1


class BaseWarning(BaseModel):
    level: str = "low"


class BaseIssueResult(BaseModel):
    issue: BaseError | BaseWarning


class TestMergeModels:
    """Test cases for merge_models function."""

    def test_basic_field_override(self, fresh_base_module: DynamicModule, fresh_overlay_module: DynamicModule) -> None:
        """Overlay fields completely override base fields."""
        fresh_base_module.User = BaseUser
        fresh_overlay_module.User = OverlayUser

        merged = merge_models(fresh_base_module, fresh_overlay_module)

        # Overlay values should override base values
        user = merged.User()
        assert user.name == "override"
        assert user.role == "admin"

    @pytest.mark.parametrize(
        "field_name,expected_description,expected_examples,expected_constraints",
        [
            ("message", "Overlay message description", None, []),
            ("level", None, ["debug", "info", "error"], []),
            ("value", "Score from 1 to 10", None, [(1, 10)]),  # (ge, le) tuple
        ],
    )
    def test_field_metadata_preserved(
        self,
        fresh_base_module: DynamicModule,
        fresh_overlay_module: DynamicModule,
        field_name: str,
        expected_description: str | None,
        expected_examples: list | None,
        expected_constraints: list[tuple[int, int]],
    ) -> None:
        """Field metadata (descriptions, examples, constraints) are preserved from overlay models."""
        # Set up models based on field being tested
        if field_name == "message":
            fresh_base_module.Result = BaseResult
            fresh_overlay_module.Result = OverlayResult
            model_name = "Result"
        elif field_name == "level":
            fresh_base_module.Config = BaseConfig
            fresh_overlay_module.Config = OverlayConfig
            model_name = "Config"
        elif field_name == "value":
            fresh_base_module.Score = BaseScore
            fresh_overlay_module.Score = OverlayScore
            model_name = "Score"

        merged = merge_models(fresh_base_module, fresh_overlay_module)
        merged_model = getattr(merged, model_name)
        field_info = merged_model.model_fields[field_name]

        # Check description
        if expected_description:
            assert field_info.description == expected_description

        # Check examples
        if expected_examples:
            assert field_info.examples == expected_examples

        # Check constraints
        if expected_constraints:
            metadata = field_info.metadata
            for ge_val, le_val in expected_constraints:
                ge_constraint = next((m for m in metadata if hasattr(m, "ge")), None)
                le_constraint = next((m for m in metadata if hasattr(m, "le")), None)

                assert ge_constraint is not None and ge_constraint.ge == ge_val
                assert le_constraint is not None and le_constraint.le == le_val

    def test_new_fields_from_overlay(
        self, fresh_base_module: DynamicModule, fresh_overlay_module: DynamicModule
    ) -> None:
        """New fields in overlay models are added to merged model."""
        fresh_base_module.Task = BaseTask
        fresh_overlay_module.Task = OverlayTask

        merged = merge_models(fresh_base_module, fresh_overlay_module)

        # Can create instance with new fields
        task = merged.Task(name="test", priority=5, completed=True)
        assert task.name == "test"
        assert task.priority == 5
        assert task.completed is True

        # New fields have their metadata
        priority_field = merged.Task.model_fields["priority"]
        assert priority_field.description == "Task priority"

    def test_base_model_without_overlay(
        self, fresh_base_module: DynamicModule, fresh_overlay_module: DynamicModule
    ) -> None:
        """Base models without overlays are included unchanged."""

        class BaseUserWithDesc(BaseModel):
            name: str = Field(description="User name")

        class BaseTask(BaseModel):
            title: str

        # Only overlay User, not Task
        class OverlayUserModified(BaseModel):
            name: str = "modified"

        fresh_base_module.User = BaseUserWithDesc
        fresh_base_module.Task = BaseTask
        fresh_overlay_module.User = OverlayUserModified

        merged = merge_models(fresh_base_module, fresh_overlay_module)

        # Task should be unchanged from base
        assert hasattr(merged, "Task")
        assert hasattr(merged, "User")

        # Task fields should be original
        task_fields = merged.Task.model_fields
        assert "title" in task_fields

        # User should be modified
        user = merged.User()
        assert user.name == "modified"

    def test_nested_model_references(
        self, fresh_base_module: DynamicModule, fresh_overlay_module: DynamicModule
    ) -> None:
        """Test nested BaseModel references (currently uses base models, not overlays)."""

        class BaseNestedResult(BaseModel):
            message: BaseMessage

        class OverlayNestedResult(BaseModel):
            message: BaseMessage  # Currently still references base, not overlay
            status: str = "pending"

        fresh_base_module.Message = BaseMessage
        fresh_base_module.Result = BaseNestedResult
        fresh_overlay_module.Message = OverlayMessage
        fresh_overlay_module.Result = OverlayNestedResult

        merged = merge_models(fresh_base_module, fresh_overlay_module)

        # Both merged models should exist
        assert hasattr(merged, "Message")
        assert hasattr(merged, "Result")

        # The overlay Result should have the status field
        assert "status" in merged.Result.model_fields

        # Create result - note that nested message still uses BaseMessage, not OverlayMessage
        result = merged.Result(
            message={"text": "hello"},  # Can only use BaseMessage fields
            status="active",
        )

        assert result.message.text == "hello"
        assert result.status == "active"
        # Note: message.urgency not available since nested resolution isn't working yet

    def test_complex_types_list(self, fresh_base_module: DynamicModule, fresh_overlay_module: DynamicModule) -> None:
        """List types with nested models (currently still use base models)."""
        fresh_base_module.Item = BaseItem
        fresh_base_module.Container = BaseContainer
        fresh_overlay_module.Item = OverlayItem

        merged = merge_models(fresh_base_module, fresh_overlay_module)

        # Both models should be merged
        assert hasattr(merged, "Item")
        assert hasattr(merged, "Container")

        # Items in list currently still use BaseItem, not OverlayItem
        container = merged.Container(
            items=[{"name": "item1"}]  # Can only use BaseItem fields for now
        )

        assert container.items[0].name == "item1"
        # Note: category not available since nested resolution isn't working yet

    def test_complex_types_union(self, fresh_base_module: DynamicModule, fresh_overlay_module: DynamicModule) -> None:
        """Union types with nested models (currently still use base models)."""
        fresh_base_module.Error = BaseError
        fresh_base_module.Warning = BaseWarning
        fresh_base_module.Result = BaseIssueResult
        fresh_overlay_module.Error = OverlayError

        merged = merge_models(fresh_base_module, fresh_overlay_module)

        # All models should exist
        assert hasattr(merged, "Error")
        assert hasattr(merged, "Warning")
        assert hasattr(merged, "Result")

        # Union currently still uses base models, not overlay
        result = merged.Result(
            issue={"code": "E001"}  # Can only use BaseError fields for now
        )

        assert result.issue.code == "E001"
        # Note: severity not available since nested resolution isn't working yet

    def test_optional_fields(self, fresh_base_module: DynamicModule, fresh_overlay_module: DynamicModule) -> None:
        """Optional fields work correctly with overlays."""

        class BaseOptionalUser(BaseModel):
            name: str
            email: str | None = None

        class OverlayOptionalUser(BaseModel):
            name: str
            email: str | None = Field(default=None, description="User email address")
            phone: str | None = None

        fresh_base_module.User = BaseOptionalUser
        fresh_overlay_module.User = OverlayOptionalUser

        merged = merge_models(fresh_base_module, fresh_overlay_module)

        # Can create with optional fields
        user1 = merged.User(name="Alice")
        assert user1.email is None
        assert user1.phone is None

        user2 = merged.User(name="Bob", email="bob@test.com", phone="123")
        assert user2.email == "bob@test.com"
        assert user2.phone == "123"

        # Email field has description from overlay
        email_field = merged.User.model_fields["email"]
        assert email_field.description == "User email address"

    @pytest.mark.parametrize(
        "missing_field,should_fail",
        [
            ("name", False),  # name is optional in overlay
            ("value", True),  # value is required in overlay
        ],
    )
    def test_field_required_status_preserved(
        self,
        fresh_base_module: DynamicModule,
        fresh_overlay_module: DynamicModule,
        missing_field: str,
        should_fail: bool,
    ) -> None:
        """Required/optional status from overlay is preserved."""

        class BaseRequiredConfig(BaseModel):
            name: str  # Required
            value: str | None = None  # Optional

        class OverlayRequiredConfig(BaseModel):
            name: str | None = None  # Make optional in overlay
            value: str  # Make required in overlay

        fresh_base_module.Config = BaseRequiredConfig
        fresh_overlay_module.Config = OverlayRequiredConfig

        merged = merge_models(fresh_base_module, fresh_overlay_module)

        # Build kwargs with all fields except the missing one
        kwargs = {"name": "test", "value": "required"}
        del kwargs[missing_field]

        if should_fail:
            with pytest.raises(ValueError):
                merged.Config(**kwargs)
        else:
            # Should succeed
            config = merged.Config(**kwargs)
            assert getattr(config, missing_field) is None  # Should get default value


class TestMergeEdgeCases:
    """Test edge cases and error conditions for merge_models."""

    def test_overlay_without_base_ignored(
        self, fresh_base_module: DynamicModule, fresh_overlay_module: DynamicModule
    ) -> None:
        """Overlay models without corresponding base models are ignored."""

        class OverlayOnlyTask(BaseModel):  # No BaseTask exists
            title: str

        fresh_base_module.User = BaseUser
        fresh_overlay_module.Task = OverlayOnlyTask

        # Should not raise error, just ignore the overlay-only model
        merged = merge_models(fresh_base_module, fresh_overlay_module)

        # Only base models should be present
        assert hasattr(merged, "User")
        assert not hasattr(merged, "Task")  # Overlay-only model ignored

    def test_empty_modules(self, fresh_base_module: DynamicModule, fresh_overlay_module: DynamicModule) -> None:
        """Handle empty modules gracefully."""
        fresh_base_module.User = BaseUser
        # overlay_module is empty

        merged = merge_models(fresh_base_module, fresh_overlay_module)

        # Should just return base models unchanged
        assert hasattr(merged, "User")
        user = merged.User(name="test")
        assert user.name == "test"

    @pytest.mark.parametrize("register_in_caller", [True, False])
    def test_register_in_caller_option(
        self, fresh_base_module: DynamicModule, fresh_overlay_module: DynamicModule, register_in_caller: bool
    ) -> None:
        """Test register_in_caller parameter controls model registration."""
        fresh_base_module.User = BaseUser
        fresh_overlay_module.User = OverlayUser

        merged = merge_models(fresh_base_module, fresh_overlay_module, register_in_caller=register_in_caller)

        # Should always work regardless of registration
        user = merged.User()
        assert user.name == "override"
        assert user.role == "admin"
