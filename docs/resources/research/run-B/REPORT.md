# RUN B — Finding and ranking the words that fit a slot

State of the art, academic and practitioner, for "what fits here, and which of those should I prefer",
with an explanation a constructor can read.

**Run:** `Crossword_Slot_Fill_Ranking_RunB_Research_20260902` · retrieved 2026-09-02 · 59 unique sources,
245 verbatim quotes, 66 registered source records, 332 evidence rows.
No design recommendations are given; findings and sources only.

## How to read this

**Source ids.** `P##` academic papers · `D##` cited-by descendants found through the citation sweep ·
`T##` software (repositories and tool documentation) · `W##` word lists and their scoring documentation ·
`C##` constructor practice and human-factors sources · `B##` sources recovered in the browser pass.

**Retrieval status.** `FETCHED` means a file was downloaded to `corpus/` and every quote attributed to that
source was copied out of that file. `ABSTRACT` means only an abstract was read. `SNIPPET` means only search
results were seen. Nothing here is summarised from memory: every citation field (year, venue, DOI, page range)
comes from the fetched document's front matter, a publisher landing page, or a Semantic Scholar / CrossRef
API record, and where a field could not be confirmed it says so.

**Verification.** Every quote was mechanically re-checked against its saved file in two layers — exact
substring after conservative normalisation, plus a sentence-completion check that catches a quote whose middle
has been altered or whose tail over-runs the source. 236 of 236 passed. The checker was negative-controlled:
a fabricated quote fails, a quote with one word silently substituted is flagged, a quote that runs past the
end of the real sentence is flagged. Three quotes were repaired (bad elisions, one raw-HTML fragment) and
logged in `corpus/main/quote_repairs.json`; twenty were re-attributed to the correct saved file.

**Construction vs solving.** Every source carries a `construction_or_solving` field in the evidence store.
Solving-side work is reported only where a specific technique transfers, and the transfer is stated per source.

## SOURCES

