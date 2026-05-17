# Threat Model (Lightweight)

This document captures the primary threats for inzen-bot and the current mitigations.

## Scope

- Local CLI usage on developer machines
- Local storage under ~/.bot
- Outbound requests to model providers (Anthropic, OpenAI-compatible, Ollama, llama.cpp)
- Session/history export features

## Assets

- API keys in environment variables
- Conversation history and named session content
- Usage/cost metadata
- Exported transcripts

## Trust Boundaries

- User terminal input to bot CLI
- Bot to provider network boundary
- Bot local filesystem writes
- Bot output displayed in terminal

## Primary Threats

1. Path traversal and unsafe file writes
- Risk: reading/writing outside intended locations via crafted session names or output paths.
- Mitigations: strict session name validation, safe export path controls (default on).

2. Accidental secret disclosure
- Risk: secrets printed in history/export output or logs.
- Mitigations: optional output redaction, redacted local security log entries.

3. Unsafe provider endpoints
- Risk: insecure or untrusted base_url values.
- Mitigations: https-by-default enforcement for non-local hosts, optional host allowlist.

4. Network reliability and abuse surface
- Risk: hanging requests or excessive retries.
- Mitigations: request timeout defaults and retry caps.

5. Prompt-injection style harmful suggestions in model output
- Risk: model suggests destructive commands that users may execute.
- Mitigations: local warning guardrail on dangerous command patterns before display.

6. Corrupted local JSON state
- Risk: malformed history/session/usage files causing crashes.
- Mitigations: tolerant JSON loading with safe fallbacks and regression tests.

## Residual Risks

- Pattern-based detection can miss novel dangerous commands.
- Redaction is best-effort and may not catch every secret format.
- Users can still bypass safe defaults via explicit unsafe flags.

## Regression Test Coverage

- Traversal/session name validation tests in tests/test_config.py and tests/test_main.py.
- Malformed JSON fallback tests in tests/test_config.py.
- Hostile prompt/dangerous output warning tests in tests/test_main.py.

## Review Cadence

- Revisit this document when adding new providers, storage formats, export modes, or command execution guidance.
