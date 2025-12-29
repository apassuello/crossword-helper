"""
Command-line interface for crossword builder.

Provides commands for creating, filling, validating, and exporting crossword grids.
"""

import click
import json
import sys
from pathlib import Path
from typing import Optional

from .core.grid import Grid
from .core.validator import GridValidator
from .core.numbering import GridNumbering
from .fill.word_list import WordList
from .fill.pattern_matcher import PatternMatcher
from .fill.autofill import Autofill
from .export.html_exporter import HTMLExporter


@click.group()
@click.version_option(version="2.0.0", prog_name="crossword")
def cli():
    """
    Crossword Builder CLI - Create and fill crossword puzzles.

    Phase 2: Advanced CLI tool with autofill engine.
    """


@cli.command()
@click.option(
    "--size",
    type=click.Choice(["11", "15", "21"]),
    default="15",
    help="Grid size (11x11, 15x15, or 21x21)",
)
@click.option(
    "--output", "-o", type=click.Path(), required=True, help="Output file path (.json)"
)
def new(size: str, output: str):
    """Create a new empty crossword grid."""
    size_int = int(size)

    # Create empty grid
    grid = Grid(size_int)

    # Save to file
    data = grid.to_dict()

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)

    click.echo(f"✓ Created {size}×{size} grid: {output}")
    click.echo(f"  Size: {size_int}×{size_int}")
    click.echo("  Black squares: 0")
    click.echo("  Ready to fill!")


@cli.command()
@click.argument("grid_file", type=click.Path(exists=True))
def validate(grid_file: str):
    """Validate a crossword grid against NYT standards."""
    # Load grid
    with open(grid_file, "r") as f:
        data = json.load(f)

    grid = Grid.from_dict(data)

    # Validate
    is_valid, errors = GridValidator.validate_all(grid)

    # Get stats
    stats = GridValidator.get_grid_stats(grid)

    click.echo(f"\n{'='*60}")
    click.echo("Grid Validation Report")
    click.echo(f"{'='*60}\n")

    click.echo(f"File: {grid_file}")
    click.echo(f"Size: {stats['size']}×{stats['size']}")
    click.echo(
        f"Black squares: {stats['black_squares']} ({stats['black_square_percentage']:.1f}%)"
    )
    click.echo(f"White squares: {stats['white_squares']}")
    click.echo(
        f"Word count: {stats['word_count']} ({stats['across_word_count']} across, {stats['down_word_count']} down)"
    )

    click.echo(f"\nSymmetric: {'✓ Yes' if stats['is_symmetric'] else '✗ No'}")
    click.echo(f"Connected: {'✓ Yes' if stats['is_connected'] else '✗ No'}")

    click.echo(f"\n{'='*60}")

    if is_valid:
        click.echo(
            click.style("✓ VALID - Grid meets all standards!", fg="green", bold=True)
        )
        if stats["meets_nyt_standards"]:
            click.echo(click.style("✓ Meets NYT standards", fg="green"))
    else:
        click.echo(click.style("✗ INVALID - Grid has errors:", fg="red", bold=True))
        for error in errors:
            click.echo(click.style(f"  • {error}", fg="red"))

    click.echo(f"{'='*60}\n")

    sys.exit(0 if is_valid else 1)


