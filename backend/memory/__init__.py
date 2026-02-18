"""
Three-tier persistent memory system for R.U.T.H. V3.
- Episodic: Conversation summaries (what happened)
- Semantic: Facts and preferences (what R.U.T.H. knows about the user)
- Procedural: Learned workflows (how to do things)
"""

from .manager import MemoryManager

__all__ = ["MemoryManager"]
