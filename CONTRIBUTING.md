# Contributing to SentinelOracle

Thank you for your interest in improving SentinelOracle!

## Development Guidelines

1. **Deterministic Logic:** Always ensure that methods handling state updates strictly avoid non-deterministic Python built-ins unless executed within `gl.nondet` handlers.
2. **Schema Integrity:** Any modifications to resolution objects must be reflected in `_verify_schema`.
3. **Submitting Changes:**
   * Fork the repository.
   * Create a feature branch (`git checkout -b feature/improvement`).
   * Commit your changes with concise messages.
   * Open a Pull Request detailing the bug fix or feature added.
