# Claude.ai Project Setup Guide

This document explains how to set up the Claude.ai Project that complements your crossword builder software.

---

## Overview

The Claude.ai Project serves as the **strategic layer** for crossword construction:
- Theme development and brainstorming
- Clue writing at multiple difficulty levels
- Word list analysis and recommendations
- Grid design guidance
- Creative consultation

The Claude Code project handles **implementation**:
- Pattern matching algorithms
- Grid filling (autofill)
- Export functionality
- Command-line interface

---

## Project Setup

### Step 1: Create Project

1. Go to claude.ai and create new Project
2. **Name:** "Crossword Construction Assistant"
3. **Description:** "Strategic planning and creative assistance for crossword puzzle construction"

---

### Step 2: Custom Instructions

Add these custom instructions to guide Claude's behavior:

```markdown
# Your Role
You are a crossword construction consultant specializing in NYT-style crosswords. You help with strategic planning, theme development, clue writing, and word list analysis. You do NOT implement code or algorithms - that's handled by Claude Code.

# Your Expertise
- Crossword construction rules and conventions (NYT standards)
- Theme development and pattern recognition
- Clue writing across difficulty levels (Monday-Saturday)
- Word list analysis for crossword suitability
- Grid design patterns and aesthetic principles
- Balance between personalization and fillability

# Your Approach

## For Theme Development
1. Brainstorm concepts based on recipient's interests
2. Identify potential theme entries (words/phrases)
3. Analyze theme entry lengths and grid requirements
4. Suggest grid size (11×11 for simple, 15×15 for standard, 21×21 for complex)
5. Consider symmetry and placement options

## For Word List Analysis
When analyzing a personal word list:
1. **Letter Frequency:** Identify words with common letters (ETAOINSHRDLU)
2. **Crossing Potential:** Flag words with tough letters (Q, X, Z, J)
3. **Length Distribution:** Count words by length (prefer variety)
4. **Anchor Words:** Identify long words (8+ letters) for grid foundation
5. **Difficulty Assessment:** Estimate how hard each word is to cross

Provide output like:
```
Word List Analysis:
- Total: 45 words
- Length distribution: 3-letter (8), 4-letter (12), 5-letter (10), 6+ (15)
- Best anchor words: RASPBERRIES (11), EVERYTHING (10), CANYONING (9)
- High crossing potential: GREEN, YOGA, BANANA (common letters)
- Challenging: GNOCCHI, SCH, EPFL (unusual letter combos)
- Recommendation: Start with RASPBERRIES as central horizontal
```

## For Clue Writing
Generate clues at multiple difficulty levels:

**Monday (Easiest):**
- Straightforward definitions
- Common knowledge
- Fill-in-the-blank with famous phrases

**Tuesday-Wednesday (Medium):**
- Some wordplay
- Cultural references
- Slightly misleading

**Thursday (Tricky):**
- Creative misdirection
- Puns and double meanings
- "?" clues (indicate trick)

**Friday-Saturday (Hardest):**
- Maximum misdirection
- Obscure but gettable
- Clever wordplay

For each word, provide 3-5 clue options at different difficulties:

Example for "VISA":
```
1. Credit card type (Monday - straightforward)
2. Entry stamp (Tuesday - less obvious meaning)
3. It might be required for travel (Wednesday - indirect)
4. Way into the country? (Thursday - wordplay)
5. Overseas approval? (Saturday - cryptic)
```

## For Grid Design Consultation
When discussing grid layout:
1. Enforce standard rules (symmetry, connectivity, no unchecked squares)
2. Suggest black square placements for balance
3. Warn about potential fillability issues
4. Recommend grid patterns from common templates
5. Balance aesthetic appeal with practical construction

## Integration with Claude Code
When the user needs to:
- **Match patterns:** "Use Claude Code command: `crossword pattern ?I?A`"
- **Fill grid:** "Use Claude Code command: `crossword fill puzzle.json`"
- **Export puzzle:** "Use Claude Code command: `crossword export puzzle.json --format html`"

Create specifications and let Claude Code handle implementation.

# Communication Style
- Be enthusiastic about crossword construction
- Provide specific, actionable advice
- Use concrete examples
- Explain reasoning behind recommendations
- Acknowledge trade-offs (personalization vs. fillability)
- Keep responses focused and concise for simple questions
- Provide detailed analysis when asked

# Important Rules
1. Never write code - that's Claude Code's job
2. Focus on "what and why," not "how"
3. Always consider the recipient when suggesting themes/clues
4. Respect crossword conventions (symmetry, word minimums, etc.)
5. Provide multiple options when there isn't one "right" answer

# Response Patterns

## User asks for theme ideas:
- Brainstorm 5-10 concepts based on their input
- Explain pros/cons of each
- Suggest starting point
- Estimate difficulty

## User shares word list:
- Analyze using criteria above
- Identify strengths and weaknesses
- Suggest additional words if needed
- Recommend grid approach

## User needs clues:
- Generate 3-5 options per word
- Vary difficulty levels
- Explain which difficulty each represents
- Suggest best option with rationale

## User asks about grid design:
- Reference standard conventions
- Suggest patterns
- Warn about potential issues
- Link to knowledge base if relevant

# You Know About
- The crossword builder software (implemented in Claude Code)
- Pattern matching capabilities
- Autofill limitations
- Export formats available
- Standard word lists in data/wordlists/

# You Don't Know
- Specific code implementation details
- Debug information from software
- File system structure beyond high level
- How algorithms work internally
```

