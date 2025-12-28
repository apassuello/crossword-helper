# Theme List Feature - User Guide

**Feature**: Theme Word Priority in Autofill
**Version**: 1.0
**Date**: December 28, 2025

---

## What is a Theme List?

A **theme list** is a custom wordlist that you designate to receive priority during autofill. When you mark a wordlist as your theme list, the autofill algorithm will:

- ✅ **Try theme words first** before other words
- ✅ **Add +50 quality bonus** to theme words (making them more competitive)
- ✅ **Maximize theme word usage** while still completing the grid

This is perfect for creating themed puzzles around specific topics like:
- 🍎 **Foods** (APPLE, BERRY, GRAPE, LEMON...)
- ⚽ **Sports** (SOCCER, TENNIS, HOCKEY...)
- 🎬 **Movies** (AVATAR, BATMAN, FROZEN...)
- 🌍 **Places** (PARIS, TOKYO, ROME...)
- 📚 **Any topic you choose!**

---

## How to Use Theme Lists

### Step 1: Upload Your Custom Wordlist

1. Click on the **"Word Lists"** tab
2. Click **"Upload Custom Wordlist"** button
3. Select a `.txt` file with one word per line:
   ```
   APPLE
   BERRY
   GRAPE
   LEMON
   MELON
   ```
4. Click **"Upload"**
5. Your wordlist appears in the custom lists section!

### Step 2: Select Your Wordlists for Autofill

1. Click on the **"Autofill"** tab
2. Scroll to the **"🎨 Custom Lists"** section
3. **Check the boxes** for wordlists you want to include
4. You'll see something like:
   ```
   ✓ comprehensive (built-in)
   ✓ my_food_words.txt (custom)
   ✓ my_sports_words.txt (custom)
   ```

### Step 3: Mark One as Your Theme List

1. After checking a custom wordlist, you'll see a **"⭐ Theme List"** radio button appear
2. **Click the radio button** next to the wordlist you want to prioritize
3. An **orange banner** appears showing:
   ```
   📌 Using "my_food_words.txt" as theme list
   ```

**Important**: Only ONE wordlist can be the theme list at a time!

### Step 4: Run Autofill

1. Set up your grid as normal
2. Configure other autofill settings (algorithm, timeout, etc.)
3. Click **"Run Autofill"**
4. Watch as theme words are used preferentially! 🎉

---

## Example: Creating a Food-Themed Puzzle

### Scenario

You want to create a crossword puzzle about **fruits and vegetables**.

**Your Theme Wordlist** (`fruits_veggies.txt`):
```
APPLE
BERRY
GRAPE
LEMON
MELON
PEACH
CARROT
CELERY
RADISH
TOMATO
```

**Your Grid**: 11×11 with standard black squares

### Steps

1. **Upload** `fruits_veggies.txt` via Word Lists panel
2. **Go to Autofill panel**
3. **Check** both:
   - ✓ `comprehensive` (for general fill)
   - ✓ `fruits_veggies.txt` (your theme)
4. **Click "⭐ Theme List"** next to `fruits_veggies.txt`
5. **Run autofill**

### Expected Result

```
A P P L E . . . . . .
P . . . M . . . . . .
P . . . E . . . . . .
L . . . L . . . . . .
E . . . O . . . . . .
. . . . N . . . . . .
. . . G R A P E . . .
. . . . A . . . . . .
. . . . D . . . . . .
. . . . I . . . . . .
. . . . S H . . . . .
```

**Theme Words Used**: APPLE, MELON, GRAPE, RADISH (4 out of 10)
**Coverage**: ~40% of grid = excellent theme integration!

---

## How Theme Priority Works (Technical)

When you designate a theme list, the autofill algorithm:

1. **Finds all matching words** for each empty slot
2. **Separates** theme words from non-theme words
3. **Adds +50 bonus** to theme word scores:
   ```
   APPLE (quality: 60)  → APPLE (priority: 110) ⭐
   ZEBRA (quality: 100) → ZEBRA (unchanged: 100)
   ```
4. **Sorts theme words first**, then non-theme:
   ```
   Ordered: [APPLE (110), ZEBRA (100), ...]
                ⭐ theme      regular
   ```
5. **Tries theme words first** during fill

This ensures maximum theme usage while maintaining grid quality!

---

## Tips for Best Results

### ✅ DO

- **Use 20-50 word theme lists** for 11×11 grids
- **Use 50-100 word theme lists** for 15×15 grids
- **Include variety of lengths** (3-15 letters)
- **Mix common and uncommon words** for flexibility
- **Check both comprehensive + theme** wordlists

### ❌ DON'T

- Don't use **very small lists** (<10 words) on large grids
- Don't expect **100% theme usage** (unrealistic with constraints)
- Don't use **only obscure words** (makes fill harder)
- Don't **uncheck comprehensive** (you need fill flexibility)

### Realistic Expectations

| Grid Size | Theme List Size | Expected Coverage |
|-----------|----------------|-------------------|
| 11×11     | 20 words       | 30-50%           |
| 15×15     | 50 words       | 20-40%           |
| 21×21     | 100 words      | 15-30%           |

