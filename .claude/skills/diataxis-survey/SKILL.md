---
name: diataxis-survey
description: Use when surveying a codebase and planning a complete documentation system using the Diátaxis framework
---

# Diataxis: Survey

You are acting as a documentation architect. You will explore the codebase, evaluate existing documentation, design the documentation architecture, and produce a structured implementation plan for a complete documentation system using the Diátaxis framework. The full plan should be written to a markdown file at `docs/diataxis/plan.md`.

**Announce at start**: "I'm using the survey skill to create the implementation plan."

For each of the items in the checklist below, create a task and complete it before moving on to the next item.

1. [ ] Instantiate an empty `docs/diataxis/plan.md`

   Every plan MUST start with this header:

   ```markdown
   # [Feature Name] Implementation Plan

   > **For agentic workers:** REQUIRED SUB-SKILL: Implement this plan task-by-task (one document per task, via `diataxis-write-doc`). Steps use checkbox (`- [ ]`) syntax for tracking.

   ---
   ```

2. [ ] Explore the codebase

   Build a mental model of how the software works. Reverse-engineer the system architecture, core user workflow(s), operational model, and conceptual structure of the software.
   1. [ ] Identify the primary purpose of the software
   2. [ ] Identify the intended users
   3. [ ] Identify core concepts and workflows
   4. [ ] Identify the main architectural components
   5. [ ] Identify runtime model and execution flow

      Create a mermaid diagram. The purpose of this diagram is to organise your understanding of the system before planning documentation. The diagram should display:
      - major components
      - relationships between components
      - execution flow
      - user interaction flow
      - subsystem boundaries

   6. [ ] Identify entry points for users
   7. [ ] Identify avenues for extensibility and integration
   8. [ ] Detect the documentation toolchain (e.g. MkDocs, Sphinx, custom system, etc.)
   9. [ ] Detect testing and development workflows
   10. [ ] Update `docs/diataxis/plan.md`

   Append the project summary, architecture summary, and toolchain summary to the plan.md document under the sections "Project Summary", "System Architecture Summary", and "Toolchain Detection" respectively. Include the mermaid diagram from step 2.4. in the "System Architecture" section.

   Be ruthlessly concise in these summaries. The purpose is to capture the essential information needed for documentation planning, not to write a comprehensive analysis of the system.

3. [ ] Survey existing documentation

   Understand what documentation already exists and how it is currently structured.
   1. [ ] Produce a catalogue of existing documentation. For every document found, record:

      ```text
      File: <path to document>
      Purpose: <one-line description of what the document is for>
      Classification: <Diátaxis classification or "Mixed">
      ```

      To assign the Diátaxis classification, consult the Diátaxis classification rules in [DIATAXIS.md](DIATAXIS.md).

   2. [ ] Detect structural problems in the existing documentation system

      Flag items in the existing documentation that violate Diátaxis principles or indicate structural problems, such as:
      - duplicated content
      - mixed-purpose documents
      - missing sections
      - navigation problems
      - structural inconsistencies
      - unclear learning paths

   3. [ ] Update `docs/diataxis/plan.md`

   Append the catalogue and structural evaluation to the plan.md document under the section "Existing Documentation". If no documentation was found, note 'No existing documentation found' in this section.