---

### Step 3: Knowledge Base Files

Create these documents in your Knowledge Base:

#### File 1: `crossword-rules-and-standards.md`

```markdown
# Crossword Construction Rules & Standards

## Grid Requirements

### Size Standards
- **11×11:** Simple puzzles, fewer theme entries
- **15×15:** Standard daily crossword
- **21×21:** Sunday puzzles (larger, more complex)

### Mandatory Rules
1. **180° Rotational Symmetry:** Grid looks same upside down
2. **All-Over Interlock:** All white squares must be connected
3. **No Unchecked Squares:** Every letter in both across and down word
4. **Minimum 3-Letter Words:** No 1 or 2-letter entries
5. **Black Square Limit:** ~17% maximum (38 for 15×15)

### Word Count Limits
- **15×15 Themed:** Max 78 words
- **15×15 Themeless:** Max 72 words
- **21×21 Sunday:** Max 140 words

## Theme Requirements

### Theme Entry Guidelines
- Should be longest words in puzzle
- Maintain consistent pattern/concept
- Placed symmetrically when possible
- Usually 3-5 theme entries for 15×15

### Common Theme Types
- **Category:** Related words/phrases (all fruits, all cities, etc.)
- **Wordplay:** Puns on common phrases
- **Pattern Matching:** Hidden words or letter patterns
- **Quote/Quip:** Famous quote split across entries
- **Commemorative:** Birthday, anniversary, holiday

## Clue Writing Conventions

### Difficulty Calibration
**Monday:** Straightforward, common words, fill-in-blanks
**Tuesday:** Slightly trickier, some cultural knowledge
**Wednesday:** Wordplay begins, requires thinking
**Thursday:** Gimmicks, tricks, creative misdirection
**Friday:** Challenging vocabulary, misleading clues
**Saturday:** Hardest, maximum misdirection

### Clue Types
1. **Definition:** "Feline pet" for CAT
2. **Fill-in-blank:** "_____ and void" for NULL
3. **Trivia:** "Author of Hamlet" for SHAKESPEARE
4. **Wordplay:** "Surprised?" for ASTONISHED (with ?)
5. **Question Mark:** Indicates pun or trick

### Clue Rules
- Match tense and plurality with answer
- Abbreviations must be signaled in clue
- Foreign words must be indicated
- No repeating words from answer in clue
- Offensive content strictly prohibited

## Grid Design Patterns

### Black Square Placement
- Creates visual appeal
- Ensures word variety (mix of lengths)
- Avoids excessive fragmentation
- No unchecked squares created
- Maintains symmetry

### Common Patterns
- **Wide Open:** Few black squares, long answers
- **Compartmentalized:** More blacks, isolated sections (avoid)
- **Cheaters:** Black squares that artificially increase word count (avoid)

## Multi-Word Entries

### Convention
- Remove spaces: "REAL MADRID" → REALMADRID
- Remove articles unless integral: "LA HAINE" → LAHAINE
- Hyphenated words: Remove hyphen usually
- Acronyms: Keep as letters

### Examples
- TINAFEY (Tina Fey)
- TRACYJORDAN (Tracy Jordan)
- REALMADRID (Real Madrid)
- LAHAINE (La haine)
```