| id | type | citation | url_or_doi | year | retrieval_status | saved_path | licence_or_access | relevance | what_it_gives_us |
|---|---|---|---|---|---|---|---|---|---|
| P01 | paper | Appel, Andrew W. and Jacobson, Guy J. The World's Fastest Scrabble Program. Communications of the ACM 31(5), 572-578, May 1988. | https://www.cs.cmu.edu/afs/cs/academic/class/15451-s06/www/lectures/scrabble.pdf | 1988 | FETCHED | corpus/L1/L1-01.pdf | green OA preprint mirror at cs.cmu.edu (course reading page); original is ACM DL paywalled (dl.acm.org/citation.cfm?id=42420, not tested) | B1 | Founding paper for the DAWG (directed acyclic word graph / minimal acyclic DFA). Gives a concrete space benchmark (trie node count vs minimized DAWG node count, and raw-word-list bytes vs DAWG bytes) and describes anchored, constrained (wildcard) traversal of the DAWG to enumerate legal fills — the core technique a crossword slot-fill engine needs for 'which words fit this pattern'. |
| P02 | paper | Gordon, Steven A. A Faster Scrabble Move Generation Algorithm. Software: Practice and Experience 24(2), 219-232, February 1994. | https://doi.org/10.1002/spe.4380240205 | 1994 | FETCHED | corpus/L1/L1-02.pdf | green OA preprint at ericsink.com/downloads/faster-scrabble-gordon.pdf; publisher version (Wiley) paywalled, not tested | B1 | Introduces the GADDAG (bidirectional-path automaton, avoids DAWG's non-deterministic prefix generation) and gives the actual COMPARATIVE MEASUREMENT the run needs: GADDAG ~5x the size of a minimized DAWG for the same lexicon but >2x the traversal speed, with a full results table (Table III sizes, Table IV timings on 1000 games). |
| P03 | paper | Daciuk, Jan; Mihov, Stoyan; Watson, Bruce W.; and Watson, Richard E. Incremental Construction of Minimal Acyclic Finite-State Automata. Computational Linguistics 26(1), 3-16, 2000. | https://doi.org/10.1162/089120100561601 | 2000 | FETCHED | corpus/L1/L1-03.pdf | open access at ACL Anthology | B1 | Gives the standard algorithm for building a minimal DAWG in one pass (add strings one at a time, minimize on the fly) instead of build-trie-then-minimize, with lower peak memory during construction — directly relevant to how a construction tool would build its own dictionary-lookup structure offline. |
| P04 | paper | Ferragina, Paolo and Manzini, Giovanni. Opportunistic Data Structures with Applications. Proceedings of the 41st Annual Symposium on Foundations of Computer Science (FOCS 2000), pp. 390-398, 2000. | https://doi.org/10.1109/SFCS.2000.892127 | 2000 | FETCHED | corpus/L1/L1-04.pdf | green OA mirror hosted as course reading at khoury.northeastern.edu; IEEE Xplore version paywalled (confirmed by 'Authorized licensed use limited to: The University of Utah... from IEEE Xplo… | B1 | Founding paper for the FM-index / 'opportunistic' compressed self-index (Burrows-Wheeler-based), giving the O(H_k(T)) space bound and O(p+occ log^e U) query time result that succinct-dictionary designs for a large word list would build on. |
| P05 | paper | Ginsberg, Matthew L.; Frank, Michael; Halpin, Michael P.; and Torrance, Mark C. Search Lessons Learned from Crossword Puzzles. Proceedings of AAAI-90, pp. 210-215, 1990. | https://cdn.aaai.org/AAAI/1990/AAAI90-032.pdf | 1990 | FETCHED | corpus/L1/L1-05.pdf | open access at AAAI (official aaai.org/cdn.aaai.org proceedings mirror) | B2 | Describes and quantifies a crossword-specific value-ordering (LCV-family) heuristic: for each of the first k candidate words for a slot, compute the number of remaining legal fills for every unfilled crossing word and take the PRODUCT across crossings; choose the candidate maximizing that product. This is the 'product of remaining crossing candidates' variant named in the task's B2 scope. Also reports a controlled comparison of the look-ahead width parameter k ('min-look'): min-look=1 vs min-look=10, showing the effect is puzzle-difficulty-dependent (on the hardest test puzzle with an ordered dictionary, min-look… |
| P06 | paper | Ginsberg, Matthew L. Dr.Fill: Crosswords and an Implemented Solver for Singly Weighted CSPs. Journal of Artificial Intelligence Research 42, 851-886, 2011 (submitted 07/11, published 12/11). | https://arxiv.org/abs/1401.4597 (author preprint); DOI 10.1613/jair.3437 per jair.org's own page metadata (citation_doi meta tag o… | 2011 | FETCHED | corpus/L1/L1-06.pdf | open access — JAIR is open access, and this is additionally mirrored on arXiv | B2 ; B2,B3,B5 ; B4 / B5 | Formalizes a general weighted-CSP value-ordering rule: order candidate fills by increasing TOTAL propagated cost, i.e. sum over every crossing variable u of the minimum remaining cost in u's domain after the candidate is placed and propagated (Eq. 7-8) — a sum-of-remaining-crossing-candidates LCV variant weighted by per-word cost rather than a flat count. Gives a quantified ablation: using this crossing-aware value-ordering together with their variable-ordering heuristic, Dr.Fill enters an average of 59.4 words correctly into a Times puzzle before its first mistake; switching the value-ordering heuristic to simpl… |
| P07 | paper | Jacobson, Guy. Space-efficient Static Trees and Graphs. Proceedings of the 30th Annual Symposium on Foundations of Computer Science (FOCS 1989), pp. 549-554, 1989. | https://doi.org/10.1109/SFCS.1989.63533 | 1989 | FETCHED | corpus/L1/L1-07.pdf | green OA mirror at gwern.net (personal archive, not the author's own site); IEEE Xplore version paywalled, not tested | B1 | Founding paper for succinct static tree/graph representations (asymptotically optimal bits/node, pointer-competitive traversal time) that underlie LOUDS-style succinct tries cited as a candidate approach for space-efficient dictionary storage. |
| P08 | paper | Frost, Daniel and Dechter, Rina. Look-ahead Value Ordering for Constraint Satisfaction Problems. Proceedings of IJCAI-95, pp. 572-578, 1995. | https://www.ijcai.org/Proceedings/95-1/Papers/075.pdf | 1995 | FETCHED | corpus/L1/L1-08.pdf | open access at ijcai.org official proceedings archive | B2 | Names and formalizes 'look-ahead value ordering' (LVO): for the variable being assigned, count for each candidate value the number of conflicts it produces against future variables' domains (by look-ahead/constraint-checking), and prefer the value with the fewest conflicts. This is the general CSP-literature statement of the sum/count-based LCV heuristic that a crossword-specific 'rank candidates by effect on crossing slots' rule specializes. |
| P09 | paper | Anbulagan and Botea, Adi. Crossword Puzzles as a Constraint Problem. In Principles and Practice of Constraint Programming (CP 2008), LNCS 5202, pp. 550-554, Springer, 2008. | https://doi.org/10.1007/978-3-540-85958-1_40 | 2008 | FETCHED | corpus/L1/L1-09.pdf | green OA author preprint at users.cecs.anu.edu.au/~anbu/papers/CP08.pdf; Springer LNCS version paywalled, not tested | B2 | Verified (FETCHED) secondary confirmation of two otherwise-paywalled seeds: that Mazlack (1976) filled grids letter-by-letter, and that Meehan and Gray (1997) compared a letter-by-letter approach against a word-by-word encoding and concluded the word-by-word approach scales to harder puzzles better. |
| P10 | paper | Haralick, Robert M. and Elliott, Gordon L. Increasing Tree Search Efficiency for Constraint Satisfaction Problems. Proceedings of the Sixth International Joint Conference on Artificial Intelligence (IJCAI-79), Tokyo, pp. 356-364, 1979. | http://www.haralick.org/DV/conferences/increasing_tree_search_efficiency_for_constraint_satisfaction_problems.pdf | 1979 | FETCHED | corpus/L1/L1-10.pdf | author-hosted copy at haralick.org (scanned reprint, no visible copyright/license notice); AI-journal version is Elsevier/ScienceDirect paywalled | B2 | Establishes and experimentally validates forward checking and the 'most-likely-to-fail-first' ordering principle for CSP tree search, the look-ahead framework inside which later work (Dechter & Pearl; Frost & Dechter) situates value-ordering heuristics. Does not itself state a least-constraining-value rule. |
| P11 | paper | Dechter, Rina and Pearl, Judea. Network-Based Heuristics for Constraint-Satisfaction Problems. Artificial Intelligence 34(1), 1-38, 1988. | https://doi.org/10.1016/0004-3702(87)90002-6 | 1988 | FETCHED | corpus/L1/L1-11.pdf | green OA preprint at ics.uci.edu/~csp/r3.pdf (Dechter's UCI research-group site); Elsevier/ScienceDirect version of record is paywalled, not tested | B2 | States, as a named CSP heuristic class, 'Value ordering: an attempt is made to assign a value that maximizes the number of options available for future assignments' — the textbook definition of the LCV family this run traces. Also introduces 'Advised Backtrack' (ABT): a tree-relaxation-based scheme that counts consistent solutions for each candidate value in a simplified (spanning-tree) version of the remaining problem and uses those counts to schedule/rank candidate values. |
| P12 | paper | Beacham, Adam; Chen, Xinguang; Sillito, Jonathan; and van Beek, Peter. Constraint Programming Lessons Learned from Crossword Puzzles. In Advances in Artificial Intelligence (Canadian AI 2001), LNCS vol. 2056, Springer, 2001. [Page range as published unconfirmed — this saved copy is the authors' self-archived preprint, which carries no Springer page numbers.] | https://doi.org/10.1007/3-540-45153-6_8 | 2001 | FETCHED | corpus/L1/L1-12.pdf | green OA author preprint at cs.uwaterloo.ca/~vanbeek/Publications/cai01a.pdf; Springer LNCS version of record paywalled, not tested | B2 | Confirms (from a FETCHED primary source) that the well-known 'Beacham et al.' crossword CSP paper is about variable-ordering heuristics and model/algorithm/heuristic interaction effects, not about value-ordering/LCV for candidate words — useful to rule out as a B2 source rather than assume relevance from its title alone. |
| P13 | paper | Mazlack, Lawrence J. Computer Construction of Crossword Puzzles Using Precedence Relationships. Artificial Intelligence 7, 1-19, 1976. [Citation confirmed via the bibliography of FETCHED source L1-05, not from memory or a search snippet.] | https://doi.org/10.1016/0004-3702(76)90019-9 | 1976 | SNIPPET |  | paywalled (Elsevier/ScienceDirect); no preprint found | B2 | Historical anchor point only. Per L1-05 (Ginsberg et al. 1990, footnote, verified quote): Mazlack's techniques 'are very different from ours, and the performance of his program... appears to be at least one or two orders of magnitude worse' than Ginsberg's word-at-a-time approach. Per L1-09 (Anbulagan & Botea 2008, verified quote): Mazlack filled grids with a letter-by-letter approach. No LCV/value-ordering or dictionary-data-structure content could be confirmed from a primary copy. This entry has no saved_path of its own (no primary copy retrieved); the two supporting quotes confirming its bibliographic fields a… |
| P14 | paper | Meehan, Gary and Gray, Peter. Constructing Crossword Grids: Use of Heuristics vs Constraints. In Research and Development in Expert Systems XIV (Proc. Expert Systems 97), pp. 159-174, 1997. [Author names, title, venue, and pages confirmed via the bibliography of FETCHED source L1-09, not from memory or a search snippet.] | unconfirmed (no DOI located; conference proceedings volume, pre-digital) | 1997 | SNIPPET |  | paywalled/unavailable online — pre-web conference proceedings volume; no publisher landing page or preprint located | B2 | Historical/comparative anchor only (word-by-word vs letter-by-letter for construction scales better word-by-word), sourced secondhand via the FETCHED L1-09. No direct value-ordering content confirmed. This entry has no saved_path of its own (no primary copy retrieved); the supporting bibliographic quote is attached to L1-09's own quotes array (grep-verified against corpus/L1/L1-09.pdf) rather than here. |
| P15 | paper | Wilson, J. M. Crossword Compilation Using Integer Programming. The Computer Journal 32(3), 273-275, 1989. | https://doi.org/10.1093/comjnl/32.3.273 | 1989 | ABSTRACT |  | paywalled (Oxford Academic / OUP); no preprint found | B2 | Confirms the seed exists and is the only integer-programming crossword-compilation paper located; per its own (paraphrased) conclusion it is a negative result for IP as a practical construction method, not a source of value-ordering or dictionary-structure technique. |
| D01 | paper | Agarwal, C. and Joshi, R. K. Automation Strategies for Unconstrained Crossword Puzzle Generation. arXiv:2007.04663, 2020. | https://arxiv.org/abs/2007.04663 | 2020 | FETCHED | corpus/main/M-03_automation_strategies.pdf | open access preprint | B2,B5 | Ranks the words of a list by how many intersections each has with the other words in the list, via a precomputed word-by-word distance matrix, and orders placement by that rank. This is a list-level crossability measure rather than a slot-level lookahead. |
| D02 | paper | Botea, A. and Bulitko, V. Scaling Up Search with Partial Initial States in Optimization Crosswords. Proceedings of the Fourteenth International Symposium on Combinatorial Search (SoCS 2021). | https://doi.org/10.1609/socs.v12i1.18547 | 2021 | FETCHED | corpus/main/M-06_socs2021_partial_initial.pdf | open access (AAAI OJS) | B4 | Describes the Romanian Optimization Crosswords problem, in which the objective is explicitly length-weighted: thematic words score in proportion to their letter count. It is a competition-specific rule, not an American-style convention. |
| D03 | paper | Gourves, L., Harutyunyan, A., Lampis, M. and Melissinos, N. Filling Crosswords Is Very Hard. 32nd International Symposium on Algorithms and Computation (ISAAC 2021), LIPIcs 212, 36:1-36:17, 2021. | https://doi.org/10.4230/LIPIcs.ISAAC.2021.36 | 2021 | FETCHED | corpus/main/M-08_filling_hard_lipics.pdf | open access, CC-BY 4.0 | B1,B2 | Complexity of the exact problem of placing dictionary words into slots with consistent shared cells. Establishes hardness under severe structural restrictions and gives parameterized results, which bounds what any exact per-slot candidate count or lookahead can promise. |
| D04 | paper | Niculescu, V. and Stefanica, R. M. Tries-Based Parallel Solutions for Generating Perfect Crosswords Grids. Algorithms 15(1), 22, 2022. | https://doi.org/10.3390/a15010022 | 2022 | FETCHED | corpus/main/M-09_tries_perfect_grids.pdf | open access, CC BY 4.0 | B1 | A construction-side paper that indexes the dictionary as one trie per word length, with each trie node carrying a 26-bit mask of which letters can continue. Reports wall-clock generation times on a ~700,000-word dictionary, sequential and parallel, on named hardware. |
| D05 | paper | Majima, K. and Ishihara, S. Generating News-Centric Crossword Puzzles As A Constraint Satisfaction and Optimization Problem. CIKM 2023. | https://doi.org/10.1145/3583780.3615151 | 2023 | FETCHED | corpus/main/M-04_news_centric.pdf | open access preprint | none — fetched, scope-checked, and not used | Fetched through the citation sweep and then not cited: a whole-word scan finds zero occurrences of trie, DAWG, GADDAG, bitset, least-constraining, value ordering or crossability, against 58 occurrences of 'crossword' as a control. Its optimisation objective is how many news-topic words a grid contains, which bears on theme selection rather than slot lookup or candidate ranking. Registered so the negative is auditable rather than silent. |
| T01 | code | crosshare-org/crosshare — Crosshare (TypeScript, AGPL-3.0), last default-branch (master) commit 2026-08-17 | https://github.com/crosshare-org/crosshare | 2026 | FETCHED | corpus/L2/L2-01-combined.txt | AGPL-3.0 (gh api repos/.../license confirms spdx_id AGPL-3.0) | B1 | A real, currently-maintained, open-source browser autofiller whose word index is a per-(length,position,letter) bitmap/bitset rather than a trie, and whose 'ranking heuristic' is a 4-tier word-quality score converted to a numeric backtracking cost. Corrects a prompt hypothesis: the filler is plain TypeScript running in a Web Worker, not Rust/WASM. |
| T02 | code | viresh-ratnakar/exet — Exet (JavaScript, MIT), last default-branch (master) commit 2026-08-19 | https://github.com/viresh-ratnakar/exet | 2026 | FETCHED | corpus/L2/L2-02-combined.txt | MIT (gh api repos/.../license confirms spdx_id MIT) | B1+B2 ; B3 | Exet's README doubles as its documentation and directly answers B2: next to each candidate the UI shows its rank/score in the chosen word list (on hover), plus a 'viablot' constrainedness indicator per cell, and demotes candidates that look-ahead analysis shows lead to dead ends. The lexicon's underlying structure is a precomputed pattern-to-word-indices map, already sorted by popularity/score. |
| T03 | code | keiranking/Phil — Phil (JavaScript UI + C/Emscripten SAT solver, Apache-2.0), last default-branch (master) commit 2025-01-02 | https://github.com/keiranking/Phil | 2025 | FETCHED | corpus/L2/L2-03-combined.txt | Apache-2.0 (gh api repos/.../license confirms spdx_id Apache-2.0) | B1 | A negative-leaning result: Phil's interactive UI match list is an unranked, alphabetically-sorted linear regex scan (no candidate quality display at all), and its separate autofill engine is a from-scratch WASM-compiled SAT solver with no notion of word quality -- it only needs a wordlist to draw satisfying assignments from. |
| T04 | code | paulgb/crossword-composer — Crossword Composer (Rust filler + JS/Svelte UI, MIT), last default-branch (master) commit 2020-04-18 | https://github.com/paulgb/crossword-composer | 2020 | FETCHED | corpus/L2/L2-04-README.md | MIT (gh api repos/.../license confirms spdx_id MIT) | B1 | A pure Rust/WASM constraint solver (no quality scoring at all) whose README gives an unusually explicit account of a 'permuted dictionary' pattern index and a structural (not quality-based) constraint-ordering heuristic. Also a second live example of the pushed_at-vs-default-branch metadata gap: pushed_at reads 2023-01-20 but the default branch's last commit is 2020-04-18 (some other branch or a metadata-only push moved pushed_at forward). |
| T05 | code | thisisparker/cursewords — cursewords (Python, AGPL-3.0), last default-branch (main) commit 2025-04-04 | https://github.com/thisisparker/cursewords | 2025 | FETCHED | corpus/L2/L2-05-README.md | AGPL-3.0 (gh api repos/.../license confirms spdx_id AGPL-3.0) | B1 | cursewords is a terminal UI for a human to open, type into, check, and reveal an already-solved .puz file -- it has no autofill, no candidate list, and no algorithm that decides what fits a slot or ranks candidates. It names no technique transferable to slot-fill/candidate ranking, so per the task's counting rule it does not count as a solving tool for B2. |
| T06 | format-spec | century-arcade/xd — the .xd crossword text format and corpus toolset (Python, MIT), last default-branch (master) commit 2026-06-12 | https://github.com/century-arcade/xd | 2026 | FETCHED | corpus/L2/L2-06-combined.txt | MIT (gh api repos/.../license confirms spdx_id MIT) | B1 | xd is a corpus/data-interchange format and toolchain (parsing, validation, a 'gridmatches' grid-similarity table) for published crosswords, not a constructor with an autofill/ranking engine -- useful as a format-spec reference and as a negative result (no ranking heuristic to report) rather than for B2. |
| T07 | code | Qxw by Mark Owen (C, GPL-2.0), quinapalus.com/qxw.html; source release 20200708 (2020-07-08), page last updated 2025-12-20 | https://www.quinapalus.com/qxw.html | 2020 | FETCHED | corpus/L2/L2-07-combined.txt | GPL-2.0 (filler.h header text: 'it under the terms of version 2 of the GNU General Public License'; not on GitHub, no SPDX API available) | B1+B2 | Qxw's UI ranks its feasible-word/feasible-letter list by look-ahead-derived 'promise' (fewer downstream dead-ends), shown via graduated red 'hotspot' markers on constrained cells -- the same concept later echoed by Exet's viablots. Despite dicts.c internally storing a per-word numeric score (used for word-list culling/statistics), the 1.3MB manual never uses the word 'score' in describing what the fill/lookup lists show the user -- a genuine negative result on whether qxw surfaces word quality scores in its candidate list. |
| T08 | code | ben4808/crosshatch — CrossHatch (TypeScript, MIT), last default-branch (master) commit 2021-05-30 [ai_speedup branch active 2026-08-01, unmerged] | https://github.com/ben4808/crosshatch | 2021 | FETCHED | corpus/L2/L2-08-combined.txt | MIT (gh api repos/.../license confirms spdx_id MIT) | B1+B2 ; B3 | CONFIRMS the prior session's report: CrossHatch's Entry Candidates ranking is a literal composite of crossing-fit and word-quality-score, with the exact formula recovered from source. Also: CrossHatch is not a commercial closed product -- it is MIT-licensed and open source on GitHub, so the Part B 'find its documentation' task for Crosshatch is answered by this repo's own README, not by a separate vendor site. Nuance: the default branch's last commit is from 2021-05-30 (code the README/quotes describe), while an unmerged 'ai_speedup' branch was pushed as recently as 2026-08-01 -- pushed_at (2026-08-01) reflects t… |
| T09 | code | szunami/xwords-rs — xwords (Rust, Apache-2.0), last default-branch (main) commit 2021-07-01 | https://github.com/szunami/xwords-rs | 2021 | FETCHED | corpus/L2/L2-09-combined.txt | Apache-2.0 (gh api repos/.../license confirms spdx_id Apache-2.0) | B1 | A genuine trie-based word index (a fourth distinct index structure alongside crosshare's bitmap, exet/crosshatch's bucket-array indices, and qxw/PCRE's linked-list-plus-regex approach) with no candidate-quality ranking at all -- a clean negative result on B2. Author's own README calls it a 'hobbyist project' of uncertain future; last real commit 2021. |
| T10 | code | rainjacket/orca-solver — Orca (Rust, MIT), last default-branch (main) commit 2026-07-03 | https://github.com/rainjacket/orca-solver | 2026 | FETCHED | corpus/L2/L2-10-combined.txt | MIT (gh api repos/.../license confirms spdx_id MIT) | B1+B2 | A recently active (2026-07), high-performance Rust filler using AC-3 arc-consistency propagation (confirmed in propagate.rs) over a per-length, per-position, per-letter bitset index (confirmed in dict.rs, structurally close to crosshare's approach) with cell-level branching and multi-threaded partition search -- a real, named CSP technique that transfers directly to 'what fits this slot' pruning. Clean, explicit negative result on candidate-quality ranking: the tool accepts a scored dictionary format but documents (and the source code confirms) that scores are currently unused, i.e. it optimizes for finding *a* f… |
| T11 | tool-doc | Crossword Compiler (WordWeb Software) — official help manual pages (gridfilling.htm, aboutwordlistscoring.htm, findingwords.htm) plus ProFill.html/wordlists.html marketing-help pages | https://www.crossword-compiler.com/en/help/html/gridfilling.htm ; https://www.crossword-compiler.com/en/help/html/aboutwordlistsco… | 2026 | FETCHED | corpus/L2/L2-11-combined.txt | proprietary software; help documentation pages are public, no login required | B1+B2 | Direct, quoted documentation of Crossword Compiler's word-scoring system (0-100 scale, ~50=common root words, ~25=less common, ~10=vulgar, 3/2=other-English-variety words) and how AutoFill/Fill Grid use it (minimum-score cutoffs, 'weak'/'strong' optimization for average score, a 'non-stop filling' search for the best-scoring set of possible fills). Also a clean within-tool contrast for B2: the Fill Grid/AutoFill engine explicitly optimizes and reports on word score, but the separate 'Find Words' pattern-search dialog sorts results alphabetically (or by length) by default, with no score-based sort offered -- docum… |
| T12 | tool-doc | CrossFire (Beekeeper Labs) — 'An Introduction to CrossFire' reference manual | https://beekeeperlabs.com/crossfire/docs/index.html | 2026 | FETCHED | corpus/L2/L2-12-cf-docs-index-decoded.txt | proprietary (Java desktop app); manual is public, no login required | B2 | CONFIRMS the prior session's 'triad of scores' report, with the manual's own definitions: Word Score (dictionary-assigned), Grid Score (quality of the immediate neighborhood around the word, >0.9 is good), and Final Score (quality of a complete grid fill built from that word, relative to the first fill found). Also documents a separate, per-word-in-grid 'crossing score' (XScore) on the Words tab, and a distinct 'Candidate quality ranking' fill-tab configuration setting that trades fill speed for how thoroughly candidates are vetted before being shown. |
| T13 | code | rf-/ingrid_core — Ingrid Core, the crossword-solving library behind the Ingrid desktop app (Rust, MIT), last default-branch (main) commit 2026-07-05; plus ingrid.cx FAQ documentation | https://github.com/rf-/ingrid_core ; https://ingrid.cx/faq/ | 2026 | FETCHED | corpus/L2/L2-13-combined.txt | MIT (gh api repos/.../license confirms spdx_id MIT); ingrid.cx app itself is closed-source freeware (beta), docs public | B1+B2 ; B6 | Ingrid's actual product/domain is ingrid.cx (Windows/macOS/Linux desktop app, currently in beta) backed by this open-source Rust core (glyph-bucketed word list + AC-style constraint propagation). Its FAQ (the real documentation) directly answers B2: the Fill panel's default 'Recommended' sort balances word score, letter score, and a factor for how many options remain in crossing slots -- another confirmed 'fit + quality' composite, independently arrived at from Crosshatch's. Correction to the prompt's premise: the term 'heatmap' does not appear anywhere in the fetched FAQ or homepage text; the actual documented p… |
| W01 | wordlist | Peter Broda. Peter Broda's Wordlist. Page states 'Update, 2024/01/07'; scored file dated July 25, 2023. peterbroda.me. | https://peterbroda.me/crosswords/wordlist/ | 2024 | FETCHED | corpus/L3/L3-01.html | no licence stated (page only labels the download links 'Download' with no licence or terms text; downloads are of the 'grid text SCORED' file only, other variants read 'Currently unavailable… | B3 | One of the oldest/most-cited free scored lists, but its own explanatory FAQ page did not survive a 2024 server failure ('I recently had a serious issue with my webserver which resulted in the loss of a huge amount of data...'), so the scale/tier documentation for this specific list could not be retrieved from the primary source. The site itself is a first-hand admission of data loss, which is itself evidence for why so many secondary sources (forum posts, T Campbell's list) are now the only place entry counts/scale descriptions for this list survive. |
| W02 | community-post | T Campbell. "Shopping for Wordlists." T Campbell's Grid (Substack). April 11, 2023. | https://tcampbell.substack.com/p/shopping-for-wordlists | 2023 | FETCHED | corpus/L3/L3-02.html | no licence stated (this is a personal blog post, not a wordlist repo) | B3 | A single constructor's snapshot comparison of nearly every list in scope for this lane, with entry counts, prices, and authorship notes (e.g. attributes the Collaborative Word List to 'Alex Boisvert', which we independently corroborated at L3-14). Useful as a cross-check on entry counts and for confirming which lists are free vs. paid. |
| W03 | wordlist | Brooke Husic and Enrique Henestroza Anguiano. Spread the Word(list). spreadthewordlist.com. FAQ/who pages accessed 2026-09-02; site reports its own last update as 'july 1, 2026'. | https://www.spreadthewordlist.com/ | 2026 | FETCHED | corpus/L3/L3-03.html (home), corpus/L3/L3-03-faq.html (FAQ), corpus/L3/L3-03-who.html (who), corpus/L3/L3-03-sample.dict (200-line sample of one downl… | spread the word(list) is licensed under CC BY-NC-SA 4.0 . you’re welcome to use spread the word(list) in a product you’re offering free of charge, with attribution. it’s no problem to sell c… | B3 ; B4 | Confirms authorship (Husic and Henestroza Anguiano, per the site's own 'who' page), a fully explicit 0/zero-cutoff scoring philosophy aimed at 'clean' fill, a stated open licence (CC BY-NC-SA 4.0, non-commercial-with-attribution but explicitly permits puzzles-for-sale), and its data pipeline (Saul Pwanson's database + Parker Higgins's xword-dl downloader). Also independently confirms the existence of the 'crossword puzzle collaboration directory' Facebook group referenced elsewhere in this lane. |
| W04 | code | christophsjones (GitHub user). crossword-wordlist. Repository, last pushed 2020-01-10. | https://github.com/christophsjones/crossword-wordlist | 2020 | FETCHED | corpus/L3/L3-04.html (repo page), corpus/L3/L3-04-README.md (README raw), corpus/L3/L3-04-sample.txt (1501-byte range sample of crossword_wordlist.txt… | no licence stated -- confirmed via `gh api repos/christophsjones/crossword-wordlist` which returns `"license": null`, and no LICENSE file appears in the repo's root file listing (README.md,… | B3 | Confirms, independently via `gh api` (not just prior-session memory), that this repo carries no licence file and was last pushed 2020-01-10. Its README is also one of the clearest short statements of a 1-50-ish tier scale among the lists surveyed, and explicitly documents its own provenance as a blend of NYT/WSJ/WaPo/UKACD/Peter Broda/Norvig-frequency sources -- itself informal evidence that constructors DO blend differently-sourced (and differently-scaled) lists by simply re-deriving one composite score per word from occurrence counts, rather than by converting one list's stated scale into another's. |
| W05 | code | Crossword-Nexus (GitHub org). collaborative-word-list. Repository, last pushed 2024-01-07. | https://github.com/Crossword-Nexus/collaborative-word-list | 2024 | FETCHED | corpus/L3/L3-05.html (repo page), corpus/L3/L3-05-README.md, corpus/L3/L3-05-LICENSE.txt, corpus/L3/L3-05-sample.dict (2001-byte range sample of xword… | MIT License. Copyright (c) 2021 Crossword-Nexus. [full standard MIT text present in LICENSE file] -- confirmed both via `gh api` (license.key: 'mit') and by reading the repo's LICENSE file d… | B3 | Independently confirms (via `gh api`, not just prior-session memory) MIT licence and 2024-01-07 last push. Shows this repo's own documentation is licence/format-complete but scale/tier-silent -- the tier meanings survive only on the predecessor site (L3-14c), which is a genuine finding about documentation completeness for this specific list. |
| W06 | wordlist | Jim Horne / Jeff Chen. XWord Info Scored Word Lists. xwordinfo.com. Accessed 2026-09-02. | https://www.xwordinfo.com/WordList | 2026 | FETCHED | corpus/L3/L3-07.html | requires a paid 'Angel' account ($50) to download; page states an account bought today would run 'until Thu Sep 2, 2027'. See L3-07b for the explicit personal-use-only / no-redistribution cl… | B3 | Authoritative first-party statement of the XWord Info / Jeff Chen list's 5-60 scale and entry counts, replacing any need to infer this from secondary sources. |
| W07 | tool-doc | Jim Horne / Jeff Chen. "Word List Frequently Asked Questions." XWord Info. Accessed 2026-09-02. | https://www.xwordinfo.com/WordListFAQ | 2026 | FETCHED | corpus/L3/L3-07b.html | DO NOT DISTRIBUTE OUR WORD LISTS. The XWord Info Word List is for your personal use only! You are not allowed to give it away or sell it to others, or create derivative lists except for your… | B3 ; B4 | The single richest primary-source explainer of a scoring scale found in this lane, including exact tier definitions AND explicit MERGE guidance for Crossword Compiler: 'If you want to combine the XWord Info Word List with your own personal one, you can do that through the "Word List" menu. Select your own list, and then use "Add Other Lists" to add the XWord Info Word List. You'll want to click "Use the added list's new scores" button.' This is a real-world merge instruction, but it documents score PRECEDENCE (which list's number wins) rather than any SCALE CONVERSION (e.g. mapping a 0-50 scale onto XWord Info's… |
| W08 | tool-doc | Beekeeper Labs. "CrossFire FAQ." beekeeperlabs.com. Accessed 2026-09-02. | https://beekeeperlabs.com/crossfire/faq.html | 2026 | FETCHED | corpus/L3/L3-08.html | no licence stated for the default dictionary itself; describes the two 'gold-standard' external lists (Cruciverb.com, xwordinfo.com) as both requiring paid deluxe membership | B3 | This is CrossFire's own documentation of (a) its bundled default list's derivation (Princeton's WordWeb + blog-frequency scoring), (b) the Ginsberg clue database setup process, and (c) THE KEY MERGE-QUESTION EVIDENCE: CrossFire merges multiple dictionary files by FILE-ORDER PRECEDENCE (earlier files in the list override later ones for a given word), not by any scale-normalization formula, and its 'Merge word lists' dialog literally OVERWRITES existing scores with either manually-chosen values or the bundled CrossFire score database -- it does not attempt to reconcile or convert an incoming list's own stated scale… |
| W09 | community-post | George Ho. "Datasets and Dictionaries for Crosswords." georgeho.org. July 30, 2022. | https://www.georgeho.org/crosswords-datasets-dictionaries/ | 2022 | FETCHED | corpus/L3/L3-09.html | no licence stated (personal blog post) | B3 | Corroborates that Matt Ginsberg's clue database is 'the go-to dataset... but it's unfortunately no longer actively maintained' among American-style constructors, and lists xd.saul.pw as the actively-maintained alternative. Useful as a secondary corroboration of the Ginsberg-database status found via L3-08/L3-15, and lists the same free wordlists (Spread the Wordlist, Collaborative Word List, Peter Broda's) already covered above -- this angle produced no new scoring-scale information, one of the two consecutive 'nothing new' angles that triggered the stop criterion together with L3-17. |
| W10 | tool-doc | Crossword Compiler. "Merging and removing word lists" / "Word Scoring in Word Lists" / "Word List Usage" / "Converting Word Lists". crossword-compiler.com online help. Accessed 2026-09-02. | https://www.crossword-compiler.com/en/help/html/addingliststoeachother.htm | 2026 | FETCHED | corpus/L3/L3-10.html (merging), corpus/L3/L3-10b.html (aboutwordlistscoring.htm), corpus/L3/L3-10c.html (wordlistusage.htm), corpus/L3/L3-10d.html (co… | no licence stated (this is product documentation for a commercial application, not a wordlist) | B3 | THE KEY MERGE-QUESTION SOURCE for Crossword Compiler. Two load-bearing findings: (1) CC's own documented scale philosophy is explicitly that magnitude doesn't matter across lists -- 'The absolute magnitude of the word scores is not very important. Mostly what matters is the relative scores' -- which is the closest thing to an official rationale for why no cross-list scale-conversion rule is published: the tool's design assumes scores are only meaningful relative to other entries in the SAME merged pool, not as an absolute universal unit. (2) The actual merge mechanics ('Add other lists...', 'change the score sett… |
| W11 | community-post | flight (user "flight", original post) and Glenn9999 (reply #8). "Understanding, obtaining, curating word lists (I use Crossfire)." Cruciverb.com Forum, Constructing > General Discussion, topic 107231. Posted May 4, 2020; key reply April 29, 2024. | https://www.cruciverb.com/index.php?topic=107231.0 | 2024 | FETCHED | corpus/L3/L3-12.html | n/a (public forum post) | B3 | DIRECT, ON-POINT COMMUNITY EVIDENCE FOR THE MERGE QUESTION. The original poster asks this project's exact research question almost verbatim in 2020 ('when some are scored using 0-50 scale, others use 0-100, and some don't score at all? Should I merge these together? Won't that Frankenstein words of different scoring scales into each other and kinda render the whole point of using these scores moot, since it will all be unstandardized?'). The one substantive reply (Glenn9999, 2024) confirms there is NO fix: merging just orders words by their raw numeric score with no scale-awareness, 'which will generate an issue… |
| W12 | community-post | admin ("Kevin", reply #3). "Word lists." Cruciverb.com Forum, topic 265. Reply posted June 19, 2009. | https://www.cruciverb.com/index.php?topic=265.0 | 2009 | FETCHED | corpus/L3/L3-13.html | n/a (public forum post) | B3 | A second, independent (15-years-earlier) forum source corroborating the same finding as L3-12: Cruciverb.com's own site administrator confirms the raw Cruciverb word lists ship UNSCORED, that constructors who do score them use inconsistent, personally-chosen ranges (explicitly citing both 1-10 and 1-100 as observed ranges), and that there is no standard reconciliation -- 'a bit hard to make it work for everyone.' |
| W13 | community-post | Alex Boisvert. "The Collaborative Word List Project" and "Some guidelines for scoring words." alexboisvert.com. Accessed 2026-09-02 (project itself dates to the mid-2000s per Google Analytics tracker code present on the page). | https://www.alexboisvert.com/xwordlist/ | 2026 | FETCHED | corpus/L3/L3-14.html (project home), corpus/L3/L3-14b.html (ccw.php, Crossword Compiler usage instructions), corpus/L3/L3-14c.html (guidelines.php, sc… | no licence stated on these pages (this is the project's original home page, which now links out to the current GitHub repo at L3-05 for the actual data/licence) | B3 | IDENTIFIES THE FOUNDER/ORIGIN of the Collaborative Word List Project as Alex Boisvert (independently corroborating L3-02's attribution), and supplies the detailed 1-100 tier-meaning guidelines that the current Crossword-Nexus/collaborative-word-list README (L3-05) does NOT restate -- this page is directly hyperlinked FROM the project's home page TO the current github.com/Crossword-Nexus/collaborative-word-list repo, establishing continuity/provenance from Boisvert's original project to the present-day Crossword-Nexus-maintained repo. Also gives the explicit community-agreed 'cutoff most constructors use': 40, des… |
| W14 | code | Matt Ginsberg (maintainer). Crossword clue database ("cluer"/"cluedata"). Directory listing at tiwwdty.com. Accessed 2026-09-02. | http://tiwwdty.com/clue/ | 2023 | FETCHED | corpus/L3/L3-15.html | no licence stated (bare Apache directory listing, no accompanying terms page found) | B3 | CONFIRMS what the Ginsberg database actually IS for purposes of this B3 (scoring) question: it is still live and downloadable as of a 2023-05-09 update, but it is a CLUE database, not a scored fill-quality word list, so it carries no scoring-scale convention to document. This directly answers the prompt's request to 'look for' this resource: it exists, it's alive, and it is out of scope for a scoring-scale comparison by its very nature. |
| W15 | community-post | Jim Horne / XWord Info. "Word List Updates." XWord Blog. June 10, 2021. | https://xwordblog.com/2021/06/10/word-list-updates/ | 2021 | FETCHED | corpus/L3/L3-17.html | no licence stated (blog post) | B3 | Second of the two consecutive 'nothing substantively new' angles (alongside L3-09 and the Rex Parker / Diary of a Crossword Fiend searches, which surfaced only an unrelated SOLVING-difficulty scale, not a word-list scoring scale) that triggered the stop criterion for the blog/forum-sweep angle of this research. |
| C01 | tool-doc | Peter Norvig. English Letter Frequency Counts: Mayzner Revisited. norvig.com, 2012-12-17 (page dated 2013, updated). | https://norvig.com/mayzner.html | 2013 | FETCHED | corpus/L4/L4-01.html | open web page | B5 | The canonical published source for letter frequency conditioned jointly on POSITION WITHIN WORD and WORD LENGTH. Norvig rebuilds Mayzner & Tresselt's 1965 tables (originally derived from a hand-collected 20,000-word sample) at Google Books scale. Site structure: 'Letter Counts by Position Within Word' gives single-letter frequency by position (1st, 2nd, ... and -1, -2, ... from the end); 'N-gram Counts by Word Length and Position within Word' gives n-gram (bigram through 9-gram) frequency broken out by exact word length AND position within that length, delivered as separate downloadable tables per n-gram length.… |
| C02 | community-post | Matt Gaffney. Our Crossword Creator Explains the 'Breakout Length' and Why It Makes Crossword Grids So Much Better. The Daily Beast, 2020-07-20. | https://www.thedailybeast.com/the-daily-beast-crossword-puzzle-creator-explains-why-the-breakout-length-makes-grids-more-fun/ | 2020 | FETCHED | corpus/L4/L4-02.html | open web page | B4 | Direct, named-author, primary-source answer to the 'does breakout length exist' question: professional constructor Matt Gaffney (Daily Beast, New York, WSJ) states in his own voice that HE personally calls six-letter entries 'breakout length' -- i.e. it is attested constructor vocabulary, but presented as his own coinage/usage rather than an industry-standard term of art. His reasoning is explicitly length-conditional: 3-5 letter entries are so limited in count that the same ones recur constantly (crosswordese), whereas 6-letter slots have exponentially more usable patterns, giving fresher, less-repeated fill. He… |
| C03 | tool-doc | Constructing Crosswords: Fill. CommuniCrossings (compiled constructor reference/wiki page), accessed 2026-09-02. | https://communicrossings.com/constructing-crosswords-fill | 2026 | FETCHED | corpus/L4/L4-03.html | open web page | B4 | A curated aggregator page that (a) independently confirms and re-quotes Gaffney's 'breakout length' passage verbatim, attributing it to him by name; (b) defines 'gluey' as the constructor term for overuse of crosswordese/abbreviations/proper names in a subarea, explicitly tied to short entries; and (c) quotes the NYT's own published submission specification verbatim, which sets a hard length threshold on tolerated abbreviations/partials: uncommon abbreviations and partial phrases are to be avoided once they exceed five letters. This is the clearest length-threshold submission-guideline language found in this lane… |
| C04 | tool-doc | Crosswordese. Wikipedia, revision accessed 2026-09-02. | https://en.wikipedia.org/wiki/Crosswordese | 2026 | FETCHED | corpus/L4/L4-05.html | CC BY-SA (Wikipedia) | B4 | Confirms 'crosswordese' (not 'breakout length') is the standard, dictionary/encyclopedia-attested term of art for the length-linked tolerance concept: it defines the phenomenon explicitly by length band ('usually short, three to five letters') and by the letter-pattern properties that make such words useful glue (vowel-heavy starts/ends, all-consonant abbreviations, unusual letter combinations, high-frequency-letter words). Also carries a book-sourced constructor/solver quote (Marc Romano) on why solvers must track this vocabulary. |
| C05 | tool-doc | Basic Rules (crossword construction rules provided by Will Shortz, editor, New York Times crossword puzzle). Cruciverb.com, accessed 2026-09-02. | https://www.cruciverb.com/index.php?action=ezportal&sa=page&p=21 | 2026 | FETCHED | corpus/L4/L4-06.html | open web page | B4 | The floor-level, non-negotiable length rule (as opposed to a graded tolerance): American-style crosswords set an absolute minimum of three letters per entry, with two-letter entries categorically disallowed. This is the baseline against which all of the graded/length-conditional tolerance guidance above operates. The page states these rules were provided to Cruciverb by Will Shortz. Note: this page's usable text is thin (~19KB, mostly the constructor community CMS chrome); the rules themselves are a short numbered list. |
| C06 | paper | Fiona Shyne, Kaylah Facey, Seth Cooper. Growing a Puzzle Garden: Exploring Casual and Serious Features in a Mixed-Initiative Logic Puzzle Authoring Tool. Proceedings of the 21st AAAI Conference on Artificial Intelligence and Interactive Digital Entertainment (AIIDE 2025), pp.326-334. | https://ojs.aaai.org/index.php/AIIDE/article/download/36836/38974/40913 | 2025 | FETCHED | corpus/L4/L4-09.pdf | open web page (AAAI proceedings, Copyright AAAI, open access on ojs.aaai.org) | B6 | Logged as the closest available adjacent HCI study (see adjacent_not_crossword for why it does not answer B6 directly). Its interface does show an estimated difficulty rating (1-7) next to each generated puzzle and three named 'evaluator' recommendation personas (Logistician = hardest puzzle, Minimalist = easiest/fewest clues, Explorer = most varied clue types) to help users pick among whole generated PUZZLES -- a coarser granularity than B6's 'next to a suggested word' question. The paper's own results section does not report which of these labels participants found helpful versus not; the qualitative feedback t… |
| C07 | paper | Joan Espasa, Ian P. Gent, Ruth Hoffmann, Christopher Jefferson, Alice M. Lynch, Andras Salamon, Matthew J. McIlree. Using Small MUSes to Explain How to Solve Pen and Paper Puzzles. arXiv:2104.15040, 2021 (v2, 2023-01-26). | https://arxiv.org/pdf/2104.15040 (arXiv:2104.15040) | 2021 | FETCHED | corpus/L4/L4-10.pdf | open web page (arXiv preprint) | B6 | This is the DEMYSTIFY paper: a general tool that generates human-interpretable, step-by-step explanations of how to solve pen-and-paper logic puzzles (Sudoku, Futoshiki, Skyscrapers, etc.) using Minimal Unsatisfiable Subsets (MUSes), validated by comparing its explanations against independent human-expert-written solving guides across a range of puzzles (matching 89% of the time on average). CRITICALLY, the paper explicitly and deliberately excludes crosswords by name in its very first footnote, scoping itself to puzzles with fixed, closed value domains (numbers/symbols per cell). This does NOT transfer cleanly t… |
| C08 | community-post | Glossary of Crossword Terminology. qv.neocities.org/xwords (constructor-authored glossary), accessed 2026-09-02. | https://qv.neocities.org/xwords/glossary | 2026 | FETCHED | corpus/L4/L4-11.html | open web page | B4 | A constructor-authored, alphabetically-organized glossary of crossword construction jargon, useful chiefly as a NEGATIVE control for B4's specific-term question: it does NOT include 'breakout length', 'glue'/'gluey', 'seed entry', 'marquee entry', or 'crosswordese' as standalone headwords in the retrieved excerpt, but does confirm and independently date the 'Natick' term (crossing two unfamiliar entries), and notes 'short fill' being pushed toward J/Q/X/Z letters in service of a pangram as a disfavored constructor practice ('scrabblef***ing'). This corroborates that the real, actively-used vocabulary for length-l… |
| C09 | community-post | Wordle Letter Frequency: The Complete Data Breakdown for Every Position. WordlyPlay Blog, accessed 2026-09-02. | https://wordlyplay.com/blog/wordle-letter-frequency-analysis-complete-data | 2026 | FETCHED | corpus/L4/L4-12.html | open web page | B5 | A worked example of position-conditioned letter frequency for a FIXED word length (5), broken into five separate top-5 tables (one per letter position), e.g. position 5 (last letter) top 5 = E(422), Y(364), T(253), R(212), L(155), with E stated to appear in 18.2% of all answers at that position. This is a low-authority source (an SEO/word-game blog, no named author, no methodology detail beyond 'I analyzed'), so treat the specific counts as illustrative rather than authoritative, but it is a concrete, citable instance of exactly the kind of position-by-length table B5 asks for, built from an actual curated word-a… |
| B01 | wordlist | Will Nediger ("bewilderingly"). Nediger-list — spaced wordlist for word puzzle construction. Codeberg repository, README and LICENSE as of 2026-09-02 (head commit ffb36d3917); 23 commits, 3.8 MiB. | https://codeberg.org/bewilderingly/Nediger-list | 2026 | FETCHED | corpus/browser/B-01_nediger_readme.txt, corpus/browser/B-02_nediger_license.txt | MIT License, Copyright (c) 2026 bewilderingly (LICENSE file read in the browser) | B3,B4 | Will Nediger's own wording of his four-score scale, replacing Exet's paraphrase, plus the licence. Carries an author caveat that Exet's paraphrase omitted: the 51-vs-99 split for long entries is self-described as sporadic and unsystematic. The top tier is explicitly length-conditional. |
| B02 | community-post | Maya (m_sch). "New York Times Crossword Analysis." Medium, 17 February 2022. | https://medium.com/@m_sch/new-york-times-crossword-analysis-7aa2f64a1c6f | 2022 | FETCHED | corpus/browser/B-04_nyt_letter_analysis.txt | open web page (Medium); no licence stated | B5 | A letter-frequency distribution computed over an actual NYT crossword ANSWER corpus, and a difference table against general English. Also states, from that corpus, why the commonest short answers are vowel-heavy and drawn from a small letter subset: they are the entries needed for crossings. It contains no position-within-word or by-length breakdown. |

---

## B1 — Data structures for wildcard pattern lookup over 100k–500k words

### The founding papers, and what they actually measure

Five founding papers were fetched in full. The **DAWG** (directed acyclic word graph — a trie with equivalent
sub-tries merged) is Appel & Jacobson 1988 [P01], and it carries the only space measurement in the founding
set that is stated in concrete numbers rather than asymptotics: for their Scrabble lexicon, minimisation
reduced "the number of nodes … from 117,150 to 19,853", and where "The lexicon represented as a raw word list
takes about 780 Kbytes, … our dawg can be represented in 175 Kbytes". The paper also describes the operation
the construction question actually needs — "a pruned traversal of the dawg, constrained by" the letters
already fixed. The move generator around it does not transfer; the anchored, constrained traversal does.

The **GADDAG** is Gordon 1994 [P02], and it is the one source in the whole run that states a direct,
quantified trade-off between two of these structures: the GADDAG "is nearly five times larger than the DAWG,
but generates moves more than twice as" fast, restated in the conclusion as "more than twice as fast, but
takes up five times as much memory for a typical lexicon", with the underlying tables (III for sizes, IV for
timings over 1000 games) in the paper. Again the transferable part is the structure — a bidirectional-path
automaton that can be entered at any anchor position — not the Scrabble move generation on top of it.

Daciuk et al. 2000 [P03] is the standard way to *build* a minimal DAWG: instead of building a trie and then
minimising it, they "construct a minimal automaton in a single phase by adding new strings one by one and
minimizing the resulting automaton on-the-fly", which "is fast and significantly lowers memory requirements"
during construction. Jacobson 1989 [P07] is the founding succinct-tree paper (asymptotically optimal bits per
node while remaining "just as time-efficient for traversal operations" as pointers), and Ferragina & Manzini
2000 [P04] is the founding FM-index / compressed self-index paper. Both were fetched, and both are included as
the named ancestors of the succinct-index family — neither is a crossword or wildcard-dictionary paper.

**Negative result.** No academic paper was found that runs a controlled comparative benchmark of trie vs DAWG
vs hash vs succinct index *for wildcard-pattern dictionary lookup at the 100k–500k word scale*. The searches
run are logged in `corpus/L1/evidence.json` under `negative_results`. The GADDAG-vs-DAWG numbers in [P02] are
the closest thing that exists, and they measure Scrabble move generation, not slot-pattern lookup.

### The one construction-side measurement

Niculescu & Ştefănică 2022 [D04], found through the citation sweep, is the only fetched paper that measures a
dictionary structure inside an actual crossword-grid generator. Its representation is a hybrid of two of the
options in the question: an **array of tries, one per word length** — "The words of the dictionary are
represented using a complex data structure that contains max_size tries; the number max_size is equal to the
maximum size of the words from the dictionary (e.g., max_size = 16 for our dictionary)", justified because
"in order to fill a crossword grid, as specified in the problem specification, we need words of specific
lengths" — with each trie node additionally carrying **a 26-bit continuation mask**: "A number—code—which is
obtained from a binary representation with 26 digits that reflects the possible continuations: – 0 on the
position i means that there is not a subtrie corresponding the ith letter; – 1 on the position i means that
there is a subtrie corresponding the ith letter." The paper states its purpose plainly: "This binary code is
very important in the fast verification of the possible letters that could be placed in a new position."

Its timings run from 0.9 s to roughly 80 minutes depending on the seeded word, on a ~700,000-word dictionary
("The experiments were conducted using a dictionary of almost 700,000 words, and the solutions were obtained
using the parallelised version with an execution time in the order of minutes"), on a two-socket Xeon E5-2660
v3 cluster node with 8 MPI processes × 32 threads. **Caveat that materially limits this number:** these are
whole-grid generation times for Romanian *perfect* crosswords (no black cells at all), not per-slot lookup
benchmarks, and not American-style grids.

### What shipped tools actually use — eight distinct structures, and no DAWG anywhere

This is the strongest B1 result, and it comes from source files rather than papers. Paths are given; reading
them in depth is Task R's job.

| Structure | Tool | File |
|---|---|---|
| Bitset over (length, position, letter), AND-ed per known letter | Crosshare [T01] | `app/lib/WordDB.ts` |
| Bitset over (length, position, letter), AND-ed per known letter | Orca [T10] | `crates/core/src/dict.rs` (`struct LengthBucket`) |
| Nested bucket arrays keyed `[len][pos][letter]` and `[len][pos1][pos2][l1][l2]` | CrossHatch [T08] | `src/lib/wordList.ts` (`indexWordList`, `queryIndexedWordList`) |
| Precomputed pattern-key → word-index map, with key generalisation on miss | Exet [T02] | `exet-lexicon.js` (`getLexChoices`, `index`, `generalizeKey`) |
| Real character trie (`FxHashMap<char, TrieNode>`) with `is_viable` walk | xwords-rs [T09] | `src/trie.rs` |
| Array of per-length tries + 26-bit continuation mask per node | Niculescu & Ştefănică [D04] | (paper, §4.1) |
| Length-bucketed glyph-id vectors, queried through arc consistency | Ingrid [T13] | `src/word_list.rs`, `src/arc_consistency.rs` |
| Linked-list "answer pool" of byte-packed entries + PCRE compiled per query | Qxw [T07] | `dicts.c` (`adddictword`) |
| Permuted dictionary per word-constraint, keyed on the letters known by visit time | crossword-composer [T04] | `src/index.rs` |
| No index at all — linear regex scan over an alphabetically sorted array | Phil [T03] | `wordlist.js` (`matchFromWordlist`) |

**The notable negative: not one shipped open-source crossword tool examined uses a DAWG or a GADDAG.** The
Scrabble lineage that produced the two most-cited structures in B1 does not appear in crossword construction
software at all. The dominant production pattern is instead the per-position letter bitset — arrived at
independently by Crosshare (TypeScript, 2026) and Orca (Rust, 2026), whose implementations are structurally
near-identical.

Every licence, language and last-default-branch-commit date in the tool table was re-verified on the main
thread with a direct `gh api` sweep over the ten repositories, rather than relayed from the retrieval lane;
the raw API responses are saved at `corpus/main/gh_repo_facts.jsonl`. All ten agreed. The sweep also confirms
two cases where GitHub's `pushed_at` does not track the default branch and would mislead: crossword-composer
[T04] reads `pushed_at` 2023-01-20 against a last default-branch commit of 2020-04-18, and CrossHatch [T08]
reads 2026-08-01 against 2021-05-30 (an unmerged `ai_speedup` branch).

Crossword Compiler [T11] and CrossFire [T12] document their scoring and fill behaviour in public help pages
but **do not document their internal index structure anywhere in the retrieved documentation** — a negative
result for the two commercial tools named in the question.

### Memory layout and serialisability

Recorded because the brief asks for it, as observation rather than recommendation. The bitset indices [T01],
[T10] and the bucket arrays [T08] are flat arrays of fixed-width integers with no interior pointers, and both
Rust bitset implementations already live in that shape. [D04]'s design sits in between: an array of 26 child
slots plus one 32-bit code word per node. By contrast [T09]'s trie is `FxHashMap<char, TrieNode>` —
pointer-chasing and hash-bucketed, the least directly serialisable of the set. Qxw [T07] packs each entry's
score into a single byte (`*(memblkp->s+memblkl++)=(char)floor(f*10.0+128.5); // score with rounding`) inside
a linked list of memory blocks. Also relevant to a WASM port: Crosshare's filler is **plain TypeScript in a
Web Worker, not Rust/WASM** — this corrects a premise carried into the run. The genuinely Rust tools are
crossword-composer [T04] (Rust compiled to WASM, 2020, unmaintained), xwords-rs [T09] (2021), Orca [T10]
(2026-07), and Ingrid's core [T13] (2026-07). Phil [T03] does use WASM, but for a Glucose 3.0 SAT solver
compiled with Emscripten, not for the word index.

---

## B2 — Ranking candidates by their effect on crossings

### Where the heuristic comes from

The general CSP statement is Dechter & Pearl 1988 [P11], which gives the textbook definition — "(b) Value
ordering. An attempt is made to assign a value that maximizes the number of options available for future
assignments" — and introduces Advised Backtrack, which counts consistent solutions for each candidate value in
a tree relaxation of the remaining problem in order to rank them. Frost & Dechter 1995 [P08] name and
formalise the operational version: a "heuristic, which we call look-ahead value ordering or LVO. LVO counts
the number of times" a candidate conflicts with future variables' domains, and "ranks the values of a variable
based on information gathered by looking ahead".

**Correction worth stating explicitly.** Haralick & Elliott [P10] is routinely cited as the LCV ancestor. The
fetched copy is the **9-page IJCAI-79 conference paper**, not the 51-page 1980 *Artificial Intelligence*
article, and its contribution is forward checking plus the "most likely to fail first" principle — which is
the *opposite* polarity to least-constraining-value. It is the look-ahead framework inside which value
ordering later sits, not a statement of the LCV rule.

### The two crossword-specific variants that exist

**Product of remaining crossing candidates — Ginsberg, Frank, Halpin & Torrance 1990 [P05].** This is an
actual grid-construction program, not a clue solver. For each of the first *k* candidate words for a slot,
"the number of possibilities for each unfilled crossing word is computed, and the product of all of these
values is calculated. The word actually chosen is that w_i that maximizes this product." The paper also
measures the look-ahead width *k* (its "min-look" parameter) rather than asserting it: at min-look 10 the
hardest test puzzle failed to solve "within the twenty minute time limit", while "For min-look set to 1,
however, only 15" seconds were needed — and its own analysis concludes that "finding a word that minimally
restricts the subsequent search is worthwhile only on puzzles of size 9 x 9 and" larger. So the founding
crossword LCV paper reports the heuristic's benefit as *conditional on grid size*, and reports a case where
more look-ahead was strictly worse.

**Cost-weighted sum of per-crossing minima — Ginsberg 2011, Dr.Fill [P06].** The rule is stated as: "We order
the variable values in order of increasing total cost as measured by (7), preferring choices that not only
work well for the word slot in question, but also minimally increase the cost of the associated crossing
words." Equation (8) makes the quantity explicit — for each crossing slot, the minimum achievable cost after
placing the candidate minus the minimum before — and the paper names it: "The heuristic value of setting v to
f is the difference between these two numbers, the total 'damage' caused by the commitment to use fill f for
variable v." This is a sum over crossings of a *score* delta, not a count. The paper also gives the only
ablation of a crossing-aware ranking found anywhere in the run: with this value ordering Dr.Fill enters 59.4
words correctly on average before its first error, and switching to simply preferring the best-scoring fill for
the slot in isolation drops that to "25.3, well under half".

Dr.Fill is a clue-answering solver, so the transfer must be named: its per-candidate score ρ is
clue-conditioned, and at construction time there is no clue. What transfers is the *shape* — the damage
function over crossing slots, computed on pattern-restricted domains — with a word-list quality score standing
in for ρ. Its companion variable-selection rule also transfers cleanly and is independent of clues: rather
than branching on the slot with the smallest damage, "choose to value not that variable for which h(f, v) is
minimized, but the variable for which the difference between the minimum value and second-best value is
maximal" — i.e. branch where the margin between the best and second-best candidate is largest.

**Negative results.** No published crossword-specific variant using MIN, LOG-SUM, or weighting by crossing
length was found; the queries are logged in `corpus/L1/evidence.json`. And despite its exact-match title,
Beacham, Chen, Sillito & van Beek 2001 [P12] — the year is **2001**, not 2005 — studies only *variable*-ordering
heuristics ("The three dynamic variable orderings heuristics used were the popular dom+deg heuristic …"), so it
does not bear on candidate ranking and can be ruled out rather than assumed relevant from its title.

### How tools present it to the user

Four tools' presentations were checked against their own documentation and source. Of the two items the
brief carried as *reported but unverified* — Ingrid's per-cell suggestions plus a constraint heatmap, and
Exet's autofill hints — Exet's are confirmed and richer than reported, and Ingrid's per-cell suggestions are
real but **its constraint heatmap does not exist**. The two the brief already had as confirmed this session —
CrossFire's score triad and Crosshatch's fit-plus-quality composite — are re-confirmed here independently,
CrossFire from the vendor manual and Crosshatch from its source code rather than its README.

*CrossFire's triad* [T12], quoted from the manual: "Word Score : dictionary-assigned score for a word.";
"Grid Score : measure of the quality of the neighborhood immediately around the word. Generally any value over
0.9 indicates a pretty good word, while lower values are generally going to lead to bad fill values in the
near future."; "Final Score : measures the quality of a complete grid fill created with this word. (This value
is relative to that of the first fill found…)". Beyond the triad, the Words tab shows entered words "along with
their lengths, their scores, and a measure of their 'crossing score'", and a Fill Options setting controls
"Candididate quality ranking … how thoroughly words are examined before added as candidates on the fill tab"
(the manual's own spelling) — an explicit user-facing knob trading fill speed against candidate vetting.

*Crosshatch's fit-plus-quality composite* [T08] is confirmed at source level, not merely from marketing text.
The README says candidates are "ranked by how well they fit with the entries around them in the grid and by
their quality score", and `src/lib/entryCandidates.ts` computes exactly that:
`let ret = (crossScore + minCrossScore) * wordScore * (ec.iffyWordKey ? 1 : 100);`, with `wordScore` coming
from discrete quality tiers in `src/lib/fill.ts` (`case QualityClass.Lively: return 12;`, Normal 9,
Crosswordese 3). So the composite is (fit term) × (quality term) × (a two-order-of-magnitude penalty for
out-of-list words).

*Ingrid* [T13] — the reported per-cell suggestions are real, the reported heatmap is not. The FAQ states: "The
default sort order in the fill panel, Recommended, tries to balance word score, letter score, and a factor
based on how many options will be available in the crossing slots for each word." That is a third independent
fit-plus-quality composite, and the only one that names remaining-crossing-options as a term in the user-facing
default sort. The claimed "constraint heatmap" does not exist: the word heatmap appears nowhere in the fetched
FAQ or homepage. The actual affordance is discrete — a slot with "shaded edges" means "you've applied some
additional constraint to the slot: approved or rejected words, a pinned filter, or an overridden required word
score", and "You can hover your mouse over the slot in the grid to see a summary of the constraints added to
it."

*Exet's autofill hints* [T02] are confirmed and are richer than reported. Suggestions "are ordered by their
popularity in English Wikipedia articles"; "Hovering over a grid-fill suggestion will show its rank (and score,
if available) in the word list"; cells with few remaining choices get "viability indicators (I call them
'viablots'). These are red circles that appear in light cells that have only a few available grid-fill
choices"; and a look-ahead runs per candidate — "the software evaluates each candidate suggestion for a light
(that matches its crossing letters) by checking if the choice leads to a dead-end for any of the crossing
clues", after which "Grid-fill suggestions that lead to dead ends are moved to the bottom of the list and are
shown with a purple background (and a warning tooltip)."

*Qxw* [T07] ranks by look-ahead promise rather than by word score: "The feasible character list shows what
characters can be used to fill the cell under the cursor (the 'current cell'), in order from most promising to
least promising." A whole-word search of the 1.35 MB manual (re-run on the main thread, not taken from the
lane's report) finds **zero** occurrences of score / scores / scored / scoring — the single substring hit is
inside the word "underscore", and a control term from the same page ("promising") matches, so the search works —
i.e. the manual never describes the fill lists as score-ranked — `dicts.c` does store a per-word score, but for word-list culling and
statistics, not for ranking the displayed candidates.

*Crossword Compiler* [T11] gives a useful within-tool contrast: its grid filler optimises on score ("By using
the optimization options you can vary the number of 'good' and 'bad' words filled into the crossword", and the
Pro filler offers "finding the best-scoring set of possible fills"), but the separate pattern-search dialog
does not — "By default the found words are sorted alphabetically. Select the sort by length option if you
prefer them to be sorted by length (shortest matches first)." Two candidate-listing surfaces in one product,
only one of them ranked.

**Tools that deliberately do no quality ranking at all**, which is itself a finding about how common the
capability is: Phil [T03] returns an unranked alphabetical regex scan and its SAT-based filler has no notion of
word quality; xwords-rs [T09] has no scoring code anywhere; Orca [T10] parses a `WORD;SCORE` dictionary but its
README states "Scores are currently unused"; crossword-composer [T04] orders word constraints structurally
(longest first, then most shared letters) purely to fail fast, with no quality term.

---

## B3 — Word-list quality as a ranking signal

### The scales

| List | Scale | Tier meanings as documented | Entries | Licence | id |
|---|---|---|---|---|---|
| Spread the Word(list) | 0–50 | 50 = "clean"; 0 = blocklisted | 314,276 (120,178 at 50, as of 2026-07-01) | CC BY-NC-SA 4.0 | W03 |
| Peter Broda | **undocumented** — file shows 30–100 | lost with the site's FAQ | ~527,330 (2023, secondary) | **no licence stated** | W01 |
| Chris Jones (`christophsjones`) | ~1–50 | 50 = "wouldn't hesitate", 25 = "acceptable", 2 = floor, 1 reserved for future semi-words | ~170k stated / 175,872 (secondary) | **none** (`gh api` → `license: null`) | W04 |
| Crossword Nexus collaborative list | 1–100 | **not in this repo** — only on the predecessor page [W13] | CI requires >425,000; 567,643 (2023, secondary) | MIT (LICENSE file read) | W05 |
| XWord Info / Jeff Chen | 5–60, fixed rungs 5/15/20/25/50/60 | 60 = "assets", 50 = "fine", 25 = weak 3–4s, 20 = weak 5s, 5 = "Avoid at all costs!" | 253,276 (118,460 from NYT) + 27,854 premium | paid Angel account, **no redistribution** | W06, W07 |
| CrossHatch bundled sample | binary 40/50 in the sampled range | ≥50 "Good", 40–49 "Okay", absent = "Iffy" | not stated | app MIT; **data repo unlicensed** | T08 |
| Exet "Lufz" | percentile **rank**, not a score band | default cutoff = 80th percentile | 346,931 | MIT | T02 |
| Nediger List | four fixed tiers | 25 / 49 / 51 / 99, in the author's own words | 348,311 (per Exet) | **MIT**, © 2026 bewilderingly | B01, T02 |
| CrossFire bundled default | unscaled, frequency-derived | none published | n/a | no licence stated | W08 |
| Ginsberg "cluer" database | **n/a — a clue database, not a scored list** | n/a | n/a | no licence stated | W14 |

Three findings sit behind that table. First, **documentation completeness does not follow licence quality**:
the MIT-licensed Crossword Nexus repo [W05] documents its format and licence but not its scale — the 1–100
tier meanings survive only on Alex Boisvert's original project page [W13], which the repo still links to, and
which supplies the community cutoff in plain words: "NOTE: I would say that 40 is the minimum value you should
use when filling a grid using this list." Second, **the most-cited free list is now the least documented**:
Peter Broda's own explainer did not survive a 2024 server failure, in his own words — "I recently had a serious
issue with my webserver which resulted in the loss of a huge amount of data, code, and previously configured
services" — leaving only the scored file itself. Third, the **most thoroughly documented scale is the one you
cannot redistribute**: XWord Info's FAQ [W07] is the richest primary explainer found, and the same page says
"DO NOT DISTRIBUTE OUR WORD LISTS."

The **"Crosshatch/Diehl" list does not exist as a published product** [T08, W02]. CrossHatch is an MIT-licensed
construction app by GitHub user ben4808; its bundled sample list is, per its own README, "based on Mark Diehl's
trimmed version of the Peter Broda word list", originally circulated through a post in the Crossword Puzzle
Collaboration Directory Facebook group. The name in the brief conflates an app with one constructor's
informally-shared rescoring of somebody else's list.

Two lists outside the brief's set turned up and are worth recording: the **Nediger List** and **Lufz**,
Exet's own Wikipedia-popularity-ranked lexicon [T02]. The Nediger List's repository was reachable only in a
browser (Codeberg returns HTTP 403 to `curl`), and reading it there replaced Exet's paraphrase with the
author's own wording [B01]: "There are four scores: 25 (entries I'll use only if absolutely necessary), 49
(entries that are likely too racy for many mainstream venues), 51 (entries I'll use in most circumstances),
and 99 (for up to 7 letters, entries that are very easy and/or inferable, and for 8 or more letters, entries
that would be considered assets in many venues)." It is MIT-licensed, © 2026, and hand-built — "I created the
wordlist by hand, with much help from Wikipedia, OneLook, and other freely available wordlists."

The browser also recovered a caveat the paraphrase had dropped, and it is the more useful half of the
finding: **the author does not trust his own top tier.** "The 51 vs 99 scoring for long entries is very
sporadic and unsystematic." A consumer of this list would have read 51-vs-99 as a quality signal on long
entries; its author says it is noise there.

### How tools merge lists on different scales: they don't

This was the sharpest result in the lane. **No tool and no forum thread documents a numeric conversion between
scales.** Four mechanisms were found, and all four push the problem onto the user:

- **Crossword Compiler** states the doctrine outright [W10, T11]: "The absolute magnitude of the word scores is
  not very important. Mostly what matters is the relative scores, with a word higher than another being used
  much more frequently (in grid filling)." Its own default list is scored 50 / 25 / 10 / 3 by commonness on an
  advertised 0–100 range. Merging ("Add other lists…") and plain-text import both ask the user what scores to
  assign; nothing rescales.
- **CrossFire** merges by **file-order precedence** [W08]: "words from earlier files override words from
  later", and its Merge dialog overwrites existing scores outright rather than reconciling them.
- **XWord Info's own merge instruction** [W07] is to click "Use the added list's new scores" — precedence
  again, not conversion, and its 5–60 numbers land unchanged next to whatever the user's own list uses.
- **The community answer is "don't"**. A 2020 Cruciverb thread [W11] asks this project's question almost
  verbatim — "when some are scored using 0-50 scale, others use 0-100, and some…", "Should I merge these
  together?", won't that "Frankenstein words of different scoring scales into each other and kinda render the
  whole point of using these scores moot, since it will all be unstandardized?" The substantive 2024 reply
  confirms there is no fix: "I think it orders preference based on the numbers, which will generate an issue if
  different word lists have different scoring ranges." The recommended workaround is to use one list only —
  "Import and uncheck the existing lists in the Config>Dictionary area. One list to rule them all." A 2009
  post from Cruciverb's own administrator [W12] says the same thing fifteen years earlier: "The cruciverb word
  lists just contain the words. People score their words differently, and sometimes with different ranges
  (1-10,1-100)."

The single documented technique that does anything cleverer is Exet's [T02], and it blends rather than
converts: having taken the Nediger List's four discrete tiers, "The scores have been augmented by a decimal
component (e.g., 51.42845) that captures the popularity ranking" — a coarse external tier scheme
sub-ranked by an internally-computed continuous signal. That is one author folding one external list into his
own ranking, not a general cross-scale rule.

Chris Jones's list [W04] documents the other observed practice: rather than convert scales, blend the *sources*
and re-derive a single score — "A score is computed for each word based on the number of occurrences in each of
these", across NYT/WSJ/WaPo/UKACD/Broda/Norvig-frequency inputs.

### The one published methodology for building a quality score

Dr.Fill's [P06] is the only crossword word-list scoring methodology in the academic literature: "Crossword
merit for the large dictionary was evaluated by hand scoring approximately 50,000 words (100 volunteers, all
crossword constructors, scored 500 words each). The words were then evaluated against many criteria (length,
Scrabble score, number of Google hits, appearances in online corpora, etc.) and a linear model was built that
best matched the 50,000 hand-scored entries. This model was used to score the remaining words." The paper is
also candid about the limit of any such score: "Note that the scores here reflect the crossword 'value' of the
words in isolation, ignoring the clues." For provenance, its "common words" dictionary is "the 'basic English'
dictionary that is supplied with Crossword Compiler".

---

## B4 — Length-dependent tolerance

### "Breakout length" is one constructor's coinage, not a term of art

The term is real and attributable, and its origin is a single author. Matt Gaffney, in the Daily Beast
(2020-07-20) [C02]: "Because six letters is what I call 'breakout length' in crosswords." His reasoning is
explicitly length-conditional — "There are exponentially more usable six-letter patterns than three-letter, so
you get much more lively stuff" — and he supports it with a frequency contrast ("CNN has appeared over 100
times in the New York Times in the Shortz Era"). A constructor aggregator re-quotes him by name [C03]: "Six
letters (the 'breakout length') — that's the promised land".

It appears nowhere else. It is absent from Cruciverb, XWord Info, Wikipedia, and a constructor-authored
glossary [C08] that does carry adjacent jargon (it defines "natick" as "a square in a puzzle where two
unfamiliar words - usually (but not always) proper names - cross one another", and records "scrabblef***ing"
for inorganically forcing J/Q/X/Z into "short fill"). **The attested vocabulary for this concept is
crosswordese / glue / short fill / Natick**, and Wikipedia's crosswordese entry [C04] defines the phenomenon by
length band directly: "The words are usually short, three to five letters".

### The thresholds that are actually written down

**XWord Info's scoring scale is length-conditional and says why** [W07]. Two adjacent tiers separate on nothing
but entry length: the 25-point tier is "Three- or four-letter words that would be hard to defend as fine",
while the 20-point tier — lower, i.e. worse — is "Five-letter entries that would be hard to defend as fine",
with the reasoning given in the FAQ's own parenthesis: "(Generally, Jeff finds that short 'gluey' entries are
less offensive than longer ones.)" That is precisely the "a 3-letter entry can be X but a longer one must be Y"
pattern the question asks for, in a published scale, with its rationale stated.

**A second published length-conditional rule** sits in the Nediger List's top tier [B01], which splits on
length inside a single score: 99 covers, "for up to 7 letters, entries that are very easy and/or inferable, and
for 8 or more letters, entries that would be considered assets in many venues". The same number means
"harmless" for a short entry and "asset" for a long one. Read in the author's own repository rather than
through Exet's paraphrase, however, it comes with a self-issued warning: "The 51 vs 99 scoring for long
entries is very sporadic and unsystematic." The length-conditional *definition* is published; the author's
own view is that its application to long entries is unreliable.

**The NYT submission specification sets a hard cutoff** [C03]: "Avoid uncommon abbreviations and partial
phrases longer than five letters", alongside "Keep crosswordese to a minimum". And the floor rule, attributed
to Will Shortz [C05], is categorical: "Do not use two-letter words. The minimum word length is three letters."

**Academically**, the one length-conditional model is Dr.Fill's [P06] — length is an explicit feature in the
linear model fitted to the 50,000 constructor-hand-scored words. There is no academic source that derives or
validates a length threshold; the model merely includes length as an input.

**A length-weighted objective exists but in a different tradition**: Romanian Optimization Crosswords, as used
in the SoCS/AIIDE line of work [D02], score thematic words "corresponding to their" letter count, so grid score
is a sum of lengths. That is a competition rule, not an American-style convention, and should not be read
across.

---

## B5 — Letter-position frequency and "crossability"

**"Crossability" is not a crossword term.** Searched directly; it exists only as a biology/genetics term. No
crossword-specific metric under that name, and no clear crossword-specific synonym ("crossing friendliness" and
similar) was found either. Clean negative.

**The canonical position-conditioned table is Norvig's** [C01], which rebuilds Mayzner & Tresselt's 1965 tables
at Google Books scale — "37 million times more data (and with a few more columns)" than Mayzner's original,
which he quotes as "I culled a corpus of 20,000 words from a variety of sources". Norvig's distillation covers
97,565 distinct words from 743,842,922,321 tokens, and it is structured exactly as the question needs: letter
frequency by position (both 1st, 2nd, … and −1, −2, … from the end), plus n-gram counts broken out by *word
length and position within that length*. The limitation is stated on the source itself and must travel with any
use of it: **this is general English prose, not a crossword-answer corpus.**

**A crossword-answer-corpus letter distribution does now exist in evidence, recovered in the browser pass**
[B02]. Computed over 781,573 NYT clue/answer rows from 1993–2021: "The letters 'e', 'a' and 's' appear the
most frequently (14%, 12% and 9% respectively). The letters 'x', 'z', 'j', and 'q' appear the least often,
making up less than 1% of all letters in NYT crossword answers (0.3%, 0.3%, 0.2% and 0.1% respectively)." Set
against general English, "Most of the letters remain within +/- 1.5% of their frequency distribution between
the English language and NYT answers" — so the crossword answer corpus is close to prose at the aggregate
letter level, and Norvig's general-English table is a defensible proxy *for that statistic*. The same source
states the crossability intuition directly from its corpus: the commonest answers are all three or four
letters, drawn from {a, e, r, o, n, l, t, i} and vowel-heavy, and "This makes sense since these small lettered
words are needed for 'crossings', the intersection between an Across and Down entry." It is a Medium post by a
single author working from a Kaggle dataset — medium authority, but the corpus and method are named.

**It does not close the position question.** Read in full, [B02] contains no letter breakdown by position
within word and none by word length; Figure 2 is a single aggregate distribution. The only concrete position ×
length table obtained [C09] is still the one built from the Wordle answer list — a curated word-answer list rather than prose, which is the right
*shape*, but it is an unattributed word-game blog with no stated methodology beyond "I analyzed the complete
Wordle answer list", and it is recorded as illustrative rather than authoritative.

**The nearest crossword-specific letter signals, and a direction problem.** Dr.Fill's merit model [P06] uses
Scrabble score as one of its features — but the polarity runs opposite to crossability. The paper's own worked
example prizes rare letters: BUZZ LIGHTYEAR is excellent fill because "The letters are interesting (high
Scrabble score, basically), and the combination ZZL is unusual", while TERN is merely acceptable because "the
letters are mundane". So the one published crossword-specific letter-quality signal *rewards* the letters that
are hardest to cross. Any crossability score would need the opposite sign, and nothing published reconciles the
two.

Ingrid [T13] ships a `letter_score` field on its `Word` struct and names "letter score" as a term in the
Recommended sort — a per-word letter-quality signal in production — but the FAQ does not define what it
computes. Agarwal & Joshi [D01] give the only *computed* crossability-like measure found: their algorithm
"generates a distance matrix for a given word list, by computing the distance of every word with every other
word in the list, and then uses it to rank words based on the number of intersections that they have with other
words." That is a list-level measure (how well a word intersects the rest of the vocabulary), not a slot-level
one, and it is used to order placement rather than to explain a candidate. Wikipedia's crosswordese entry [C04]
describes the letter patterns that make glue useful qualitatively — vowel-heavy starts and ends, all-consonant
abbreviations, unusual combinations — without a table.

---

## B6 — What insight next to a suggested word actually helps

**There is no user study on crossword construction tools. This is a clean negative and it is the finding.**
Searched: ACM Digital Library, CHI / IUI / CSCW / Creativity & Cognition, Semantic Scholar (keyless API
returned HTTP 429 on every attempt; fell back to web search), and general web, across queries including
"crossword construction user study", "computational creativity support crossword puzzle generation",
"explainable constraint satisfaction 'why not' explanation user study", and constructor-facing phrasings such
as "kills 12-Down" / "remaining candidates" fill-suggestion affordance. The full query log is in
`corpus/L4/evidence.json`.

**The closest real user study is about a different puzzle.** Puzzle Garden [C06] (AIIDE 2025) is a
mixed-initiative *authoring* tool with a genuine 3-week, 18-participant study, but for logic-grid puzzles, and
its granularity is wrong for this question: it shows a 1–7 difficulty estimate and three named recommender
personas beside whole generated puzzles, not beside a candidate word. Its results section does not report
whether participants found those labels useful; the qualitative feedback it does report concerns browser
compatibility and navigation.

**The adjacent explanation literature excludes crosswords by name.** DEMYSTIFY [C07] generates human-readable
explanations of solving steps from Minimal Unsatisfiable Subsets and validates them against expert-written
guides ("Demystify produces solving strategies which closely match human-produced guides to solving those same
puzzles (on average 89% of the" time). Its first footnote rules crosswords out: "In this paper we will not
consider puzzles based around language, such as Crosswords." The reason matters for transfer — MUS explanation
presupposes a small fixed per-cell domain (digits 1–9), whereas a crossword slot draws from an open vocabulary
of tens of thousands, so the explanation a constructor needs is a lexical-availability signal rather than a
deduction chain.

**What exists instead is shipped design rationale, none of it validated.** Ingrid's FAQ [T13] is the only
documentation that names remaining crossing options as a ranking factor a user sees, and it also documents a
warning-style affordance that leaves the judgment to the constructor — it "warns about options that contain
four or more letters of overlap with an" existing entry — plus hover-to-summarise on constrained slots. Exet
[T02] is the nearest thing in shipped software to the brief's "kills slot 12-Down": it evaluates each candidate
"by checking if the choice leads to a dead-end for any of the crossing clues" and demotes those to the bottom
with a purple background and a warning tooltip — but it demotes the candidate rather than naming *which*
crossing it kills. Qxw [T07] orders feasible characters "from most promising to least promising" and marks
constrained cells. CrossFire [T12] shows the three-score triad plus a crossing score per entered word.

Note also that Dr.Fill's damage function [P06] computes, per candidate, exactly how much each crossing slot's
prospects degrade — the quantity B6 asks about — but it is an internal search heuristic that was never surfaced
to or evaluated with a human constructor.

---

## Cited-by sweep

Required by the brief for every confirmed founding paper. All twelve founding papers were resolved on
Semantic Scholar and their full citation lists pulled (4,299 citing papers in total), then filtered for
crossword relevance in title, abstract or venue. 99 hits, 68 unique after deduplication. The per-paper counts
are the result:

| Founding paper | id | Citations pulled | Crossword-relevant descendants |
|---|---|---|---|
| Ginsberg et al. 1990 | P05 | 101 | 34 |
| Dr.Fill 2011 | P06 | 35 | 32 |
| Mazlack 1976 | P13 | 26 | 19 |
| Beacham et al. 2001 | P12 | 42 | 7 |
| Anbulagan & Botea 2008 | P09 | 7 | 5 |
| Haralick & Elliott | P10 | 1,487 | 1 |
| Daciuk et al. 2000 | P03 | 227 | 1 (false positive — "cross-word acoustic context", speech recognition) |
| **Appel & Jacobson 1988 (DAWG)** | P01 | 95 | **0** |
| **Gordon 1994 (GADDAG)** | P02 | 24 | **0** |
| **Jacobson 1989 (succinct trees)** | P07 | 791 | **0** |
| **Ferragina & Manzini 2000 (FM-index)** | P04 | 1,318 | **0** |
| **Frost & Dechter 1995 (LVO)** | P08 | 146 | **0** |

Two lineages have **no crossword descendants at all**. The Scrabble and succinct-index structures (P01, P02,
P07, P04) were never taken up by crossword-specific published work — which is consistent with the tool survey,
where no shipped crossword tool uses a DAWG or GADDAG. And the paper that names look-ahead value ordering (P08)
has no crossword descendant either: the crossword LCV variants in P05 and P06 were arrived at independently
rather than by specialising the CSP literature's named heuristic.

Four construction-relevant descendants were fetched in full and are cited above: [D04] (tries per length, the
only construction-side index measurement), [D03] Gourvès et al., *Filling Crosswords Is Very Hard* (ISAAC 2021,
CC-BY — hardness for the exact "place dictionary words in slots with consistent shared cells" problem, "NP-hard
when the grid graph is a matching for alphabets of size 3 … or a union of stars for a binary alphabet" once
words cannot be reused), [D01] Agarwal & Joshi's intersection-count ranking, and [D02] the Romanian
Optimization Crosswords line. The remaining 64 are recorded in `corpus/main/descendants_dedup.json`; the large
majority are clue-answering solvers (WebCrow, Proverb descendants, the LLM crossword-solving line from 2021
onward) and fall outside the construction scope.

### Appendix — construction-relevant descendants, with citation fields

The brief asks for every crossword-relevant descendant with full citation fields. The 68 unique descendants
split into a clue-answering-solver majority and the 26 below, which a lexical screen
(`construct|generat|compil|creat|fill|grid` over title and abstract) tags as construction-related. Treat the
tag as a screen, not a judgment: two rows (CrossWordBench, Language Models are Crossword Solvers) are
solver-evaluation papers that generate puzzles as test material. `retrieval_status` is FETCHED where the full
PDF was downloaded to `corpus/main/`, ABSTRACT where only the Semantic Scholar abstract was read, and SNIPPET
where neither was available. The 42 not listed here are clue-answering solvers (the WebCrow family, Proverb
descendants, and the 2021-onward LLM crossword-solving line) and are in `corpus/main/descendants_dedup.json`.

| Title | Authors (first 3) | Year | Venue | DOI / id | OA | retrieval_status | id | Descends from |
|---|---|---|---|---|---|---|---|---|
| CrossWordBench: Evaluating the Reasoning Capabilities of LLMs and LVLMs with Controllable Puzzle Generation | Jixuan Leng, Chengsong Huang, Langlin Huang | 2025 | arXiv.org | 10.48550/arXiv.2504.00043 | open access (arXiv) | ABSTRACT | — | P06 |
| Using GermaNet for the Generation of Crossword Puzzles | Claus Zinn, Marie Hinrichs, Erhard W. Hinrichs | 2024 | Conference on Natural Language Processing | S2 CorpusID:272819864 | not established | SNIPPET | — | P05, P06 |
| Extended Seeds in Optimization Crosswords | Adi Botea, Vadim Bulitko | 2024 | 2024 IEEE Conference on Games (CoG) | 10.1109/CoG60054.2024.10645649 | not established | ABSTRACT | — | P06 |
| Language Models are Crossword Solvers | Soumadeep Saha, Sutanoya Chakraborty, Saptarshi Saha | 2024 | North American Chapter of the Association for  | 10.18653/v1/2025.naacl-long.104 | open access | ABSTRACT | — | P06 |
| Clue-Instruct: Text-Based Clue Generation for Educational Crossword Puzzles | Andrea Zugarini, Kamyar Zeinalipour, Surya Sai Kadali | 2024 | International Conference on Language Resources | 10.48550/arXiv.2404.06186 | open access (arXiv) | ABSTRACT | — | P06 |
| Generating News-Centric Crossword Puzzles As A Constraint Satisfaction and Optimization Problem | Kaito Majima, Shotaro Ishihara | 2023 | International Conference on Information and Kn | 10.1145/3583780.3615151 | open access | FETCHED | D05 | P05, P13 |
| Automated Crossword Solving | Eric Wallace, Nicholas Tomlin, Albert Xu | 2022 | Annual Meeting of the Association for Computat | 10.18653/v1/2022.acl-long.219 | open access | ABSTRACT | — | P06 |
| Tries-Based Parallel Solutions for Generating Perfect Crosswords Grids | Virginia Niculescu, Robert Manuel Ştefănică | 2022 | Algorithms | 10.3390/a15010022 | open access | FETCHED | D04 | P13 |
| Filling Crosswords is Very Hard | L. Gourvès, Ararat Harutyunyan, M. Lampis | 2021 | International Symposium on Algorithms and Comp | 10.4230/LIPIcs.ISAAC.2021.36 | open access (arXiv) | FETCHED | D03 | P05, P09 |
| Evolving Romanian Crossword Puzzles with Deep Learning and Heuristic Search | V. Bulitko, A. Botea | 2021 | 2021 IEEE Conference on Games (CoG) | 10.1109/CoG52621.2021.9619056 | not established | ABSTRACT | — | P05 |
| Decrypting Cryptic Crosswords: Semantically Complex Wordplay Puzzles as a Target for NLP | Josh Rozner, Christopher Potts, Kyle Mahowald | 2021 | Neural Information Processing Systems | arXiv:2104.08620 | open access (arXiv) | ABSTRACT | — | P06 |
| Automation Strategies for Unconstrained Crossword Puzzle Generation | Charu Agarwal, R. Joshi | 2020 | arXiv.org | arXiv:2007.04663 | open access (arXiv) | FETCHED | D01 | P05, P06, P12 |
| Towards a Semantic Approach for Candidate Answer Generation in Solving Crossword Puzzles | Anu Thomas, S. Sangeetha | 2020 | — | 10.1016/j.procs.2020.04.250 | open access | ABSTRACT | — | P06 |
| Web Based IT Crossword Generator | — | 2018 | — | none located | not established | SNIPPET | — | P05 |
| Cruciform: Solving Crosswords with Natural Language Processing | Dragomir R. Radev, Rui Zhang, Steven R. Wilson | 2016 | arXiv.org | arXiv:1611.02360 | open access (arXiv) | ABSTRACT | — | P06 |
| A crossword puzzle generator using genetic algorithms with Wisdom of Artificial Crowds | Douglas Bonomo, Adrian P. Lauf, Roman V. Yampolskiy | 2015 | International Conference on Computer Games | 10.1109/CGames.2015.7272960 | not established | SNIPPET | — | P05, P12 |
| SACRY: Syntax-based Automatic Crossword puzzle Resolution sYstem | Alessandro Moschitti, M. Nicosia, Gianni Barlacchi | 2015 | Annual Meeting of the Association for Computat | 10.3115/v1/P15-4014 | open access | ABSTRACT | — | P06 |
| Automatic Generation of Crossword Puzzles | Leonardo Rigutini, M. Diligenti, Marco Maggini | 2012 | Int. J. Artif. Intell. Tools | 10.1142/S0218213012500145 | not established | SNIPPET | — | P05, P12 |
| The Crossword Solver DR.FILL | M. Ginsberg | 2012 | ICGA Journal | 10.3233/ICG-2012-35203 | not established | SNIPPET | — | P06 |
| Dr.Fill: Crosswords and an Implemented Solver for Singly Weighted CSPs | M. Ginsberg | 2011 | Journal of Artificial Intelligence Research | 10.1613/jair.3437 | open access | ABSTRACT | — | P05 |
| A Fully Automatic Crossword Generator | Leonardo Rigutini, M. Diligenti, Marco Maggini | 2008 | 2008 Seventh International Conference on Machi | 10.1109/ICMLA.2008.104 | not established | ABSTRACT | — | P05 |
| Practical crossword generation with checkpoint search | Ariel Arbiser | 2005 | IADIS AC | S2 CorpusID:10070228 | not established | SNIPPET | — | P05, P13 |
| Memory efficient decoding graph compilation with wide cross-word acoustic context | M. Novak, Vladimír Bergl | 2004 | Interspeech | 10.21437/Interspeech.2004-138 | not established | SNIPPET | — | P03 |
| Constructing Crossword Grids : Use of Heuristics vs Constraints | G. Meehan, Peter Gray | 1997 | — | S2 CorpusID:637215 | not established | SNIPPET | — | P05, P13 |
| Microcomputer compilation and solution of crosswords | R. Davis, Erik J. Juvshol | 1985 | Microprocessors and microsystems | 10.1016/0141-9331(85)90167-X | not established | SNIPPET | — | P13 |
| Filling Crosswords is Very Hard (cid:63) | Laurent Gourvès, Ararat Harutyunyan, Michael Lampis | n.d. | — | S2 CorpusID:282201183 | not established | SNIPPET | — | P05, P09 |

---

## What was dropped, and why

Per question, from the lanes' own `dropped` logs (`corpus/L*/evidence.json`).

**B1.** Aoe 1992, *An Efficient Implementation of Trie Structures* — paywalled at Wiley, no preprint found in
one pass; double-array tries are an encoding detail rather than a wildcard-lookup benchmark. Eleven small
GitHub repos (crosswyrd, Crossword-Filler, crossword_filler, Crossword-Solver, grid-filler, RoboCrossword,
thanthese/crossword, xword_constructor, crossword-owl and others) — 0–16 stars, no evidence of a real word
index or ranking heuristic in README or description, dropped for redundancy under the source cap once
xwords-rs, CrossHatch and Orca covered the same niches with confirmed implementations. khiner/CrosswordFiller —
its "beam search" is a search strategy, not a candidate-quality heuristic, and the author describes it as an
early recovered project.

**B2.** Ginsberg's AAAI-99 Proverb paper — a clue-answering solver whose only value-ordering remark is about
experimental hygiene, not a crossing-effect technique. Dechter & Meiri's preprocessing evaluation — encountered
only as a citation inside P05 and P11, general CSP preprocessing, out of scope. cursewords [T05] was retrieved
but records a negative: it is a solving UI with no autofill, candidate list, or ranking of any kind, so it names
no transferable technique.

**B3.** Rex Parker and Diary of a Crossword Fiend — searched for word-list scoring conventions; Rex Parker's
published scale is a *solving-difficulty* rating (0 = easy Monday … 10 = hard Saturday), a different concept,
out of scope. Together with two other angles surfacing nothing new, this triggered the stop criterion.

**Cited-by sweep.** Majima & Ishihara 2023, *Generating News-Centric Crossword Puzzles As A Constraint
Satisfaction and Optimization Problem* [D05], was fetched in full (744 KB, arXiv:2308.04688) and then cited
nowhere: a whole-word scan of it returns zero occurrences of trie, tries, DAWG, GADDAG, bitset,
least-constraining, value ordering or crossability, against 58 hits for the control term "crossword". Its optimisation objective is how many news-topic words a grid contains, which bears on theme
selection rather than on slot lookup or candidate ranking. Recorded here rather than silently discarded.

**B4/B5/B6.** Three pages could not be retrieved and are recorded rather than substituted for: an NYT-crossword
letter-frequency analysis on Medium (403), a working constructor's Patreon post on sorted short-fill lists
(403, Cloudflare), and a themeless-construction blog post (403). A general-HCI explanation-type taxonomy (Lim &
Dey, CHI 2009) and an IUI 2026 study of assistance timing in Rush Hour were logged as adjacent-not-crossword
rather than cited, because neither concerns construction-time suggestions.

---

## Gaps

1. **No per-slot lookup benchmark exists, anywhere.** Not in the academic literature (searched), not in the
   tool documentation. The only two quantified comparisons in the whole run are Scrabble move generation
   (GADDAG vs DAWG, [P02]) and whole-grid generation time for black-cell-free Romanian grids ([D04]). Nobody has
   published "trie vs bitset vs bucket-array for wildcard lookup at 44k–500k words".
2. **No crossword tool documents its internal index.** Crossword Compiler and CrossFire describe scoring and
   fill behaviour in detail and the data structure not at all; the open-source picture had to be reconstructed
   from source files.
3. **Three of the four ranking composites in shipped tools are undocumented in their weighting.** CrossHatch's
   formula was recovered from source, but Ingrid's "letter score", CrossFire's Grid Score computation, and the
   relative weights inside Ingrid's Recommended sort are stated only qualitatively.
4. **Half-closed by the browser pass, and the remaining half is the harder half.** A crossword-answer-corpus
   letter *distribution* now exists [B02], and it shows the aggregate distribution sits within ±1.5% of
   general English — which retroactively licenses Norvig [C01] as a proxy at that level. But no
   crossword-corpus table conditioned on **position within word** or on **word length** was found anywhere,
   and the one source that could plausibly have carried it does not. The only position × length table in the
   run is still Wordle's [C09]. Nothing published conditions crossword letter frequency on position.
5. **No B6 evidence of any kind about what actually helps a constructor.** Not a weak study — none. Every
   affordance documented in B6 is a tool author's unvalidated design rationale.
6. **Peter Broda's scale is unrecoverable from primary sources** as the site now stands, and two Wayback
   attempts returned HTTP 429. Given how many other lists derive from it (Mark Diehl's trimmed version,
   CrossHatch's sample, Chris Jones's blend), this is a provenance hole under several other lists.
7. **Closed.** Nediger's own wording, and the list's MIT licence, were read in a browser session [B01]. The
   paraphrase was accurate but incomplete: it omitted the author's own warning that the 51-vs-99 split on long
   entries is "sporadic and unsystematic".
8. **Mazlack 1976 [P13] and Meehan & Gray 1997 [P14] were never read.** Both are cited throughout the
   crossword-construction literature; both are characterised here only secondhand, through quotes in [P05] and
   [P09]. Meehan & Gray in particular compared word-by-word against letter-by-letter filling and concluded
   word-by-word scales better — the specific ordering heuristics behind that could bear on B2 and are unknown.
9. **Word-list licensing is largely absent rather than permissive.** Broda: no licence stated. Chris Jones:
   none. CrossHatch's data repo: none. CrossFire's default dictionary: none. Only Spread the Wordlist
   (CC BY-NC-SA 4.0), Crossword Nexus (MIT) and Exet's Lufz (MIT) carry an explicit grant, and XWord Info
   explicitly forbids redistribution.

---

## Retrieval access

Every claim about a source being closed, empty, or gated is scoped to the client that observed it. A
**targeted browser pass (claude-in-chrome) was run over three sources** at human pace — no crawling, no
pagination, no bulk extraction — and it changed two verdicts:

- **codeberg.org/bewilderingly/Nediger-list** — HTTP 403 "Access denied" (13-byte body) to `curl` with a
  browser UA; **renders in full in a browser**, README, LICENSE and 23 commits. The 403 was a client wall,
  not a data wall. Gap 7 closed [B01].
- **The Medium NYT crossword analysis** — HTTP 403 to `curl`; **read in full in a browser**. Gap 4 half
  closed [B02].
- **Wilson 1989 [P15] at Oxford Academic** — `curl` received a Cloudflare "Just a moment…" challenge. In a
  browser the article page renders, confirming the citation fields (*The Computer Journal* 32(3), 1989,
  273–275, DOI 10.1093/comjnl/32.3.273, published 01 January 1989) and displaying the abstract, but states
  "You do not currently have access to this article." **This paywall is now established with a
  JavaScript-capable client rather than inferred from an HTTP probe**, and no attempt was made to circumvent
  it. P15 remains ABSTRACT.

The remaining rows below were judged on HTTP probes alone and have **not** been tested in a browser; nothing
in this report asserts that any of them is genuinely closed:

| Source | Signal | Why it matters |
|---|---|---|
| `sciencedirect.com` — Mazlack 1976 [P13] | HTTP 403 to curl and to WebFetch | Earliest crossword-construction paper; characterised only secondhand |
| Meehan & Gray 1997 [P14] — no online copy located at all | pre-web proceedings volume; no publisher landing page or DOI found. Searched arXiv, CiteSeerX, ResearchGate (listing only, no PDF), Semantic Scholar (listing only; API 429), and an Aberdeen author-homepage search | Compared word-by-word against letter-by-letter filling and concluded word-by-word scales better; the ordering heuristics behind that conclusion are unknown and bear on B2 (gap 8) |
| `peterbroda.me` historical snapshot | archive.org HTTP 429 (twice) | Might recover the lost scale documentation |
| `facebook.com/groups/1515117638602016` | not attempted (login wall) | Original circulation point for Mark Diehl's list |
| ada nicolle Patreon post; brightsprout blog | HTTP 403 | Practitioner writing on short-fill lists and seed entries (B4) |
| `mdpi.com` PDF route for [D04] | HTTP 403, 395-byte body | **Resolved without a browser** — `mdpi-res.com` served the same PDF at HTTP 200 |
| `dl.acm.org`, Springer LNCS, Wiley, IEEE Xplore versions of record | not tested | Green OA copies were used instead; page ranges taken from the preprint where the publisher version was not consulted, and flagged in [P12] |

Two access notes that affect what the citations mean. [P10]'s fetched copy is the **IJCAI-79 conference paper**
(9 pages, author-hosted), not the 1980 *Artificial Intelligence* journal article — the citation here reflects
what was read. [P06]'s DOI (10.1613/jair.3437) is asserted by jair.org's own page metadata but **the doi.org
resolver currently 404s on it**; the arXiv preprint 1401.4597 was used and matches the JAIR header and
pagination.

## Artifacts

- `sources.jsonl` — 63 registered source records
- `claims.jsonl` — 65 claims, each resolved to its cited sources **exactly** (report id → tmp_id → source_id),
  not by the positional [N]→source mapping in `scripts/extract_claims.py`, which mis-indexes a hand-curated
  source list. Every id was identity-probed against the registered title. `support_status` is set to
  `supported` on the strength of the two-layer quote verification behind each cited source —
  `verify_claim_support.py` was **not** run, so this is an asserted status, not a per-claim check
- `corpus/main/gh_repo_facts.jsonl` — main-thread `gh api` re-verification of all ten repositories
- `corpus/browser/` — the browser pass: Nediger README and LICENSE, the NYT letter analysis, the Wilson
  publisher page, each recording the `curl` result it overturned
- `evidence.jsonl` — 316 rows (236 verbatim quotes + access observations + negative-result logs), each with
  `access_mode`: 297 `subagent_http` (lane retrieval), 19 `http_browser_ua` (main-thread `curl` with a
  browser user-agent), 13 `browser_session` (the claude-in-chrome pass over Nediger, the NYT analysis, and
  Wilson). Only the last class can support a claim that a source is genuinely closed, and only Wilson's
  paywall is claimed on that basis
- `corpus/L1…L4, main/` — 160+ retrieved files: 21 PDFs, source files from ten repositories, decoded help
  pages, word-list samples
- `corpus/main/descendants_dedup.json` — the 68 unique crossword-relevant descendants
- `corpus/main/quote_repairs.json` — the three repaired quotes, with old and new text
- `corpus/main/verify_quotes.py` — the two-layer quote checker; `corpus/main/s2.py`, `cites_driver.py` — the
  citation sweep
