# Changelog

All notable changes to inzen-bot are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.6] - 2026-05-21

### CI/CD

- Enforce tag/version match and publish only windows installer

## [0.3.5] - 2026-05-20

### Bug Fixes

- Include all Windows executables in release asset upload

## [0.3.4] - 2026-05-20

### Release

- V0.3.4

## [0.3.3] - 2026-05-20

### Features

- Add Inzen CLI Bot with credential management and setup wizard

### Miscellaneous

- Add Output/ to .gitignore (generated installer binary)
- Bump version to 0.3.3

### Refactoring

- Rename app to Inzen CLI Bot, keep bot as CLI command

## [0.3.2] - 2026-05-18

### Dependencies

- Upgrade urllib3 to 2.7.0 in lockfile

### Miscellaneous

- Bump version to 0.3.2

## [0.3.1] - 2026-05-18

### Features

- Enhance security features and improve export functionality

### Miscellaneous

- Bump pytest from 9.0.2 to 9.0.3 (#11)
- Prep release for security enhancements
- Bump version to 0.3.1

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