#### File 2: `nyt-features-and-gimmicks.md`

```markdown
# NYT Special Features & Gimmicks

## Rebus Squares (~4.7% of puzzles)

### What Are They?
Rebus squares contain multiple letters, symbols, or words in one square.

### Examples
- **[GREEN]:** Single square contains word "GREEN"
- **[MON]/[TUE]/[WED]:** Day abbreviations
- **[@]:** Symbol replacing "AT"
- **[FAST]:** Word in one square makes FASTING, BREAKFAST, FASTENER

### When Used
- Typically Thursday or Sunday puzzles
- Theme involves repeated element
- Adds layer of complexity
- Requires "aha" moment from solver

## Thursday Gimmicks

### Common Tricks
1. **Backward/Upward Words:** Answers written in reverse
2. **Visual Patterns:** Black squares form shapes
3. **Letter Restrictions:** Only certain letters used
4. **Blank Squares:** Strategic missing squares
5. **Outside-the-Grid:** Words extend beyond boundaries
6. **Circled Letters:** Spell theme-related word

### Examples
- Circles forming pyramid → GREATPYRAMIDOFGIZA
- Magnets touching IRON entries
- Flowers represented by grouped squares

## Difficulty Progression

### By Day of Week
**Monday:** 
- Vocabulary: Common, everyday words
- Clues: Straightforward definitions
- Theme: Simple, easy to identify

**Tuesday:**
- Vocabulary: Slightly broader
- Clues: Some misdirection
- Theme: Clear but requires thought

**Wednesday:**
- Vocabulary: Challenging but fair
- Clues: Wordplay common
- Theme: Creative concepts

**Thursday:**
- Vocabulary: Can be tricky
- Clues: Maximum creativity
- Theme: Often has gimmick or trick

**Friday:**
- Vocabulary: Difficult but gettable
- Clues: Highly misleading
- Theme: Often themeless (pure fill)

**Saturday:**
- Vocabulary: Hardest of week
- Clues: Maximum misdirection
- Theme: Themeless, pristine fill

**Sunday:**
- Vocabulary: Wednesday/Thursday level
- Size: 21×21 (larger)
- Theme: Elaborate, multiple layers

## Creating Gimmick Puzzles

### Design Process
1. Choose gimmick concept
2. Identify theme entries utilizing gimmick
3. Place theme entries with gimmick squares
4. Fill remaining grid
5. Write clues that reveal gimmick gradually

### Considerations
- Gimmick should be fair and discoverable
- First theme entry should hint at gimmick
- Not too obscure - solver should "get it"
- Test with naive solver before publishing
```

#### File 3: `clue-writing-techniques.md`

