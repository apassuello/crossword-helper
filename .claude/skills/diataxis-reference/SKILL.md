---
name: diataxis-reference
description: Write Diátaxis-compliant reference documentation that describes the machinery clearly, accurately, and neutrally.
---

# Diátaxis: Reference

You are writing reference documentation.

Reference documentation describes the machinery.
It is information-oriented.
Its purpose is to provide accurate, authoritative, structured technical information that users can consult while working.

Reference documentation is not:

- a tutorial
- a how-to guide
- an explanation
- a marketing page
- a conceptual discussion

Reference documentation exists to describe the system clearly and completely.

Users consult reference documentation for:

- truth
- certainty
- exact behaviour
- syntax
- options
- interfaces
- limitations
- operational facts

This skill is called by `diataxis-write-doc` with validated document context. Use that context as binding.

Before writing, ensure that you know the correct place to edit. If you are working with Python code, for example, you may need to edit the docstrings in the source code rather than the generated documentation files.

# Task Checklist

1. [ ] Design the reference structure

   Organise the document according to the structure of the module, function, class, or subsystem being described.

   Use predictable, standard patterns.

   Prioritise:
   - scanability
   - consistency
   - completeness
   - navigability
   - precision

   Users should be able to quickly locate facts without reading linearly.

2. [ ] Write the reference document

   Adopt the existing conventions.

Reference documentation should:

- describe the machinery
- describe interfaces and behaviour
- provide lookup information
- provide operational facts
- remain neutral and factual

Write with:

- neutrality
- precision
- factuality
- consistency
- clarity

Use:

- declarative statements
- standard terminology
- structured formatting
- concise and frequent examples

Good:

- `Subcommands are: build, test, deploy.`
- `The default timeout is 30 seconds.`
- `You must provide an API key.`

Bad:

- `You will love this feature.`
- `Let's explore how this works.`
- `In this tutorial...`

3. [ ] Remove non-reference content

   Remove:
   - tutorials
   - walkthroughs
   - onboarding
   - conceptual essays
   - architecture discussion
   - motivational language
   - marketing language
   - opinionated commentary

   If explanation or workflow guidance is required:
   - link to the appropriate document instead

4. [ ] Handle document transformations

   If `Status` indicates an existing document transformation:
   - `Rewrite`
     - preserve accurate technical information
     - remove instructional or conceptual drift
     - improve structure and consistency

   - `Split`
     - separate unrelated interfaces or subsystems
     - keep each reference focused on one part of the machinery

   - `Merge`
     - consolidate fragmented technical reference
     - eliminate duplicated definitions

   - `Remove`
     - preserve nothing unless required elsewhere

5. [ ] Perform final validation

   Verify:
   - [ ] The document describes the machinery directly
   - [ ] The structure mirrors the product structure
   - [ ] The language is neutral and factual
   - [ ] The document is easy to scan
   - [ ] Examples remain concise and illustrative
   - [ ] Warnings and constraints are explicit
   - [ ] Terminology is consistent throughout
   - [ ] Information is accurate and authoritative
   - [ ] The document is unmistakably reference material

Source principles extracted from the Diátaxis reference guidelines.
