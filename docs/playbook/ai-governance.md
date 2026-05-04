# AI Governance

Guardrails for using AI in the development process. These are not bureaucracy — they exist because AI tools introduce new categories of risk that traditional development processes do not cover.

---

## What AI Can Access

**Allowed:** repository code, project documentation, public APIs, public package registries, tool output from sanctioned integrations.

**Not allowed:** production databases, customer PII, credentials or secrets, internal systems not explicitly approved for AI access. If you are unsure whether a data source is approved, it is not.

---

## Data Handling

- **No secrets in prompts.** Never paste API keys, tokens, passwords, or connection strings into an AI prompt or chat session.
- **No PII in AI traces without redaction.** If observability tooling (Langfuse, OTEL) captures AI interactions, PII must be redacted before it reaches the trace store. Use the redaction utilities in the observability layer.
- **No proprietary code shared with external AI providers without approval.** If you are using a third-party AI service (not self-hosted), confirm that the provider's data retention and training policies are acceptable before sending proprietary code. When in doubt, ask.

---

## Secrets Protection

- `.env` files are gitignored. Always.
- Secrets live in a vault or secret manager (e.g., GCP Secret Manager, HashiCorp Vault), never in source code, commit messages, or AI prompts.
- If a secret accidentally appears in a prompt or commit, rotate it immediately. Treat it as compromised.

---

## Generated Code Ownership

All AI-generated code is:

1. **Reviewed by a human** before merge. AI proposes; humans decide.
2. **Committed under the developer's name** with a `Co-Authored-By` trailer identifying the AI tool. The developer owns the code — legally, operationally, and in terms of accountability.
3. **Subject to the same standards** as hand-written code: convention checks, test coverage, code review, LLD adherence.

The `Co-Authored-By` trailer is not optional. It provides an audit trail showing which code had AI involvement.

---

## Model Retention

AI providers may retain prompts and completions per their terms of service. Be aware of:

- [Anthropic usage policy](https://www.anthropic.com/policies)
- [OpenAI data usage policy](https://openai.com/enterprise-privacy)
- [Google AI terms](https://ai.google.dev/terms)

Review the applicable provider policy before sending sensitive (but non-secret) project context. Self-hosted models (vLLM, Ollama) do not have this concern.

---

## Prompt Injection

Treat AI tool results as untrusted input. Specifically:

- If an AI tool parses external content (user uploads, web pages, API responses), the content may contain prompt injection attempts.
- Flag and review any AI output that contains unexpected instructions, attempts to modify system behavior, or references to actions the AI was not asked to perform.
- Do not auto-execute AI-suggested shell commands without reading them first.

---

## Supply Chain Risk

AI-suggested dependencies (packages, libraries, frameworks) must be reviewed before adoption:

- **License compatibility** — is the license compatible with the project?
- **Maintenance status** — is the package actively maintained? When was the last release?
- **Security history** — are there known vulnerabilities? Check advisory databases.
- **Popularity and trust** — is this a well-known package, or could it be a typosquat or malicious package?

AI models are trained on a snapshot of the ecosystem. They may suggest packages that are deprecated, renamed, or compromised after the training cutoff.

---

## Audit Trail

Every AI-assisted change must have:

1. A `Co-Authored-By` trailer in the commit message identifying the AI tool and model.
2. A link to a GitHub issue that describes why the change was made.

This is enforced by the development workflow (see [dev-practices](../../ai/dev-practices/SKILL.md)). The combination of issue linkage and co-author trailer makes it possible to trace any line of code back to the decision that produced it and know whether AI was involved.