4. [ ] Design the documentation architecture

   Design the high-level documentation architecture before planning individual documents.

   This step should work from broad structure toward sharper structure. First establish the major documentation areas, then define what belongs in each area. In the next step, we will refine the hierarchy until it forms a coherent documentation website.

   The output of this step is not a document-by-document plan. The output is a structured documentation architecture: the navigation model, the purpose of each section, and the kinds of content each section should contain.
   1. [ ] Define the documentation vision

      Write a short statement describing what the documentation system needs to help users do.

      This should explain:
      - who the documentation is for
      - what users need to understand
      - what users need to accomplish

   2. [ ] Design the top-level navigation

      Design the main sections of the documentation website.

      A good default structure is:

      ```text
      Home
      Getting Started
      Tutorials
      How-to Guides
      Reference
      Explanation
      Architecture
      Contributing
      Troubleshooting
      About
      ```

      Adjust this structure if the project requires a different navigation model.

      For each top-level section, record:

      ```text
      Section: <navigation label>
      Purpose: <what this section is for>
      Contains: <types of documents or topics that belong here>
      Excludes: <types of content that should not go here>
      ```

   3. [ ] Design the learning architecture

      Plan how a new user should move from first contact to productive use.

      This should define:
      - the first page a new user should read
      - the first successful outcome they should achieve
      - the core tutorials required for onboarding
      - the order in which tutorials should be read
      - where conceptual explanations are needed to support learning
      - where users should be redirected from tutorials into reference or how-to material

   4. [ ] Design the task architecture

      Plan how users will find instructions for accomplishing specific tasks.

      Group tasks by user goal, not by internal code structure.

      For each task group, record:

      ```text
      Task group: <name>
      User goal: <what the user is trying to do>
      Likely documents: <kinds of how-to guides needed>
      Related reference: <reference pages users may need>
      Related explanation: <conceptual pages users may need>
      ```

   5. [ ] Design the conceptual architecture

      Plan how explanations should be organised.

      The conceptual structure should reflect the mental model of the software, not the file tree.

      Identify:
      - core concepts users must understand
      - architectural ideas users need before advanced use
      - design decisions that need explanation
      - domain concepts that are specific to the project
      - relationships between concepts

   6. [ ] Design the reference architecture

      Plan how reference documentation should be organised.

      The reference structure should mirror the public interface of the software.

      Depending on the project, this may include:
      - API reference
      - CLI reference
      - configuration reference
      - module reference
      - schema reference
      - plugin or extension reference
      - error reference
      - command reference

   7. [ ] Design the contributor and developer architecture

      Plan documentation for people who need to modify, extend, test, or release the software.

      This should include, where applicable:
      - development setup
      - repository structure
      - testing workflow
      - build workflow
      - release workflow
      - coding conventions
      - documentation conventions
      - contribution process

   8. [ ] Evaluate the proposed architecture against existing documentation

      Compare the proposed architecture with the existing documentation structure.

      Identify:
      - existing sections that can be reused
      - sections that need to move
      - sections that need to be split
      - sections that need to be merged
      - sections that should be removed
      - missing top-level sections
      - navigation ambiguities

   9. [ ] Update `docs/diataxis/plan.md`

      Append the documentation architecture to the plan under the section "Documentation Architecture".

      This section should contain:
      - documentation vision
      - proposed top-level navigation
      - purpose of each major section
      - learning architecture
      - task architecture
      - conceptual architecture
      - reference architecture
      - contributor/developer architecture
      - structural issues to resolve

5. [ ] Plan the documentation

   Convert the documentation architecture into a specific document-by-document plan. The plan should live in `docs/diataxis/plan.md` under the section "Documentation Plan".

   This step should produce the exact documentation system that needs to exist. Every planned document must have a clear place in the documentation hierarchy, a clear purpose, and a Diátaxis classification.

   Write the plan assuming the engineer has zero context for our codebase and questionable taste. Document everything they need to know. Give them the whole plan as bite-sized tasks. DRY. YAGNI. Frequent commits.

   Prioritise a minimal complete documentation system first. Add optional or advanced documents only where they are justified by the software architecture, user workflows, or operational needs.
   1. [ ] Plan the full documentation hierarchy

      Create a nested documentation tree showing every planned page.

      Use this format:

      ```text
      Home
      Getting Started
        - Installation
        - Quick Start
      Tutorials
        - <tutorial title>
      How-to Guides
        - <task group>
          - <guide title>
      Reference
        - <reference group>
          - <reference title>
      Explanation
        - <concept group>
          - <explanation title>
      Contributing
        - <developer document title>
      ```

   2. [ ] Plan each document

      For every document in the hierarchy, create an entry using this format:

      ```text
      Title: <document title>
      Path: <where this document fits in the navigation hierarchy>
      File: <recommended file path>
      Diátaxis classification: <tutorial / how-to / reference / explanation>
      Purpose: <one-sentence description of what this document is for>
      Contents:
        - <major heading or topic>
        - <major heading or topic>
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
          - <existing document path>
        Target:
          - <new document path>
          - <new document path>
        Reason: <ruthlessly concise explanation of why this transformation is required>
      ```

      Omit the `Transformation` section for documents that require no structural changes.

   3. [ ] Update `docs/diataxis/plan.md`

      Append the document-by-document plan under the section "Documentation Plan".

      This section must include:
      - the full nested documentation hierarchy
      - one planning entry for every document in the hierarchy.

## Rules

- Do not perform documentation gap analysis yet.
- Do not redesign the documentation structure yet.
- Do not classify documents yet.
- Focus on understanding the system itself.
- Prioritise conceptual understanding over implementation detail.
- Reverse-engineer the system from the perspective of:
  - users
  - operators
  - contributors
  - maintainers
- Build an internal mental model before planning documentation.
- If the project is a software package or application, create an internal mermaid diagram for reasoning purposes.
- The mermaid diagram is for internal reasoning only.
- Do not present the diagram to the user unless explicitly requested.
- Avoid low-level implementation noise.
- Focus on:
  - component relationships
  - execution flow
  - subsystem boundaries
  - extension points
  - configuration entry points
  - user interaction flow
