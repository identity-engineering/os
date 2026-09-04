# Contributing to IE OS (Open Core)

Thank you for considering a contribution.

## Scope

This repository is the **Open Core** of Identity Engineering OS:

- Schemas and contracts
- Local Surface Runtime
- Free-tier CLI and templates
- Documentation of the geometric + ownership model

Managed Pro features live elsewhere and are out of scope here.

## Principles for contributions

1. **Framework-grounded**  
   Every change must remain consistent with the core primitives (Mass, Curvature, Gravitation, Rotation, Frequency, Relativity, Identity Stem, Causal Entropic Forces, Questions as Probes, Ownership as relative degrees of freedom). See the public Framework and `docs/principles.md`.

2. **Local-first and Privacy by design**  
   Do not introduce mandatory cloud dependencies into the Free path.

3. **Small, reviewable PRs**  
   Prefer focused changes. Large architectural moves should be discussed first (open an issue).

4. **Tests**  
   Behavioural changes to the runtime or CLI should come with tests.

## Development

Install the package with its development dependencies in editable mode:

```bash
python -m pip install -e ".[dev]"
```

Run the test suite with:

```bash
pytest
```

## Process

1. Open an issue for non-trivial ideas (especially anything that touches schemas or Ownership defaults).
2. Fork or branch from `main`.
3. Keep commits focused.
4. Open a pull request against `main`. Describe the geometric intent, not only the code change.
5. Maintainers review for consistency with the Open Core boundary and the Framework.

## License

By contributing you agree that your contributions are licensed under the MIT License of this repository.
