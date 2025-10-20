# Contributing to shared-call-py

## Getting Started

- **Clone the repo**
  ```bash
  git clone https://github.com/SohamRatnaparkhi/shared-call-py.git
  cd shared-call-py
  ```
- **Install Poetry** (https://python-poetry.org/docs/#installation)
- **Install dependencies**
  ```bash
  poetry install
  ```
- **Activate the virtualenv**
  ```bash
  poetry shell
  ```

## Development Workflow

- **Run tests with coverage (src only)**
  ```bash
  poetry run pytest
  ```
- **Lint and format**
  ```bash
  poetry run ruff check .
  poetry run black src tests
  ```
- **Type check**
  ```bash
  poetry run mypy src
  ```

## Submitting Changes

- **Create a feature branch**
  ```bash
  git checkout -b feat/your-feature
  ```
- **Commit using clear messages**
  ```bash
  git commit -m "feat: add amazing thing"
  ```
- **Run the full test suite before opening a PR**
- **Open a pull request** describing the problem, solution, and any additional context.
