# Contributing to MT4 Docker

Thank you for your interest in contributing to MT4 Docker! This document provides guidelines and instructions for contributing.

## Code of Conduct

Please be respectful and constructive in all interactions. We aim to maintain a welcoming environment for all contributors.

## How to Contribute

### Reporting Issues

1. Check existing issues to avoid duplicates
2. Use the issue template when available
3. Provide clear reproduction steps
4. Include system information (OS, Docker version)
5. Attach relevant logs if applicable

### Submitting Pull Requests

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Make your changes
4. Run tests (`./run_tests.sh all`)
5. Commit with clear messages
6. Push to your fork
7. Open a pull request

### Development Setup

```bash
# Clone repository
git clone https://github.com/yourusername/mt4-docker.git
cd mt4-docker

# Install development dependencies
# Ensure Docker is installed and running

# Run tests
chmod +x run_tests.sh
./run_tests.sh all
```

## Testing

### Running Tests

```bash
# Run all tests
./run_tests.sh all

# Run unit tests only
./run_tests.sh unit

# Run integration tests only
./run_tests.sh integration

# Run with verbose output
./run_tests.sh all verbose
```

### Writing Tests

- Unit tests go in `tests/unit/`
- Integration tests go in `tests/integration/`
- Follow existing test patterns
- Use the test framework assertions
- Ensure tests are idempotent

Example test:

```bash
test_my_feature() {
    # Arrange
    local input="test data"
    
    # Act
    local result=$(my_function "$input")
    
    # Assert
    assert_equals "expected" "$result" "my_function should return expected"
}
```

## Code Style

### Shell Scripts

- Use `#!/bin/bash` shebang
- Follow [Google Shell Style Guide](https://google.github.io/styleguide/shellguide.html)
- Use meaningful variable names
- Add error handling with `set -e`
- Quote variables: `"$var"` not `$var`
- Use `[[ ]]` for conditionals

### Docker

- Keep images minimal
- Use specific version tags
- Order Dockerfile commands for cache efficiency
- Document exposed ports and volumes
- Use multi-stage builds when appropriate

### Documentation

- Update README.md for user-facing changes
- Update technical docs for implementation changes
- Use clear, concise language
- Include examples where helpful
- Keep documentation in sync with code

## Commit Messages

Follow conventional commit format:

```
type(scope): subject

body

footer
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Test additions or changes
- `chore`: Build process or auxiliary tool changes

Example:
```
feat(ea): add support for custom EA parameters

- Allow users to pass parameters to EAs via environment variables
- Update deploy_ea.sh to handle parameter files
- Add documentation for parameter configuration

Closes #123
```

## Release Process

1. Update version in relevant files
2. Update CHANGELOG.md
3. Run full test suite
4. Create git tag: `git tag -a v1.0.0 -m "Release v1.0.0"`
5. Push tag: `git push origin v1.0.0`
6. GitHub Actions will create release

## Security

- Never commit credentials or secrets
- Use environment variables for sensitive data
- Report security issues privately to maintainers
- Follow principle of least privilege

## Questions?

Feel free to open an issue for questions or discussions about contributing.