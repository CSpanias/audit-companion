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

Each command starts its interactive assessment and generates JSON and HTML
reports in a dedicated timestamped directory under `audit-companion/`. Add
`--output-dir reports` to choose another parent directory.

## Build the documentation

```powershell
mkdocs serve
```

To produce the static site:

```powershell
mkdocs build --strict
```
