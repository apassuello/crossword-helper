"""
State management for pause/resume functionality in autofill.

Handles serialization and deserialization of complete algorithm state,
enabling pause/resume workflow for long-running autofill operations.
"""

import json
import gzip
from typing import Dict, List, Set, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from ..core.grid import Grid


@dataclass
class CSPState:
    """
    Complete CSP algorithm state for serialization.

    Captures all necessary state to resume backtracking from exact position.
    """
    # Grid state
    grid_dict: Dict  # Grid.to_dict() result

    # CSP state
    domains: Dict[int, List[str]]  # slot_id -> valid words (Set converted to List)
    constraints: Dict[int, List[List]]  # slot_id -> [(other_slot, pos1, pos2)]
    used_words: List[str]  # Set converted to List for JSON
    slot_id_map: Dict[str, int]  # JSON keys must be strings

    # Slot information
    slot_list: List[Dict]  # All slots
    slots_sorted: List[int]  # MCV-sorted slot IDs

    # Backtracking position
    current_slot_index: int  # Resume from this position

    # Metadata
    iteration_count: int
    locked_slots: List[int]  # Theme entries + user edits (Set -> List)
    timestamp: str  # ISO format

    # Random seed for restarts
    random_seed: Optional[int] = None

    # Letter frequency table (optional, can be rebuilt)
    letter_frequency_table: Optional[Dict[int, Dict[int, Dict[str, int]]]] = None


@dataclass
class BeamSearchState:
    """
    Complete Beam Search algorithm state for serialization.

    Captures all necessary state to resume beam search from exact position.
    """
    # Beam states (list of serialized BeamState objects)
    beam: List[Dict]  # Each dict contains: grid_dict, used_words, slot_assignments, etc.

    # Search progress
    filled_slots: List[List]  # Set of (row, col, direction) tuples as lists
    slot_idx: int  # Current slot index
    iterations: int  # Total iterations so far

    # Failure tracking (prevents thrashing)
    slot_attempt_history: Dict[str, int]  # JSON-encoded (beam_sig, slot_id) -> attempts
    recently_failed: List[List]  # List of (row, col, direction) tuples as lists

    # Configuration (needed for resume)
    beam_width: int
    candidates_per_slot: int
    min_score: int
    diversity_bonus: float
    theme_entries: Dict[str, str]  # JSON-encoded slot tuples -> words

    # Grid metadata
    all_slots: List[Dict]  # All slots in grid
    total_slots: int

    # Timestamp
    timestamp: str  # ISO format


@dataclass
class SerializedState:
    """
    Top-level serialized state container.

    Wraps algorithm-specific state with metadata for versioning and validation.
    """
    version: str  # State format version (e.g., "1.0")
    algorithm: str  # 'csp' or 'beam'
    task_id: str  # Unique task identifier
    timestamp: str  # ISO timestamp when saved
    metadata: Dict[str, Any]  # Options, config, stats
    state_data: Dict[str, Any]  # Algorithm-specific state