@cli.command()
@click.argument("grid_file", type=click.Path(exists=True))
@click.option(
    "--wordlists",
    "-w",
    multiple=True,
    required=True,
    help="Word list files (can specify multiple)",
)
@click.option(
    "--timeout", "-t", type=int, default=300, help="Maximum seconds to spend filling"
)
@click.option(
    "--min-score", type=int, default=30, help="Minimum word quality score (1-100)"
)
@click.option(
    "--algorithm",
    "-a",
    type=click.Choice(["regex", "trie", "beam", "repair", "hybrid"]),
    default="hybrid",
    help="Fill algorithm (regex/trie=classic CSP, beam=beam search, repair=iterative repair, hybrid=beam+repair)",
)
@click.option(
    "--beam-width",
    type=int,
    default=5,
    help="Beam width for beam search algorithms (default: 5)",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output file (defaults to overwriting input)",
)
@click.option(
    "--allow-nonstandard",
    is_flag=True,
    default=False,
    help="Allow non-standard grid sizes (not 11/15/21)",
)
@click.option(
    "--json-output",
    is_flag=True,
    default=False,
    help="Output JSON with progress to stderr (for API integration)",
)
@click.option(
    "--attempts",
    type=int,
    default=1,
    help="Number of randomized restart attempts (Phase 3.2)",
)
@click.option(
    "--theme-entries",
    type=click.Path(exists=True),
    help="JSON file with theme entries to preserve during fill (format: {\"(row,col,direction)\": \"WORD\"})",
)
@click.option(
    "--theme-wordlist",
    type=click.Path(exists=True),
    help="Wordlist to prioritize (theme list) - algorithm will prefer words from this list",
)
@click.option(
    "--adaptive",
    is_flag=True,
    default=False,
    help="Enable adaptive mode: automatically place black squares when stuck",
)
@click.option(
    "--max-adaptations",
    type=int,
    default=3,
    help="Maximum number of adaptive black square placements (default: 3)",
)
def fill(
    grid_file: str,
    wordlists: tuple,
    timeout: int,
    min_score: int,
    algorithm: str,
    beam_width: int,
    output: Optional[str],
    allow_nonstandard: bool,
    json_output: bool,
    attempts: int,
    theme_entries: Optional[str],
    theme_wordlist: Optional[str],
    adaptive: bool,
    max_adaptations: int,
):
    """Fill a crossword grid using CSP autofill."""
    # Create progress reporter (only for JSON output - stderr goes to web API)
    from .core.progress import ProgressReporter
    progress = ProgressReporter(enabled=json_output)

    # Load grid
    if not json_output:
        click.echo(f"Loading grid from {grid_file}...")
    progress.update(5, f'Loading grid from {grid_file}')

    with open(grid_file, "r") as f:
        data = json.load(f)

    grid = Grid.from_dict(data, strict_size=not allow_nonstandard)

    # Load word lists
    if not json_output:
        click.echo("Loading word lists...")

    all_words = []
    for idx, wordlist_file in enumerate(wordlists):
        progress.update(10 + int((idx / len(wordlists)) * 20), f'Loading wordlist {idx+1}/{len(wordlists)}')
        if not json_output:
            click.echo(f"  • {wordlist_file}")
        with open(wordlist_file, "r") as f:
            words = [line.strip().upper() for line in f if line.strip()]
            all_words.extend(words)

    word_list = WordList(all_words)

    if not json_output:
        click.echo(f"  Loaded {len(word_list)} words")

    # Load theme wordlist if provided (Phase 3.4: Theme List Priority)
    theme_words = set()
    if theme_wordlist:
        progress.update(22, f'Loading theme wordlist from {theme_wordlist}')
        if not json_output:
            click.echo(f"⭐ Loading theme wordlist from {theme_wordlist}...")

        with open(theme_wordlist, "r") as f:
            theme_words = {line.strip().upper() for line in f if line.strip() and not line.startswith('#')}

        if not json_output:
            click.echo(f"  ⭐ Loaded {len(theme_words)} theme words (will be prioritized)")

    # Load theme entries if provided
    theme_entries_dict = None
    if theme_entries:
        progress.update(25, f'Loading theme entries from {theme_entries}')
        if not json_output:
            click.echo(f"Loading theme entries from {theme_entries}...")

        with open(theme_entries, "r") as f:
            theme_data = json.load(f)

        # Convert JSON format {"(row,col,direction)": "WORD"} to Python format {(row, col, direction): "WORD"}
        theme_entries_dict = {}
        for key_str, word in theme_data.items():
            # Parse key like "(0,1,across)" or "(0, 1, across)"
            key_str = key_str.strip("()")
            parts = [p.strip().strip("'\"") for p in key_str.split(",")]
            if len(parts) == 3:
                row, col, direction = int(parts[0]), int(parts[1]), parts[2]
                theme_entries_dict[(row, col, direction)] = word.upper()

        if not json_output:
            click.echo(f"  Loaded {len(theme_entries_dict)} theme entries")
            for (row, col, direction), word in theme_entries_dict.items():
                click.echo(f"    • {direction.capitalize()} at ({row},{col}): {word}")

    # Create pattern matcher based on algorithm
    from .fill.pattern_matcher import PatternMatcher
    from .fill.trie_pattern_matcher import TriePatternMatcher
    from .fill.beam_search_autofill import BeamSearchAutofill
    from .fill.iterative_repair import IterativeRepair
    from .fill.hybrid_autofill import HybridAutofill

    # Use trie for beam/repair/hybrid algorithms for better performance
    use_trie = algorithm in ['trie', 'beam', 'repair', 'hybrid']
    pattern_matcher = TriePatternMatcher(word_list) if use_trie else PatternMatcher(word_list)

    # Display algorithm info
    if not json_output:
        algo_descriptions = {
            'regex': 'classic regex-based CSP',
            'trie': 'fast trie-based CSP',
            'beam': f'beam search (width={beam_width})',
            'repair': 'iterative repair',
            'hybrid': f'hybrid (beam width={beam_width} + repair)'
        }
        click.echo(f"  Algorithm: {algorithm} ({algo_descriptions.get(algorithm, algorithm)})")

    progress.update(30, f'Loaded {len(word_list)} words, starting autofill')

    # Create appropriate autofill instance based on algorithm
    if algorithm == 'beam':
        autofill = BeamSearchAutofill(
            grid, word_list, pattern_matcher,
            beam_width=beam_width, min_score=min_score, progress_reporter=progress,
            theme_entries=theme_entries_dict, theme_words=theme_words
        )
    elif algorithm == 'repair':
        autofill = IterativeRepair(
            grid, word_list, pattern_matcher,
            min_score=min_score, progress_reporter=progress,
            theme_entries=theme_entries_dict, theme_words=theme_words
        )
    elif algorithm == 'hybrid':
        autofill = HybridAutofill(
            grid, word_list, pattern_matcher,
            beam_width=beam_width, min_score=min_score, progress_reporter=progress,
            theme_entries=theme_entries_dict, theme_words=theme_words
        )
    else:
        # Default to classic Autofill for 'regex' and 'trie'
        # Note: Classic autofill doesn't support theme entries
        if theme_entries_dict and not json_output:
            click.echo(click.style(
                f"Warning: Theme entries not supported for {algorithm} algorithm. Use beam, repair, or hybrid.",
                fg="yellow"
            ))
        autofill = Autofill(grid, word_list, None, timeout, min_score, algorithm, progress)

    # Wrap with adaptive autofill if enabled
    if adaptive:
        from .fill.adaptive_autofill import AdaptiveAutofill
        if not json_output:
            click.echo(click.style(f"⚡ Adaptive mode enabled (max {max_adaptations} adaptations)", fg="cyan"))
        progress.update(35, f'Adaptive mode enabled (max {max_adaptations} adaptations)')

        # Wrap the base autofill with adaptive wrapper
        # Note: AdaptiveAutofill needs wordlists as list, not WordList object
        adaptive_options = {
            'min_score': min_score,
            'timeout': timeout,
            'max_adaptations': max_adaptations,
            'theme_entries': theme_entries_dict or {}
        }
        autofill = AdaptiveAutofill(
            grid=grid,
            wordlists=[word_list],  # Wrap in list
            options=adaptive_options,
            progress_reporter=progress
        )

    # Get empty slots
    empty_slots = grid.get_empty_slots()
    if not empty_slots:
        if not json_output:
            click.echo(click.style("\n✓ Grid is already completely filled!", fg="green"))
        return

    if not json_output:
        click.echo(f"\nFilling {len(empty_slots)} empty slots...")
        if attempts > 1:
            timeout_per_attempt = timeout // attempts
            click.echo(f"Strategy: Randomized restart ({attempts} attempts)")
            click.echo(f"Timeout: {timeout}s total ({timeout_per_attempt}s per attempt), Min score: {min_score}\n")
        else:
            click.echo(f"Timeout: {timeout}s, Min score: {min_score}\n")

    # Fill grid
    # New algorithms (beam, repair, hybrid) use fill(timeout), classic uses fill() or fill_with_restarts()
    if algorithm in ['beam', 'repair', 'hybrid']:
        # New algorithms don't support multiple attempts - they use timeout directly
        if attempts > 1 and not json_output:
            click.echo(click.style(
                f"Warning: --attempts parameter ignored for {algorithm} algorithm",
                fg="yellow"
            ))

        if json_output:
            result = autofill.fill(timeout=timeout)
        else:
            with click.progressbar(length=100, label="Progress") as bar:
                result = autofill.fill(timeout=timeout)
                # Update progress bar
                if result.total_slots > 0:
                    progress_pct = int((result.slots_filled / result.total_slots) * 100)
                    bar.update(progress_pct)
    else:
        # Classic autofill (regex, trie)
        if attempts > 1:
            timeout_per_attempt = timeout // attempts
            if json_output:
                result = autofill.fill_with_restarts(attempts=attempts, timeout_per_attempt=timeout_per_attempt)
            else:
                with click.progressbar(length=100, label="Progress") as bar:
                    result = autofill.fill_with_restarts(attempts=attempts, timeout_per_attempt=timeout_per_attempt)
                    # Update progress bar
                    if result.total_slots > 0:
                        progress_pct = int((result.slots_filled / result.total_slots) * 100)
                        bar.update(progress_pct)
        else:
            # Single attempt
            if json_output:
                result = autofill.fill()
            else:
                with click.progressbar(length=100, label="Progress") as bar:
                    result = autofill.fill()
                    # Update progress bar
                    if result.total_slots > 0:
                        progress_pct = int((result.slots_filled / result.total_slots) * 100)
                        bar.update(progress_pct)

    # Send completion status for API integration with diagnostic info
    if result.success:
        progress.update(100, f'Successfully filled {result.slots_filled}/{result.total_slots} slots', 'complete')
    else:
        # Generate suggestions for partial fill
        suggestions = []
        if min_score > 20:
            suggestions.append(f"Try lowering minimum score (currently {min_score})")
        if result.slots_filled == 0:
            suggestions.append("Pattern may be too constrained - try adding more black squares")
        elif result.slots_filled < result.total_slots * 0.3:
            suggestions.append("Very few slots filled - pattern likely too difficult")
            suggestions.append("Consider using a different black square layout")
        else:
            suggestions.append(f"Good progress ({result.slots_filled}/{result.total_slots} filled)")
            suggestions.append("Try: lower min score, longer timeout, or more wordlists")

        suggestion_text = " | ".join(suggestions[:2])  # Limit to 2 suggestions
        progress.update(
            min(95, int((result.slots_filled / result.total_slots) * 100)) if result.total_slots > 0 else 0,
            f'Partial fill: {result.slots_filled}/{result.total_slots} slots. {suggestion_text}',
            'complete'
        )

    # Output results based on format
    if json_output:
        # JSON output for API integration
        output_data = {
            "success": result.success,
            "grid": result.grid.to_dict()["grid"],  # Just the grid array (includes partial fills)
            "slots_filled": result.slots_filled,
            "total_slots": result.total_slots,
            "fill_percentage": int((result.slots_filled / result.total_slots) * 100) if result.total_slots > 0 else 0,
            "time_elapsed": result.time_elapsed,
            "iterations": result.iterations,
            "problematic_slots_count": len(result.problematic_slots)
        }

        # Add suggestions for partial fills
        if not result.success:
            suggestions = []
            if min_score > 20:
                suggestions.append({"type": "min_score", "message": f"Lower minimum score (currently {min_score})", "action": "Reduce to 20 or below"})
            if result.slots_filled == 0:
                suggestions.append({"type": "pattern", "message": "Pattern too constrained", "action": "Simplify black square pattern"})
            elif result.slots_filled < result.total_slots * 0.5:
                suggestions.append({"type": "difficulty", "message": "Pattern very difficult", "action": "Try different layout or lower constraints"})
            else:
                suggestions.append({"type": "timeout", "message": "Increase timeout or reduce min score", "action": f"Good progress: {result.slots_filled}/{result.total_slots} filled"})

            output_data["suggestions"] = suggestions

        click.echo(json.dumps(output_data))
    else:
        # Human-readable output for CLI
        click.echo(f"\n{'='*60}")
        click.echo("Autofill Results")
        click.echo(f"{'='*60}\n")

        if result.success:
            click.echo(
                click.style("✓ SUCCESS - Grid filled completely!", fg="green", bold=True)
            )
        else:
            click.echo(
                click.style(
                    "✗ PARTIAL - Could not fill entire grid", fg="yellow", bold=True
                )
            )

        click.echo(f"\nSlots filled: {result.slots_filled}/{result.total_slots}")
        click.echo(f"Time elapsed: {result.time_elapsed:.2f}s")
        click.echo(f"Iterations: {result.iterations:,}")

        if result.problematic_slots:
            click.echo(f"\nProblematic slots: {len(result.problematic_slots)}")
            for slot in result.problematic_slots[:5]:  # Show first 5
                pattern = grid.get_pattern_for_slot(slot)
                click.echo(
                    f"  • {slot['direction'].capitalize()} {slot['row']},{slot['col']}: {pattern}"
                )

        click.echo(f"\n{'='*60}\n")

        # Save result (only in CLI mode)
        output_file = output or grid_file
        with open(output_file, "w") as f:
            json.dump(result.grid.to_dict(), f, indent=2)

        click.echo(f"✓ Saved to: {output_file}")


