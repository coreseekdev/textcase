# TextCase

A full-stack text-based Computer-Aided Software Engineering (CASE) tool that supports requirements management, testing, and modeling through a unified interface.

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

### Running the application

```bash
# Using poetry
poetry run tse

# Or after activating the virtual environment
poetry shell
tse
```

### Expected output
```
Hello, World!
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

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
