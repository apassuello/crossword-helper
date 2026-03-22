# Crossword Helper Documentation

**Welcome to the Crossword Helper documentation!** This guide helps you find the right documentation for your needs.

**Version**: 2.1.0
**Last Updated**: March 2026

> 📚 **New to the project?** Check out [../READING_LIST.md](../READING_LIST.md) for guided reading paths based on your role (user, developer, contributor).

---

## 🚀 Quick Start

### New to the Project?
**Start here →** [ARCHITECTURE.md](./ARCHITECTURE.md)
Get a high-level understanding of the system architecture, components, and data flow.

**Time**: 15-20 minutes
**Next**: [DEVELOPMENT.md](./dev/DEVELOPMENT.md) to set up your environment

### Want to Contribute?
**Start here →** [DEVELOPMENT.md](./dev/DEVELOPMENT.md)
Complete setup guide with prerequisites, installation, and your first code change.

**Time**: 30 minutes to set up, <1 hour to first contribution
**Next**: [CONTRIBUTING.md](./dev/CONTRIBUTING.md) for coding standards

### Using the API?
**Start here →** [API_REFERENCE.md](./api/API_REFERENCE.md)
Human-readable API documentation with curl examples and workflows.

**Time**: 5 minutes for quick start
**Next**: [openapi.yaml](./api/openapi.yaml) for machine-readable spec

### Writing Tests?
**Start here →** [TESTING.md](./ops/TESTING.md)
Comprehensive testing guide with examples and best practices.

**Time**: 10 minutes to understand, 2+ hours to write tests
**Next**: Run `pytest` and start testing!

---

## 📚 Documentation Structure

```
docs/
├── README.md                    # This file - Documentation navigation
├── ARCHITECTURE.md              # System architecture (start here!)
├── ROADMAP.md                   # Development roadmap and status
├── ALGORITHM_DEEP_DIVE.md       # Algorithm deep dive (CSP, beam search, scoring, matching)
├── IMPROVEMENTS.md              # Identified bugs, gaps, and implementation plan
├── NEW_FEATURES.md              # Feature proposals (heatmap, constraint viz, corpus scoring)
├── CLI_INTEGRATION_GUIDE.md     # Quick reference for backend developers
├── NEW_ENDPOINTS_DOCUMENTATION.md # Additional endpoint documentation
├── THEME_LIST_FEATURE.md        # Theme word feature guide
│
├── specs/                       # Component Specifications
│   ├── CLI_SPEC.md             # CLI tool specification
│   ├── BACKEND_SPEC.md         # Backend API specification
│   └── FRONTEND_SPEC.md        # Frontend React app specification
│
├── api/                         # API Documentation
│   ├── openapi.yaml            # OpenAPI 3.1.0 spec
│   └── API_REFERENCE.md        # Human-readable API reference
│
├── ops/                         # Operational Documentation
│   └── TESTING.md              # Testing guide (55+ examples)
│
├── dev/                         # Developer Documentation
│   ├── DEVELOPMENT.md          # Development guide
│   └── CONTRIBUTING.md         # Contribution guidelines
│
└── archive/                     # Archived Documentation
    ├── README.md               # Archive index
    ├── analysis/               # Technical analysis (15 docs)
    ├── legacy-phases/          # Historical phase docs (11 docs)
    ├── legacy-specs/           # Old specifications (15 docs)
    ├── progress/               # Progress reports (15 docs)
    └── validation-reports/     # Validation reports (3 docs)
```

---

## 🎯 Find Documentation By Need