@cli.command()
@click.argument("grid_file", type=click.Path(exists=True))
@click.option(
    "--format",
    "-",
    type=click.Choice(["text", "json", "grid"]),
    default="grid",
    help="Display format",
)
def show(grid_file: str, format: str):
    """Display a crossword grid."""
    # Load grid
    with open(grid_file, "r") as f:
        data = json.load(f)

    grid = Grid.from_dict(data)

    if format == "json":
        click.echo(json.dumps(data, indent=2))
    elif format == "text":
        click.echo(str(grid))
    else:  # grid format with numbering
        numbering = GridNumbering.auto_number(grid)

        click.echo(f"\n{grid.size}×{grid.size} Crossword Grid")
        click.echo("=" * (grid.size * 2 + 1))

        for row in range(grid.size):
            line = []
            for col in range(grid.size):
                cell = grid.get_cell(row, col)
                if cell == "#":
                    line.append("##")
                elif (row, col) in numbering:
                    # Show number
                    num = numbering[(row, col)]
                    line.append(f"{num:2d}" if num < 100 else str(num))
                else:
                    line.append(f" {cell}")
            click.echo(" ".join(line))

        click.echo("=" * (grid.size * 2 + 1))
        click.echo(f"Black squares: {len(grid.get_black_squares())}")
        click.echo()


