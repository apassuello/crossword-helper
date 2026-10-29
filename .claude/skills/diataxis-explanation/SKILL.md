---
name: diataxis-explanation
description: Write Diátaxis-compliant explanation documentation that deepens understanding through context, reasoning, and conceptual discussion.
---

# Diátaxis: Explanation

You are writing explanation documentation.

Explanation documentation deepens understanding.
It provides context, reasoning, perspective, and conceptual clarity.

Explanation is not:

- a tutorial
- a how-to guide
- reference documentation
- onboarding
- procedural instruction

Explanation exists to help the reader understand:

- why something exists
- why something works the way it does
- how concepts relate
- what tradeoffs and constraints shaped the system
- how to think about the subject

Explanation is reflective and understanding-oriented.

This skill is called by `diataxis-write-doc` with validated document context. Use that context as binding.

# Task Checklist

1. [ ] Validate the explanation scope

   Ensure the document is genuinely explanatory.

   Explanation documentation should:
   - deepen understanding
   - provide context
   - explain reasoning
   - connect concepts
   - discuss tradeoffs and alternatives

   Reject scopes that are:
   - tutorial-oriented
   - task-oriented
   - reference-heavy
   - procedural
   - implementation-step driven

2. [ ] Define the conceptual topic

   Identify the topic being explained.

   Good explanation topics:
   - authentication architecture
   - database connection policies
   - plugin system design
   - caching tradeoffs
   - deployment model rationale

   Bad explanation topics:
   - how to deploy
   - API parameter reference
   - installation instructions

3. [ ] Define the central questions

   Identify the key questions the explanation answers.

   Examples:
   - Why is the system designed this way?
   - What tradeoffs exist?
   - How do these concepts relate?

   Explanation should illuminate, not instruct.

4. [ ] Design the conceptual structure

   Organise the explanation around ideas, relationships, reasoning, history, constraints, and implications.

5. [ ] Write the explanation document

   Use the structure that best suits the topic. Optimise for understanding, not procedure.

   Write with:
   - clarity
   - perspective
   - intellectual honesty
   - conceptual depth

   Use:
   - analogies
   - comparisons
   - examples
   - discussion of alternatives

   Always link to related how-to or reference documentation if implementation details are required.

6. [ ] Remove non-explanation content

   Remove tutorials, procedures, installation steps, API dumps, exhaustive reference listings, and operational checklists.

7. [ ] Handle document transformations

   If `Status` indicates an existing document transformation:
   - `Rewrite`: preserve conceptual insight, remove procedural drift, improve clarity.
   - `Split`: separate unrelated conceptual topics.
   - `Merge`: consolidate fragmented conceptual discussions.
   - `Remove`: preserve nothing unless required elsewhere.

8. [ ] Perform final validation

   Verify:
   - [ ] The document explains why, not merely how
   - [ ] The document avoids exhaustive reference detail
   - [ ] The document is unmistakably explanation content

Source principles extracted from the Diátaxis explanation guidelines.
