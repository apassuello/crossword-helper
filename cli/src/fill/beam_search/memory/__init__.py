"""
Memory optimization components for beam search.

This package provides memory-efficient alternatives to standard operations:
- GridSnapshot: Copy-on-write grid cloning
- GridPool: Object pooling for Grid instances
- StatePool: Object pooling for BeamState instances
- DomainManager: Efficient domain storage with bitsets
"""

from .grid_snapshot import GridSnapshot
from .pools import GridPool, StatePool
from .domain_manager import DomainManager, Domain, SetDomain, BitsetDomain

__all__ = [
    'GridSnapshot',
    'GridPool',
    'StatePool',
    'DomainManager',
    'Domain',
    'SetDomain',
    'BitsetDomain'
]
