# Changelog

All notable changes to inzen-bot are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.4] - 2026-05-20

### Features

- Enhance security features and improve export functionality

### Security

- Pin transitive `idna` to `>=3.15` to address the ReDoS advisory in older `idna` versions.

### CI

- Build Windows and Linux installers automatically on `main` and pull requests.
- Publish Windows and Linux installer artifacts to GitHub Releases on version tags.

### Miscellaneous

- Bump pytest from 9.0.2 to 9.0.3 (#11)

## [0.3.0] - 2026-04-27

### Documentation

- Add contributing guidelines and release process to README

### Features

- Implement usage tracking and export functionality; update roadmap
- Add interactive chat mode with slash commands
- Add interactive mode, security hardening, and docs

### Miscellaneous

- Add changelog generation and automatic version bumping
- Bump version to 0.3.0

## [0.2.1] - 2026-04-11

### Documentation

- Update README and add ROADMAP

## [0.2.0] - 2026-04-11

### Dependencies

- Bump cryptography from 46.0.6 to 46.0.7 (#10)
- Bump anthropic from 0.86.0 to 0.87.0 (#9)
- Bump pygments from 2.19.2 to 2.20.0 (#8)

### Documentation

- Add contributing guidelines for inzen-bot

### Features

- Add test suite - all passing
- Add .env.example file with environment variable setup instructions
- Implement session management with save, load, and clear functionality
- Add session management tests and CI workflow for PyPI publishing

### Miscellaneous

- Update version to 0.1.1 and change license to GPL-3.0-or-later
- Bump version to 0.2.0