### "I want to understand the system"
- **Overview**: [ARCHITECTURE.md](./ARCHITECTURE.md) - System architecture and design
- **Algorithms**: [ALGORITHM_DEEP_DIVE.md](./ALGORITHM_DEEP_DIVE.md) - CSP, beam search, scoring, pattern matching
- **Deep Dive**: [specs/](./specs/) - Detailed component specifications
- **Visual**: [ARCHITECTURE.md#diagrams](./ARCHITECTURE.md) - System diagrams

### "I want to set up my development environment"
1. [DEVELOPMENT.md#getting-started](./dev/DEVELOPMENT.md#getting-started) - Prerequisites and installation
2. [DEVELOPMENT.md#verification](./dev/DEVELOPMENT.md#verification) - Verify your setup
3. [CONTRIBUTING.md](./dev/CONTRIBUTING.md) - Coding standards

### "I want to use the API"
- **Quick Start**: [API_REFERENCE.md#quick-start](./api/API_REFERENCE.md#quick-start) - Your first API call
- **All Endpoints**: [API_REFERENCE.md](./api/API_REFERENCE.md) - Complete API reference
- **OpenAPI Spec**: [openapi.yaml](./api/openapi.yaml) - Machine-readable specification
- **Workflows**: [API_REFERENCE.md#complete-workflows](./api/API_REFERENCE.md#complete-workflows) - End-to-end examples

### "I want to understand the CLI tool"
- **Overview**: [specs/CLI_SPEC.md](./specs/CLI_SPEC.md) - Complete CLI documentation
- **Commands**: [specs/CLI_SPEC.md#command-reference](./specs/CLI_SPEC.md#command-reference) - All 13 commands
- **Algorithms**: [ALGORITHM_DEEP_DIVE.md](./ALGORITHM_DEEP_DIVE.md) - CSP, Beam Search, Hybrid, Iterative Repair
- **Integration**: [CLI_INTEGRATION_GUIDE.md](./CLI_INTEGRATION_GUIDE.md) - Backend↔CLI quick reference

### "I want to work on the backend"
- **Architecture**: [specs/BACKEND_SPEC.md](./specs/BACKEND_SPEC.md) - Backend design
- **API Endpoints**: [specs/BACKEND_SPEC.md#api-routes](./specs/BACKEND_SPEC.md#api-routes) - API routes
- **Additional Endpoints**: [NEW_ENDPOINTS_DOCUMENTATION.md](./NEW_ENDPOINTS_DOCUMENTATION.md) - Progress, theme, wordlist endpoints
- **CLI Integration**: [specs/BACKEND_SPEC.md#cli-adapter](./specs/BACKEND_SPEC.md#cli-adapter) - CLIAdapter pattern

### "I want to work on the frontend"
- **Architecture**: [specs/FRONTEND_SPEC.md](./specs/FRONTEND_SPEC.md) - React app design
- **Components**: [specs/FRONTEND_SPEC.md#component-hierarchy](./specs/FRONTEND_SPEC.md#component-hierarchy) - All components
- **State Management**: [specs/FRONTEND_SPEC.md#state-management](./specs/FRONTEND_SPEC.md#state-management) - State patterns

### "I want to write tests"
- **Overview**: [TESTING.md](./ops/TESTING.md) - Testing strategy
- **Examples**: [TESTING.md#unit-testing](./ops/TESTING.md#unit-testing) - 55+ test examples
- **Running Tests**: [TESTING.md#running-tests](./ops/TESTING.md#running-tests) - Command reference
- **Coverage**: [TESTING.md#code-coverage](./ops/TESTING.md#code-coverage) - Coverage goals

### "I want to add a new feature"
1. [NEW_FEATURES.md](./NEW_FEATURES.md) - Proposed features with implementation plans
2. [IMPROVEMENTS.md](./IMPROVEMENTS.md) - Known bugs and gaps to fix
3. [DEVELOPMENT.md#adding-new-features](./dev/DEVELOPMENT.md#adding-new-features) - Feature checklist
4. [CONTRIBUTING.md](./dev/CONTRIBUTING.md) - Coding standards
5. [TESTING.md](./ops/TESTING.md) - Write tests

### "I need historical context"
- **Archive**: [archive/README.md](./archive/README.md) - Historical documentation
- **Analysis**: [archive/analysis/](./archive/analysis/) - Technical research
- **Progress**: [archive/progress/](./archive/progress/) - Development history

---

## 📖 Documentation Types

### 🏗️ Architecture Documentation
**Purpose**: Understand how the system works at a high level

| Document | What It Covers | Read Time | Best For |
|----------|---------------|-----------|----------|
| [ARCHITECTURE.md](./ARCHITECTURE.md) | System design, components, data flow | 15-20 min | New developers, architects |
| [ALGORITHM_DEEP_DIVE.md](./ALGORITHM_DEEP_DIVE.md) | CSP, beam search, scoring, pattern matching | 20-30 min | Algorithm developers |
| [IMPROVEMENTS.md](./IMPROVEMENTS.md) | Known bugs, gaps, and fix plans | 15-20 min | Contributors, maintainers |
| [NEW_FEATURES.md](./NEW_FEATURES.md) | Feature proposals and implementation plans | 15-20 min | Feature planning |
| [ROADMAP.md](./ROADMAP.md) | Development plan and status | 5-10 min | Understanding project direction |

### 📋 Specification Documentation
**Purpose**: Detailed component-level documentation

| Document | What It Covers | Read Time | Best For |
|----------|---------------|-----------|----------|
| [CLI_SPEC.md](./specs/CLI_SPEC.md) | CLI commands, algorithms, data structures | 30-40 min | CLI development, algorithm work |
| [BACKEND_SPEC.md](./specs/BACKEND_SPEC.md) | API routes, CLIAdapter, error handling | 30-40 min | Backend development |
| [FRONTEND_SPEC.md](./specs/FRONTEND_SPEC.md) | React components, state, API integration | 25-35 min | Frontend development |

### 🔌 API Documentation
**Purpose**: Use or integrate with the API

| Document | What It Covers | Read Time | Best For |
|----------|---------------|-----------|----------|
| [API_REFERENCE.md](./api/API_REFERENCE.md) | All endpoints with examples | 20-30 min | API consumers, integration |
| [openapi.yaml](./api/openapi.yaml) | Machine-readable API spec | N/A | Tool integration, SDK generation |

### 🛠️ Operational Documentation
**Purpose**: Run, test, and maintain the system

| Document | What It Covers | Read Time | Best For |
|----------|---------------|-----------|----------|
| [TESTING.md](./ops/TESTING.md) | Test strategy, examples, coverage | 20-30 min | Writing tests, QA |

### 👨‍💻 Developer Documentation
**Purpose**: Set up and contribute to the project

| Document | What It Covers | Read Time | Best For |
|----------|---------------|-----------|----------|
| [DEVELOPMENT.md](./dev/DEVELOPMENT.md) | Setup, workflow, debugging | 30-40 min | New developers, onboarding |
| [CONTRIBUTING.md](./dev/CONTRIBUTING.md) | Coding standards, PR process | 10-15 min | Contributors |

---

## 🎓 Learning Paths

### Path 1: New Developer (Total: 2-3 hours)
1. Read [ARCHITECTURE.md](./ARCHITECTURE.md) - 15 min
2. Follow [DEVELOPMENT.md#getting-started](./dev/DEVELOPMENT.md#getting-started) - 30 min
3. Read [CONTRIBUTING.md](./dev/CONTRIBUTING.md) - 10 min
4. Try [DEVELOPMENT.md#common-tasks](./dev/DEVELOPMENT.md#common-tasks) - 30 min
5. Write your first test using [TESTING.md](./ops/TESTING.md) - 1 hour

**Goal**: Make your first contribution

### Path 2: Backend Developer (Total: 1.5-2 hours)
1. Read [ARCHITECTURE.md](./ARCHITECTURE.md) - 15 min
2. Read [BACKEND_SPEC.md](./specs/BACKEND_SPEC.md) - 30 min
3. Read [CLI_SPEC.md](./specs/CLI_SPEC.md) algorithms section - 15 min
4. Review [API_REFERENCE.md](./api/API_REFERENCE.md) - 20 min
5. Study [TESTING.md#backend-tests](./ops/TESTING.md) - 20 min

**Goal**: Understand backend architecture and add an endpoint

### Path 3: Frontend Developer (Total: 1.5-2 hours)
1. Read [ARCHITECTURE.md](./ARCHITECTURE.md) - 15 min
2. Read [FRONTEND_SPEC.md](./specs/FRONTEND_SPEC.md) - 30 min
3. Review [API_REFERENCE.md](./api/API_REFERENCE.md) for API integration - 20 min
4. Study component examples - 20 min
5. Set up dev environment - 15 min

**Goal**: Understand React app and add a component

### Path 4: API Consumer (Total: 45 min - 1 hour)
1. Read [ARCHITECTURE.md](./ARCHITECTURE.md) overview - 5 min
2. Follow [API_REFERENCE.md#quick-start](./api/API_REFERENCE.md#quick-start) - 10 min
3. Review [API_REFERENCE.md#core-operations](./api/API_REFERENCE.md#core-operations) - 15 min
4. Try [API_REFERENCE.md#complete-workflows](./api/API_REFERENCE.md#complete-workflows) - 15-30 min

**Goal**: Make successful API calls

### Path 5: Algorithm Developer (Total: 1.5-2 hours)
1. Read [ARCHITECTURE.md](./ARCHITECTURE.md) - 15 min
2. Read [ALGORITHM_DEEP_DIVE.md](./ALGORITHM_DEEP_DIVE.md) - 30 min (CSP, beam search, hybrid, scoring)
3. Read [IMPROVEMENTS.md](./IMPROVEMENTS.md) - 15 min (known bugs and optimization opportunities)
4. Review [CLI_SPEC.md#performance](./specs/CLI_SPEC.md#performance-characteristics) - 15 min
5. Study test examples in [TESTING.md](./ops/TESTING.md) - 20 min

**Goal**: Understand CSP/Beam Search/Hybrid and optimize

---

## 🔍 Search Tips

### Finding Information Quickly

**By Keyword**:
- Use GitHub search: `"keyword" in:docs path:docs/`
- Use grep: `grep -r "keyword" docs/`

**By Concept**:
| Looking for... | Check... |
|----------------|----------|
| Algorithms | [ALGORITHM_DEEP_DIVE.md](./ALGORITHM_DEEP_DIVE.md) or [CLI_SPEC.md#autofill-algorithms](./specs/CLI_SPEC.md#autofill-algorithms) |
| API endpoints | [API_REFERENCE.md](./api/API_REFERENCE.md) or [openapi.yaml](./api/openapi.yaml) |
| Data structures | Any SPEC.md file, search for "Data Structures" |
| Performance | [CLI_SPEC.md#performance](./specs/CLI_SPEC.md#performance-characteristics) |
| Testing | [TESTING.md](./ops/TESTING.md) |
| Code examples | Any SPEC.md file, search for code blocks |

---

## 📊 Documentation Statistics

- **Total Active Documentation**: ~25,000+ lines across 14 files
- **Archive**: 87 files preserved for historical reference
- **Code Examples**: 200+ across all documents
- **API Endpoints Documented**: 26+ (see NEW_ENDPOINTS_DOCUMENTATION.md for additional)
- **Test Examples**: 55+
- **CLI Commands**: 13
- **Autofill Algorithms**: 4 (CSP, Beam Search, Hybrid, Iterative Repair) + Adaptive wrapper
- **React Components**: 10 major components

---

## 🤝 Contributing to Documentation

Found an error or want to improve the documentation?

1. Check [CONTRIBUTING.md](./dev/CONTRIBUTING.md) for guidelines
2. Make your changes
3. Update relevant cross-references
4. Submit a pull request

**Documentation Standards**:
- Use Markdown with code syntax highlighting
- Include practical examples
- Cross-reference related sections
- Keep Table of Contents updated
- Add to this README if creating new docs

---

## ❓ Still Can't Find What You Need?

1. **Search the archive**: [archive/README.md](./archive/README.md) - Historical docs
2. **Check validation reports**: [archive/validation-reports/](./archive/validation-reports/) - Known gaps
3. **Ask the team**: Open an issue on GitHub
4. **Contribute**: Add missing documentation and submit a PR!

---

**Happy coding! 🎉**

For questions about specific files, see the individual README files in each directory.
