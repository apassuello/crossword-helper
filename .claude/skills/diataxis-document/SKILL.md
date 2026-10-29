---
name: diataxis-document
description: Use to orchestrate a complete Diátaxis documentation workflow from survey and planning through iterative document implementation and refinement.
---

# Diataxis: Document

This skill is the primary entry point for the Diátaxis documentation workflow. You are orchestrating a series of tasks that will produce a complete documentation system for a project. For each of the items in the checklist below, create a task and complete it before moving on to the next item.

1. [ ] Invoke `diataxis-survey`

   Running this skill will survey the codebase and produce a documentation architecture and implementation plan. The output will be a markdown file at `docs/diataxis/plan.md`.

2. [ ] Request user review of the plan

   The user must explicitly approve the plan before any implementation begins. Prompt the user to inspect the plan at the path: `docs/diataxis/plan.md`. Ask if they approve the plan as-is, if they would like to request changes. If the user requests changes, revise the plan and request approval again. If the user rejects the plan entirely, stop immediately and report that no documentation was written. If the user approve the plan, proceed to the next step.

3. [ ] Recursively implement documents

   Identify the approved document set. Create a new task for each document and complete it before moving on to the next one.

   Dispatch a new subagent for each document. Give each subagent only the complete plan entry for the document it is writing.

   Instruct each subagent to invoke `diataxis-write-doc` with that plan entry. Do not invoke the type-specific skills directly from this orchestration skill.

4. [ ] Improve navigation and cross-linking

   Review the documentation system as a whole and identify opportunities to improve navigation and cross-linking. Create new tasks for each improvement and complete them sequentially.

5. [ ] Produce final implementation summary

   At completion, produce a summary containing an overview of the implemented documentation system. Include a list of implemented documents, and instructions for running the documentation toolchain if applicable.

## Rules

- Do not write any documentation before the user explicitly approves the plan.
- Do not skip the survey and planning phase.
- Do not generate documentation opportunistically during analysis.
- Treat the survey output (`docs/diataxis/plan.md`) as the source of truth for implementation. Do not deviate from the plan during implementation.
- Only write documents that exist in the approved plan.
- Use `diataxis-write-doc` for every planned document.
- Let `diataxis-write-doc` validate context and route to the correct type-specific writing skill.