class StateManager:
    """
    Manages serialization/deserialization of autofill state.

    Supports:
    - CSP backtracking state
    - Beam search state (future)
    - Compression (gzip)
    - Version management
    """

    VERSION = "1.0"

    def __init__(self, storage_dir: Optional[Path] = None):
        """
        Initialize state manager.

        Args:
            storage_dir: Directory for state files (defaults to /tmp/crossword_states)
        """
        if storage_dir is None:
            storage_dir = Path("/tmp/crossword_states")

        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def save_csp_state(
        self,
        task_id: str,
        csp_state: CSPState,
        metadata: Dict[str, Any],
        compress: bool = True
    ) -> Path:
        """
        Save CSP state to file.

        Args:
            task_id: Unique task identifier
            csp_state: Complete CSP state
            metadata: Additional metadata (options, stats)
            compress: Whether to gzip compress (default: True)

        Returns:
            Path to saved state file
        """
        # Create serialized state container
        serialized = SerializedState(
            version=self.VERSION,
            algorithm='csp',
            task_id=task_id,
            timestamp=datetime.now().isoformat(),
            metadata=metadata,
            state_data=asdict(csp_state)
        )

        # Convert to JSON
        json_data = json.dumps(asdict(serialized), indent=2)

        # Determine file path
        if compress:
            file_path = self.storage_dir / f"{task_id}.json.gz"
            with gzip.open(file_path, 'wt', encoding='utf-8') as f:
                f.write(json_data)
        else:
            file_path = self.storage_dir / f"{task_id}.json"
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(json_data)

        return file_path

    def load_csp_state(
        self,
        task_id: str
    ) -> Tuple[CSPState, Dict[str, Any]]:
        """
        Load CSP state from file.

        Args:
            task_id: Task identifier

        Returns:
            Tuple of (CSPState, metadata)

        Raises:
            FileNotFoundError: If state file doesn't exist
            ValueError: If state format is invalid or incompatible
        """
        # Try compressed first, then uncompressed
        file_path_gz = self.storage_dir / f"{task_id}.json.gz"
        file_path_json = self.storage_dir / f"{task_id}.json"

        if file_path_gz.exists():
            with gzip.open(file_path_gz, 'rt', encoding='utf-8') as f:
                json_data = f.read()
        elif file_path_json.exists():
            with open(file_path_json, 'r', encoding='utf-8') as f:
                json_data = f.read()
        else:
            raise FileNotFoundError(f"State file not found for task_id: {task_id}")

        # Parse JSON
        data = json.loads(json_data)

        # Validate version
        if data.get('version') != self.VERSION:
            raise ValueError(
                f"Incompatible state version: {data.get('version')} "
                f"(expected {self.VERSION})"
            )

        # Validate algorithm
        if data.get('algorithm') != 'csp':
            raise ValueError(
                f"Wrong algorithm: {data.get('algorithm')} (expected 'csp')"
            )

        # Extract state data
        state_data = data['state_data']
        metadata = data['metadata']

        # Reconstruct CSPState (converting Lists back to Sets where needed)
        csp_state = CSPState(
            grid_dict=state_data['grid_dict'],
            domains={
                int(k): v for k, v in state_data['domains'].items()
            },  # Keep as List
            constraints={
                int(k): v for k, v in state_data['constraints'].items()
            },
            used_words=state_data['used_words'],  # Keep as List
            slot_id_map={
                k: v for k, v in state_data['slot_id_map'].items()
            },
            slot_list=state_data['slot_list'],
            slots_sorted=state_data['slots_sorted'],
            current_slot_index=state_data['current_slot_index'],
            iteration_count=state_data['iteration_count'],
            locked_slots=state_data['locked_slots'],  # Keep as List
            timestamp=state_data['timestamp'],
            random_seed=state_data.get('random_seed'),
            letter_frequency_table=state_data.get('letter_frequency_table')
        )

        return csp_state, metadata

    def get_state_info(self, task_id: str) -> Dict[str, Any]:
        """
        Get metadata about saved state without loading full state.

        Args:
            task_id: Task identifier

        Returns:
            Dictionary with state information:
            - task_id, timestamp, algorithm
            - slots_filled, total_slots
            - grid_size

        Raises:
            FileNotFoundError: If state file doesn't exist
        """
        # Try compressed first
        file_path_gz = self.storage_dir / f"{task_id}.json.gz"
        file_path_json = self.storage_dir / f"{task_id}.json"

        if file_path_gz.exists():
            with gzip.open(file_path_gz, 'rt', encoding='utf-8') as f:
                data = json.load(f)
        elif file_path_json.exists():
            with open(file_path_json, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            raise FileNotFoundError(f"State file not found for task_id: {task_id}")

        # Extract key info
        metadata = data['metadata']

        return {
            'task_id': data['task_id'],
            'timestamp': data['timestamp'],
            'algorithm': data['algorithm'],
            'version': data['version'],
            'slots_filled': metadata.get('slots_filled', 0),
            'total_slots': metadata.get('total_slots', 0),
            'grid_size': metadata.get('grid_size', [15, 15]),
            'iteration_count': data['state_data'].get('iteration_count', 0)
        }

    def delete_state(self, task_id: str) -> bool:
        """
        Delete saved state file.

        Args:
            task_id: Task identifier

        Returns:
            True if file was deleted, False if not found
        """
        file_path_gz = self.storage_dir / f"{task_id}.json.gz"
        file_path_json = self.storage_dir / f"{task_id}.json"

        deleted = False
        if file_path_gz.exists():
            file_path_gz.unlink()
            deleted = True
        if file_path_json.exists():
            file_path_json.unlink()
            deleted = True

        return deleted

    def list_states(self, max_age_days: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        List all saved states.

        Args:
            max_age_days: Only return states newer than this (default: all)

        Returns:
            List of state info dictionaries
        """
        states = []

        # Find all state files
        for file_path in self.storage_dir.glob("*.json*"):
            try:
                # Extract task_id from filename
                task_id = file_path.stem.replace('.json', '')

                # Get state info
                info = self.get_state_info(task_id)

                # Filter by age if specified
                if max_age_days is not None:
                    state_time = datetime.fromisoformat(info['timestamp'])
                    age_days = (datetime.now() - state_time).days
                    if age_days > max_age_days:
                        continue

                states.append(info)
            except Exception:
                # Skip invalid state files
                continue

        # Sort by timestamp (newest first)
        states.sort(key=lambda x: x['timestamp'], reverse=True)

        return states

    def cleanup_old_states(self, max_age_days: int = 7) -> int:
        """
        Delete state files older than specified days.

        Args:
            max_age_days: Delete states older than this many days

        Returns:
            Number of states deleted
        """
        deleted_count = 0

        for file_path in self.storage_dir.glob("*.json*"):
            try:
                # Get file modification time
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                age_days = (datetime.now() - mtime).days

                if age_days > max_age_days:
                    file_path.unlink()
                    deleted_count += 1
            except Exception:
                # Skip files that can't be deleted
                continue

        return deleted_count

    @staticmethod
    def capture_csp_state(
        autofill_instance,
        current_slot_index: int,
        locked_slots: Optional[Set[int]] = None
    ) -> CSPState:
        """
        Capture current CSP state from Autofill instance.

        This is a helper to extract state from an active Autofill object.

        Args:
            autofill_instance: Active Autofill object
            current_slot_index: Current backtracking position
            locked_slots: Slots that should not be modified (theme + user edits)

        Returns:
            CSPState ready for serialization
        """
        if locked_slots is None:
            locked_slots = set()

        # Convert domains from Set to List for JSON
        domains_list = {
            slot_id: list(words)
            for slot_id, words in autofill_instance.domains.items()
        }

        # Convert slot_id_map to JSON-serializable format
        # Keys are tuples like (row, col, direction), convert to lists
        slot_id_map_str = {
            json.dumps(list(key)): value
            for key, value in autofill_instance.slot_id_map.items()
        }

        return CSPState(
            grid_dict=autofill_instance.grid.to_dict(),
            domains=domains_list,
            constraints=autofill_instance.constraints,
            used_words=list(autofill_instance.used_words),
            slot_id_map=slot_id_map_str,
            slot_list=autofill_instance.slot_list,
            slots_sorted=getattr(autofill_instance, 'slots_sorted', []),
            current_slot_index=current_slot_index,
            iteration_count=autofill_instance.iterations,
            locked_slots=list(locked_slots),
            timestamp=datetime.now().isoformat(),
            random_seed=getattr(autofill_instance, 'random_seed', None),
            letter_frequency_table=getattr(
                autofill_instance,
                'letter_frequency_table',
                None
            )
        )

    @staticmethod
    def restore_to_autofill(
        autofill_instance,
        csp_state: CSPState
    ) -> None:
        """
        Restore CSP state into Autofill instance.

        Mutates the autofill_instance to restore saved state.

        Args:
            autofill_instance: Autofill object to restore state into
            csp_state: Saved CSP state
        """
        # Restore grid
        autofill_instance.grid = Grid.from_dict(csp_state.grid_dict)

        # Restore CSP state (convert Lists back to Sets where needed)
        autofill_instance.domains = {
            slot_id: set(words)
            for slot_id, words in csp_state.domains.items()
        }
        autofill_instance.constraints = csp_state.constraints
        autofill_instance.used_words = set(csp_state.used_words)

        # Restore slot_id_map (convert JSON lists back to tuples)
        autofill_instance.slot_id_map = {}
        for key_str, value in csp_state.slot_id_map.items():
            # Parse JSON-encoded list like "[0, 0, \"across\"]" back to tuple
            key_list = json.loads(key_str)
            key = tuple(key_list)
            autofill_instance.slot_id_map[key] = value

        autofill_instance.slot_list = csp_state.slot_list
        autofill_instance.iterations = csp_state.iteration_count

        # Restore optional fields
        if csp_state.random_seed is not None:
            autofill_instance.random_seed = csp_state.random_seed

        if csp_state.letter_frequency_table is not None:
            autofill_instance.letter_frequency_table = csp_state.letter_frequency_table

        # Store sorted slots for resume
        if not hasattr(autofill_instance, 'slots_sorted'):
            autofill_instance.slots_sorted = csp_state.slots_sorted

    def save_beam_search_state(
        self,
        task_id: str,
        beam_state: BeamSearchState,
        metadata: Dict[str, Any],
        compress: bool = True
    ) -> Path:
        """
        Save Beam Search state to file.

        Args:
            task_id: Unique task identifier
            beam_state: Complete Beam Search state
            metadata: Additional metadata (options, stats)
            compress: Whether to gzip compress (default: True)

        Returns:
            Path to saved state file
        """
        # Create serialized state container
        serialized = SerializedState(
            version=self.VERSION,
            algorithm='beam',
            task_id=task_id,
            timestamp=datetime.now().isoformat(),
            metadata=metadata,
            state_data=asdict(beam_state)
        )

        # Convert to JSON
        json_data = json.dumps(asdict(serialized), indent=2)

        # Determine file path
        if compress:
            file_path = self.storage_dir / f"{task_id}.json.gz"
            with gzip.open(file_path, 'wt', encoding='utf-8') as f:
                f.write(json_data)
        else:
            file_path = self.storage_dir / f"{task_id}.json"
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(json_data)

        return file_path

    def load_beam_search_state(
        self,
        task_id: str
    ) -> Tuple[BeamSearchState, Dict[str, Any]]:
        """
        Load Beam Search state from file.

        Args:
            task_id: Task identifier

        Returns:
            Tuple of (BeamSearchState, metadata)

        Raises:
            FileNotFoundError: If state file doesn't exist
            ValueError: If state format is invalid or incompatible
        """
        # Try compressed first, then uncompressed
        file_path_gz = self.storage_dir / f"{task_id}.json.gz"
        file_path_json = self.storage_dir / f"{task_id}.json"

        if file_path_gz.exists():
            with gzip.open(file_path_gz, 'rt', encoding='utf-8') as f:
                json_data = f.read()
        elif file_path_json.exists():
            with open(file_path_json, 'r', encoding='utf-8') as f:
                json_data = f.read()
        else:
            raise FileNotFoundError(f"State file not found for task_id: {task_id}")

        # Parse JSON
        data = json.loads(json_data)

        # Validate version
        if data.get('version') != self.VERSION:
            raise ValueError(
                f"Incompatible state version: {data.get('version')} "
                f"(expected {self.VERSION})"
            )

        # Validate algorithm
        if data.get('algorithm') != 'beam':
            raise ValueError(
                f"Wrong algorithm: {data.get('algorithm')} (expected 'beam')"
            )

        # Extract state data
        state_data = data['state_data']
        metadata = data['metadata']

        # Reconstruct BeamSearchState
        beam_state = BeamSearchState(
            beam=state_data['beam'],
            filled_slots=state_data['filled_slots'],
            slot_idx=state_data['slot_idx'],
            iterations=state_data['iterations'],
            slot_attempt_history=state_data['slot_attempt_history'],
            recently_failed=state_data['recently_failed'],
            beam_width=state_data['beam_width'],
            candidates_per_slot=state_data['candidates_per_slot'],
            min_score=state_data['min_score'],
            diversity_bonus=state_data['diversity_bonus'],
            theme_entries=state_data['theme_entries'],
            all_slots=state_data['all_slots'],
            total_slots=state_data['total_slots'],
            timestamp=state_data['timestamp']
        )

        return beam_state, metadata

    @staticmethod
    def serialize_beam_state(beam_state_obj) -> Dict:
        """
        Serialize a BeamState object to dictionary.

        Args:
            beam_state_obj: BeamState instance from beam_search/state.py

        Returns:
            Dictionary representation of BeamState
        """
        return {
            'grid_dict': beam_state_obj.grid.to_dict(),
            'slots_filled': beam_state_obj.slots_filled,
            'total_slots': beam_state_obj.total_slots,
            'score': beam_state_obj.score,
            'used_words': list(beam_state_obj.used_words),
            'slot_assignments': {
                json.dumps(list(k)): v
                for k, v in beam_state_obj.slot_assignments.items()
            },
            'domains': {
                json.dumps(list(k)): v
                for k, v in beam_state_obj.domains.items()
            },
            'domain_reductions': {
                json.dumps(list(k)): v
                for k, v in beam_state_obj.domain_reductions.items()
            }
        }

    @staticmethod
    def deserialize_beam_state(beam_state_dict: Dict):
        """
        Deserialize dictionary to BeamState object.

        Args:
            beam_state_dict: Dictionary representation

        Returns:
            BeamState instance
        """
        from .beam_search.state import BeamState

        # Restore grid
        grid = Grid.from_dict(beam_state_dict['grid_dict'])

        # Restore slot_assignments with tuple keys
        slot_assignments = {}
        for key_str, value in beam_state_dict['slot_assignments'].items():
            key_list = json.loads(key_str)
            slot_assignments[tuple(key_list)] = value

        # Restore domains with tuple keys
        domains = {}
        for key_str, value in beam_state_dict['domains'].items():
            key_list = json.loads(key_str)
            domains[tuple(key_list)] = value

        # Restore domain_reductions with tuple keys
        domain_reductions = {}
        for key_str, value in beam_state_dict['domain_reductions'].items():
            key_list = json.loads(key_str)
            domain_reductions[tuple(key_list)] = value

        return BeamState(
            grid=grid,
            slots_filled=beam_state_dict['slots_filled'],
            total_slots=beam_state_dict['total_slots'],
            score=beam_state_dict['score'],
            used_words=set(beam_state_dict['used_words']),
            slot_assignments=slot_assignments,
            domains=domains,
            domain_reductions=domain_reductions
        )

    @staticmethod
    def capture_beam_search_state(
        orchestrator_instance,
        beam: List,
        filled_slots: Set,
        slot_idx: int
    ) -> BeamSearchState:
        """
        Capture current Beam Search state from orchestrator instance.

        Args:
            orchestrator_instance: Active BeamSearchOrchestrator object
            beam: Current beam (list of BeamState objects)
            filled_slots: Set of filled slot tuples (row, col, direction)
            slot_idx: Current slot index

        Returns:
            BeamSearchState ready for serialization
        """
        # Serialize each BeamState in the beam
        serialized_beam = [
            StateManager.serialize_beam_state(state)
            for state in beam
        ]

        # Convert filled_slots set to list
        filled_slots_list = [list(slot_tuple) for slot_tuple in filled_slots]

        # Convert slot_attempt_history with tuple keys to JSON strings
        slot_attempt_history = {}
        for (beam_sig, slot_id), attempts in orchestrator_instance.slot_attempt_history.items():
            key_str = json.dumps([beam_sig, list(slot_id)])
            slot_attempt_history[key_str] = attempts

        # Convert recently_failed to list of lists
        recently_failed = [list(slot_tuple) for slot_tuple in orchestrator_instance.recently_failed]

        # Convert theme_entries with tuple keys to JSON strings
        theme_entries = {}
        for slot_tuple, word in orchestrator_instance.theme_entries.items():
            key_str = json.dumps(list(slot_tuple))
            theme_entries[key_str] = word

        # Get all slots
        all_slots = orchestrator_instance.grid.get_empty_slots()

        return BeamSearchState(
            beam=serialized_beam,
            filled_slots=filled_slots_list,
            slot_idx=slot_idx,
            iterations=orchestrator_instance.iterations,
            slot_attempt_history=slot_attempt_history,
            recently_failed=recently_failed,
            beam_width=orchestrator_instance.beam_width,
            candidates_per_slot=orchestrator_instance.candidates_per_slot,
            min_score=orchestrator_instance.min_score,
            diversity_bonus=orchestrator_instance.diversity_bonus,
            theme_entries=theme_entries,
            all_slots=all_slots,
            total_slots=len(all_slots),
            timestamp=datetime.now().isoformat()
        )