@cli.command()
@click.argument("grid_file", type=click.Path(exists=True))
@click.option(
    "--format",
    "-",
    type=click.Choice(["html"]),
    default="html",
    help="Export format (html)",
)
@click.option(
    "--output", "-o", type=click.Path(), required=True, help="Output file path"
)
@click.option("--title", "-t", default="Crossword Puzzle", help="Puzzle title")
def export(grid_file: str, format: str, output: str, title: str):
    """Export a crossword grid to various formats."""
    # Load grid
    with open(grid_file, "r") as f:
        data = json.load(f)

    grid = Grid.from_dict(data)

    # Export based on format
    if format == "html":
        HTMLExporter.export_to_file(grid, output, title)
        click.echo(f"✓ Exported to HTML: {output}")
    else:
        click.echo(f"Format {format} not yet supported", err=True)
        sys.exit(1)


# Phase 3.1: Commands for web API parity


@cli.command()
@click.argument("pattern_arg")
@click.option(
    "--wordlists", "-w", multiple=True, help="Word list files (can specify multiple)"
)
@click.option(
    "--max-results", type=int, default=20, help="Maximum number of results to return"
)
@click.option(
    "--algorithm",
    "-a",
    type=click.Choice(["regex", "trie"]),
    default="regex",
    help="Pattern matching algorithm (regex=classic, trie=fast)",
)
@click.option(
    "--json-output",
    is_flag=True,
    default=False,
    help="Output JSON format (for API compatibility)",
)
def pattern(pattern_arg: str, wordlists: tuple, max_results: int, algorithm: str, json_output: bool):
    """
    Find words matching a pattern (Phase 3.1).

    Pattern uses ? for wildcards (e.g., "C?T" matches CAT, COT, CUT).

    Examples:
        crossword pattern "C?T"
        crossword pattern "?I?E" --wordlists standard.txt --max-results 10
        crossword pattern "A?PLE" --json-output
    """
    from .core.scoring import analyze_letters
    from .core.progress import ProgressReporter

    # Initialize progress reporter (only for JSON output mode)
    progress = ProgressReporter(enabled=json_output)
    progress.start(f'Searching for pattern "{pattern_arg}"')

    # Load word lists if specified
    all_words = []
    sources = []

    if wordlists:
        total_wordlists = len(wordlists)
        for idx, wordlist_file in enumerate(wordlists):
            try:
                # Calculate progress range for this wordlist (0-30% total allocated for loading)
                wordlist_start_pct = int((idx / total_wordlists) * 30)
                wordlist_end_pct = int(((idx + 1) / total_wordlists) * 30)

                # Report progress starting wordlist
                progress.update(
                    wordlist_start_pct,
                    f'Loading wordlist {idx + 1}/{total_wordlists}: {Path(wordlist_file).name}'
                )

                # Create progress callback for granular loading updates
                def loading_progress_callback(current, total):
                    if total > 0:
                        # Map wordlist loading progress (0-100%) to this wordlist's range
                        loading_pct = current / total
                        overall_pct = wordlist_start_pct + int(loading_pct * (wordlist_end_pct - wordlist_start_pct))
                        progress.update(
                            overall_pct,
                            f'Loading {Path(wordlist_file).name}: {current:,} / {total:,} words'
                        )

                word_list = WordList.from_file(
                    wordlist_file,
                    progress_callback=loading_progress_callback if json_output else None
                )
                for word in word_list.get_all():
                    all_words.append((word.text, word.score, Path(wordlist_file).stem))
                sources.append(Path(wordlist_file).stem)
            except Exception as e:
                click.echo(f"Warning: Could not load {wordlist_file}: {e}", err=True)

        progress.update(30, f'Loaded {len(all_words)} words from {total_wordlists} wordlist(s)')
    else:
        # If no wordlists specified, create minimal list
        default_words = ["CAT", "DOG", "BIRD", "FISH", "TREE", "STAR", "MOON", "SUN"]
        word_list = WordList(default_words)
        for word in word_list.get_all():
            all_words.append((word.text, word.score, "builtin"))
        sources = ["builtin"]
        progress.update(30, 'Using default wordlist')

    # Create pattern matcher based on algorithm
    progress.update(50, f'Initializing {algorithm} algorithm')
    full_word_list = WordList([word for word, _, _ in all_words])

    if algorithm == "trie":
        from .fill.trie_pattern_matcher import TriePatternMatcher
        pattern_matcher = TriePatternMatcher(full_word_list)
    else:
        pattern_matcher = PatternMatcher(full_word_list)

    # Search for pattern with progress tracking
    progress.update(70, f'Searching {len(all_words)} words for pattern "{pattern_arg}"')

    # Create progress callback for fine-grained updates
    def search_progress_callback(current, total):
        if total > 0:
            percent = int((current / total) * 100)
            # Map 70-90% range to search progress
            overall_percent = 70 + int((percent / 100) * 20)
            progress.update(
                overall_percent,
                f'Searched {current:,} / {total:,} words'
            )

    matches = pattern_matcher.find(
        pattern_arg,
        min_score=0,
        max_results=max_results,
        progress_callback=search_progress_callback if json_output else None
    )

    progress.update(90, f'Found {len(matches)} matches, formatting results')

    # Format results
    results = []
    for word, word_score in matches[:max_results]:
        source = next((src for w, s, src in all_words if w == word), "unknown")

        results.append(
            {
                "word": word,
                "score": word_score,
                "source": source,
                "length": len(word),
                "letter_quality": analyze_letters(word),
            }
        )

    if json_output:
        output = {
            "results": results,
            "meta": {
                "pattern": pattern_arg,
                "total_found": len(matches),
                "results_returned": min(len(matches), max_results),
                "sources_searched": sources,
            },
        }
        progress.complete(f'Search complete: {len(results)} results returned')
        click.echo(json.dumps(output, indent=2))
    else:
        click.echo(f"\nPattern: {pattern_arg}")
        click.echo(f"Found {len(results)} matches:\n")
        for result in results:
            click.echo(
                f"  {result['word']:15} score={result['score']:3} source={result['source']}"
            )
        if not results:
            click.echo("  (no matches found)")


