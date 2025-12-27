# Crossword Wordlist Documentation

**Last Updated:** December 27, 2025

---

## Current Wordlist: `comprehensive.txt`

### Source
- **Base Source:** Chris Jones' crossword-wordlist
  Repository: https://github.com/christophsjones/crossword-wordlist
- **Original Size:** 175,873 entries (scored)
- **Compiled From:** NYT, WSJ, WaPo, UKACD, Peter Broda's list, Peter Norvig's frequency counts

### Filtering Applied
The original wordlist was aggressively filtered to remove low-quality entries:

**Filter Criteria:**
1. **Score >= 50** (common words) OR **Score >= 40 AND Length >= 5** (acceptable longer words)
2. **Alphabetic only** (no numbers, punctuation)
3. **Single words only** (no spaces)
4. **Length 3-21 characters** (reasonable for crosswords)
5. **Blacklist removal** (45 known gibberish words removed)

**Blacklisted Words:**
- 3-letter crosswordese: SSS, ORS, TOS, ASO, ERS, III, NNN, MMM, etc.
- Abbreviations: NSA, DEA, TSN, UAE, IOS, etc.
- Compound gibberish: ASMAD, ARNES, ASTHE, NOEAR, SDATE, etc.

### Final Statistics
- **Total Entries:** 44,024 unique words
- **File Size:** ~400 KB
- **Quality:** High (crosswordese and gibberish removed)

### Scoring System (from original)
According to Chris Jones:
- **50** = common word or phrase you wouldn't hesitate to use
- **25** = acceptable word
- **2** = lowest score in the list

Our filter keeps only score >= 40 (with exceptions for longer words).

---

## Backup

The previous wordlist (contaminated version) is backed up as:
```
comprehensive.txt.backup_20251227
```

---

## Usage with Autofill

### Recommended Settings
For best results when using autofill:

```python
# High quality fills only
min_score = 50

# Balanced (allows some uncommon words)
min_score = 40

# Maximum flexibility (use with caution)
min_score = 30
```

### Testing the Wordlist
To verify quality:

```bash
# Check for known gibberish words (should return empty)
grep -E "^(SSS|ORS|TOS|ASMAD|ASTHE)$" data/wordlists/comprehensive.txt

# Count total entries
wc -l data/wordlists/comprehensive.txt

# Sample random words
shuf data/wordlists/comprehensive.txt | head -20
```

---

## Wordlist Quality Comparison

| Metric | Old (Contaminated) | New (Filtered) |
|--------|-------------------|----------------|
| Total Words | ~300,000+ | 44,024 |
| Gibberish Words | Many (SSS, ORS, etc.) | None (removed) |
| Abbreviations | Many | Minimal |
| Quality Check | ❌ Failed | ✅ Passed |

---

## Future Improvements

Consider adding:
1. **Themed wordlists** for specific puzzle types
2. **Frequency scoring** from modern corpora
3. **Regional variations** (UK vs US English)
4. **Contemporary terms** (2024-2025 additions)

---

## License & Attribution

The original wordlist is from Chris Jones' crossword-wordlist repository, compiled from freely available sources including:
- New York Times crosswords
- Wall Street Journal crosswords
- Washington Post crosswords
- UKACD (UK Advanced Cryptics Dictionary)
- Peter Broda's word list
- Peter Norvig's frequency counts

**License:** Free to use with attribution
**Repository:** https://github.com/christophsjones/crossword-wordlist

---

**Filtered by:** Claude Code
**Date:** December 27, 2025
**Filter Script:** Available upon request
