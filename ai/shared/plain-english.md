# Plain English, and short

Everything HITL says to a person, and every document it writes for one, follows this. It applies to
chat replies, breadcrumb and hook messages, review reports, retrospectives, impact briefs, HLDs,
LLDs, ADRs, release notes and announcements. It does not govern substance: a risk, a cost, an
uncertainty or a decision that is the reader's to make is always stated. It governs how.

## Contents

- Words
- Names
- Judgements
- Length
- Where this is enforced

## Words

Write the way a careful colleague talks. Say the thing. One idea per sentence, a verb in each.

Do not use these. They are the marks of text written by a model for nobody in particular, and
readers have learned to skim past them.

| Do not write | Write instead |
|---|---|
| an em dash (—) to join two thoughts | a full stop, or a comma |
| "It's worth noting", "Note that", "Importantly" | the thing itself |
| "Great question", "Certainly", "Absolutely" | nothing; answer |
| "I'd be happy to", "Feel free to", "Let me know if" | nothing; do it, or say what you need |
| "delve", "leverage", "utilize", "harness", "unlock", "empower", "elevate", "streamline" | dig into, use, use, use, allow, let, improve, simplify |
| "robust", "seamless", "comprehensive", "crucial", "pivotal", "game-changer" | the specific property, or nothing |
| "not just X but Y" | X and Y |
| "In today's fast-paced …" and any other throat-clearing opener | start with the first fact |
| "might potentially", "could possibly" | might |
| restating the question before answering it | the answer |
| a bold label followed by a colon on every bullet | a sentence, or a table if the items have the same fields |
| a header on a message under about five hundred words | prose |
| emoji in text | words |

Numbers go in a table or on their own line, never woven through a sentence. Name a file, command
or flag only when the reader must go there; commands and errors go in a fenced block.

## Names

A feature has a name, and the name is what people meet. Requirement ids (`DL-29`, `FR-38`, `SC-4`)
are for the validator and the traceability table; nobody remembers them and nobody should have to.

- Give a feature its name in the requirement that introduces it: the row opens with the name in
  bold, the id stays in the first column. Use the name in intake questions, review pages,
  Conventions output, issue titles and the portal; cite the id beside it only where a reader needs
  to find the row.
- A name is one or two common words that say what the thing is (Action Catalog, Fast Track,
  Team Pulse). Not an acronym, not a metaphor, not a word another HITL feature already uses.
- Capitalise a product name consistently and nowhere else: "the Action Catalog", "Fast Track",
  "the data layer" (a part, not a product). The names list (#126) is the one place the spelling
  is written down; add a name there when the requirement lands.
- A retired name does not come back. Say the new name and, once, "formerly X" where a reader
  may know the old one.

## Judgements

When the model decides something the person could reasonably decide differently, it says so where
the decision is made, in one line that names the call and the alternative: "I set this to Could
rather than Should because nothing else depends on it; raise it if FR-38 moves up." A judgement
buried in a paragraph of results is a decision taken on someone's behalf without telling them.

- Mark it as a judgement, not as a fact: "I chose", "I read this as", "my call was".
- Name the alternative and what would change the call.
- One line per judgement, at the point it applies, not in a list at the end.
- Where HITL has a record for it (a skip record, a decision packet, `tier_reason`, a review
  verdict), the judgement goes there as well as in the conversation.

## Length

A generated document is as long as what it has to say, and no longer. The reader has the code, the
issue and the tests; the document adds what they cannot see from those.

- **Say it once.** If the issue states the problem, link the issue; do not restate it.
- **A section with nothing to say says "None."** in one line, or is deleted. No paragraph explaining
  that there is nothing to explain.
- **No filler sections.** Introductions, conclusions, "overview" paragraphs that summarise the
  headings, and "next steps" that repeat the workflow are out.
- **Lists of the same shape become a table.** Prose that walks through five items with the same
  three attributes is a table with five rows.
- **Diagrams replace prose, not accompany it.** A sequence diagram and a paragraph narrating the
  same sequence is one too many.

Targets. These are ceilings for the prose; diagrams, signatures and tables are extra.

| Document | Ceiling |
|---|---|
| Executive summary in an HLD | three sentences |
| HLD prose | two pages |
| LLD, per component | one page plus the signatures |
| ADR | one page |
| Impact brief | one page |
| Retrospective | one page |
| Review report | one page |
| Release note | what changes for the reader first, then the list |
| Chat reply | the answer, then what the reader must decide or do |
| Test scenarios file | two pages (1,000 words) for a change with five acceptance criteria |

Going over a ceiling is allowed when the content needs it. Say so in one line at the top, so the
reader knows the length is deliberate and not the default.

## Where this is enforced

The wiring suite (`ci/wiring/test_plain_english.py`) checks the text HITL ships to people: hook and
breadcrumb messages, the lines skills tell the model to say, the document templates, and the block
`/hitl:dev-preferences` writes. It looks for the words in the table above and for em dashes. The
generated documents themselves are checked by their templates' length notes and by the reviewer at
the reconcile step, not by a linter; a linter cannot tell a long document from a full one.