@cli.command()
@click.argument("text")
@click.option(
    "--json-output",
    is_flag=True,
    default=False,
    help="Output JSON format (for API compatibility)",
)
def normalize(text: str, json_output: bool):
    """
    Normalize crossword entry according to conventions (Phase 3.1).

    Examples:
        crossword normalize "Tina Fey"
        crossword normalize "self-aware" --json-output
    """
    from .core.conventions import ConventionHelper

    helper = ConventionHelper()
    normalized, rule_info = helper.normalize(text)
    alternatives = helper.get_alternatives(text, normalized)

    if json_output:
        output = {
            "original": text,
            "normalized": normalized,
            "rule": rule_info,
            "alternatives": alternatives,
        }
        click.echo(json.dumps(output, indent=2))
    else:
        click.echo(f"\nOriginal:    {text}")
        click.echo(f"Normalized:  {normalized}")
        click.echo(f"\nRule: {rule_info['description']}")
        click.echo(f"{rule_info['explanation']}")

        if rule_info.get("examples"):
            click.echo("\nExamples:")
            for example_in, example_out in rule_info["examples"][:3]:
                click.echo(f"  {example_in:20} → {example_out}")

        if alternatives:
            click.echo("\nAlternatives:")
            for alt in alternatives:
                click.echo(f"  {alt['form']:20} ({alt['note']})")