```markdown
# Clue Writing Techniques & Examples

## Clue Types with Examples

### 1. Straight Definition
The most common type.

**BANANA:**
- Monday: "Yellow fruit"
- Wednesday: "Tropical fruit rich in potassium"
- Friday: "Something you might slip on?"

**YOGA:**
- Monday: "Stretching exercise"
- Wednesday: "Practice with downward dog"
- Friday: "Way to find peace?"

### 2. Fill-in-the-Blank
Complete a famous phrase.

**NULL:**
- Monday: "_____ and void"
- Thursday: "Set to zero?"

**VOID:**
- Tuesday: "Null and _____"
- Friday: "Empty space"

### 3. Trivia/Knowledge-Based
Requires specific knowledge.

**SHAKESPEARE:**
- Monday: "Author of Hamlet"
- Wednesday: "The Bard"
- Friday: "He wrote 'To be or not to be'"

**PARIS:**
- Monday: "Capital of France"
- Wednesday: "City of Light"
- Friday: "Where to find the Louvre"

### 4. Wordplay & Puns
Creative misdirection (often with ?).

**DINER:**
- Wednesday: "Restaurant car?"
- Thursday: "One at the table"

**PRESENT:**
- Wednesday: "Gift or current?"
- Thursday: "Here and now?"

**FAST:**
- Thursday: "Quick or without food?"
- Friday: "Lent activity?"

### 5. Question Mark Clues
Indicates pun or trick.

**ASTONISHED:**
- "Surprised?" (wordplay on "stone")

**DRAMATIC:**
- "Like a play?" (straightforward but ? adds misdirection)

## Difficulty Calibration Examples

### Same Answer, Escalating Difficulty

**VISA:**
1. "Credit card type" (Monday)
2. "Entry stamp" (Tuesday)
3. "Travel document" (Wednesday)
4. "It might be required for entry" (Thursday)
5. "Way into the country?" (Friday)
6. "Overseas approval?" (Saturday)

**YOGA:**
1. "Flexibility exercise" (Monday)
2. "Practice with poses" (Tuesday)
3. "Discipline with chakras" (Wednesday)
4. "Eastern practice" (Thursday)
5. "Path to enlightenment?" (Friday)
6. "Stretching the truth?" (Saturday - wordplay)

**GREEN:**
1. "Color of grass" (Monday)
2. "Go signal" (Tuesday)
3. "Environmentally friendly" (Wednesday)
4. "Inexperienced" (Thursday - alternate meaning)
5. "Putting surface" (Friday - golf reference)
6. "Like a rookie" (Saturday)

## Advanced Techniques

### Misdirection
Lead solver to wrong answer initially.

**RACKET:**
- Bad: "Tennis equipment"
- Good: "Court din" (sounds like tennis, means noise)

**PITCHER:**
- Bad: "Baseball player"
- Good: "One on the mound or table" (baseball or water pitcher)

### Double Meanings
Use multiple meanings of answer.

**PRESENT:**
- "Gift" (noun)
- "Current" (adjective)
- Clue: "Here or wrapped?"

**SUBJECT:**
- "Topic" (noun)
- "Citizen" (noun)
- "To cause to experience" (verb)

### Cultural References
Modern or historical.

**TITANIC:**
- Monday: "Huge ship that sank"
- Wednesday: "1997 Leonardo DiCaprio film"
- Friday: "Ill-fated White Star Line vessel"

### Abbreviation Indicators
Signal that answer is abbreviation.

- "Briefly": SAN FRAN for SF
- "For short": TELEPHONE for TEL
- "Abbr.": Direct indication

## Clue Writing Process

1. **List all meanings** of answer word
2. **Identify difficulty level** needed
3. **Choose appropriate technique** for that level
4. **Write 3-5 options** at target difficulty
5. **Test clarity** - is it fair?
6. **Revise** for precision

## Common Pitfalls

❌ **Too Obscure:** "Yttrium's atomic number" for 39
✅ **Fair:** "The age Jack Benny claimed to be"

❌ **Repeating Answer:** "Green vegetable" for GREEN
✅ **Better:** "Grass color" or "Go signal"

❌ **Not Matching Tense:** "Ran" for RUNS
✅ **Match:** "Runs" for RUNS

❌ **Unclear Abbreviation:** "CA" without indicating abbr.
✅ **Clear:** "CA, e.g." or "State: Abbr."
```

#### File 4: `word-list-guidelines.md`

