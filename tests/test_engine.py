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
    assert output[1] == ""
    assert output[output.index("Platforms in scope") + 1] == ""
    context_headers = [
        index for index, line in enumerate(output) if line.startswith("[CONTEXT ")
    ]
    assert context_headers
    assert all(output[index + 1] == "" for index in context_headers)
    assert output[output.index("  2. Android") + 1] == ""
    assert output[output.index("Is the shared control enabled?") + 1] == ""
    assert "Expected: Enabled" in output
    assert (
        "1. Compliant       2. Non-compliant\n3. Not applicable  4. Unknown"
        in output
    )
    first_question_index = output.index("Is the shared control enabled?")
    assert output[first_question_index - 1] == ""
    assert output[first_question_index - 2].startswith("Progress:")
    assert output[first_question_index - 2].endswith("1/2")
    second_question_index = output.index("Is the iOS control enabled?")
    assert output[second_question_index - 1] == ""
    assert output[second_question_index - 2].startswith("Progress:")
    assert output[second_question_index - 2].endswith("2/2")
    assert output.count("") >= len(results.context) + len(results.responses)


def test_interview_batches_repeated_questions_by_configured_scope() -> None:
    data = make_pack().model_dump()
    data["interview_scope_field"] = "platforms"
    for question in data["questions"]:
        question["repeat_for"] = ["platforms"]
    pack = AssessmentPack.model_validate(data)
    answers = iter(
        [
            "1,2",
            "",
            "Customer tenant",
            "",
            "1",
            "",
            "1",
            "",
            "1",
            "",
        ]
    )
    output: list[str] = []

    results = run_interview(
        pack,
        lambda _prompt: next(answers),
        output_fn=output.append,
    )

    assert [
        (response.question_id, response.scope["platforms"])
        for response in results.responses
    ] == [
        ("shared", "iOS"),
        ("ios-only", "iOS"),
        ("shared", "Android"),
    ]
    progress_lines = [line for line in output if line.startswith("Progress:")]
    expected_counters = [
        "1/2 iOS",
        "2/2 iOS",
        "1/1 Android",
        "1/1 Android completed",
    ]
    assert len(progress_lines) == len(expected_counters)
    assert all(
        line.endswith(counter)
        for line, counter in zip(progress_lines, expected_counters)
    )
    assert all("Overall" not in line for line in progress_lines)
    assert not any(line.startswith("Domain:") for line in output)
    assert (
        "1. Compliant       2. Non-compliant\n3. Not applicable  4. Unknown"
        in output
    )


def test_review_uses_clear_answer_and_optional_notes_prompts() -> None:
    pack = make_pack()
    prompts = []
    answers = iter(["1", ""])

    def input_fn(message: str) -> str:
        prompts.append(message)
        return next(answers)

    conduct_review(
        [pack.questions[0]],
        {},
        input_fn,
        lambda _message: None,
    )

    assert prompts == [
        "Answer [1-4]: ",
        "Notes (optional, Enter to skip): ",
    ]


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
    assert output[-1] == ""


def test_review_separates_question_guidance_and_expected_sections() -> None:
    question = make_pack().questions[0].model_copy(
        update={
            "theme": "Authentication",
            "guidance": {
                "common": "Review the settings.",
                "ios": "Devices > Settings",
            },
        }
    )
    answers = iter(["1", ""])
    output: list[str] = []

    conduct_review(
        [question],
        {"platforms": ["iOS"]},
        input_fn=lambda _prompt: next(answers),
        output_fn=output.append,
    )

    index = output.index("Is the shared control enabled?")
    assert output[index - 2].startswith("Progress:")
    assert output[index - 2].endswith("1/1")
    assert output[index - 1] == ""
    assert output[index + 1] == ""
    assert not any(line.startswith("Domain:") for line in output)
    assert output[output.index("Evidence: Review the settings.") + 1] == ""
    assert output[output.index("Where to check: Devices > Settings") + 1] == ""
    assert output[output.index("Expected: Enabled") + 1] == ""
