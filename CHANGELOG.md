# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Comprehensive testing framework with unit and integration tests
- CI/CD pipeline with GitHub Actions
- Automated security scanning with Trivy
- Shell script linting with ShellCheck
- Test runner script with coverage reporting
- Contributing guidelines
- Release automation workflow

### Changed
- Restructured project directory for better organization
- Improved error handling in all scripts
- Enhanced documentation with testing instructions

### Security
- Added VNC password protection
- Implemented resource limits for containers
- Added security scanning in CI pipeline

## [1.0.0] - 2024-01-29

### Added
- Initial release of MT4 Docker
- Docker container for running MetaTrader 4 on Linux
- VNC access for GUI interaction
- Automated EA compilation and deployment
- Comprehensive documentation
- Quick start scripts
- Monitoring and logging capabilities
- Support for headless EA deployment
- Environment-based configuration

### Security
- Secure credential management with .env files
- VNC password protection
- Docker resource limits

### Documentation
- Setup guide
- Troubleshooting guide
- VNC connection guide
- Demo MT4 terminal guide