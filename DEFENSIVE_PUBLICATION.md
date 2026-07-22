# The Conscience Loop — Defensive Publication
**Published: July 22, 2026 · Author: Andres M. (ammtz) · Status: public prior art, free to use**

## Disclosure

A method for improving AI assistant output reliability via a user-invoked
two-pass self-review ritual, triggered by a fixed natural-language sentence:

> "Let's expand on that. Describe to me the differences, and after that,
> read what you wrote yourself, and if you understand it, describe it to me again."

On trigger, the AI must: (1) enumerate differences between its prior answer's
claims and the evidence it actually verified; (2) literally re-read its prior
answer and fetch, via available tools, every primary source it had cited
secondhand (files, web pages, documents, logs); (3) produce a revised second
answer that must materially differ from the first or explicitly state that the
first answer failed contact with the sources. The second pass is the
deliverable; the visible delta between passes exposes the AI's assumptions.

## Novelty claimed

Not self-critique in general, but the synthesis: a fixed portable trigger
sentence + mandatory re-sourcing (re-reading without fetching sources is
rejected as invalid) + a must-differ requirement on the second pass + the
delta-as-audit-trail presented to the user. Implementable as a prompt, an
assistant skill, or agent scaffolding on any model.

## Intent

This publication places the method in the public domain as prior art.
Anyone may use it; no one may patent it.