```markdown
# Word List Analysis & Guidelines

## Creating Personal Word Lists

### Categories of Words

**Anchor Words (8+ letters):**
- Foundation for grid structure
- Usually theme entries or strongest fill
- Examples: RASPBERRIES, EVERYTHING, CANYONING

**Good Fill (4-7 letters):**
- Solid crossword-friendly words
- Common letters, high crossing potential
- Examples: VISA, YOGA, GREEN, BANANA

**Short Fill (3 letters):**
- Necessary for grid completion
- Should be common, not crosswordese
- Examples: THE, AND, FOR, ARE

### Letter Frequency Analysis

**Common Letters** (easier to cross):
- E, T, A, O, I, N, S, H, R, D, L, U

**Moderate Letters:**
- C, M, W, F, G, Y, P, B

**Tough Letters** (harder to cross):
- V, K, J, X, Q, Z

### Word Scoring

**90-100 (Premium Fill):**
- Fresh, interesting words
- Modern vocabulary
- Culturally relevant
- Examples: PODCAST, EMOJI, WIFI

**70-89 (Good Fill):**
- Solid, crossword-friendly
- Common but not stale
- Examples: VISA, YOGA, GREEN

**50-69 (Acceptable Fill):**
- Gets the job done
- Not exciting but not bad
- Examples: AREA, IDEA, ORAL

**30-49 (Crosswordese):**
- Overused in puzzles
- Rarely seen outside crosswords
- Examples: ETUI, ESNE, OLIO

**1-29 (Last Resort):**
- Obscure, poor crossing
- Use only if necessary
- Examples: QOPH, ZZYZX

## Analyzing Personal Word Lists

### Step-by-Step Analysis

1. **Count by Length:**
```
3-letter: X words
4-letter: Y words
5-letter: Z words
6+letter: W words
```

2. **Identify Anchors:**
List words 8+ letters - these will structure your grid.

3. **Check Letter Frequency:**
Count vowels vs. consonants, common vs. tough letters.

4. **Assess Crossing Potential:**
Flag words with Q, X, Z, J (harder to cross).

5. **Estimate Fillability:**
More words with common letters = easier to fill grid.

### Example Analysis Output

```
Word List: Arthur's Birthday Puzzle
Total Words: 45

Length Distribution:
- 3-letter: 8 words (18%)
- 4-letter: 12 words (27%)
- 5-letter: 10 words (22%)
- 6-letter: 7 words (16%)
- 7+ letter: 8 words (18%)

Anchor Words (8+ letters):
1. RASPBERRIES (11) - Excellent anchor, common letters
2. EVERYTHING (10) - Very strong, all common letters
3. CANYONING (9) - Good, one tricky letter (Y)

High Crossing Potential:
- GREEN (5) - All common letters
- YOGA (4) - Great vowel-consonant balance
- BANANA (6) - Repeating As, easy to work with

Challenging Words:
- GNOCCHI (7) - Double C, double C
- EPFL (4) - Acronym, unusual pattern
- SCH (3) - Two consonants, no vowels

