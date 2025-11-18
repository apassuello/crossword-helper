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
@click.version_option(version='2.0.0', prog_name='crossword')
def cli():
    """
    Crossword Builder CLI - Create and fill crossword puzzles.

    Phase 2: Advanced CLI tool with autofill engine.
    """
    pass


@cli.command()
@click.option('--size', type=click.Choice(['11', '15', '21']), default='15',
              help='Grid size (11x11, 15x15, or 21x21)')
@click.option('--output', '-o', type=click.Path(), required=True,
              help='Output file path (.json)')
def new(size: str, output: str):
    """Create a new empty crossword grid."""
    size_int = int(size)

    # Create empty grid
    grid = Grid(size_int)

    # Save to file
    data = grid.to_dict()

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)

    click.echo(f"✓ Created {size}×{size} grid: {output}")
    click.echo(f"  Size: {size_int}×{size_int}")
    click.echo(f"  Black squares: 0")
    click.echo(f"  Ready to fill!")


@cli.command()
@click.argument('grid_file', type=click.Path(exists=True))
def validate(grid_file: str):
    """Validate a crossword grid against NYT standards."""
    # Load grid
    with open(grid_file, 'r') as f:
        data = json.load(f)

    grid = Grid.from_dict(data)

    # Validate
    is_valid, errors = GridValidator.validate_all(grid)

    # Get stats
    stats = GridValidator.get_grid_stats(grid)

    click.echo(f"\n{'='*60}")
    click.echo(f"Grid Validation Report")
    click.echo(f"{'='*60}\n")

    click.echo(f"File: {grid_file}")
    click.echo(f"Size: {stats['size']}×{stats['size']}")
    click.echo(f"Black squares: {stats['black_squares']} ({stats['black_square_percentage']:.1f}%)")
    click.echo(f"White squares: {stats['white_squares']}")
    click.echo(f"Word count: {stats['word_count']} ({stats['across_word_count']} across, {stats['down_word_count']} down)")

    click.echo(f"\nSymmetric: {'✓ Yes' if stats['is_symmetric'] else '✗ No'}")
    click.echo(f"Connected: {'✓ Yes' if stats['is_connected'] else '✗ No'}")

    click.echo(f"\n{'='*60}")

    if is_valid:
        click.echo(click.style("✓ VALID - Grid meets all standards!", fg='green', bold=True))
        if stats['meets_nyt_standards']:
            click.echo(click.style("✓ Meets NYT standards", fg='green'))
    else:
        click.echo(click.style("✗ INVALID - Grid has errors:", fg='red', bold=True))
        for error in errors:
            click.echo(click.style(f"  • {error}", fg='red'))

    click.echo(f"{'='*60}\n")

    sys.exit(0 if is_valid else 1)


@cli.command()
@click.argument('grid_file', type=click.Path(exists=True))
@click.option('--wordlists', '-w', multiple=True, required=True,
              help='Word list files (can specify multiple)')
@click.option('--timeout', '-t', type=int, default=300,
              help='Maximum seconds to spend filling')
@click.option('--min-score', type=int, default=30,
              help='Minimum word quality score (1-100)')
@click.option('--output', '-o', type=click.Path(),
              help='Output file (defaults to overwriting input)')
@click.option('--allow-nonstandard', is_flag=True, default=False,
              help='Allow non-standard grid sizes (not 11/15/21)')
