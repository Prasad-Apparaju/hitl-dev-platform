# Progress Banners (reference)

Reference for the Design Feature skill. Output the banner for the current phase at the start of every phase — before any questions, analysis, or content.

Format: `---` line, `**Design Feature — Phase N / 10: [Name]**`, trail, `---`.

| Phase | Name | Banner trail |
|---|---|---|
| 1 | Impact Analysis | `▶ Impact · ○ ROI · ○ HLD · ○ ADRs · ○ LLD · ○ IaC · ○ Slices · ○ Tests · ○ Training · ○ Packet` |
| 2 | ROI Check | `✅ Impact · ▶ ROI · ○ HLD · ○ ADRs · ○ LLD · ○ IaC · ○ Slices · ○ Tests · ○ Training · ○ Packet` |
| 3 | HLD | `✅ Impact · ✅ ROI · ▶ HLD · ○ ADRs · ○ LLD · ○ IaC · ○ Slices · ○ Tests · ○ Training · ○ Packet` |
| 4 | ADR Capture | `✅ Impact · ✅ ROI · ✅ HLD · ▶ ADRs · ○ LLD · ○ IaC · ○ Slices · ○ Tests · ○ Training · ○ Packet` |
| 5 | LLD | `✅ Impact · ✅ ROI · ✅ HLD · ✅ ADRs · ▶ LLD · ○ IaC · ○ Slices · ○ Tests · ○ Training · ○ Packet` |
| 6 | IaC Planning | `✅ Impact · ✅ ROI · ✅ HLD · ✅ ADRs · ✅ LLD · ▶ IaC · ○ Slices · ○ Tests · ○ Training · ○ Packet` |
| 7 | Slice Decomposition | `✅ Impact · ✅ ROI · ✅ HLD · ✅ ADRs · ✅ LLD · ✅ IaC · ▶ Slices · ○ Tests · ○ Training · ○ Packet` |
| 8 | Test Case Planning | `✅ Impact · ✅ ROI · ✅ HLD · ✅ ADRs · ✅ LLD · ✅ IaC · ✅ Slices · ▶ Tests · ○ Training · ○ Packet` |
| 9 | Training Stub | `✅ Impact · ✅ ROI · ✅ HLD · ✅ ADRs · ✅ LLD · ✅ IaC · ✅ Slices · ✅ Tests · ▶ Training · ○ Packet` |
| 10 | Decision Packet | `✅ Impact · ✅ ROI · ✅ HLD · ✅ ADRs · ✅ LLD · ✅ IaC · ✅ Slices · ✅ Tests · ✅ Training · ▶ Packet` |
