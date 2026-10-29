---
name: diataxis-how-to-guide
description: Write a Diátaxis-compliant how-to guide focused on helping competent users accomplish a specific real-world task or solve a specific problem
---

# Diátaxis: How-to Guide

You are writing a how-to guide.

How-to guides are practical directions for competent users.
They help the user accomplish a specific real-world task.
They are goal-oriented and action-oriented.

A how-to guide is not:

- a tutorial
- an explanation
- a reference document
- a feature overview
- a conceptual discussion
- a complete course on a topic

A how-to guide exists to help the user successfully accomplish one clearly-defined goal.

This skill is called by `diataxis-write-doc` with validated document context. Use that context as binding.

# Task Checklist

1. [ ] Validate that this should be a how-to guide

   Ensure the document is:
   - task-oriented
   - focused on a specific goal
   - intended for competent users
   - helping users accomplish real work

   Reject scopes that are:
   - too broad
   - conceptual
   - tutorial-like
   - reference-heavy

   Narrow broad topics into specific operational goals.

   Good:
   - How to configure OAuth with GitHub
   - How to deploy to Kubernetes
   - How to recover a failed migration

   Bad:
   - Authentication
   - Kubernetes
   - Building a web application

2. [ ] Define the operational goal

   Write a concise internal statement describing:
   - what the user is trying to achieve
   - when they would use this guide
   - what successful completion looks like

   The guide must solve one clearly-defined real-world problem.

3. [ ] Define the user assumptions

   Assume the reader:
   - already understands the basics
   - understands standard tooling
   - can follow operational instructions
   - does not need beginner teaching

   Do not explain:
   - obvious UI interactions
   - basic concepts
   - standard development workflows
   - elementary domain knowledge

4. [ ] Design the action flow

   Structure the guide as a smooth operational sequence.

   Optimise for:
   - minimal context switching
   - low cognitive load
   - natural progression
   - operational clarity

   Avoid:
   - backtracking
   - unresolved prerequisites
   - unnecessary branching
   - fragmented instructions

5. [ ] Write the guide

   Use the following structure.

   ```markdown
   # <Title>

   ## Goal

   One short paragraph describing:

   - what the user will accomplish
   - when they would use this guide
   - assumptions about prior knowledge

   ## Prerequisites

   Only include prerequisites that are genuinely required.

   ## Steps

   Ordered actions required to complete the task.

   Use:

   - short sections
   - explicit commands
   - expected outcomes
   - verification steps where appropriate

   ## Final Result

   Show how the user confirms success.

   ## Next Steps

   Link to:

   - relevant reference docs
   - explanation docs
   - adjacent how-to guides
   ```

6. [ ] Apply how-to writing rules

   Ensure the guide:
   - focuses on action
   - stays tightly scoped
   - uses direct language
   - prioritises usability over completeness
   - stays focused on the user's goal

   Use:
   - imperative instructions
   - conditional guidance
   - realistic examples
   - meaningful action-oriented headings

   Good:
   - Configure the OAuth provider
   - Verify the deployment
   - Rotate expired credentials

   Bad:
   - Configuration
   - Advanced topics
   - Options

7. [ ] Remove non-how-to content

   Remove:
   - tutorials
   - conceptual explanations
   - architecture discussion
   - feature overviews
   - API dumps
   - exhaustive configuration listings
   - historical discussion
   - marketing language

   If additional context is required:
   - keep it brief
   - link to explanation/reference documents instead

8. [ ] Handle document transformations

   If `Status` indicates an existing document transformation:
   - `Rewrite`
     - preserve operational guidance
     - remove structural problems
     - tighten scope

   - `Split`
     - extract narrowly-scoped operational guides
     - ensure each guide solves one problem

   - `Merge`
     - consolidate overlapping operational workflows
     - remove duplicated instructions

   - `Remove`
     - preserve nothing unless required elsewhere

9. [ ] Perform final validation

   Verify the following checklist before completing. If any of these are not true, revise the guide until they are.
   - [ ] The guide solves one specific real-world problem
   - [ ] The title clearly states the goal
   - [ ] Reference material is linked, not embedded
   - [ ] Headings are action-oriented
   - [ ] The user can verify success
