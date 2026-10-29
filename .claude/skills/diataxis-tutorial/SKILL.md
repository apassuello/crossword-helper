---
name: diataxis-tutorial
description: Write beginner-focused software tutorials that teach one thing well through a reproducible, step-by-step workflow.
---

# Diátaxis: Tutorial

You are writing a tutorial.

Tutorials teach through guided practice.
A tutorial helps a beginner achieve a meaningful working outcome while learning one primary concept.

The goal is not merely to explain concepts.
The goal is to guide the reader through a successful end-to-end workflow.

A tutorial should:

- teach through doing
- remain linear and reproducible
- minimise cognitive load
- maintain a working project throughout
- build confidence through visible progress

The tutorial must produce:

- a concrete outcome
- a functioning result
- understanding of one new concept

This skill is called by `diataxis-write-doc` with validated document context. Use that context as binding.

# Task Checklist

1. [ ] Validate the tutorial scope

   Define exactly what the tutorial teaches and what the reader will achieve.

   The tutorial must:
   - focus on one primary concept
   - produce one concrete outcome
   - remain tightly scoped
   - avoid teaching an entire ecosystem

   Assume the reader is a beginner.

   If required inputs are missing:
   - recommend sensible defaults
   - ask the user to confirm before proceeding

   Validate:
   - the subject matter
   - the intended audience
   - the final outcome
   - the output format
   - the scope boundaries

2. [ ] Validate the tutorial title

   Ensure the title:
   - promises a concrete outcome
   - is beginner-friendly
   - clearly communicates what the reader will build or achieve

   If the title is weak:
   - recommend a stronger title

3. [ ] Determine the output format

   Determine the tutorial output format.

   Examples:
   - markdown
   - mdx
   - rst
   - html

   If no format was provided:
   - recommend markdown by default

4. [ ] Define the learning outcome

   Write a concise internal summary describing:
   - what the reader will build
   - what the reader will learn
   - what successful completion looks like
   - the primary concept being taught

5. [ ] Plan the tutorial flow

   Design a beginner-friendly learning path.

   The tutorial should:
   - remain linear
   - minimise setup complexity
   - minimise cognitive load
   - introduce concepts only when needed
   - keep the project functional throughout

   Every major step must:
   - run
   - compile
   - produce observable output

   Never:
   - introduce intentionally broken code
   - require unnecessary branching
   - require tedious manual editor actions when commands are clearer

6. [ ] Design the implementation sequence

   Produce a concise outline of:
   - each implementation step
   - the purpose of the step
   - the expected observable outcome

   Sequence steps to maximise:
   - confidence
   - visible progress
   - clarity
   - reproducibility

7. [ ] Define the environment and dependency plan

   Summarise:
   - required dependencies
   - required tools
   - runtime requirements
   - setup assumptions

   Keep dependencies minimal whenever possible.

8. [ ] Write the tutorial

   Use the following structure:

   ```markdown
   # <Title>

   ## Introduction

   Explain:

   - what the reader will build
   - why it matters
   - what they will learn

   ## Prerequisites

   List only genuinely required setup.

   ## Step-by-step implementation

   Guide the reader through the implementation in small safe steps.

   ## Final result review

   Show the completed result and explain what now works.

   ## Next steps

   Link to:

   - related tutorials
   - how-to guides
   - explanations
   - reference documentation

   ## Complete example

   Provide runnable code or repository links whenever possible.
   ```

9. [ ] Apply tutorial writing rules

   Write for beginners.

   Use:
   - direct procedural language
   - short paragraphs
   - clear progress-oriented headings
   - visually simple examples
   - copy/pasteable commands and code

   Always:
   - specify filenames and paths
   - explain technical terms immediately
   - separate user-editable values clearly
   - use realistic example values
   - demonstrate success after major steps
   - explain what successful output looks like

   Never:
   - include shell prompts in copyable commands
   - bury important actions inside long explanations
   - use marketing language
   - add unnecessary personality

10. [ ] Keep the tutorial functional throughout

    Ensure:
    - the project remains runnable throughout the tutorial
    - every major step leaves the project in a working state
    - progress is continuously visible to the reader

    Show the final result early whenever possible.

11. [ ] Handle document transformations

    If `Status` indicates an existing document transformation:
    - `Rewrite`
      - preserve useful instructional flow
      - remove structural problems
      - tighten the scope around one learning outcome

    - `Split`
      - separate unrelated learning goals into distinct tutorials
      - ensure each tutorial teaches one concept well

    - `Merge`
      - consolidate fragmented beginner workflows into one coherent learning path

    - `Remove`
      - preserve nothing unless required elsewhere

12. [ ] Perform final validation

    Verify:
    - [ ] The tutorial teaches one primary concept
    - [ ] The title promises a concrete outcome
    - [ ] The introduction explains why the tutorial matters
    - [ ] The final result is shown early
    - [ ] The tutorial assumes beginner knowledge
    - [ ] Jargon is minimised or explained immediately
    - [ ] All examples are copy/pasteable
    - [ ] Shell prompts are excluded from commands
    - [ ] User-editable values are clearly separated
    - [ ] Example values are realistic and unambiguous
    - [ ] Dependencies are minimised
    - [ ] Filenames and edit locations are explicit
    - [ ] Headings are clear and consistent
    - [ ] Every major step demonstrates success
    - [ ] The project remains functional throughout
    - [ ] A complete working example is linked where possible
    - [ ] The document is unmistakably a tutorial