def fill(grid_file: str, wordlists: tuple, timeout: int, min_score: int, output: Optional[str],
         allow_nonstandard: bool):
    """Fill a crossword grid using CSP autofill."""
    # Load grid
    click.echo(f"Loading grid from {grid_file}...")
    with open(grid_file, 'r') as f:
        data = json.load(f)

    grid = Grid.from_dict(data, strict_size=not allow_nonstandard)

    # Load word lists
    click.echo(f"Loading word lists...")
    all_words = []
    for wordlist_file in wordlists:
        click.echo(f"  • {wordlist_file}")
        with open(wordlist_file, 'r') as f:
            words = [line.strip().upper() for line in f if line.strip()]
            all_words.extend(words)

    word_list = WordList(all_words)
    click.echo(f"  Loaded {len(word_list)} words")

    # Create autofill engine
    pattern_matcher = PatternMatcher(word_list)
    autofill = Autofill(grid, word_list, pattern_matcher, timeout, min_score)

    # Get empty slots
    empty_slots = grid.get_empty_slots()
    if not empty_slots:
        click.echo(click.style("\n✓ Grid is already completely filled!", fg='green'))
        return

    click.echo(f"\nFilling {len(empty_slots)} empty slots...")
    click.echo(f"Timeout: {timeout}s, Min score: {min_score}\n")

    # Fill grid
    with click.progressbar(length=100, label='Progress') as bar:
        result = autofill.fill()

        # Update progress bar
        if result.total_slots > 0:
            progress = int((result.slots_filled / result.total_slots) * 100)
            bar.update(progress)

    # Display results
    click.echo(f"\n{'='*60}")
    click.echo(f"Autofill Results")
    click.echo(f"{'='*60}\n")

    if result.success:
        click.echo(click.style("✓ SUCCESS - Grid filled completely!", fg='green', bold=True))
    else:
        click.echo(click.style("✗ PARTIAL - Could not fill entire grid", fg='yellow', bold=True))

    click.echo(f"\nSlots filled: {result.slots_filled}/{result.total_slots}")
    click.echo(f"Time elapsed: {result.time_elapsed:.2f}s")
    click.echo(f"Iterations: {result.iterations:,}")

    if result.problematic_slots:
        click.echo(f"\nProblematic slots: {len(result.problematic_slots)}")
        for slot in result.problematic_slots[:5]:  # Show first 5
            pattern = grid.get_pattern_for_slot(slot)
            click.echo(f"  • {slot['direction'].capitalize()} {slot['row']},{slot['col']}: {pattern}")

    click.echo(f"\n{'='*60}\n")

    # Save result
    output_file = output or grid_file
    with open(output_file, 'w') as f:
        json.dump(result.grid.to_dict(), f, indent=2)

    click.echo(f"✓ Saved to: {output_file}")


@cli.command()
@click.argument('grid_file', type=click.Path(exists=True))
@click.option('--format', '-f', type=click.Choice(['text', 'json', 'grid']), default='grid',
              help='Display format')
def show(grid_file: str, format: str):
    """Display a crossword grid."""
    # Load grid
    with open(grid_file, 'r') as f:
        data = json.load(f)

    grid = Grid.from_dict(data)

    if format == 'json':
        click.echo(json.dumps(data, indent=2))
    elif format == 'text':
        click.echo(str(grid))
    else:  # grid format with numbering
        numbering = GridNumbering.auto_number(grid)

        click.echo(f"\n{grid.size}×{grid.size} Crossword Grid")
        click.echo("=" * (grid.size * 2 + 1))

        for row in range(grid.size):
            line = []
            for col in range(grid.size):
                cell = grid.get_cell(row, col)
                if cell == '#':
                    line.append('##')
                elif (row, col) in numbering:
                    # Show number
                    num = numbering[(row, col)]
                    line.append(f"{num:2d}" if num < 100 else str(num))
                else:
                    line.append(f" {cell}")
            click.echo(' '.join(line))

        click.echo("=" * (grid.size * 2 + 1))
        click.echo(f"Black squares: {len(grid.get_black_squares())}")
        click.echo()


@cli.command()
@click.argument('grid_file', type=click.Path(exists=True))
@click.option('--format', '-f', type=click.Choice(['html']), default='html',
              help='Export format (html)')
@click.option('--output', '-o', type=click.Path(), required=True,
              help='Output file path')
@click.option('--title', '-t', default='Crossword Puzzle',
              help='Puzzle title')
def export(grid_file: str, format: str, output: str, title: str):
    """Export a crossword grid to various formats."""
    # Load grid
    with open(grid_file, 'r') as f:
        data = json.load(f)

    grid = Grid.from_dict(data)

    # Export based on format
    if format == 'html':
        HTMLExporter.export_to_file(grid, output, title)
        click.echo(f"✓ Exported to HTML: {output}")
    else:
        click.echo(f"Format {format} not yet supported", err=True)
        sys.exit(1)


# Phase 3.1: Commands for web API parity

@cli.command()
@click.argument('pattern_arg')
@click.option('--wordlists', '-w', multiple=True,
              help='Word list files (can specify multiple)')
@click.option('--max-results', type=int, default=20,
              help='Maximum number of results to return')
@click.option('--json-output', is_flag=True, default=False,
              help='Output JSON format (for API compatibility)')
