# python-project-template

[kr-한국어](README.md) | **[en-English]**

A standardized Python project template with minimal configuration, integrating essential tools like `black`, `isort`, `mypy`, and `pylint` with `tox` for code formatting, linting, and type checking. This template simplifies the development workflow by including all necessary settings.

---

## Purpose

This template aims to reduce the hassle of setting up a new Python project every time and helps maintain consistent code style and quality by providing:

- Code formatter: **black**
- Import organizer: **isort**
- Type checker: **mypy**
- Code linter: **pylint**
- Integrated test and lint automation tool: **tox**

With `tox`, you can easily run the above tools and test across multiple Python versions with the default environment setup.

---

## Main Configuration Files

- `tox.ini`  
  Defines environments for running various lint, format, and type check tools individually or all at once.  
  Designed to allow running all check tools with a single `tox` command or selecting specific tools as needed.

- `pyproject.toml`  
  Centralizes configuration for major tools like `black`, `isort`, `mypy`, and `pylint`.  
  Maintains consistent style and rules, and supports convenient tool configuration.

---

## How to Use

### 1. Create a Template Repository

- Use [python-project-template](https://github.com/yourusername/python-project-template) repository as a template on GitHub  
- Click the "Use this template" button to create a new project and clone it

---

### 2. Install Dependencies

After creating and activating a Python virtual environment in the project root:

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate    # Windows PowerShell

pip install --upgrade pip setuptools wheel
pip install tox
```

---

### 3. Run Check Tools

- **Run all check tools (black, isort, mypy, pylint):**

  ```bash
  tox
  ```

- **Run individual tools (examples):**

  ```bash
  tox -e black    # Code formatting (black)
  tox -e isort    # Import sorting (isort)
  tox -e mypy     # Type checking (mypy)
  tox -e pylint   # Code linting (pylint)
  tox -e lint     # Shortcut for running only pylint
  ```

### 4. Customize Settings

- Modify options for each tool in the `[tool.black]`, `[tool.isort]`, `[tool.mypy]`, `[tool.pylint]` sections of `pyproject.toml`.
- If needed, adjust target paths or environment variables in `tox.ini`.

---

## Recommended Workflow

1. After coding, run `tox -e black` and `tox -e isort` to format code style and organize imports
2. Run `tox -e mypy` to check for type errors
3. Run `tox -e pylint` to check code quality and potential issues
4. Finally, run the `tox` command to perform all checks at once

---

## Additional References

- Python Official Style Guide: [PEP 8](https://pep8.org/)
- `tox` Official Documentation: [https://tox.readthedocs.io/](https://tox.readthedocs.io/)
- Detailed options and usage can be found on each tool's official site

---

## Contributing

We welcome contributions from all developers!
You can participate in various ways, such as reporting bugs, suggesting features, or improving the code.
For detailed instructions on how to contribute, please refer to the [Contributing](./CONTRIBUTING.en.md) Guide.

---

## 📝 License

[MIT License](LICENSE)
