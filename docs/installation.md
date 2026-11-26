# Installation

## Development setup

Audit Companion is under active development. To install the source and its
documentation tooling with `uv`:

```powershell
uv sync --extra dev --extra docs
```

Or with Python's built-in virtual environment:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev,docs]"
```

The package requires Python 3.11 or later.

## Start an assessment

```powershell
audit-companion mdm
audit-companion remote-access
audit-companion voip
```

Each command starts its interactive assessment and generates JSON, Markdown,
and HTML reports. Add `--output-dir reports` to write the reports elsewhere.

To try the pack format with a custom assessment:

```powershell
audit-companion validate examples\minimal.yaml
audit-companion run examples\minimal.yaml --output-dir reports
```

## Build the documentation

```powershell
mkdocs serve
```

To produce the static site:

```powershell
mkdocs build --strict
```