def pattern(pattern_arg: str, wordlists: tuple, max_results: int, json_output: bool):
    """
    Find words matching a pattern (Phase 3.1).

    Pattern uses ? for wildcards (e.g., "C?T" matches CAT, COT, CUT).

    Examples:
        crossword pattern "C?T"
        crossword pattern "?I?E" --wordlists standard.txt --max-results 10
        crossword pattern "A?PLE" --json-output
    """
    from .core.scoring import analyze_letters

    # Load word lists if specified
    all_words = []
    sources = []

    if wordlists:
        for wordlist_file in wordlists:
            try:
                word_list = WordList.from_file(wordlist_file)
                for word in word_list.get_all():
                    all_words.append((word.text, word.score, Path(wordlist_file).stem))
                sources.append(Path(wordlist_file).stem)
            except Exception as e:
                click.echo(f"Warning: Could not load {wordlist_file}: {e}", err=True)

    # If no wordlists specified, create minimal list
    if not all_words:
        default_words = ['CAT', 'DOG', 'BIRD', 'FISH', 'TREE', 'STAR', 'MOON', 'SUN']
        word_list = WordList(default_words)
        for word in word_list.get_all():
            all_words.append((word.text, word.score, 'builtin'))
        sources = ['builtin']

    # Create pattern matcher
    full_word_list = WordList([word for word, _, _ in all_words])
    pattern_matcher = PatternMatcher(full_word_list)

    # Search for pattern
    matches = pattern_matcher.find(pattern_arg, min_score=0, max_results=max_results)

    # Format results
    results = []
    for word, word_score in matches[:max_results]:
        source = next((src for w, s, src in all_words if w == word), 'unknown')

        results.append({
            'word': word,
            'score': word_score,
            'source': source,
            'length': len(word),
            'letter_quality': analyze_letters(word)
        })

    if json_output:
        output = {
            'results': results,
            'meta': {
                'pattern': pattern_arg,
                'total_found': len(matches),
                'results_returned': min(len(matches), max_results),
                'sources_searched': sources
            }
        }
        click.echo(json.dumps(output, indent=2))
    else:
        click.echo(f"\nPattern: {pattern_arg}")
        click.echo(f"Found {len(results)} matches:\n")
        for result in results:
            click.echo(f"  {result['word']:15} score={result['score']:3} source={result['source']}")
        if not results:
            click.echo("  (no matches found)")


@cli.command()
@click.argument('text')
@click.option('--json-output', is_flag=True, default=False,
              help='Output JSON format (for API compatibility)')
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
            'original': text,
            'normalized': normalized,
            'rule': rule_info,
            'alternatives': alternatives
        }
        click.echo(json.dumps(output, indent=2))
    else:
        click.echo(f"\nOriginal:    {text}")
        click.echo(f"Normalized:  {normalized}")
        click.echo(f"\nRule: {rule_info['description']}")
        click.echo(f"{rule_info['explanation']}")

        if rule_info.get('examples'):
            click.echo(f"\nExamples:")
            for example_in, example_out in rule_info['examples'][:3]:
                click.echo(f"  {example_in:20} → {example_out}")

        if alternatives:
            click.echo(f"\nAlternatives:")
            for alt in alternatives:
                click.echo(f"  {alt['form']:20} ({alt['note']})")


@cli.command()
@click.argument('grid_file', type=click.Path(exists=True))
@click.option('--json-output', is_flag=True, default=False,
              help='Output JSON format (for API compatibility)')
@click.option('--allow-nonstandard', is_flag=True, default=False,
              help='Allow non-standard grid sizes (not 11/15/21)')
def number(grid_file: str, json_output: bool, allow_nonstandard: bool):
    """
    Auto-number a crossword grid (Phase 3.1).

    Examples:
        crossword number grid.json
        crossword number grid.json --json-output
        crossword number grid.json --allow-nonstandard  # For 9x9, 13x13, etc.
    """
    # Load grid
    with open(grid_file, 'r') as f:
        data = json.load(f)

    grid = Grid.from_dict(data, strict_size=not allow_nonstandard)

    # Auto-number
    numbering = GridNumbering.auto_number(grid)

    # Get grid info/stats
    stats = GridValidator.get_grid_stats(grid)

    if json_output:
        # Convert tuple keys to strings for JSON
        numbering_serializable = {
            f"({k[0]},{k[1]})": v
            for k, v in numbering.items()
        }

        output = {
            'numbering': numbering_serializable,
            'grid_info': {
                'size': [stats['size'], stats['size']],
                'black_squares': stats['black_squares'],
                'black_square_percentage': stats['black_square_percentage'],
                'white_squares': stats['white_squares'],
                'word_count': stats['word_count'],
                'meets_nyt_standards': stats.get('meets_nyt_standards', False)
            }
        }
        click.echo(json.dumps(output, indent=2))
    else:
        click.echo(f"\n{'='*60}")
        click.echo(f"Grid Numbering")
        click.echo(f"{'='*60}\n")

        click.echo(f"File: {grid_file}")
        click.echo(f"Size: {stats['size']}×{stats['size']}")
        click.echo(f"Numbered squares: {len(numbering)}")

        click.echo(f"\nNumbering:")
        for (row, col), num in sorted(numbering.items(), key=lambda x: x[1]):
            click.echo(f"  {num:3d}: row {row}, col {col}")

        click.echo(f"\n{'='*60}\n")


if __name__ == '__main__':
    cli()
