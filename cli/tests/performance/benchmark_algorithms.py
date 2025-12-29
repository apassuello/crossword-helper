"""
Benchmark script comparing Regex vs Trie pattern matching algorithms.

Tests performance with various:
- Pattern types (exact, few wildcards, many wildcards)
- Wordlist sizes (small, medium, large)
- Score thresholds

Generates detailed performance report.
"""

import time
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.fill.word_list import WordList
from src.fill.pattern_matcher import PatternMatcher
from src.fill.trie_pattern_matcher import TriePatternMatcher


class BenchmarkResult:
    """Store benchmark results for comparison."""

    def __init__(self, name, regex_time, trie_time, result_count):
        self.name = name
        self.regex_time = regex_time
        self.trie_time = trie_time
        self.result_count = result_count
        self.speedup = regex_time / trie_time if trie_time > 0 else 0

    def __str__(self):
        return (f"{self.name:40} | "
                f"Regex: {self.regex_time*1000:7.2f}ms | "
                f"Trie: {self.trie_time*1000:7.2f}ms | "
                f"Speedup: {self.speedup:5.1f}x | "
                f"Results: {self.result_count:5}")


def load_wordlist(wordlist_path: Path, max_words: int = None):
    """Load words from file."""
    words = []
    with open(wordlist_path, 'r') as f:
        for line in f:
            word = line.strip().upper()
            if word and not word.startswith('#'):
                words.append(word)
                if max_words and len(words) >= max_words:
                    break
    return WordList(words)


def benchmark_pattern(pattern: str, regex_matcher: PatternMatcher,
                     trie_matcher: TriePatternMatcher, min_score: int = 30,
                     max_results: int = 100, iterations: int = 10):
    """Benchmark a single pattern with both algorithms."""

    # Warm up (first run may include cache misses)
    regex_matcher.find(pattern, min_score, max_results)
    trie_matcher.find(pattern, min_score, max_results)

    # Benchmark regex
    start = time.perf_counter()
    for _ in range(iterations):
        regex_results = regex_matcher.find(pattern, min_score, max_results)
    regex_time = (time.perf_counter() - start) / iterations

    # Benchmark trie
    start = time.perf_counter()
    for _ in range(iterations):
        trie_results = trie_matcher.find(pattern, min_score, max_results)
    trie_time = (time.perf_counter() - start) / iterations

    # Verify results match
    regex_words = {w for w, s in regex_results}
    trie_words = {w for w, s in trie_results}

    if regex_words != trie_words:
        print(f"WARNING: Results differ for pattern '{pattern}'!")
        print(f"  Regex: {len(regex_words)} words")
        print(f"  Trie: {len(trie_words)} words")
        print(f"  Difference: {regex_words ^ trie_words}")

    return BenchmarkResult(
        f"Pattern: {pattern} (min_score={min_score})",
        regex_time,
        trie_time,
        len(regex_results)
    )


