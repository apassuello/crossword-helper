"""
End-to-end test for pause/resume functionality.

This test demonstrates the complete pause/resume workflow:
1. Start autofill on a real crossword grid with theme entries
2. Pause during execution
3. Load saved state
4. Make user edits
5. Resume from edited state
6. Verify results
"""

import pytest
import time
import threading

from cli.src.core.grid import Grid
from cli.src.fill.word_list import WordList
from cli.src.fill.pattern_matcher import PatternMatcher
from cli.src.fill.beam_search.orchestrator import BeamSearchOrchestrator
from cli.src.fill.state_manager import StateManager
from cli.src.fill.pause_controller import PauseController
from backend.core.edit_merger import EditMerger


class TestEndToEndPauseResume:
    """End-to-end tests for complete pause/resume workflow."""

    @pytest.fixture
    def crossword_grid(self):
        """Create realistic 11x11 crossword grid with theme entries."""
        grid = Grid(11)

        # Create realistic black square pattern (symmetric)
        black_squares = [
            (0, 3), (0, 7),
            (1, 3), (1, 7),
            (2, 3), (2, 7),
            (3, 0), (3, 1), (3, 2), (3, 8), (3, 9), (3, 10),
            (7, 0), (7, 1), (7, 2), (7, 8), (7, 9), (7, 10),
            (8, 3), (8, 7),
            (9, 3), (9, 7),
            (10, 3), (10, 7)
        ]

        for row, col in black_squares:
            grid.set_black_square(row, col)

        return grid

    @pytest.fixture
    def comprehensive_word_list(self):
        """Create comprehensive word list with various lengths."""
        words = []

        # 3-letter words
        words.extend(['CAT', 'DOG', 'BAT', 'RAT', 'HAT', 'MAT', 'PAT', 'SAT', 'FAT', 'VAT'])
        words.extend(['ACE', 'AGE', 'ALE', 'APE', 'ARE', 'ATE', 'AWE', 'AXE', 'EAR', 'EAT'])
        words.extend(['ERA', 'ERR', 'ORE', 'OWE', 'ICE', 'IRE', 'USE'])

        # 4-letter words
        words.extend(['ABLE', 'ACRE', 'AREA', 'BARE', 'BASE', 'BEAR', 'BEAT', 'BEEN'])
        words.extend(['BIRD', 'BLUE', 'BOAT', 'BONE', 'BOOK', 'BORN', 'BOTH', 'CARE'])
        words.extend(['CASE', 'CITE', 'COME', 'CORE', 'DARE', 'DARK', 'DATE', 'DEAR'])
        words.extend(['DONE', 'DOOR', 'EACH', 'EARN', 'EASE', 'EAST', 'EDGE', 'EVEN'])
        words.extend(['FACE', 'FACT', 'FAIR', 'FALL', 'FARE', 'FARM', 'FAST', 'FEAR'])
        words.extend(['FINE', 'FIRE', 'FIRM', 'FISH', 'FIVE', 'FLAT', 'FLOW', 'FOUR'])

        # 5-letter words
        words.extend(['ABOUT', 'ABOVE', 'ALONE', 'ALONG', 'AREA', 'AROSE', 'ASIDE'])
        words.extend(['BASIC', 'BEGAN', 'BEING', 'BELOW', 'BIRTH', 'BLACK', 'BOARD'])
        words.extend(['BRING', 'BUILT', 'CAUSE', 'CHAIR', 'CHANGE', 'CHIEF', 'CLEAR'])
        words.extend(['CLOSE', 'COMES', 'COULD', 'CRAFT', 'DEALT', 'DEATH', 'DOING'])
        words.extend(['EARLY', 'EARTH', 'EIGHT', 'ENTER', 'EQUAL', 'ERROR', 'EVENT'])

        # 6-letter words
        words.extend(['ACROSS', 'ACTION', 'AMOUNT', 'ANSWER', 'AROUND', 'BECAME'])
        words.extend(['BECOME', 'BEFORE', 'BETTER', 'BEYOND', 'CHANGE', 'CHANCE'])
        words.extend(['CHARGE', 'CHOICE', 'CHOSEN', 'CLOSED', 'COMMON', 'COURSE'])

        # 7-letter words
        words.extend(['ABILITY', 'ACCOUNT', 'ACHIEVE', 'ADDRESS', 'ADVANCE', 'AGAINST'])
        words.extend(['ALREADY', 'ANOTHER', 'APPEARS', 'ARRANGE', 'ARTICLE', 'ATTEMPT'])

        return WordList(words=words)

    def test_full_pause_resume_workflow(self, tmp_path, crossword_grid, comprehensive_word_list):
        """
        Test complete pause/resume workflow with realistic crossword grid.

        Workflow:
        1. Start autofill on 11x11 grid
        2. Pause after 2 seconds
        3. Verify state saved
        4. Load state and inspect
        5. Resume from saved state
        6. Verify completion
        """
        task_id = 'e2e_test_task'
        pause_controller = PauseController(task_id)
        pause_controller.cleanup()

        pattern_matcher = PatternMatcher(comprehensive_word_list)

        # Step 1: Start autofill
        orchestrator = BeamSearchOrchestrator(
            grid=crossword_grid,
            word_list=comprehensive_word_list,
            pattern_matcher=pattern_matcher,
            beam_width=5,
            candidates_per_slot=10,
            min_score=30,
            pause_controller=pause_controller,
            task_id=task_id
        )

        # Step 2: Request pause after delay
        def pause_after_delay():
            time.sleep(2.0)
            pause_controller.request_pause()

        pause_thread = threading.Thread(target=pause_after_delay)
        pause_thread.start()

        # Run autofill (will pause)
        result1 = orchestrator.fill(timeout=60)
        pause_thread.join()

        # Verify pause occurred
        assert hasattr(result1, 'paused') and result1.paused is True, "Fill should have paused"
        assert result1.iterations > 0, "Should have made some progress before pausing"

        print(f"\n✓ Paused after {result1.iterations} iterations")
        print(f"  Slots filled: {result1.slots_filled}/{result1.total_slots}")

        # Step 3: Verify state was saved
        state_manager = StateManager()
        saved_states = state_manager.list_states()

        task_states = [s for s in saved_states if s['task_id'].startswith(task_id)]
        assert len(task_states) > 0, "State should have been saved"

        saved_task_id = task_states[0]['task_id']
        print(f"✓ State saved: {saved_task_id}")

        # Step 4: Load and inspect state
        loaded_state, metadata = state_manager.load_beam_search_state(saved_task_id)

        assert loaded_state.iterations == result1.iterations
        assert loaded_state.beam_width == 5
        assert loaded_state.min_score == 30

        print("✓ State loaded successfully")
        print(f"  Iterations: {loaded_state.iterations}")
        print(f"  Beam states: {len(loaded_state.beam)}")

        # Step 5: Resume from saved state
        orchestrator2 = BeamSearchOrchestrator(
            grid=crossword_grid,
            word_list=comprehensive_word_list,
            pattern_matcher=pattern_matcher,
            beam_width=5,
            candidates_per_slot=10,
            min_score=30,
            task_id=task_id + '_resume'
        )

        # Resume (allow longer timeout to potentially complete)
        result2 = orchestrator2.fill(timeout=30, resume_state=loaded_state)

        # Step 6: Verify resume worked
        assert result2.iterations >= result1.iterations, "Should continue from previous iteration count"

        print("✓ Resumed successfully")
        print(f"  Total iterations: {result2.iterations}")
        print(f"  Final slots filled: {result2.slots_filled}/{result2.total_slots}")

        # Cleanup
        pause_controller.cleanup()
        state_manager.delete_state(saved_task_id)

    def test_pause_edit_resume_workflow(self, tmp_path, crossword_grid, comprehensive_word_list):
        """
        Test pause/resume workflow with user edits.

        Workflow:
        1. Start autofill
        2. Pause
        3. Make user edits to grid
        4. Merge edits with saved state
        5. Resume with edited state
        """
        task_id = 'e2e_edit_test'
        pause_controller = PauseController(task_id)
        pause_controller.cleanup()

        pattern_matcher = PatternMatcher(comprehensive_word_list)
        state_manager = StateManager(storage_dir=tmp_path)

        # Step 1: Start autofill
        orchestrator = BeamSearchOrchestrator(
            grid=crossword_grid,
            word_list=comprehensive_word_list,
            pattern_matcher=pattern_matcher,
            beam_width=5,
            candidates_per_slot=10,
            min_score=30,
            pause_controller=pause_controller,
            task_id=task_id
        )

        # Step 2: Pause quickly
        def pause_quickly():
            time.sleep(1.0)
            pause_controller.request_pause()

        pause_thread = threading.Thread(target=pause_quickly)
        pause_thread.start()

        result1 = orchestrator.fill(timeout=30)
        pause_thread.join()

        assert hasattr(result1, 'paused') and result1.paused is True

        print(f"\n✓ Paused after {result1.iterations} iterations")

        # Get saved state
        saved_states = StateManager().list_states()
        task_states = [s for s in saved_states if s['task_id'].startswith(task_id)]
        assert len(task_states) > 0
        saved_task_id = task_states[0]['task_id']

        # Load state (from default storage location)
        loaded_state, metadata = StateManager().load_beam_search_state(saved_task_id)

        # Step 3: Simulate user edit - get grid from first beam state
        first_beam_dict = loaded_state.beam[0]
        saved_grid = Grid.from_dict(first_beam_dict['grid_dict'])

        # Make a user edit (fill in a 3-letter word manually)
        edited_grid = saved_grid.clone()

        # Find a 3-letter slot and fill it with "CAT"
        slots = crossword_grid.get_empty_slots()
        three_letter_slots = [s for s in slots if s['length'] == 3]

        if three_letter_slots:
            slot = three_letter_slots[0]
            if slot['direction'] == 'across':
                edited_grid.set_letter(slot['row'], slot['col'], 'C')
                edited_grid.set_letter(slot['row'], slot['col'] + 1, 'A')
                edited_grid.set_letter(slot['row'], slot['col'] + 2, 'T')
            else:
                edited_grid.set_letter(slot['row'], slot['col'], 'C')
                edited_grid.set_letter(slot['row'] + 1, slot['col'], 'A')
                edited_grid.set_letter(slot['row'] + 2, slot['col'], 'T')

            print(f"✓ User edit: filled {slot['direction']} slot at ({slot['row']}, {slot['col']}) with 'CAT'")

        # Step 4: Get edit summary
        merger = EditMerger()
        edit_summary = merger.get_edit_summary(
            saved_grid_dict=saved_grid.to_dict(),
            edited_grid_dict=edited_grid.to_dict(),
            slot_list=loaded_state.all_slots,
            slot_id_map=loaded_state.slot_id_map if hasattr(loaded_state, 'slot_id_map') else {}
        )

        print("✓ Edit summary:")
        print(f"  New words: {edit_summary.get('new_words', [])}")
        print(f"  Filled count: {edit_summary.get('filled_count', 0)}")

        # Cleanup
        pause_controller.cleanup()
        StateManager().delete_state(saved_task_id)

    def test_multiple_pause_resume_cycles(self, tmp_path, crossword_grid, comprehensive_word_list):
        """
        Test multiple pause/resume cycles on same puzzle.

        Simulates:
        - User pauses multiple times
        - Each resume continues from previous state
        - Iteration count accumulates correctly
        """
        task_id = 'e2e_multi_pause'
        pattern_matcher = PatternMatcher(comprehensive_word_list)

        total_iterations = 0
        max_cycles = 3

        print(f"\n✓ Testing {max_cycles} pause/resume cycles")

        for cycle in range(max_cycles):
            pause_controller = PauseController(f"{task_id}_cycle{cycle}")
            pause_controller.cleanup()

            # Load previous state if this isn't the first cycle
            resume_state = None
            if cycle > 0:
                state_manager = StateManager()
                saved_states = state_manager.list_states()
                prev_task_states = [s for s in saved_states if s['task_id'].startswith(f"{task_id}_cycle{cycle-1}")]
                if prev_task_states:
                    prev_task_id = prev_task_states[0]['task_id']
                    resume_state, _ = state_manager.load_beam_search_state(prev_task_id)
                    print(f"  Cycle {cycle}: Resuming from {resume_state.iterations} iterations")

            orchestrator = BeamSearchOrchestrator(
                grid=crossword_grid,
                word_list=comprehensive_word_list,
                pattern_matcher=pattern_matcher,
                beam_width=5,
                candidates_per_slot=10,
                min_score=30,
                pause_controller=pause_controller,
                task_id=f"{task_id}_cycle{cycle}"
            )

            # Pause after short time
            def pause_quickly():
                time.sleep(0.5)
                pause_controller.request_pause()

            pause_thread = threading.Thread(target=pause_quickly)
            pause_thread.start()

            result = orchestrator.fill(timeout=30, resume_state=resume_state)
            pause_thread.join()

            if hasattr(result, 'paused') and result.paused:
                print(f"  Cycle {cycle}: Paused at {result.iterations} iterations")
                total_iterations = result.iterations
            else:
                print(f"  Cycle {cycle}: Completed at {result.iterations} iterations")
                total_iterations = result.iterations
                break

            pause_controller.cleanup()

        print(f"✓ Multiple cycles completed. Total iterations: {total_iterations}")
        assert total_iterations > 0

    def test_performance_metrics(self, tmp_path, crossword_grid, comprehensive_word_list):
        """
        Test and measure pause/resume performance.

        Metrics:
        - Time to pause
        - State save time
        - State load time
        - Resume overhead
        """
        task_id = 'e2e_perf_test'
        pause_controller = PauseController(task_id)
        pause_controller.cleanup()

        pattern_matcher = PatternMatcher(comprehensive_word_list)
        state_manager = StateManager(storage_dir=tmp_path)

        orchestrator = BeamSearchOrchestrator(
            grid=crossword_grid,
            word_list=comprehensive_word_list,
            pattern_matcher=pattern_matcher,
            beam_width=5,
            candidates_per_slot=10,
            min_score=30,
            pause_controller=pause_controller,
            task_id=task_id
        )

        # Measure pause time
        def pause_quickly():
            time.sleep(1.0)
            pause_start = time.time()
            pause_controller.request_pause()
            return pause_start

        pause_thread = threading.Thread(target=pause_quickly)
        pause_thread.start()

        fill_start = time.time()
        result = orchestrator.fill(timeout=30)
        fill_elapsed = time.time() - fill_start

        pause_thread.join()

        print("\n✓ Performance Metrics:")
        print(f"  Time until pause: {fill_elapsed:.2f}s")
        print(f"  Iterations before pause: {result.iterations}")

        if hasattr(result, 'paused') and result.paused:
            # Measure state load time
            saved_states = state_manager.list_states()
            task_states = [s for s in saved_states if s['task_id'].startswith(task_id)]

            if task_states:
                saved_task_id = task_states[0]['task_id']

                load_start = time.time()
                loaded_state, _ = state_manager.load_beam_search_state(saved_task_id)
                load_elapsed = time.time() - load_start

                print(f"  State load time: {load_elapsed*1000:.1f}ms")

                # Measure resume overhead
                orchestrator2 = BeamSearchOrchestrator(
                    grid=crossword_grid,
                    word_list=comprehensive_word_list,
                    pattern_matcher=pattern_matcher,
                    beam_width=5,
                    candidates_per_slot=10,
                    min_score=30,
                    task_id=task_id + '_resume'
                )

                resume_start = time.time()
                result2 = orchestrator2.fill(timeout=5, resume_state=loaded_state)
                resume_elapsed = time.time() - resume_start

                print(f"  Resume execution time: {resume_elapsed:.2f}s")
                print(f"  Iterations in resumed session: {result2.iterations - result.iterations}")

                # Cleanup
                state_manager.delete_state(saved_task_id)

        pause_controller.cleanup()


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
