# TextCase

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

A full-stack text-based Computer-Aided Software Engineering (CASE) tool that supports requirements management, testing, and modeling through a unified interface.

## 📜 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## ✨ Features

- [ ] Requirements management
- [ ] Test case management
- [ ] Modeling support
- [ ] Text-based interface
- [ ] Web interface
- [x] Command-line interface

## 🚀 Getting Started

### Prerequisites

- Python 3.11 or higher
- [Poetry](https://python-poetry.org/) (for dependency management)
- [pyenv](https://github.com/pyenv/pyenv) (recommended for Python version management)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/textcase.git
   cd textcase
   ```

2. **Set up Python version**
   ```bash
   pyenv install 3.11.12  # If not already installed
   pyenv local 3.11.12    # Set local Python version
   ```

3. **Install dependencies**
   ```bash
   poetry install
   ```

## 🛠 Usage

### Basic Commands

#### 1. Create a new module
Create a new module with the specified prefix and path.

```bash
# Create a new module
poetry run tse create <PREFIX> <MODULE_PATH>

# Example: Create a requirements module
poetry run tse create REQ ./reqs/

# Create a submodule with a parent reference
poetry run tse create TST ./reqs/tests --parent REQ

# Customize ID format with separator and digits
poetry run tse create REQ ./reqs/ --sep "-" --digits 4  # Creates IDs like REQ-0001
```

#### 2. Add a new document
Add a new case item to a module.

```bash
# Add a new case item with auto-generated ID
poetry run tse add <MODULE_PREFIX>

# Add a new case item with custom string name
poetry run tse add -n FOOBAR <MODULE_PREFIX>

# Add a new case item with custom numeric ID
poetry run tse add -n 3 <MODULE_PREFIX>  # Will format as 003 based on module settings
```

#### 3. Edit a document
Edit an existing document using the system editor.

```bash
# Edit a document by ID
poetry run tse edit <DOC_ID>

# Examples
poetry run tse edit REQ1     # Edit REQ001.md (with leading zeros based on module settings)
poetry run tse edit REQ001   # Edit REQ001.md directly
poetry run tse edit TST42    # Edit TST042.md in the TST module
```

#### 4. Link documents
Create links between documents.

```bash
# Link two documents (source -> target)
poetry run tse link <SOURCE> <TARGET>

# Link with a specific label
poetry run tse link <SOURCE> <TARGET> -l "related"

# Examples
poetry run tse link TST1 REQ1                # Link TST001 to REQ001 with no label
poetry run tse link TST1 REQ1 -l "verifies"  # Link with a specific label
poetry run tse link TST001 REQ001            # Link using full IDs
```

### Project Structure

A TextCase project typically follows this structure:
```
project_root/
├── .textcase.yml        # Project configuration
├── reqs/                # Requirements documents (REQ module)
│   ├── REQ001.md        # Requirement document
│   └── tests/           # Test cases (TST submodule)
│       └── TST001.md    # Test case document
└── docs/               # Documentation
```

### Document Format

TextCase uses Markdown files with YAML frontmatter for document metadata:

```markdown
---
links:
  REQ001: []      # Link with no label
  REQ002:         # Link with labels
    - "verifies"
    - "implements"
---

# TST001: Test Case Title

Test case description goes here...
```

### Advanced Usage

#### Verbose Output

Add the `-v` or `--verbose` flag to get detailed debug output:

```bash
poetry run tse -v link TST1 REQ1
```

#### Environment Variables

```bash
# Set the editor for editing documents
export EDITOR=code  # Use VS Code

# Enable direct editing (default)
export USE_DIRECT_EDIT=1
```

## 🧪 Development

### Setting up development environment

1. **Install development dependencies**
   ```bash
   poetry install --with dev
   ```

2. **Run tests**
   ```bash
   poetry run pytest
   ```

### Development tools

- **Code formatting**: `black .`
- **Import sorting**: `isort .`
- **Linting**: `flake8`
- **Type checking**: `mypy .`
- **Testing**: `pytest`

## 📝 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
