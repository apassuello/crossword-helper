# Crossword Construction Helper

A Flask-based web application that assists crossword puzzle constructors with pattern matching, grid numbering validation, and convention normalization.

## Features

- **Pattern Matching**: Find words matching specific patterns with wildcards and known letters
- **Numbering Validation**: Validate and generate crossword grid numbering schemes
- **Convention Normalization**: Normalize crossword entries according to publication standards

## Quick Start

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd crossword-helper
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

### Running the Application

Start the development server:
```bash
python run.py
```

The application will be available at `http://localhost:5000`

## Project Structure

```
crossword-helper/
├── backend/              # Backend Python code
│   ├── core/            # Core business logic
│   ├── api/             # REST API routes
│   └── data/            # Data access layer
├── frontend/            # Frontend assets
│   ├── static/          # CSS and JavaScript
│   └── templates/       # HTML templates
├── tests/               # Test suite
│   ├── unit/           # Unit tests
│   └── integration/    # Integration tests
├── data/                # Wordlist data files
└── docs/                # Documentation

## Development Commands

### Run Tests
```bash
pytest
```

### Run Tests with Coverage
```bash
pytest --cov=backend --cov-report=html
```

### Run Development Server
```bash
python run.py
```

## Contributing

This project is under active development. Architecture documentation will be added to the `docs/` directory.

## License

TBD
