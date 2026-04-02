# Run the generate command
run:
    uv run -- orchid-ng

alias r := run

# Execute any commands
exec *args:
    uv run -- orchid-ng {{args}}

alias e := exec

# This help menu
help:
    just -l

alias h := help

# Clean up project cache files
clean:
    find ./src -name "__pycache__" -type d -exec rm -r {} +
    find ./tests -name "__pycache__" -type d -exec rm -r {} +
    rm -rf .pytest_cache .ruff_cache dist build *.egg-info

# Format the code with `ruff`
fmt:
    uv run ruff format .

# Lint the code with `ruff`
lint:
    uv run ruff check .

# Run tests with `pytest`
test:
    uv run pytest -v --maxfail=1 --disable-warnings

alias t := test

lock:
    uv lock

install:
    uv sync --all-extras --dev

build:
    uv build