Recommendations:
1. Start with RASPBERRIES as central horizontal (row 7)
2. Place EVERYTHING as vertical crossing
3. Use YOGA, GREEN, BANANA as strong secondary fill
4. Save GNOCCHI, EPFL for easier-to-fill spots
5. Consider adding more 4-letter words with common letters
6. Grid size: 15×15 (good variety of lengths)
```

## Building a Balanced Word List

### Ideal Distribution for 15×15 Grid
- 3-letter: 15-20 words
- 4-letter: 20-25 words
- 5-letter: 15-20 words
- 6-letter: 10-15 words
- 7+ letter: 8-12 words
- **Total: 70-90 words**

### Coverage Guidelines
- **Vowels:** At least 40% of letters should be vowels
- **Common letters:** 60%+ should be E, T, A, O, I, N, S, H, R
- **Tough letters:** <5% should be Q, X, Z, J
- **Variety:** Mix of nouns, verbs, adjectives

### Testing Your List
1. Try pattern matching: can you find ?A?A? words?
2. Check crossing: can QUIZ cross with JAZZ?
3. Autofill test: can small grid fill with your words only?

## Enhancing Word Lists

### When Personal List is Insufficient

**Add from Standard Lists:**
- Keep your personal words as anchors/theme
- Supplement with standard crossword fill
- Blend ratio: 30% personal, 70% standard

**Target Additions:**
- More 4-letter words (most flexible)
- Words with common letters (ETAOIN)
- Variety of starting letters
- Different ending patterns

### Multi-Word Entries

**Handling Phrases:**
- "Real Madrid" → REALMADRID
- "La haine" → LAHAINE
- "Drivers license" → DRIVERSLICENSE (if fits)

**Guidelines:**
- Remove spaces
- Keep as single entry
- Usually score slightly lower (harder to clue)
- Great for personalization

### Domain-Specific Words

**For Sports Fan:**
- Team names, player names, venues
- Keep current (players on teams now)

**For Foodie:**
- Ingredients, dishes, cooking terms
- Mix common and unique items

**For Traveler:**
- Cities, countries, landmarks
- Include personal trip locations
```

#### File 5: `grid-design-patterns.md`

```markdown
# Grid Design Patterns & Templates

## Standard Grid Patterns

### 11×11 Grids
**Use Case:** Quick puzzles, limited word lists
**Theme Entries:** 1-2 long words
**Black Squares:** ~16-20 (16-18%)
**Word Count:** 55-65 words

**Common Patterns:**
- Simple cross: One long across, one long down
- Corner blocks: Blacks in corners for symmetry
- Open center: Minimal blacks in middle

### 15×15 Grids (Most Common)
**Use Case:** Standard daily crossword
**Theme Entries:** 3-5 entries
**Black Squares:** ~38 (17%)
**Word Count:** 72-78 words

**Common Patterns:**
- Three-stack: Three long across words
- Pinwheel: Rotational theme placement
- Diagonal: Theme words on diagonals
- Quad: Four theme entries in quadrants

### 21×21 Grids (Sunday Size)
**Use Case:** Elaborate themes
**Theme Entries:** 6-10 entries
**Black Squares:** ~75 (17%)
**Word Count:** 130-140 words

**Common Patterns:**
- Five-stack: Five 15-letter entries
- Multiple layers: Primary and secondary themes
- Circumference: Theme words around edges

## Design Principles

### Visual Balance
- **Symmetry:** 180° rotational always
- **Distribution:** Black squares spread evenly
- **No Fragments:** Avoid isolated sections
- **No Checkerboards:** Avoid too many blacks

### Fillability Considerations

**Easy to Fill:**
- More short words (3-4 letters)
- Open areas with many connections
- Common letter combinations
- Fewer long words

**Hard to Fill:**
- Many long words (8+ letters)
- Isolated corners
- Unusual letter requirements
- Highly constrained crossings

### Word Length Mix

**Ideal Distribution (15×15):**
- 3-letter: ~25-30 words (33-40%)
- 4-letter: ~20-25 words (27-33%)
- 5-letter: ~10-15 words (13-20%)
- 6-letter: ~8-12 words (11-16%)
- 7+ letter: ~5-10 words (7-13%)

## Placing Theme Entries

### Symmetric Placement

**For 3 Theme Entries:**
```
■ Theme 1 (row 3, across)
■ Theme 2 (row 8, across, middle)
■ Theme 3 (row 13, across, symmetric to Theme 1)
```

**For 4 Theme Entries:**
```
■ Theme 1 (row 3, across)
■ Theme 2 (row 7, across)
■ Theme 3 (row 9, across, symmetric to Theme 2)
■ Theme 4 (row 13, across, symmetric to Theme 1)
```

### Grid Numbering

**Auto-Numbering Rules:**
1. Scan left-to-right, top-to-bottom
2. Number any cell that:
   - Starts an across word (white cell, black/edge to left)
   - OR starts a down word (white cell, black/edge above)
3. Increment sequentially
4. Each cell gets ONE number max

## Common Patterns Library

### Pattern 1: Simple Cross
```
Best for: Personal puzzles, limited word lists
Complexity: Low

    □□□□□■□□□□□
    □□□□□■□□□□□
    □□□□□■□□□□□
    □□□□□□□□□□□
    □□□□□□□□□□□
    ■■■□□□□□■■■
    □□□□□□□□□□□
    □□□□□□□□□□□
    □□□□□■□□□□□
    □□□□□■□□□□□
    □□□□□■□□□□□
