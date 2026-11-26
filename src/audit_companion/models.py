"""Validated models shared by assessment packs and the interview engine."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


Answer = Literal["compliant", "non_compliant", "not_applicable", "unknown"]
ContextType = Literal["text", "integer", "choice", "multi_choice"]


class ContextField(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    label: str
    type: ContextType = "text"
    phase: Literal["setup", "context"] = "context"
    required: bool = False
    options: list[str] = Field(default_factory=list)
    evidence: str | None = None
    location: str | None = None
    applies_when: dict[str, list[str]] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_options(self) -> "ContextField":
        if self.type in ("choice", "multi_choice") and not self.options:
            raise ValueError(f"{self.type} context fields must define options")
        if self.type not in ("choice", "multi_choice") and self.options:
            raise ValueError("Only choice context fields may define options")
        return self


class Question(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    question: str
    expected_value: str
    expected_answer: Literal["compliant", "non_compliant"] = "compliant"
    section: str | None = None
    evidence: str | None = None
    location: str | None = None
    applies_when: dict[str, list[str]] = Field(default_factory=dict)
    repeat_for: list[str] = Field(default_factory=list)
    finding_title: str
    description: str
    solution: str
    references: list[str] = Field(default_factory=list)
    positive: str | None = None
    sureformat_id: str | None = None


class AssessmentPack(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    title: str
    version: str
    context: list[ContextField] = Field(default_factory=list)
    questions: list[Question] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_schema(self) -> "AssessmentPack":
        context_ids = [field.id for field in self.context]
        question_ids = [question.id for question in self.questions]
        if len(context_ids) != len(set(context_ids)):
            raise ValueError("Context field ids must be unique")
        if len(question_ids) != len(set(question_ids)):
            raise ValueError("Question ids must be unique")
        known_context_ids = set(context_ids)
        ordered_context = [
            field
            for phase in ("setup", "context")
            for field in self.context
            if field.phase == phase
        ]
        context_order = {
            field.id: index for index, field in enumerate(ordered_context)
        }
        for index, item in enumerate(ordered_context):
            unknown_ids = set(item.applies_when) - known_context_ids
            if unknown_ids:
                raise ValueError(
                    f"{item.id} has applicability conditions for unknown context "
                    f"fields: {', '.join(sorted(unknown_ids))}"
                )
            later_ids = {
                field_id
                for field_id in item.applies_when
                if context_order[field_id] >= index
            }
            if later_ids:
                raise ValueError(
                    f"{item.id} depends on context fields that have not been "
                    f"collected yet: {', '.join(sorted(later_ids))}"
                )
            for field_id, values in item.applies_when.items():
                source_field = ordered_context[context_order[field_id]]
                if (
                    source_field.type in ("choice", "multi_choice")
                    and not set(values).issubset(source_field.options)
                ):
                    raise ValueError(
                        f"{item.id} uses unknown option(s) for {field_id}"
                    )
        for item in self.questions:
            unknown_ids = set(item.applies_when) - known_context_ids
            unknown_repeat_ids = set(item.repeat_for) - known_context_ids
            if unknown_ids:
                raise ValueError(
                    f"{item.id} has applicability conditions for unknown context "
                    f"fields: {', '.join(sorted(unknown_ids))}"
                )
            if unknown_repeat_ids:
                raise ValueError(
                    f"{item.id} repeats over unknown context fields: "
                    f"{', '.join(sorted(unknown_repeat_ids))}"
                )
            if len(item.repeat_for) != len(set(item.repeat_for)):
                raise ValueError(f"{item.id} has duplicate repeat_for fields")
            for field_id in item.repeat_for:
                if self.context[context_ids.index(field_id)].type not in (
                    "choice",
                    "multi_choice",
                ):
                    raise ValueError(
                        f"{item.id} can only repeat over choice context fields"
                    )
            for field_id, values in item.applies_when.items():
                source_field = ordered_context[context_order[field_id]]
                if (
                    source_field.type in ("choice", "multi_choice")
                    and not set(values).issubset(source_field.options)
                ):
                    raise ValueError(
                        f"{item.id} uses unknown option(s) for {field_id}"
                    )
        return self


class QuestionResponse(BaseModel):
    question_id: str
    answer: Answer
    scope: dict[str, str] = Field(default_factory=dict)
    notes: str | None = None


class AssessmentResults(BaseModel):
    pack_id: str
    pack_title: str
    pack_version: str
    context: dict[str, str | int | list[str]]
    context_notes: dict[str, str]
    responses: list[QuestionResponse]
    findings: list[dict[str, object]]
    positive_observations: list[dict[str, object]]
