"""Command-line entry point."""

import argparse
from datetime import datetime
from pathlib import Path
from textwrap import dedent

from rich.panel import Panel
from rich.text import Text
from rich_argparse import RawDescriptionRichHelpFormatter

from audit_companion import __version__
from audit_companion.engine import AssessmentError, run_interview
from audit_companion.models import AssessmentPack
from audit_companion.packs import PackLoadError, load_builtin_pack
from audit_companion.reporting import export_results
from audit_companion.sureformat import SureFormatExportError, export_sureformat_xml
from audit_companion.ui import console


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="audit-companion",
        description="Run guided MDM, remote-access, or VoIP assessments.",
        formatter_class=RawDescriptionRichHelpFormatter,
        epilog=dedent("""\
            Examples:
              audit-companion mdm
              audit-companion remote-access
              audit-companion voip
        """),
    )
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)

    domain_help = {
        "mdm": "Start a guided MDM assessment",
        "remote-access": "Start a guided remote-access assessment",
        "voip": "Start a guided VoIP assessment",
    }
    for command, help_text in domain_help.items():
        _add_assessment_options(commands.add_parser(command, help=help_text))
    return parser


def _add_assessment_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("audit-companion"),
        help="Parent directory for timestamped assessment outputs",
    )
    parser.add_argument(
        "--csacyber",
        action="store_true",
        help=argparse.SUPPRESS,
    )


def main() -> None:
    args = build_parser().parse_args()
    try:
        pack: AssessmentPack = load_builtin_pack(args.command)
        _run_pack(pack, args.output_dir, args.csacyber)
    except (PackLoadError, AssessmentError, SureFormatExportError) as error:
        console.print(Text(str(error), style="red"), stderr=True)
        raise SystemExit(2) from error


def _run_pack(pack: AssessmentPack, output_dir: Path, csacyber: bool) -> None:
    results = run_interview(pack)
    run_timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    report_dir = output_dir / f"{pack.id}-{run_timestamp}"
    report_dir.mkdir(parents=True, exist_ok=False)
    xml_paths = []
    unmapped = []
    if csacyber:
        xml_paths, unmapped = export_sureformat_xml(
            results,
            pack,
            report_dir,
            _prompt_hostname,
        )
    json_path, html_path = export_results(
        results,
        report_dir,
        include_json=not csacyber,
        executive_summary=pack.executive_summary,
    )
    console.print(
        Panel.fit(
            Text(
                f"Responses: {len(results.responses)}\n"
                f"Findings: {len(results.findings)}\n"
                f"Positive observations: {len(results.positive_observations)}",
                style="green",
            ),
            title="Assessment Complete",
            border_style="green",
        )
    )
    console.print(Text(f"Output directory: {report_dir}", style="cyan"))
    if json_path:
        console.print(Text(f"JSON: {json_path}", style="cyan"))
    console.print(Text(f"HTML: {html_path}", style="cyan"))
    for xml_path in xml_paths:
        console.print(Text(f"XML: {xml_path}", style="cyan"))
    if unmapped:
        console.print(
            Text(
                "Findings without SureFormat mappings were omitted: "
                + ", ".join(unmapped),
                style="yellow",
            )
        )


def _prompt_hostname(scope: dict[str, str]) -> str:
    scope_description = (
        " for " + ", ".join(f"{field_id}={value}" for field_id, value in scope.items())
        if scope
        else ""
    )
    while True:
        hostname = console.input(f"SureCloud hostname{scope_description}: ").strip()
        if hostname:
            return hostname
        console.print(Text("Hostname is required.", style="red"))


if __name__ == "__main__":
    main()