def run_benchmarks(wordlist_path: Path, wordlist_size: int = None):
    """Run comprehensive benchmark suite."""

    print(f"\n{'='*90}")
    print("BENCHMARK: Pattern Matching Performance Comparison")
    print(f"{'='*90}")

    # Load wordlist
    print(f"\nLoading wordlist from: {wordlist_path}")
    if wordlist_size:
        print(f"Limiting to first {wordlist_size:,} words")

    word_list = load_wordlist(wordlist_path, wordlist_size)
    print(f"Loaded {len(word_list):,} words")

    # Create matchers
    print("\nInitializing pattern matchers...")

    regex_start = time.perf_counter()
    regex_matcher = PatternMatcher(word_list)
    regex_init_time = time.perf_counter() - regex_start

    trie_start = time.perf_counter()
    trie_matcher = TriePatternMatcher(word_list)
    trie_init_time = time.perf_counter() - trie_start

    print(f"  Regex initialization: {regex_init_time*1000:.2f}ms")
    print(f"  Trie initialization: {trie_init_time*1000:.2f}ms")
    print(f"  Trie build overhead: {(trie_init_time - regex_init_time)*1000:.2f}ms")

    # Test patterns
    test_patterns = [
        # (pattern, min_score, description)
        ("CAT", 30, "Exact match (3 letters)"),
        ("HOUSE", 30, "Exact match (5 letters)"),
        ("C?T", 30, "1 wildcard (3 letters)"),
        ("?I?A", 30, "2 wildcards (4 letters)"),
        ("RE??", 30, "2 wildcards (4 letters)"),
        ("???", 30, "All wildcards (3 letters)"),
        ("????", 30, "All wildcards (4 letters)"),
        ("?????", 30, "All wildcards (5 letters)"),
        ("C?????", 30, "5 wildcards (6 letters)"),
        ("?O?N?A?N", 30, "5 wildcards (8 letters)"),
        ("???????????", 30, "All wildcards (11 letters)"),
        ("A?E", 50, "2 wildcards, high score"),
        ("????", 70, "All wildcards, very high score"),
    ]

    print(f"\n{'='*90}")
    print("Running Benchmarks (10 iterations per pattern)...")
    print(f"{'='*90}")
    print(f"{'Pattern':<40} | {'Regex':<12} | {'Trie':<12} | {'Speedup':<8} | {'Results'}")
    print(f"{'-'*90}")

    results = []

    for pattern, min_score, description in test_patterns:
        result = benchmark_pattern(
            pattern,
            regex_matcher,
            trie_matcher,
            min_score=min_score,
            max_results=100,
            iterations=10
        )
        results.append(result)
        print(result)

    # Summary statistics
    print(f"\n{'='*90}")
    print("Summary Statistics")
    print(f"{'='*90}")

    avg_speedup = sum(r.speedup for r in results) / len(results)
    min_speedup = min(r.speedup for r in results)
    max_speedup = max(r.speedup for r in results)

    total_regex_time = sum(r.regex_time for r in results)
    total_trie_time = sum(r.trie_time for r in results)

    print("\nSpeedup Statistics:")
    print(f"  Average: {avg_speedup:.1f}x faster")
    print(f"  Minimum: {min_speedup:.1f}x faster")
    print(f"  Maximum: {max_speedup:.1f}x faster")

    print("\nTotal Time (all patterns):")
    print(f"  Regex: {total_regex_time*1000:.2f}ms")
    print(f"  Trie:  {total_trie_time*1000:.2f}ms")
    print(f"  Savings: {(total_regex_time - total_trie_time)*1000:.2f}ms ({(1 - total_trie_time/total_regex_time)*100:.1f}% faster)")

    # Cache statistics
    print(f"\n{'='*90}")
    print("Cache Performance")
    print(f"{'='*90}")

    regex_cache_stats = regex_matcher.get_cache_stats() if hasattr(regex_matcher, 'get_cache_stats') else None
    trie_cache_stats = trie_matcher.get_cache_stats()

    if regex_cache_stats:
        print("\nRegex Cache:")
        print(f"  Hit rate: {regex_cache_stats['hit_rate']}")
        print(f"  Cache size: {regex_cache_stats['cache_size']}")

    print("\nTrie Cache:")
    print(f"  Hit rate: {trie_cache_stats['hit_rate']}")
    print(f"  Cache size: {trie_cache_stats['cache_size']}")

    # Trie statistics
    trie_stats = trie_matcher.get_trie_stats()
    print("\nTrie Structure:")
    print(f"  Total words: {trie_stats['total_words']:,}")
    print(f"  Total nodes: {trie_stats['total_nodes']:,}")
    print(f"  Avg nodes/word: {trie_stats['avg_nodes_per_word']:.1f}")
    print(f"  Length tries: {trie_stats['num_length_tries']}")
    print(f"  Length ranges: {trie_stats['length_ranges']}")

    print(f"\n{'='*90}")


def main():
    """Run benchmarks with different wordlist sizes."""

    # Find wordlist files
    project_root = Path(__file__).parent.parent.parent
    wordlists_dir = project_root / 'data' / 'wordlists'

    # Test with different wordlist sizes
    test_configs = [
        # (wordlist_file, max_words, description)
        ('core/common_3_letter.txt', None, 'Small wordlist (3-letter words)'),
        ('core/crosswordese.txt', None, 'Medium wordlist (crosswordese)'),
        ('comprehensive.txt', 10000, 'Large wordlist (10k words)'),
        ('comprehensive.txt', 50000, 'Very large wordlist (50k words)'),
        ('comprehensive.txt', None, 'Huge wordlist (full comprehensive ~454k words)'),
    ]

    for wordlist_file, max_words, description in test_configs:
        wordlist_path = wordlists_dir / wordlist_file

        if not wordlist_path.exists():
            print(f"\nSkipping {description}: {wordlist_path} not found")
            continue

        print(f"\n\n{'#'*90}")
        print(f"# {description}")
        print(f"{'#'*90}")

        try:
            run_benchmarks(wordlist_path, max_words)
        except Exception as e:
            print(f"\nERROR: {e}")
            import traceback
            traceback.print_exc()

        # Add delay between tests
        time.sleep(1)

    print(f"\n\n{'='*90}")
    print("BENCHMARK COMPLETE")
    print(f"{'='*90}\n")


if __name__ == '__main__':
    main()
