from audit_companion.engine import (
    applicable_items,
    build_results,
    conduct_review,
    expand_question_scopes,
    run_interview,
)
from audit_companion.models import (
    AssessmentPack,
    QuestionResponse,
)


def make_pack() -> AssessmentPack:
    return AssessmentPack.model_validate(
        {
            "id": "test-pack",
            "title": "Test assessment",
            "version": "1.0",
            "context": [
                {
                    "id": "platforms",
                    "label": "Platforms in scope",
                    "type": "multi_choice",
                    "phase": "setup",
                    "required": True,
                    "options": ["iOS", "Android"],
                },
                {
                    "id": "tenant",
                    "label": "Tenant name",
                    "required": True,
                    "applies_when": {"platforms": ["iOS"]},
                },
            ],
            "questions": [
                {
                    "id": "shared",
                    "question": "Is the shared control enabled?",
                    "expected_value": "Enabled",
                    "finding_title": "Shared control disabled",
                    "description": "The shared control is not enabled.",
                    "solution": "Enable it.",
                },
                {
                    "id": "ios-only",
                    "question": "Is the iOS control enabled?",
                    "expected_value": "Enabled",
                    "applies_when": {"platforms": ["iOS"]},
                    "finding_title": "iOS control disabled",
                    "description": "The iOS control is not enabled.",
                    "solution": "Enable it.",
                },
            ],
        }
    )


def test_applicability_matches_selected_values_in_multi_choice_context() -> None:
    pack = make_pack()

    selected = applicable_items(
        pack.questions,
        {"platforms": ["iOS", "Android"]},
    )
    not_selected = applicable_items(
        pack.questions,
        {"platforms": ["Android"]},
    )

    assert [question.id for question in selected] == ["shared", "ios-only"]
    assert [question.id for question in not_selected] == ["shared"]


def test_results_exclude_unknown_and_not_applicable_answers() -> None:
    pack = make_pack()
    results = build_results(
        pack,
        {"platforms": ["iOS"]},
        {},
        [
            QuestionResponse(question_id="shared", answer="non_compliant", notes="Evidence"),
            QuestionResponse(question_id="ios-only", answer="unknown"),
        ],
    )

    assert [finding["question_id"] for finding in results.findings] == ["shared"]
    assert results.positive_observations == []


def test_questions_can_repeat_for_each_selected_platform() -> None:
    pack = make_pack()
    shared = pack.questions[0].model_copy(update={"repeat_for": ["platforms"]})
    instances = expand_question_scopes(
        [shared],
        {"platforms": ["iOS", "Android"]},
    )

    assert [scope for _, scope in instances] == [
        {"platforms": "iOS"},
        {"platforms": "Android"},
    ]

    results = build_results(
        pack,
        {"platforms": ["iOS", "Android"]},
        {},
        [
            QuestionResponse(
                question_id=question.id,
                answer="non_compliant",
                scope=scope,
            )
            for question, scope in instances
        ],
    )
    assert [finding["scope"] for finding in results.findings] == [
        {"platforms": "iOS"},
        {"platforms": "Android"},
    ]


def test_pack_rejects_applicability_conditions_on_later_context() -> None:
    data = make_pack().model_dump()
    data["context"][0]["applies_when"] = {"tenant": ["Customer"]}

    try:
        AssessmentPack.model_validate(data)
    except ValueError as error:
        assert "not been collected yet" in str(error)
    else:
        raise AssertionError("Expected invalid forward context dependency to fail")


def test_interview_collects_setup_before_conditioned_context_and_questions() -> None:
    pack = make_pack()
    answers = iter(["1", "", "Customer tenant", "", "2", "Observed", "1", ""])
    output: list[str] = []

    results = run_interview(pack, lambda _prompt: next(answers), output.append)

    assert results.context == {"platforms": ["iOS"], "tenant": "Customer tenant"}
    assert [response.question_id for response in results.responses] == ["shared", "ios-only"]
    assert results.findings[0]["question_id"] == "shared"
    assert results.positive_observations[0]["question_id"] == "ios-only"


def test_guidance_uses_the_current_repeated_scope() -> None:
    pack = make_pack()
    question = pack.questions[0].model_copy(
        update={
            "applies_when": {"platforms": ["iOS"]},
            "repeat_for": ["platforms"],
            "guidance": {
                "ios": "iOS configuration location",
                "android": "Android configuration location",
            },
        }
    )
    answers = iter(["1", ""])
    output: list[str] = []

    conduct_review(
        [question],
        {"platforms": ["iOS", "Android"]},
        lambda _prompt: next(answers),
        output.append,
    )

    assert any("iOS configuration location" in line for line in output)
    assert not any("Android configuration location" in line for line in output)
