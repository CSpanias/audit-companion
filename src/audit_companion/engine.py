"""Interactive assessment workflow and result generation."""

from collections.abc import Callable, Iterable, Mapping
from itertools import product
from typing import Protocol, TypeVar

from audit_companion.models import (
    AssessmentPack,
    AssessmentResults,
    ContextField,
    Question,
    QuestionResponse,
)
from audit_companion.ui import emit, emit_detail, emit_panel, prompt


def _show_guidance(
    guidance: Mapping[str, str],
    context: Mapping[str, object],
    scope: Mapping[str, str],
    output_fn: Callable[[str], None] | None,
) -> None:
    common = guidance.get("common")
    if common:
        emit_detail("Evidence", common.strip(), "blue", output_fn)

    selected_values = []
    for field_id, value in context.items():
        if field_id in scope:
            continue
        selected_values.extend(value if isinstance(value, list) else [value])
    selected_values.extend(scope.values())
    normalized_values = [str(value).casefold() for value in selected_values]
    specific = [
        text.strip()
        for key, text in guidance.items()
        if key != "common"
        and any(key.casefold() in value for value in normalized_values)
    ]
    if specific:
        emit_detail("Where to check", "\n".join(specific), "yellow", output_fn)


class Applicable(Protocol):
    applies_when: dict[str, list[str]]


T = TypeVar("T", bound=Applicable)


class AssessmentError(ValueError):
    """Raised when a pack cannot produce a meaningful assessment."""


def applies(
    conditions: Mapping[str, list[str]],
    context: Mapping[str, object],
) -> bool:
    """Return whether all configured context conditions match."""
    for field_id, allowed_values in conditions.items():
        value = context.get(field_id)
        values = value if isinstance(value, list) else [value]
        if not any(candidate in allowed_values for candidate in values):
            return False
    return True


def applicable_items(
    items: Iterable[T],
    context: Mapping[str, object],
) -> list[T]:
    return [
        item
        for item in items
        if applies(item.applies_when, context)
    ]


def expand_question_scopes(
    questions: Iterable[Question],
    context: Mapping[str, object],
    scope_field_order: str | None = None,
) -> list[tuple[Question, dict[str, str]]]:
    instances = []
    for question in questions:
        scope_options = []
        for field_id in question.repeat_for:
            value = context.get(field_id)
            values = value if isinstance(value, list) else [value]
            scope_options.append(
                [(field_id, str(candidate)) for candidate in values if candidate is not None]
            )

        combinations = product(*scope_options) if scope_options else [()]
        for combination in combinations:
            scope = dict(combination)
            if applies(question.applies_when, {**context, **scope}):
                instances.append((question, scope))
    if scope_field_order:
        selected = context.get(scope_field_order)
        selected_values = selected if isinstance(selected, list) else [selected]
        scope_order = {
            str(value): index
            for index, value in enumerate(selected_values)
            if value is not None
        }
        instances.sort(
            key=lambda item: scope_order.get(
                item[1].get(scope_field_order, ""),
                len(scope_order),
            )
        )
    return instances


def collect_context(
    fields: Iterable[ContextField],
    context: dict[str, str | int | list[str]] | None = None,
    notes: dict[str, str] | None = None,
    input_fn: Callable[[str], str] | None = None,
    output_fn: Callable[[str], None] | None = None,
) -> tuple[dict[str, str | int | list[str]], dict[str, str]]:
    context = context if context is not None else {}
    notes = notes if notes is not None else {}
    fields = list(fields)

    for current, field in enumerate(fields, start=1):
        if not applies(field.applies_when, context):
            continue

        emit(f"[CONTEXT {current}/{len(fields)}]", output_fn, "bold cyan")
        emit("", output_fn)
        if field.description:
            emit_panel("Context", field.description.strip(), "blue", output_fn)
        if field.evidence:
            emit_panel("Evidence", field.evidence, "blue", output_fn)
        if field.location:
            emit_panel("Location", field.location, "yellow", output_fn)
        _show_guidance(field.guidance, context, {}, output_fn)

        value = _collect_value(field, input_fn, output_fn)
        if value is not None:
            context[field.id] = value

        note = prompt("Notes (optional): ", input_fn).strip()
        if note:
            notes[field.id] = note
        emit("", output_fn)

    return context, notes


def _collect_value(
    field: ContextField,
    input_fn: Callable[[str], str] | None,
    output_fn: Callable[[str], None] | None,
) -> str | int | list[str] | None:
    while True:
        emit(field.label, output_fn, "bold")
        emit("", output_fn)
        if field.type in ("choice", "multi_choice"):
            for index, option in enumerate(field.options, start=1):
                emit(f"  {index}. {option}", output_fn, "cyan")
            emit("", output_fn)
            prompt_text = (
                "Select one or more options (comma-separated): "
                if field.type == "multi_choice"
                else "Select an option: "
            )
        else:
            prompt_text = "> "

        raw_value = prompt(prompt_text, input_fn).strip()
        if not raw_value:
            if field.required:
                emit("A value is required.", output_fn, "red")
                continue
            return None

        if field.type == "integer":
            try:
                value = int(raw_value)
                if value < 0:
                    raise ValueError
                return value
            except ValueError:
                emit("Enter a non-negative whole number.", output_fn, "red")
                continue

        if field.type in ("choice", "multi_choice"):
            try:
                selections = [int(part.strip()) for part in raw_value.split(",")]
                if any(index < 1 or index > len(field.options) for index in selections):
                    raise ValueError
                chosen = [field.options[index - 1] for index in selections]
                if field.type == "choice" and len(chosen) != 1:
                    raise ValueError
                descriptions = [
                    field.option_descriptions[option]
                    for option in chosen
                    if option in field.option_descriptions
                ]
                if descriptions:
                    emit_panel(
                        "Selection guidance",
                        "\n\n".join(descriptions),
                        "blue",
                        output_fn,
                    )
                return chosen if field.type == "multi_choice" else chosen[0]
            except ValueError:
                emit("Select a valid option number.", output_fn, "red")
                continue

        return raw_value