@cli.command()
@click.argument("grid_file", type=click.Path(exists=True))
@click.option(
    "--json-output",
    is_flag=True,
    default=False,
    help="Output JSON format (for API compatibility)",
)
@click.option(
    "--allow-nonstandard",
    is_flag=True,
    default=False,
    help="Allow non-standard grid sizes (not 11/15/21)",
)
def number(grid_file: str, json_output: bool, allow_nonstandard: bool):
    """
    Auto-number a crossword grid (Phase 3.1).

    Examples:
        crossword number grid.json
        crossword number grid.json --json-output
        crossword number grid.json --allow-nonstandard  # For 9x9, 13x13, etc.
    """
    # Load grid
    with open(grid_file, "r") as f:
        data = json.load(f)

    grid = Grid.from_dict(data, strict_size=not allow_nonstandard)

    # Auto-number
    numbering = GridNumbering.auto_number(grid)

    # Get grid info/stats
    stats = GridValidator.get_grid_stats(grid)

    if json_output:
        # Convert tuple keys to strings for JSON
        numbering_serializable = {f"({k[0]},{k[1]})": v for k, v in numbering.items()}

        output = {
            "numbering": numbering_serializable,
            "grid_info": {
                "size": [stats["size"], stats["size"]],
                "black_squares": stats["black_squares"],
                "black_square_percentage": stats["black_square_percentage"],
                "white_squares": stats["white_squares"],
                "word_count": stats["word_count"],
                "meets_nyt_standards": stats.get("meets_nyt_standards", False),
            },
        }
        click.echo(json.dumps(output, indent=2))
    else:
        click.echo(f"\n{'='*60}")
        click.echo("Grid Numbering")
        click.echo(f"{'='*60}\n")

        click.echo(f"File: {grid_file}")
        click.echo(f"Size: {stats['size']}×{stats['size']}")
        click.echo(f"Numbered squares: {len(numbering)}")

        click.echo("\nNumbering:")
        for (row, col), num in sorted(numbering.items(), key=lambda x: x[1]):
            click.echo(f"  {num:3d}: row {row}, col {col}")

        click.echo(f"\n{'='*60}\n")


@cli.command("build-cache")
@click.argument("wordlist", type=click.Path(exists=True))
@click.option(
    "--output", "-o",
    type=click.Path(),
    help="Output path for cache file (default: same as wordlist with .pkl extension)"
)
def build_cache(wordlist: str, output: Optional[str]):
    """
    Build binary cache file for fast wordlist loading.

    This pre-processes a wordlist file (validates, scores, indexes) and saves
    the result to a binary .pkl file. Subsequent loads will be 10-20x faster.

    Example:
        crossword build-cache data/wordlists/comprehensive.txt
    """
    import time

    wordlist_path = Path(wordlist)

    # Determine output path
    if output:
        cache_path = Path(output)
    else:
        cache_path = wordlist_path.with_suffix('.pkl')

    click.echo(f"Building cache for: {wordlist_path.name}")
    click.echo(f"Output: {cache_path}")
    click.echo()

    # Load wordlist (this will be slow)
    click.echo("Loading wordlist...")
    start_time = time.time()

    try:
        word_list = WordList.from_file(str(wordlist_path), use_cache=False)
        load_time = time.time() - start_time

        click.echo(f"✓ Loaded {len(word_list)} words in {load_time:.2f}s")

        # Save cache
        click.echo("Writing cache file...")
        cache_start = time.time()
        word_list.to_cache(str(cache_path))
        cache_time = time.time() - cache_start

        click.echo(f"✓ Cache written in {cache_time:.2f}s")

        # Verify cache works
        click.echo("Verifying cache...")
        verify_start = time.time()
        WordList.from_cache(str(cache_path))
        verify_time = time.time() - verify_start

        click.echo(f"✓ Cache loads in {verify_time:.2f}s ({load_time/verify_time:.1f}x faster!)")
        click.echo()
        click.echo(f"Cache file: {cache_path}")
        click.echo(f"Cache size: {cache_path.stat().st_size / 1024 / 1024:.1f} MB")

    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("task_id")
