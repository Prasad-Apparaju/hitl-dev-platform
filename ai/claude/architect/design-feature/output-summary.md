## Output Summary — Design Feature

Present this completion summary after all packets are approved:

```
┌─────────────────────────────────────────────────┐
│ DESIGN COMPLETE — GH-<N>: [title]               │
├─────────────────────────────────────────────────┤
│ Tier: N  |  Slices: M  |  Est. effort: N days   │
├─────────────────────────────────────────────────┤
│ ARTIFACTS                                       │
│  HLD:              docs/02-design/.../hld/...   │
│  LLDs:             N files                      │
│  ADRs:             N stubs (architect to fill)  │
│  Decision packets: N files                      │
│  Training stub:    [path or "not required"]     │
│  .hitl context:    implementation-approved      │
├─────────────────────────────────────────────────┤
│ SLICE HANDOFF                                   │
│  Slice 1: domain [A] → assign to developer      │
│           LLD: docs/.../lld/[A]/...             │
│           Packet: docs/decisions/issue-<N>-s1   │
│  Slice 2: domain [B] → [SEQUENTIAL after s1]    │
│           LLD: docs/.../lld/[B]/...             │
│           Packet: docs/decisions/issue-<N>-s2   │
├─────────────────────────────────────────────────┤
│ NEXT STEPS                                      │
│  1. Assign packet(s) to developer(s)            │
│  2. Each developer runs /hitl:tdd with their LLD     │
│  3. Sequential slices: merge slice 1 before     │
│     handing off slice 2                         │
└─────────────────────────────────────────────────┘
```
