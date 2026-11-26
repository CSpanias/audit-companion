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

## Validate and run the example pack

```powershell
audit-companion validate examples\minimal.yaml
audit-companion run examples\minimal.yaml --output-dir reports
```

The current CLI works with pack files. The planned
`audit-companion mdm`, `audit-companion remote-access`, and
`audit-companion voip` commands will be added as their assessment content is
migrated.

## Build the documentation

```powershell
mkdocs serve
```

To produce the static site:

```powershell
mkdocs build --strict
```
