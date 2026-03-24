"""
Flask API routes for wordlist management.

This module provides endpoints for listing, viewing, creating, updating,
and analyzing wordlists.
"""

from flask import Blueprint, request, jsonify
from backend.data.wordlist_manager import WordListManager

wordlist_api = Blueprint("wordlist_api", __name__)

# Initialize wordlist manager
wordlist_manager = WordListManager()


@wordlist_api.route("/wordlists", methods=["GET"])
def list_wordlists():
    """
    GET /api/wordlists - List all available wordlists with metadata.

    Query params:
    - category: Filter by category (core, themed, custom, etc.)

    Returns:
    {
        "wordlists": [...],
        "categories": {...},
        "tags": {...}
    }
    """
    try:
        category = request.args.get("category")

        wordlists = wordlist_manager.list_all(category=category)
        categories = wordlist_manager.get_categories()
        tags = wordlist_manager.get_tags()

        return (
            jsonify({"wordlists": wordlists, "categories": categories, "tags": tags}),
            200,
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@wordlist_api.route("/wordlists/<path:name>", methods=["GET"])
def get_wordlist(name):
    """
    GET /api/wordlists/<name> - Get specific wordlist content and metadata.

    Query params:
    - stats: Include word statistics (true/false)

    Returns:
    {
        "metadata": {...},
        "words": [...],
        "stats": {...}  // if requested
    }
    """
    try:
        include_stats = request.args.get("stats", "false").lower() == "true"

        # Load words
        words = wordlist_manager.load(name)

        # Get metadata
        metadata = wordlist_manager.get_wordlist_info(name)

        response = {"metadata": metadata, "words": words}

        # Add statistics if requested
        if include_stats:
            response["stats"] = wordlist_manager.analyze_words(name)

        return jsonify(response), 200

    except FileNotFoundError:
        return jsonify({"error": f'Wordlist "{name}" not found'}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@wordlist_api.route("/wordlists/<path:name>", methods=["POST"])
def create_wordlist(name):
    """
    POST /api/wordlists/<name> - Create new wordlist.

    Body:
    {
        "words": ["WORD1", "WORD2"],
        "metadata": {
            "description": "...",
            "tags": ["tag1", "tag2"],
            "difficulty": "easy|medium|hard"
        }
    }
    """
    try:
        data = request.json

        if not data or "words" not in data:
            return jsonify({"error": "Words array required"}), 400

        # Create wordlist
        wordlist_manager.add_words(name, data["words"], create=True)

        # Update metadata if provided
        if "metadata" in data:
            metadata = wordlist_manager._metadata
            metadata["wordlists"][name] = {
                **metadata["wordlists"].get(name, {}),
                **data["metadata"],
            }
            wordlist_manager.save_metadata()

        return (
            jsonify(
                {
                    "message": f'Wordlist "{name}" created successfully',
                    "word_count": len(data["words"]),
                }
            ),
            201,
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@wordlist_api.route("/wordlists/<path:name>", methods=["PUT"])
def update_wordlist(name):
    """
    PUT /api/wordlists/<name> - Update existing wordlist.

    Body:
    {
        "words": ["WORD1", "WORD2"],  // Replace all words
        "add_words": ["WORD3"],        // Add specific words
        "remove_words": ["WORD4"],     // Remove specific words
        "metadata": {...}              // Update metadata
    }
    """
    try:
        data = request.json

        if not data:
            return jsonify({"error": "Request body required"}), 400

        # Handle word updates
        if "words" in data:
            # Replace all words
            filepath = wordlist_manager.wordlist_dir / f"{name}.txt"
            filepath.parent.mkdir(parents=True, exist_ok=True)

            with open(filepath, "w", encoding="utf-8") as f:
                for word in data["words"]:
                    f.write(f"{word.upper()}\n")

            # Clear cache
            if name in wordlist_manager._cache:
                del wordlist_manager._cache[name]

        elif "add_words" in data or "remove_words" in data:
            # Add/remove specific words
            words = set(wordlist_manager.load(name))

            if "add_words" in data:
                words.update(word.upper() for word in data["add_words"])

            if "remove_words" in data:
                words.difference_update(word.upper() for word in data["remove_words"])

            # Write back
            filepath = wordlist_manager.wordlist_dir / f"{name}.txt"
            with open(filepath, "w", encoding="utf-8") as f:
                for word in sorted(words):
                    f.write(f"{word}\n")

            # Update cache
            wordlist_manager._cache[name] = sorted(words)

        # Update metadata if provided
        if "metadata" in data:
            metadata = wordlist_manager._metadata
            if name not in metadata["wordlists"]:
                metadata["wordlists"][name] = {}
            metadata["wordlists"][name].update(data["metadata"])
            wordlist_manager.save_metadata()

        return jsonify({"message": f'Wordlist "{name}" updated successfully'}), 200

    except FileNotFoundError:
        return jsonify({"error": f'Wordlist "{name}" not found'}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@wordlist_api.route("/wordlists/<path:name>", methods=["DELETE"])
def delete_wordlist(name):
    """
    DELETE /api/wordlists/<name> - Delete wordlist.
    """
    try:
        filepath = wordlist_manager.wordlist_dir / f"{name}.txt"

        if not filepath.exists():
            return jsonify({"error": f'Wordlist "{name}" not found'}), 404

        # Delete file
        filepath.unlink()

        # Remove from cache
        if name in wordlist_manager._cache:
            del wordlist_manager._cache[name]

        # Remove from metadata
        if name in wordlist_manager._metadata["wordlists"]:
            del wordlist_manager._metadata["wordlists"][name]
            wordlist_manager.save_metadata()

        return jsonify({"message": f'Wordlist "{name}" deleted successfully'}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@wordlist_api.route("/wordlists/<path:name>/stats", methods=["GET"])
def get_wordlist_stats(name):
    """
    GET /api/wordlists/<name>/stats - Get detailed statistics for a wordlist.
    """
    try:
        stats = wordlist_manager.analyze_words(name)
        return jsonify(stats), 200

    except FileNotFoundError:
        return jsonify({"error": f'Wordlist "{name}" not found'}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@wordlist_api.route("/wordlists/search", methods=["POST"])
def search_wordlists():
    """
    POST /api/wordlists/search - Search for words across wordlists.

    Body:
    {
        "pattern": "?A?E",
        "wordlists": ["core/common_3_letter", "themed/slang"]  // optional
    }
    """
    try:
        data = request.json

        if not data or "pattern" not in data:
            return jsonify({"error": "Pattern required"}), 400

        results = wordlist_manager.search_pattern(
            data["pattern"], data.get("wordlists")
        )

        # Group by word
        word_sources = {}
        for word, source in results:
            if word not in word_sources:
                word_sources[word] = []
            word_sources[word].append(source)

        return (
            jsonify(
                {
                    "pattern": data["pattern"],
                    "total_matches": len(word_sources),
                    "results": [
                        {"word": word, "sources": sources}
                        for word, sources in word_sources.items()
                    ],
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@wordlist_api.route("/wordlists/import", methods=["POST"])
def import_wordlist():
    """
    POST /api/wordlists/import - Import wordlist from text or URL.

    Body:
    {
        "name": "imported_list",
        "content": "WORD1\nWORD2\n...",  // Direct text
        "url": "https://...",              // Or URL to fetch
        "category": "imports",
        "metadata": {...}
    }
    """
    try:
        data = request.json

        if not data or "name" not in data:
            return jsonify({"error": "Name required"}), 400

        if "content" not in data and "url" not in data:
            return jsonify({"error": "Either content or url required"}), 400

        # Parse words from content
        if "content" in data:
            lines = data["content"].split("\n")
        else:
            # URL import would go here
            return jsonify({"error": "URL import not yet implemented"}), 501

        # Extract words (skip comments and empty lines)
        words = []
        for line in lines:
            line = line.strip()
            if line and not line.startswith("#"):
                words.append(line.upper())

        # Determine category
        category = data.get("category", "imports")
        name_with_category = f"{category}/{data['name']}"

        # Create wordlist
        wordlist_manager.add_words(name_with_category, words, create=True)

        # Add metadata
        metadata = {
            "category": category,
            "description": data.get("metadata", {}).get(
                "description", "Imported wordlist"
            ),
            "tags": data.get("metadata", {}).get("tags", ["imported"]),
            "source": data.get("url", "direct_import"),
        }

        wordlist_manager._metadata["wordlists"][name_with_category] = metadata
        wordlist_manager.save_metadata()

        return (
            jsonify(
                {
                    "message": "Wordlist imported successfully",
                    "name": name_with_category,
                    "word_count": len(words),
                }
            ),
            201,
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500