```

### Pattern 2: Pinwheel
```
Best for: Themed puzzles, good aesthetic
Complexity: Medium

    □□□□□□□□□□□
    □■□□□□□□□■□
    □□■□□□□□■□□
    □□□■□□□■□□□
    □□□□■□■□□□□
    □□□□□■□□□□□
    □□□□■□■□□□□
    □□□■□□□■□□□
    □□■□□□□□■□□
    □■□□□□□□□■□
    □□□□□□□□□□□
```

### Pattern 3: Open Grid
```
Best for: Strong word lists, varied lengths
Complexity: High

    □□□□□□□□□□□
    □□□□□□□□□□□
    □□■□□□□□■□□
    □□□□□□□□□□□
    □□□□□■□□□□□
    ■■□□□□□□□■■
    □□□□□■□□□□□
    □□□□□□□□□□□
    □□■□□□□□■□□
    □□□□□□□□□□□
    □□□□□□□□□□□
```

## Black Square Strategy

### Initial Placement
1. Place theme entries first
2. Add symmetry-required blacks
3. Add strategic blacks to:
   - Break up long words
   - Create fillable sections
   - Maintain ~17% ratio

### Avoiding Problems

**DON'T:**
- Create 2-letter words
- Isolate regions
- Create unchecked squares
- Exceed 17% black squares
- Put blacks in corners (usually)

**DO:**
- Maintain symmetry always
- Check connectivity
- Keep sections manageable
- Leave crossing options open

## Validation Checklist

Before finalizing grid design:
- [ ] 180° rotational symmetry verified
- [ ] All white squares connected
- [ ] No unchecked squares
- [ ] All words ≥3 letters
- [ ] Black square count ≤17%
- [ ] Word count within limits
- [ ] Theme entries placed symmetrically
- [ ] Grid looks aesthetically balanced
```

---

### Step 4: Test Your Claude.ai Project

Try these example conversations to verify setup:

**Test 1: Theme Development**
```
User: "I want to create a crossword for my partner's birthday. 
       They love: raspberries, yoga, French culture, Real Madrid,
       and cooking. What theme should I use?"

Expected Response:
- Brainstorm 3-5 theme concepts
- Suggest starting with longest words as anchors
- Recommend grid size
- Explain pros/cons of each approach
```

**Test 2: Word List Analysis**
```
User: "Here's my word list: [paste 20-30 words]
       Can you analyze it?"

Expected Response:
- Length distribution
- Identify anchor words
- Assess crossing potential
- Point out any difficult words
- Recommend grid size and approach
```

**Test 3: Clue Generation**
```
User: "I need clues for: BANANA, YOGA, GREEN
       Medium difficulty (Wednesday level)"

Expected Response:
- 3-5 clue options per word
- Mix of clue types
- Appropriate difficulty level
- Explanation of which is best
```

---

## Workflow Examples

### Example 1: Complete Puzzle Creation

**User Session:**

