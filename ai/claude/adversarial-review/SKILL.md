---
description: Renamed. The adversarial review became the verification review in HITL 2.11.0 — run /hitl:dev-verification-review. This command stays for one release so old habits still land, and then goes.
argument-hint: "[same arguments as /hitl:dev-verification-review]"
disable-model-invocation: true
---

# This command moved

The adversarial review was replaced by the **verification review** in HITL 2.11.0: the same
independent, clean-context reviewer, now given a checklist to run rather than a design to attack,
and asked for one page back.

Run the new command with the same arguments:

```
/hitl:dev-verification-review $ARGUMENTS
```

Nothing else changes for you. The step keys in your change file (`adv_design`, `adv_code`,
`adversarial_review`) are the same, your existing review records still pass the gate, and the
record path is still `.hitl/reviews/`.

This alias is removed in the release after 2.11.0. Update any notes or scripts that name the old
command.