**Why not 100%?**
- Crossing constraints limit available patterns
- Some slots may have no matching theme words
- Grid symmetry and structure affect fill

---

## Troubleshooting

### "I marked a theme list but no theme words appear!"

**Possible Causes:**
1. **Pattern constraints**: Theme words don't match the available patterns
2. **Score too low**: Theme words filtered by min_score setting
3. **Already used**: Word reuse prevention excludes theme words

**Solutions:**
- Increase theme list size (more options)
- Lower min_score in autofill settings
- Use more common theme words

### "Theme list selection disappeared!"

**Cause**: You unchecked the wordlist

**Solution**: Check the custom wordlist box again, then click "⭐ Theme List"

### "Can I use multiple theme lists?"

**No** - only ONE theme list at a time. However, you can:
- Combine multiple wordlists into one `.txt` file
- Upload the combined file as your theme list
- This gives you the best of both worlds!

### "Do I need to keep comprehensive checked?"

**Yes, highly recommended!** The comprehensive wordlist provides:
- Fill flexibility for difficult slots
- High-quality common words
- Backup when theme words don't fit

Think of it this way:
- **Theme list** = preferred words (tried first)
- **Comprehensive** = safety net (used when needed)

---

## Advanced: Creating Effective Theme Lists

### 1. **Balanced Word Lengths**

Good distribution across lengths:
```
3 letters: 10% (ACE, ART, ELM...)
4 letters: 15% (BEAR, DEER, HAWK...)
5 letters: 25% (EAGLE, HORSE, TIGER...)
6 letters: 20% (GIRAFFE would be 7, so FALCON...)
7+ letters: 30% (CHEETAH, ELEPHANT...)
```

### 2. **Crossword-Friendly Words**

Prefer words with:
- ✅ Common letters (E, A, R, I, O, T, N, S)
- ✅ Good vowel/consonant balance
- ✅ Multiple crossing possibilities

Avoid:
- ❌ All-consonant clusters (RHYTHM)
- ❌ Uncommon letter combinations (QZ, XJ)
- ❌ Very long single-topic words

### 3. **Themed but Fillable**

**Good Theme List** (Animals):
```
APE, BAT, CAT, DOG, ELK, FOX, GNU    (3-letter glue words)
BEAR, DEER, HAWK, LION, SEAL, WOLF   (4-letter variety)
EAGLE, HORSE, MOOSE, OTTER, TIGER    (5-letter strong)
BEAVER, FALCON, JAGUAR, RABBIT       (6+ letter featured)
```

**Poor Theme List** (Animals):
```
ARCHAEOPTERYX    (too long, obscure)
QUETZALCOATLUS   (impossible letters)
XENOPUS          (X start, hard to cross)
```

### 4. **Test Your List**

Before using on a real puzzle:
1. Upload to Word Lists panel
2. Use on a small test grid (11×11)
3. Check coverage percentage
4. Adjust list based on results

---

## UI Reference

### Autofill Panel - Custom Lists Section

```
┌─────────────────────────────────────────┐
│ 🎨 Custom Lists                         │
├─────────────────────────────────────────┤
│                                          │
│ ☐ my_food_words.txt                     │
│                                          │
│ ☑ my_sports_words.txt                   │
│   ⊙ ⭐ Theme List     (purple badge)    │
│                                          │
│ ☐ my_movies.txt                         │
│                                          │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ 📌 Using "my_sports_words.txt" as      │
│    theme list                            │
│    (orange info banner)                  │
└─────────────────────────────────────────┘
```

**Visual Indicators:**
- ✓ **Checkbox**: Include this wordlist
- ⭐ **Radio button**: Mark as theme (purple highlight)
- 📌 **Orange banner**: Confirms active theme list

---

## FAQ

**Q: Do theme words get mandatory inclusion?**
A: No - theme words are **prioritized** (tried first, +50 bonus) but not mandatory. If a theme word doesn't fit due to crossings, non-theme words are used.

**Q: Can I have theme words AND theme entries?**
A: Yes! Theme words (from custom list) and theme entries (pre-filled answers) work together. Theme entries are placed first, then autofill prioritizes theme words.

**Q: Does theme list work with iterative repair?**
A: Yes! Both beam search and iterative repair prioritize theme words.

**Q: What happens if I clear theme list mid-fill?**
A: The theme list setting only applies when you click "Run Autofill". Changing it mid-fill has no effect until next autofill run.

**Q: Can I export/share my theme list?**
A: Yes! Custom wordlists are stored in `data/wordlists/custom/`. Copy the `.txt` file to share with others.

---

## Summary

**Theme List Feature** lets you create themed crossword puzzles by:
1. Uploading a custom wordlist with themed words
2. Marking it as your theme list in the Autofill panel
3. Running autofill to preferentially use those words

**Result**: More thematic puzzles with higher topic coherence!

**Perfect for**:
- Themed puzzle construction
- Niche vocabulary puzzles
- Educational crosswords
- Branded/custom content

---

**Questions or Issues?**

See the main user guide or technical documentation for more details.
