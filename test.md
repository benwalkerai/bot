# Manual Test Plan — inzen-bot

Run through each section before tagging and publishing a new release. Tick each item as you go.

> **Pre-requisite:** `ANTHROPIC_API_KEY` is set in your environment and `bot` is installed (`uv pip install -e .` or the published package).

---

## 1. One-shot queries

- [ ] `bot hello` — receives a response, no errors
- [ ] `bot what is the ls command` — response contains a code block
- [ ] `bot step 2?` — response continues from previous context (history is working)
- [ ] `bot --provider openai hello` — uses OpenAI for this query (requires `OPENAI_API_KEY`)
- [ ] `bot --provider ollama hello` — uses Ollama (requires local Ollama running)

---

## 2. Provider and model management

- [ ] `bot --providers` — lists anthropic, openai, ollama, llamacpp with current default marked
- [ ] `bot --set-provider openai` — prints confirmation; `bot --providers` now shows openai as default
- [ ] `bot --set-provider anthropic` — restores anthropic as default
- [ ] `bot --set-model claude-haiku-4-5` — prints confirmation; model appears in `~/.bot/config.json`
- [ ] `bot --set-provider nonexistent` — exits with error and lists valid providers

---

## 3. Conversation history

- [ ] `bot hello` then `bot what did I just say?` — assistant references the previous message
- [ ] `bot --history` — prints the conversation history with USER/ASSISTANT labels
- [ ] `bot --clear` — prints confirmation; `bot --history` now shows no history
- [ ] `bot --history` after clear — shows "No history" message

---

## 4. Named sessions

- [ ] `bot --session work what is docker` — receives a response
- [ ] `bot --session work what did I just ask?` — assistant references docker question
- [ ] `bot --sessions` — lists the `work` session with message count, provider, and first message preview
- [ ] `bot --session personal hello` — creates a separate session, does not bleed context from `work`
- [ ] `bot --sessions` — shows both `work` and `personal`
- [ ] `bot --clear-session personal` — prints confirmation; `bot --sessions` no longer shows `personal`

---

## 5. System prompt override

- [ ] `bot --system "You are a pirate" hello` — response is in pirate style
- [ ] `bot hello` immediately after — response reverts to default assistant style (override was not persisted)

---

## 6. Session export

- [ ] `bot --export work` — prints markdown to stdout with session name, provider, and messages
- [ ] `bot --export work --format text` — prints plain text with USER/ASSISTANT labels
- [ ] `bot --export work --output /tmp/work.md` — creates file; `cat /tmp/work.md` shows the markdown
- [ ] `bot --export nonexistent` — exits with error "No session named..."
- [ ] `bot --clear-session work` then `bot --export work` — shows "session is empty" or error

---

## 7. Token/cost usage tracking

- [ ] `bot hello` — usage footer is printed under the response (e.g. `↑ 42 in · ↓ 183 out · ~$0.0001`)
- [ ] `bot --usage` — shows a table with input/output token counts and estimated cost for anthropic
- [ ] `bot --provider openai hello` then `bot --usage` — shows usage for both anthropic and openai rows

---

## 8. Interactive chat mode

- [ ] `bot --chat` — shows "Interactive mode" banner with hint text; `You:` prompt appears
- [ ] Type a message and press Enter — streams a response, then `You:` prompt returns
- [ ] Type a follow-up message — response references prior context (history preserved within session)
- [ ] `/help` — prints the command table listing `/history`, `/clear`, `/exit`
- [ ] `/history` — prints all messages exchanged so far in the current chat
- [ ] `/clear` — prints "History cleared"; `/history` immediately after shows no messages
- [ ] `/exit` — exits cleanly with code 0
- [ ] `/quit` — exits cleanly with code 0
- [ ] `q` — exits cleanly with code 0
- [ ] Press `Ctrl+C` at the `You:` prompt — exits with "Interrupted" message and code 0
- [ ] `bot --chat explain what a venv is` — first message is sent automatically, then REPL continues
- [ ] `bot --session myproject --chat` — loads existing session history; new turns are saved to `myproject`
- [ ] `bot --system "You are concise" --chat` — override applies for the whole session

---

## 9. Help and edge cases

- [ ] `bot --help` — prints full help text with all flags
- [ ] `bot` (no arguments, no flags) — prints usage hint and exits with code 0
- [ ] `bot --set-provider ollama` then `bot hello` with Ollama not running — shows a clear connection error, not a crash
