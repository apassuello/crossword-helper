# Documentation

## Active Documentation

```
docs/
├── README.md                # This file
├── ARCHITECTURE.md          # System architecture and design
├── ALGORITHM_DEEP_DIVE.md   # Algorithm details (CSP, beam search, scoring)
├── user-guide/              # Guide for people using the web app (tutorial, how-tos, reference)
│   └── site/                # The same guide as HTML, built by scripts/build_user_guide.py
├── api/
│   ├── API_REFERENCE.md     # HTTP API reference
│   └── openapi.yaml         # OpenAPI 3.1.0 spec
├── specs/
│   └── CLI_SPEC.md          # CLI specification
├── ops/
│   └── TESTING.md           # Testing guide
├── dev/
│   ├── DEVELOPMENT.md       # Developer setup and workflow
│   └── FABRICATION-LOG.md   # Claims found false against code; unaudited backlog
├── superpowers/
│   ├── specs/               # Design specs for in-flight capability families
│   └── plans/               # Per-task implementation plans behind those specs
├── screenshots/             # UI captures referenced from other docs
└── resources/
    ├── SOURCES.md           # Index of the research reports below, cited by row id
    ├── research/            # Verbatim run-A/B/C/R reports: claims, evidence, manifests
    └── art-of-construction.pdf  # Reference: The Art of Crossword Construction
```

## Where to Start

- **Use the app to build crosswords**: [user-guide/README.md](./user-guide/README.md)
- **Understand the system**: [ARCHITECTURE.md](./ARCHITECTURE.md)
- **Set up for development**: [dev/DEVELOPMENT.md](./dev/DEVELOPMENT.md)
- **Use the API**: [api/API_REFERENCE.md](./api/API_REFERENCE.md)
- **Use the CLI**: [specs/CLI_SPEC.md](./specs/CLI_SPEC.md)
- **Understand algorithms**: [ALGORITHM_DEEP_DIVE.md](./ALGORITHM_DEEP_DIVE.md)
- **Write tests**: [ops/TESTING.md](./ops/TESTING.md)
- **Contribute**: [../CONTRIBUTING.md](../CONTRIBUTING.md)
- **Check what documentation to trust**: [dev/FABRICATION-LOG.md](./dev/FABRICATION-LOG.md)
- **Follow in-flight design work**: [superpowers/specs/](./superpowers/specs/) for the specs;
  finished plans are in [archive/completed-plans/](./archive/completed-plans/), and a plans
  directory beside the specs exists only while one is in flight
- **Cite the research**: [resources/SOURCES.md](./resources/SOURCES.md) is the index; cite its row
  ids rather than the reports directly
- **Reference**: [resources/art-of-construction.pdf](./resources/art-of-construction.pdf)

## Archived Documentation

Historical docs (session notes, old specs, progress reports) are in [archive/](./archive/) and [../.archive/docs/](../.archive/docs/).