@click.option(
    "--json-output",
    is_flag=True,
    default=False,
    help="Output JSON format (for API compatibility)",
)
def pause(task_id: str, json_output: bool):
    """
    Pause a running autofill task.

    Sends a pause signal to the specified task. The task will save its
    current state and exit gracefully at the next checkpoint.

    Examples:
        crossword pause task_abc123
        crossword pause task_abc123 --json-output
    """
    try:
        from .fill.pause_controller import PauseController

        controller = PauseController(task_id=task_id)
        controller.request_pause()

        if json_output:
            output = {
                "success": True,
                "task_id": task_id,
                "message": f"Pause requested for task {task_id}"
            }
            click.echo(json.dumps(output))
        else:
            click.echo(click.style(f"✓ Pause requested for task: {task_id}", fg="green"))
            click.echo("The task will save its state and exit at the next checkpoint.")

    except Exception as e:
        if json_output:
            click.echo(json.dumps({"success": False, "error": str(e)}))
        else:
            click.echo(click.style(f"✗ Error: {e}", fg="red"), err=True)
        sys.exit(1)


@cli.command()
@click.argument("state_file", type=click.Path(exists=True))
@click.option(
    "--output", "-o", type=click.Path(), help="Output file (defaults to overwriting state file)"
)
@click.option(
    "--json-output",
    is_flag=True,
    default=False,
    help="Output JSON format (for API compatibility)",
)
@click.option(
    "--algorithm",
    "-a",
    type=click.Choice(["regex", "trie", "beam", "repair", "hybrid"]),
    default="hybrid",
    help="Fill algorithm to use for resumption",
)
@click.option(
    "--timeout", "-t", type=int, default=300, help="Maximum seconds to spend filling"
)
@click.option(
    "--min-score", type=int, default=30, help="Minimum word quality score (1-100)"
)
def resume(
    state_file: str,
    output: Optional[str],
    json_output: bool,
    algorithm: str,
    timeout: int,
    min_score: int,
):
    """
    Resume autofill from a saved state file.

    Loads a previously saved autofill state and continues filling from
    where it left off. The state file preserves all progress, assignments,
    and constraints.

    Examples:
        crossword resume autofill_state_task_abc123.json
        crossword resume state.json -o completed.json
        crossword resume state.json --algorithm hybrid --timeout 600
    """
    try:
        from .fill.state_manager import StateManager
        from .fill.pattern_matcher import PatternMatcher
        from .fill.trie_pattern_matcher import TriePatternMatcher
        from .fill.beam_search_autofill import BeamSearchAutofill
        from .fill.iterative_repair import IterativeRepair
        from .fill.hybrid_autofill import HybridAutofill
        from .core.progress import ProgressReporter

        # Initialize progress reporter
        progress = ProgressReporter(enabled=json_output)
        progress.start(f"Resuming from {Path(state_file).name}")

        # Load state
        if not json_output:
            click.echo(f"Loading saved state from {state_file}...")

        state_manager = StateManager()

        # Extract task_id from filename (format: autofill_state_<task_id>.json)
        task_id = Path(state_file).stem.replace("autofill_state_", "")

        try:
            csp_state, metadata = state_manager.load_csp_state(task_id)
        except FileNotFoundError:
            # Try loading directly by path
            with open(state_file, "r") as f:
                state_data = json.load(f)
                csp_state = state_data["csp_state"]
                metadata = state_data.get("metadata", {})

        progress.update(20, "State loaded successfully")

        # Reconstruct grid and wordlist
        grid = Grid.from_dict(csp_state.grid_dict)

        # Load word list (use same as original if available)
        original_wordlists = metadata.get("wordlists", [])
        all_words = []

        if original_wordlists:
            for wl_file in original_wordlists:
                try:
                    with open(wl_file, "r") as f:
                        words = [line.strip().upper() for line in f if line.strip()]
                        all_words.extend(words)
                except FileNotFoundError:
                    if not json_output:
                        click.echo(
                            click.style(
                                f"Warning: Original wordlist {wl_file} not found, using default",
                                fg="yellow",
                            )
                        )

        if not all_words:
            # Fallback to default wordlist
            default_wl = Path(__file__).parent.parent / "data" / "wordlists" / "comprehensive.txt"
            if default_wl.exists():
                with open(default_wl, "r") as f:
                    all_words = [line.strip().upper() for line in f if line.strip()]

        word_list = WordList(all_words)

        progress.update(40, f"Loaded {len(word_list)} words")

        # Create pattern matcher
        use_trie = algorithm in ["trie", "beam", "repair", "hybrid"]
        pattern_matcher = (
            TriePatternMatcher(word_list) if use_trie else PatternMatcher(word_list)
        )

        # Create autofill instance
        if algorithm == "beam":
            autofill = BeamSearchAutofill(
                grid,
                word_list,
                pattern_matcher,
                beam_width=5,
                min_score=min_score,
                progress_reporter=progress,
            )
        elif algorithm == "repair":
            autofill = IterativeRepair(
                grid,
                word_list,
                pattern_matcher,
                min_score=min_score,
                progress_reporter=progress,
            )
        elif algorithm == "hybrid":
            autofill = HybridAutofill(
                grid,
                word_list,
                pattern_matcher,
                beam_width=5,
                min_score=min_score,
                progress_reporter=progress,
            )
        else:
            autofill = Autofill(
                grid, word_list, None, timeout, min_score, algorithm, progress
            )

        # Restore CSP state
        autofill.csp = csp_state

        if not json_output:
            click.echo("\nResuming autofill...")
            click.echo(f"  Previously filled: {metadata.get('slots_filled', 0)} slots")
            click.echo(f"  Algorithm: {algorithm}")
            click.echo(f"  Timeout: {timeout}s\n")

        progress.update(60, "Starting autofill from saved state")

        # Continue filling
        result = autofill.fill(timeout=timeout)

        # Save result
        output_file = output or state_file
        with open(output_file, "w") as f:
            json.dump(result.grid.to_dict(), f, indent=2)

        if json_output:
            output_data = {
                "success": result.success,
                "grid": result.grid.to_dict()["grid"],
                "slots_filled": result.slots_filled,
                "total_slots": result.total_slots,
                "time_elapsed": result.time_elapsed,
                "output_file": output_file,
            }
            progress.complete("Resume complete")
            click.echo(json.dumps(output_data))
        else:
            click.echo(f"\n{'='*60}")
            click.echo("Resume Results")
            click.echo(f"{'='*60}\n")

            if result.success:
                click.echo(click.style("✓ SUCCESS - Grid completed!", fg="green", bold=True))
            else:
                click.echo(
                    click.style("✗ PARTIAL - Could not complete grid", fg="yellow", bold=True)
                )

            click.echo(f"\nSlots filled: {result.slots_filled}/{result.total_slots}")
            click.echo(f"Time elapsed: {result.time_elapsed:.2f}s")
            click.echo(f"\n✓ Saved to: {output_file}")
            click.echo(f"{'='*60}\n")

    except Exception as e:
        if json_output:
            click.echo(json.dumps({"success": False, "error": str(e)}))
        else:
            click.echo(click.style(f"✗ Error: {e}", fg="red"), err=True)
        sys.exit(1)