def conduct_review(
    questions: Iterable[Question],
    context: Mapping[str, object],
    input_fn: Callable[[str], str] | None = None,
    output_fn: Callable[[str], None] | None = None,
    scope_field_order: str | None = None,
) -> list[QuestionResponse]:
    question_instances = expand_question_scopes(
        questions,
        context,
        scope_field_order,
    )
    if not question_instances:
        raise AssessmentError("No assessment questions apply to the selected context.")
    responses = []
    scope_totals: dict[str, int] = {}
    if scope_field_order:
        for _, scope in question_instances:
            scope_value = scope.get(scope_field_order)
            if scope_value is not None:
                scope_totals[scope_value] = scope_totals.get(scope_value, 0) + 1
    scope_counters: dict[str, int] = {}

    for overall_current, (question, scope) in enumerate(question_instances, start=1):
        scope_value = scope.get(scope_field_order) if scope_field_order else None
        if scope_value is None:
            counter = f"[{overall_current}/{len(question_instances)}]"
        else:
            current = scope_counters.get(scope_value, 0) + 1
            scope_counters[scope_value] = current
            counter = (
                f"[{current}/{scope_totals[scope_value]}] {scope_value}  |  "
                f"Overall {overall_current}/{len(question_instances)}"
            )
        emit(counter, output_fn, "bold cyan")
        emit("", output_fn)
        emit(question.question, output_fn, "bold")
        emit("", output_fn)
        group = question.commentary_group or question.theme
        if group:
            emit(f"Domain: {group}", output_fn, "dim")
        additional_scope = {
            field_id: value
            for field_id, value in scope.items()
            if field_id != scope_field_order
        }
        if additional_scope:
            emit(
                "Scope: "
                + ", ".join(
                    f"{field_id}={value}"
                    for field_id, value in additional_scope.items()
                ),
                output_fn,
                "yellow",
            )
        if question.evidence:
            emit_detail("Evidence", question.evidence, "blue", output_fn)
        if question.location:
            emit_detail(
                "Where to check",
                question.location,
                "yellow",
                output_fn,
            )
        _show_guidance(question.guidance, context, scope, output_fn)
        emit_detail("Expected", question.expected_value, "green", output_fn)
        emit(
            "1. Compliant       2. Non-compliant\n"
            "3. Not applicable  4. Unknown",
            output_fn,
        )
        emit("", output_fn)

        answers = {
            "1": "compliant",
            "2": "non_compliant",
            "3": "not_applicable",
            "4": "unknown",
        }
        while True:
            choice = prompt("Answer [1-4]: ", input_fn).strip()
            if choice in answers:
                break
            emit("Select 1, 2, 3, or 4.", output_fn, "red")

        notes = prompt("Notes (optional, Enter to skip): ", input_fn).strip() or None
        responses.append(
            QuestionResponse(
                question_id=question.id,
                answer=answers[choice],
                scope=scope,
                notes=notes,
            )
        )
        emit("", output_fn)

    return responses


def build_results(
    pack: AssessmentPack,
    context: dict[str, str | int | list[str]],
    context_notes: dict[str, str],
    responses: list[QuestionResponse],
) -> AssessmentResults:
    questions_by_id = {question.id: question for question in pack.questions}
    findings = []
    positives = []

    for response in responses:
        question = questions_by_id[response.question_id]
        observation = {
            "question_id": question.id,
            "scope": response.scope,
            "section": question.section,
            "theme": question.theme,
            "commentary_group": question.commentary_group,
            "remediation_id": question.remediation_id,
            "title": question.finding_title,
            "description": question.description,
            "commentary": question.commentary,
            "solution": question.solution,
            "expected_value": question.expected_value,
            "references": question.references,
            "notes": response.notes,
        }
        if response.answer == "unknown" or response.answer == "not_applicable":
            continue
        if response.answer == question.expected_answer:
            observation["title"] = question.positive or question.finding_title
            observation["description"] = question.positive or question.description
            observation["commentary"] = None
            positives.append(observation)
        else:
            findings.append(observation)

    return AssessmentResults(
        pack_id=pack.id,
        pack_title=pack.title,
        pack_version=pack.version,
        context=context,
        context_notes=context_notes,
        responses=responses,
        findings=findings,
        positive_observations=positives,
    )


def run_interview(
    pack: AssessmentPack,
    input_fn: Callable[[str], str] | None = None,
    output_fn: Callable[[str], None] | None = None,
) -> AssessmentResults:
    """Run the context interview and applicable control questionnaire."""
    emit(f"{pack.title} (v{pack.version})", output_fn, "bold green")
    emit("", output_fn)
    context, context_notes = collect_context(
        (field for field in pack.context if field.phase == "setup"),
        input_fn=input_fn,
        output_fn=output_fn,
    )
    collect_context(
        (field for field in pack.context if field.phase == "context"),
        context,
        context_notes,
        input_fn,
        output_fn,
    )
    responses = conduct_review(
        pack.questions,
        context,
        input_fn,
        output_fn,
        pack.interview_scope_field,
    )
    return build_results(pack, context, context_notes, responses)
