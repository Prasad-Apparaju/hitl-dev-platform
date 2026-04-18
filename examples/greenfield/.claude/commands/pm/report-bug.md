# Report a Bug

**Input:** $ARGUMENTS (description of the bug)

If `$ARGUMENTS` is empty, ask: "What went wrong? Describe what you did, what you expected, and what actually happened."

---

## Steps

1. **Gather details** from the user:
   - What page/feature were you using?
   - What did you do (steps to reproduce)?
   - What did you expect to happen?
   - What actually happened?
   - URL, screenshot path, or error message (if available)

2. **Check if a similar issue exists:**
   ```bash
   gh issue list --search "<keywords>" --state open
   ```
   If a duplicate exists, tell the user and link to it instead of creating a new one.

3. **Create the GitHub issue:**
   ```bash
   gh issue create --title "fix: <short description>" --body "<structured body>"
   ```

   Issue body format:
   ```
   ## Bug Report

   **Page/Feature:** <where it happened>
   **Steps to reproduce:**
   1. <step>
   2. <step>

   **Expected:** <what should have happened>
   **Actual:** <what happened instead>

   **Environment:** http://34.60.225.241:3000 (alpha deployment)
   **Additional context:** <error messages, screenshots, URLs>
   ```

4. **Return the issue URL** to the user.

## Important Rules

- Always check for duplicates before creating
- Keep the title short and descriptive — starts with "fix:"
- Include reproduction steps — "it's broken" is not actionable
