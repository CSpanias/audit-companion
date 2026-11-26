import pytest

from audit_companion.models import AssessmentPack, ContextField, Question


@pytest.fixture
def minimal_pack() -> AssessmentPack:
    return AssessmentPack(
        id="example-access-review",
        title="Example access review",
        version="1.0",
        executive_summary=(
            "The review assessed remote access security for {client_name}."
        ),
        context=[
            ContextField(
                id="access_platform",
                label="Which access platform is in scope?",
                type="choice",
                phase="setup",
                required=True,
                options=["Platform A", "Platform B"],
            ),
            ContextField(
                id="organization",
                label="Organization or tenant name",
                phase="context",
                required=True,
            ),
        ],
        questions=[
            Question(
                id="mfa-enabled",
                question="Is multi-factor authentication required?",
                expected_value="MFA is required for every remote session.",
                applies_when={"access_platform": ["Platform A"]},
                repeat_for=["access_platform"],
                finding_title="Multi-factor authentication is not consistently required",
                description="Remote access can be used without multi-factor authentication.",
                solution="Require multi-factor authentication for all remote access.",
                positive="Multi-factor authentication is required for remote access.",
                references=["https://www.cisa.gov/secure-our-world/use-strong-passwords"],
            ),
            Question(
                id="access-review",
                question="Are remote access permissions reviewed periodically?",
                expected_value="Access is reviewed at least quarterly.",
                repeat_for=["access_platform"],
                finding_title="Remote access permissions are not reviewed periodically",
                description="No recurring review of remote access permissions was confirmed.",
                solution="Establish a recurring review and retain evidence of completion.",
            ),
        ],
    )
