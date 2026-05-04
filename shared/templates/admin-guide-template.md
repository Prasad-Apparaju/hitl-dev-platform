# Admin Guide — [Project Name]

This guide is for admin users who manage the system day-to-day. No terminal or engineering skills required for most tasks.

---

## Accessing the Admin Page

1. Log in at `http://YOUR_HOST:PORT`
2. Navigate to `/admin`
3. If you see an access denied message, your account needs admin access.

**To grant admin access:**
[Describe how — database command, API call, or another admin grants it via UI]

---

## Feature Flags

Controls global product behavior. Changes take effect immediately.

| Flag | What it does | Default | When to change |
|------|-------------|:-------:|---------------|
| [Flag name] | [One sentence — what it controls] | [On/Off] | [When/why an admin would toggle it] |

---

## Model / Provider Configuration

If the system uses AI models, this section covers how to manage them.

### Available Profiles

| Profile | Description | Cost | When to use |
|---------|-------------|:----:|------------|
| [production] | [Balanced cost/quality] | Medium | Default |
| [quality-max] | [Best models, higher cost] | High | Demos, premium |
| [budget] | [Cheapest models] | Low | Batch work, testing |

### How to Switch

1. Go to Admin → Model Profiles
2. Find the profile you want
3. Click **Activate**
4. New AI calls immediately use the new models — no restart needed

### Provider Health

| Indicator | Meaning | Action |
|:---------:|---------|--------|
| Green | Provider responding | None |
| Red | Provider unreachable | Check provider status page. System auto-recovers after 2 min. |

---

## User Management

| Task | How |
|------|-----|
| View all users | Admin → User list |
| Deactivate a user | Toggle the Active switch off (user becomes read-only) |
| Reactivate a user | Toggle the Active switch on |
| Grant admin | [Describe how] |
| Remove admin | [Describe how] |

---

## Common Admin Tasks

Write 5-10 common scenarios with the action to take. Pattern:

### "[Symptom the admin notices]"
→ [What to do]. [Why this fixes it].

### "[Another symptom]"
→ [Action].

---

## Service URLs

| Service | URL | Purpose |
|---------|-----|---------|
| Frontend | `http://HOST:3000` | Product UI |
| Admin | `http://HOST:3000/admin` | This page |
| API docs | `http://HOST:8000/docs` | API documentation |
| [Observability] | `http://HOST:3001` | [AI traces / logs / metrics] |
| [Logs] | `http://HOST:3002` | [Log dashboard] |

---

## Escalation

If you can't resolve an issue from the admin page:

1. Check the log dashboard ([Grafana/Loki URL]) for error messages
2. Check the AI trace viewer ([Langfuse URL]) for failed AI calls
3. If the issue is infrastructure (containers down, database unreachable), escalate to engineering
4. If the issue is AI quality (bad outputs, wrong tone), try switching model profiles first

---

## Writing Tips for This Guide

- **Audience:** Admin users, not engineers. Avoid terminal commands unless there's no UI alternative.
- **Format:** Task-oriented. "How do I X?" → step-by-step answer.
- **Update:** Every time a new admin feature is added, add a section here.
- **Screenshots:** Add screenshots if the UI is complex. Text descriptions are fine for simple toggles.
- **Common tasks section:** This is the most-read part. Add real scenarios from support tickets and Slack questions.
