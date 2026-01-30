# LurkBot Documentation

This directory contains the official documentation for LurkBot.

## Documentation Structure

```
docs/
├── index.md                    # Documentation home page
├── getting-started/            # Installation and quick start guides
├── user-guide/                 # User-facing documentation
│   ├── cli/                    # CLI usage guides
│   ├── channels/               # Channel configuration
│   ├── agents/                 # Agent configuration
│   ├── tools/                  # Tool usage
│   └── configuration/          # Configuration reference
├── advanced/                   # Advanced features
├── developer/                  # Developer documentation
├── api/                        # API reference
├── reference/                  # Complete reference manuals
├── troubleshooting/            # FAQ and debugging
└── design/                     # Internal design documents
```

## Building the Documentation

The documentation is built using [MkDocs](https://www.mkdocs.org/) with the [Material theme](https://squidfunk.github.io/mkdocs-material/).

### Prerequisites

```bash
pip install mkdocs-material
```

### Local Development

```bash
# Serve documentation locally
mkdocs serve

# Build static site
mkdocs build
```

### Deployment

Documentation is automatically deployed to GitHub Pages when changes are pushed to the `main` branch.

## Contributing to Documentation

1. Follow the existing structure and style
2. Use clear, concise language
3. Include code examples where appropriate
4. Test all code examples before submitting
5. Update the navigation in `mkdocs.yml` if adding new pages

## Documentation Standards

- **Language**: English for user-facing docs, Chinese for internal design docs
- **Format**: GitHub-flavored Markdown
- **Code blocks**: Always specify the language
- **Links**: Use relative paths for internal links

## License

Documentation is released under the same MIT License as the LurkBot project.
