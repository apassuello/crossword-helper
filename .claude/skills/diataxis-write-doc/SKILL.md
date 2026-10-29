---
name: diataxis-write-doc
description: Validate one planned Diátaxis document context and route it to the correct specialised writer for tutorial, how-to guide, reference, or explanation documentation.
---

# Diataxis: Write Doc

Write one document from an approved Diátaxis plan.

This skill is the only handoff point between `diataxis-document` and the type-specific writers. Validate the document context, then invoke exactly one specialised skill.

## Required Context

The caller must provide:

```text
Title: <document title>
Path: <where this document fits in the navigation hierarchy>
File: <recommended file path>
Diátaxis classification: <tutorial / how-to / reference / explanation>
Purpose: <one-sentence description of what this document is for>
Contents:
  - <major heading or topic>
Depends on:
  - <documents that should exist or be read before this one>
Related documents:
  - <documents users may need next>
Priority: <Required / Recommended / Optional>
Status: <Existing / Rewrite / Split / Merge / New / Remove>
Transformation:
  Type: <Rewrite / Split / Merge / Move / Remove>
  Source:
    - <existing document path>
  Target:
    - <new document path>
  Reason: <why this transformation is required>
```

Omit `Transformation` only when no structural change is required.

## Checklist

1. [ ] Validate context

   Require `Title`, `File`, `Diátaxis classification`, `Purpose`, `Contents`, `Priority`, and `Status`.

   If `Status` is `Rewrite`, `Split`, `Merge`, or `Remove`, require a matching `Transformation`.

   Stop and ask for the missing fields if the context is ambiguous.

2. [ ] Reject invalid classifications

   Accept only:
   - `tutorial`
   - `how-to`
   - `how-to guide`
   - `reference`
   - `explanation`

3. [ ] Route to the writer

   Invoke the matching skill with the validated context:
   - `tutorial` -> `diataxis-tutorial`
   - `how-to` or `how-to guide` -> `diataxis-how-to-guide`
   - `reference` -> `diataxis-reference`
   - `explanation` -> `diataxis-explanation`

4. [ ] Preserve the plan

   Write only the planned document unless the specialised writer identifies a direct dependency needed to complete it.

## Rules

- Treat `docs/diataxis/plan.md` as source of truth.
- Do not invent documents outside the approved plan.
- Do not change the document classification during routing.
- Do not write mixed-purpose documentation.
- Keep the final document direct, useful, and easy to maintain.
