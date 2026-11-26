"""Command-line entry point."""

import argparse
from importlib.resources import as_file, files
from pathlib import Path
from textwrap import dedent
from typing import Literal

from rich.panel import Panel
from rich.text import Text
from rich_argparse import RawDescriptionRichHelpFormatter

from audit_companion import __version__
from audit_companion.engine import AssessmentError, run_interview
from audit_companion.models import AssessmentPack
from audit_companion.packs import PackLoadError, load_pack
from audit_companion.reporting import export_results
from audit_companion.sureformat import SureFormatExportError, export_sureformat_xml
from audit_companion.ui import console

BuiltinPack = Literal["mdm", "remote-access", "voip"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="audit-companion",
        description="Run guided, pack-driven security assessments.",
        formatter_class=RawDescriptionRichHelpFormatter,
        epilog=dedent("""\
            Examples:
              audit-companion mdm
              audit-companion remote-access
              audit-companion voip
              audit-companion validate examples/minimal.yaml
              audit-companion run examples/minimal.yaml --output-dir reports
        """),
    )
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)

    run_parser = commands.add_parser("run", help="Run a custom assessment pack")
    run_parser.add_argument("pack", type=Path, help="Path to a YAML assessment pack")
    _add_run_options(run_parser)

    validate_parser = commands.add_parser(
        "validate",
        help="Validate an assessment pack",
    )
    validate_parser.add_argument("pack", type=Path, help="Path to a YAML assessment pack")

    domain_help = {
        "mdm": "Start a guided MDM assessment",
        "remote-access": "Start a guided remote-access assessment",
        "voip": "Start a guided VoIP assessment",
    }
    for command, help_text in domain_help.items():
        _add_run_options(commands.add_parser(command, help=help_text))
    return parser


def load_builtin_pack(pack_id: BuiltinPack) -> AssessmentPack:
    resource = files("audit_companion").joinpath(
        "data",
        "packs",
        f"{pack_id}.yaml",
    )
    with as_file(resource) as pack_path:
        return load_pack(pack_path)


def _add_run_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("."),
        help="Directory for assessment reports (default: current directory)",
    )
    parser.add_argument(
        "--csacyber",
        action="store_true",
        help=argparse.SUPPRESS,
    )


def main() -> None:
    args = build_parser().parse_args()
    try:
        if args.command in {"mdm", "remote-access", "voip"}:
            pack = load_builtin_pack(args.command)
        else:
            pack = load_pack(args.pack)

        if args.command == "validate":
            console.print(Text(f"Valid assessment pack: {pack.id} - {pack.title}", style="green"))
            return

        _run_pack(pack, args.output_dir, args.csacyber)
    except (PackLoadError, AssessmentError, SureFormatExportError) as error:
        console.print(Text(str(error), style="red"), stderr=True)
        raise SystemExit(2) from error


def _run_pack(pack: AssessmentPack, output_dir: Path, csacyber: bool) -> None:
    results = run_interview(pack)
    xml_paths = []
    unmapped = []
    if csacyber:
        xml_paths, unmapped = export_sureformat_xml(
            results,
            pack,
            output_dir,
            _prompt_hostname,
        )
    json_path, markdown_path, html_path = export_results(
        results,
        output_dir,
        include_json=not csacyber,
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
    if json_path:
        console.print(Text(f"JSON: {json_path}", style="cyan"))
    console.print(Text(f"Markdown: {markdown_path}", style="cyan"))
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