@cli.command("list-states")
@click.option(
    "--json-output",
    is_flag=True,
    default=False,
    help="Output JSON format (for API compatibility)",
)
@click.option(
    "--sort-by",
    type=click.Choice(["timestamp", "progress", "size"]),
    default="timestamp",
    help="Sort states by timestamp, progress, or grid size",
)
@click.option(
    "--max-age-days",
    type=int,
    help="Only show states newer than this many days",
)
def list_states(json_output: bool, sort_by: str, max_age_days: Optional[int]):
    """
    List all saved autofill states.

    Shows information about paused/saved autofill tasks that can be resumed.

    Examples:
        crossword list-states
        crossword list-states --sort-by progress
        crossword list-states --max-age-days 7
        crossword list-states --json-output
    """
    try:
        from .fill.state_manager import StateManager

        state_manager = StateManager()
        states = state_manager.list_states(max_age_days=max_age_days)

        # Sort states
        if sort_by == "timestamp":
            states.sort(key=lambda s: s.get("timestamp", ""), reverse=True)
        elif sort_by == "progress":
            states.sort(
                key=lambda s: s.get("slots_filled", 0) / max(s.get("total_slots", 1), 1),
                reverse=True,
            )
        elif sort_by == "size":
            states.sort(key=lambda s: s.get("grid_size", [0, 0])[0], reverse=True)

        if json_output:
            output = {"states": states, "count": len(states)}
            click.echo(json.dumps(output, indent=2))
        else:
            click.echo(f"\n{'='*60}")
            click.echo(f"Saved Autofill States ({len(states)} total)")
            click.echo(f"{'='*60}\n")

            if not states:
                click.echo("No saved states found.")
            else:
                for state in states:
                    task_id = state.get("task_id", "unknown")
                    timestamp = state.get("timestamp", "unknown")
                    grid_size = state.get("grid_size", [0, 0])
                    filled = state.get("slots_filled", 0)
                    total = state.get("total_slots", 0)
                    progress_pct = (filled / total * 100) if total > 0 else 0

                    click.echo(f"Task ID: {task_id}")
                    click.echo(f"  Timestamp: {timestamp}")
                    click.echo(f"  Grid size: {grid_size[0]}×{grid_size[1]}")
                    click.echo(f"  Progress: {filled}/{total} slots ({progress_pct:.1f}%)")
                    click.echo()

            click.echo(f"{'='*60}\n")

    except Exception as e:
        if json_output:
            click.echo(json.dumps({"success": False, "error": str(e)}))
        else:
            click.echo(click.style(f"✗ Error: {e}", fg="red"), err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
