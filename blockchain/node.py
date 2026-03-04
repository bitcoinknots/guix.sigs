"""
Minimal P2P node for the PoW blockchain.

Each node:
  - Maintains its own local Blockchain instance.
  - Keeps a registry of peer node URLs.
  - Implements a longest-chain consensus rule to resolve forks:
    if a peer's chain is longer and valid, adopt it.

Usage (two nodes on localhost):
    node_a = Node("node_a")
    node_b = Node("node_b")
    node_a.register_peer(node_b)
    node_b.register_peer(node_a)

    node_a.blockchain.add_transaction("alice", "bob", 10)
    node_a.mine("alice")
    node_b.resolve_conflicts()   # node_b adopts node_a's longer chain
"""

from __future__ import annotations

from typing import List, Optional, Set

from blockchain import Blockchain, Block


class Node:
    """
    A network node that holds a Blockchain and communicates with peers.

    Parameters
    ----------
    node_id   : human-readable identifier for this node.
    difficulty: PoW difficulty passed to the underlying Blockchain.
    """

    def __init__(self, node_id: str, difficulty: int = 4) -> None:
        self.node_id = node_id
        self.blockchain = Blockchain(difficulty=difficulty)
        self._peers: Set["Node"] = set()

    # ------------------------------------------------------------------
    # Peer management
    # ------------------------------------------------------------------

    def register_peer(self, peer: "Node") -> None:
        """Add *peer* to the set of known peers (idempotent)."""
        if peer is not self:
            self._peers.add(peer)

    def deregister_peer(self, peer: "Node") -> None:
        """Remove *peer* from the set of known peers."""
        self._peers.discard(peer)

    @property
    def peers(self) -> List["Node"]:
        return list(self._peers)

    # ------------------------------------------------------------------
    # Mining
    # ------------------------------------------------------------------

    def mine(self, miner_address: str) -> Optional[Block]:
        """Mine a block and broadcast it to all peers."""
        block = self.blockchain.mine(miner_address)
        if block:
            self._broadcast(block)
        return block

    # ------------------------------------------------------------------
    # Consensus: longest valid chain wins
    # ------------------------------------------------------------------

    def resolve_conflicts(self) -> bool:
        """
        Replace the local chain with the longest valid chain found among
        peers.  Returns True if the chain was replaced, False otherwise.
        """
        best_length = len(self.blockchain.chain)
        best_chain: Optional[List[Block]] = None

        for peer in self._peers:
            peer_chain = peer.blockchain.chain
            if len(peer_chain) > best_length and peer.blockchain.is_valid_chain():
                best_length = len(peer_chain)
                best_chain = peer_chain

        if best_chain is not None:
            self.blockchain.replace_chain(best_chain)
            return True
        return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _broadcast(self, block: Block) -> None:
        """
        Notify every peer that a new block has been mined.
        Peers that are behind will call resolve_conflicts to catch up.
        """
        for peer in self._peers:
            if len(peer.blockchain.chain) < len(self.blockchain.chain):
                peer.resolve_conflicts()

    def __repr__(self) -> str:
        return (
            f"Node(id={self.node_id!r}, "
            f"chain_length={len(self.blockchain.chain)})"
        )