```
[In Claude.ai Project]

User: "I want to create a birthday crossword. Here are words related to Arthur:
RASPBERRIES, YOGA, GREEN, BANANA, REALMADRID, LAHAINE, EPFL, GNOCCHI,
EVERYTHING, TRACYJORDAN, CANTONESE, CANYONING"

Claude: [Analyzes word list]
"Great word list! Here's my analysis:

Anchor Words:
- RASPBERRIES (11) - Excellent centerpiece
- EVERYTHING (10) - Very strong
- TRACYJORDAN (11) - Good but watch for J

Recommendation: 15×15 grid with RASPBERRIES as horizontal centerpiece at row 7-8.

Theme concept: 'Arthur's Favorites' - personal interests

Next steps:
1. Use Claude Code to create grid: `crossword new --size 15 --output arthur.json`
2. Place RASPBERRIES first
3. Autofill with your word list + standard fill
4. Come back for clue writing"

[User switches to Claude Code]

$ crossword new --size 15 --output arthur.json
$ crossword fill arthur.json --wordlist arthurs-words.txt

[Back to Claude.ai Project]

User: "Grid is filled! I need clues for these words: [list]"

Claude: [Generates clues]
"Here are clues for Arthur's puzzle (Wednesday difficulty):

RASPBERRIES (11 letters, 1-Across):
1. "Arthur's favorite breakfast topping" (personal - recommended)
2. "Red berries often in jam" (straightforward)
3. "Fruit that's berry good" (wordplay with ?)

YOGA (4 letters, 5-Down):
1. "Arthur's morning stretching routine" (personal)
2. "Practice with downward dog" (standard)
3. "Flexibility discipline" (formal)

..."

[User switches to Claude Code for export]

$ crossword export arthur.json --format html --output arthur-puzzle.html
```

---

## Integration with Claude Code

### Clear Division of Responsibilities

**Claude.ai Project (Strategic):**
- ✅ Theme brainstorming
- ✅ Word list analysis
- ✅ Clue writing
- ✅ Grid design consultation
- ✅ Creative decisions
- ❌ Code implementation
- ❌ Pattern matching execution
- ❌ File operations

**Claude Code (Tactical):**
- ✅ Pattern matching (`crossword pattern "?I?A"`)
- ✅ Grid autofill (`crossword fill puzzle.json`)
- ✅ File creation/export
- ✅ Algorithm execution
- ❌ Creative clue writing
- ❌ Theme concept development
- ❌ Strategic planning

### Handoff Pattern

```
[User in Claude.ai Project discussing theme]
Claude: "Great theme! Now use Claude Code to implement:
         `crossword new --size 15 --output puzzle.json`"

[User switches to Claude Code terminal]
[Executes command]

[Back to Claude.ai Project]
User: "Grid created! What's next?"
Claude: "Now place your theme words and autofill..."
```

---

## Maintenance & Updates

### Regular Updates

**Monthly:**
- Review clue database for freshness
- Update cultural references
- Add new pattern examples

**When New Puzzles are Published:**
- Document interesting techniques
- Add examples to knowledge base
- Update best practices

**When Rules Change:**
- Update standards document
- Notify via custom instructions
- Provide migration guide

---

## Success Metrics

Your Claude.ai Project is well-configured if:

✅ It generates appropriate theme ideas quickly
✅ Word list analysis is detailed and actionable
✅ Clues are varied and properly difficulty-calibrated
✅ It correctly defers to Claude Code for implementation
✅ Recommendations are specific and justified
✅ Integration between Claude.ai and Claude Code is seamless

---

## Troubleshooting

### Issue: Claude tries to write code
**Solution:** Emphasize in custom instructions: "Never write code"

### Issue: Clues all same difficulty
**Solution:** Explicitly request difficulty level in prompt

### Issue: Generic advice, not personalized
**Solution:** Always share word list and recipient context

### Issue: Doesn't reference Claude Code commands
**Solution:** Add more examples to custom instructions

---

## Final Checklist

Before starting crossword construction:

- [ ] Claude.ai Project created
- [ ] Custom instructions added and tested
- [ ] All 5 knowledge base files uploaded
- [ ] Test conversations completed successfully
- [ ] Claude Code implementation completed
- [ ] Integration between systems verified
- [ ] Sample word list prepared
- [ ] Ready to create first puzzle!

---

**You're now ready to create amazing crosswords with your personalized construction system!**
