# Contributing to bfast-llm

First of all, thank you for taking the time to contribute to `bfast-llm`! 

Here are some guidelines to help you get started.

---

## 🛠️ Development Setup

We use [uv](https://github.com/astral-sh/uv) to manage project dependencies and virtual environments.

1. **Clone the repository**:
   ```bash
   git clone https://github.com/marcelomarkus/bfast-llm.git
   cd bfast-llm
   ```

2. **Install development dependencies**:
   ```bash
   uv sync --all-extras
   ```

3. **Activate the virtual environment**:
   ```bash
   source .venv/bin/activate
   ```

---

## 🧪 Running Tests & Checks

Before submitting a Pull Request, please ensure all tests and linting checks pass:

1. **Run tests**:
   ```bash
   uv run pytest -v
   ```

2. **Check formatting (Black)**:
   ```bash
   uv run black --check .
   ```

3. **Check lints (Ruff)**:
   ```bash
   uv run ruff check .
   ```

---

## 📝 Pull Request Guidelines

* Create a feature or fix branch from `main` (e.g., `feat/my-awesome-feature` or `fix/issue-123`).
* Write clear, self-contained unit tests inside the `tests/` directory for any new logic.
* Ensure code coverage remains high.
* Document any changes in the appropriate docs (`docs/` and `docs/pt/docs/`).
