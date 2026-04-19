# Security Policy

## Reporting Vulnerabilities

**Do not open a public GitHub issue for security vulnerabilities.**

Instead, email **prasad.apparaju@gmail.com** with:

- A description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if you have one)

You will receive an acknowledgment within 72 hours and a detailed response within one week.

## Supported Versions

| Version | Supported |
|---------|-----------|
| `main` branch (latest) | Yes |
| Older commits / tags | Best effort |

This is an early-stage project without formal releases yet. Security fixes are applied to the `main` branch.

## Scope

This repository contains process documentation, templates, skills (Claude Code commands), and lightweight tooling (Python scripts, CI workflows). It does not include production application code.

Security concerns most relevant to this repo:

- **CI workflow injection** -- malicious input to convention checker or manifest generator
- **Template injection** -- templates that could produce unsafe code when filled in by AI
- **Skill prompt injection** -- skill definitions that could be manipulated to bypass safety checks

## AI-Generated Code Review Requirements

This project's workflow requires that all AI-generated code be reviewed by a human before merging. The convention checker and CI actions enforce structural checks, but security review of generated code is a human responsibility.

If you discover a case where the process allows unsafe AI-generated code to bypass review, please report it using the process above.

## Disclosure Policy

Once a fix is available, the vulnerability will be disclosed in the repository's commit history with a clear description. Critical issues may also be noted in the README or changelog.
