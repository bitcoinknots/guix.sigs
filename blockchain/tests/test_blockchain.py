"""
Unit tests for the PoW blockchain implementation.

Run with:
    python -m pytest blockchain/tests/ -v
"""

import sys
import os

# Allow importing from the parent blockchain/ package directory.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from blockchain import Block, Blockchain, Transaction
from node import Node


# ---------------------------------------------------------------------------
# Transaction tests
# ---------------------------------------------------------------------------

class TestTransaction:
    def test_to_dict_contains_required_fields(self):
        tx = Transaction("alice", "bob", 5.0)
        d = tx.to_dict()
        assert d["sender"] == "alice"
        assert d["recipient"] == "bob"
        assert d["amount"] == 5.0
        assert "timestamp" in d


# ---------------------------------------------------------------------------
# Block tests
# ---------------------------------------------------------------------------

class TestBlock:
    def test_compute_hash_is_deterministic(self):
        block = Block(1, [], "0" * 64, timestamp=1000.0)
        assert block.compute_hash() == block.compute_hash()

    def test_changing_nonce_changes_hash(self):
        block = Block(1, [], "0" * 64, timestamp=1000.0)
        h1 = block.compute_hash()
        block.nonce += 1
        h2 = block.compute_hash()
        assert h1 != h2

    def test_to_dict_contains_required_fields(self):
        block = Block(0, [], "0" * 64)
        d = block.to_dict()
        for key in ("index", "timestamp", "transactions", "previous_hash", "nonce", "hash"):
            assert key in d


# ---------------------------------------------------------------------------
# Blockchain / PoW tests
# ---------------------------------------------------------------------------

class TestBlockchain:
    def setup_method(self):
        # Use difficulty=2 so tests run quickly.
        self.bc = Blockchain(difficulty=2)

    def test_genesis_block_exists(self):
        assert len(self.bc.chain) == 1
        genesis = self.bc.chain[0]
        assert genesis.index == 0
        assert genesis.previous_hash == "0" * 64

    def test_genesis_chain_is_valid(self):
        assert self.bc.is_valid_chain()

    def test_mine_returns_none_without_transactions(self):
        result = self.bc.mine("miner")
        assert result is None

    def test_mine_adds_block(self):
        self.bc.add_transaction("alice", "bob", 10)
        block = self.bc.mine("miner")
        assert block is not None
        assert len(self.bc.chain) == 2
        assert block.hash.startswith("00")   # difficulty=2

    def test_chain_valid_after_mining(self):
        self.bc.add_transaction("alice", "bob", 10)
        self.bc.mine("miner")
        assert self.bc.is_valid_chain()

    def test_balance_after_transactions(self):
        self.bc.add_transaction("alice", "bob", 10)
        self.bc.mine("miner")
        assert self.bc.get_balance("bob") == 10.0
        assert self.bc.get_balance("alice") == -10.0

    def test_miner_receives_reward(self):
        self.bc.add_transaction("alice", "bob", 5)
        self.bc.mine("miner")
        assert self.bc.get_balance("miner") == self.bc.mining_reward

    def test_tamper_invalidates_chain(self):
        self.bc.add_transaction("alice", "bob", 10)
        self.bc.mine("miner")
        # Tamper with a transaction in the last block.
        self.bc.chain[1].transactions[0]["amount"] = 9999
        assert not self.bc.is_valid_chain()

    def test_multiple_blocks(self):
        for i in range(3):
            self.bc.add_transaction("alice", "bob", i + 1)
            self.bc.mine("miner")
        assert len(self.bc.chain) == 4   # genesis + 3
        assert self.bc.is_valid_chain()

    def test_proof_of_work_satisfies_difficulty(self):
        self.bc.add_transaction("x", "y", 1)
        block = self.bc.mine("miner")
        assert block.hash.startswith("0" * self.bc.difficulty)

    def test_is_valid_proof(self):
        self.bc.add_transaction("x", "y", 1)
        block = self.bc.mine("miner")
        assert self.bc.is_valid_proof(block, block.hash)

    def test_to_dict(self):
        d = self.bc.to_dict()
        assert d["difficulty"] == self.bc.difficulty
        assert d["length"] == len(self.bc.chain)
        assert len(d["chain"]) == len(self.bc.chain)


# ---------------------------------------------------------------------------
# Node / P2P tests
# ---------------------------------------------------------------------------

class TestNode:
    def setup_method(self):
        self.node_a = Node("node_a", difficulty=2)
        self.node_b = Node("node_b", difficulty=2)
        self.node_a.register_peer(self.node_b)
        self.node_b.register_peer(self.node_a)

    def test_register_peer(self):
        assert self.node_b in self.node_a.peers

    def test_deregister_peer(self):
        self.node_a.deregister_peer(self.node_b)
        assert self.node_b not in self.node_a.peers

    def test_register_self_ignored(self):
        self.node_a.register_peer(self.node_a)
        assert self.node_a not in self.node_a.peers

    def test_mine_broadcasts_to_peer(self):
        self.node_a.blockchain.add_transaction("alice", "bob", 5)
        self.node_a.mine("alice")
        # node_b should have adopted node_a's longer chain.
        assert len(self.node_b.blockchain.chain) == len(self.node_a.blockchain.chain)

    def test_resolve_conflicts_adopts_longer_chain(self):
        # Mine two blocks on node_a without broadcasting.
        self.node_a.blockchain.add_transaction("alice", "bob", 1)
        self.node_a.blockchain.mine("alice")
        self.node_a.blockchain.add_transaction("alice", "bob", 2)
        self.node_a.blockchain.mine("alice")

        assert len(self.node_b.blockchain.chain) == 1   # only genesis

        replaced = self.node_b.resolve_conflicts()
        assert replaced is True
        assert len(self.node_b.blockchain.chain) == 3

    def test_resolve_conflicts_keeps_own_chain_if_longest(self):
        self.node_a.blockchain.add_transaction("x", "y", 1)
        self.node_a.blockchain.mine("x")
        self.node_b.blockchain.add_transaction("x", "y", 1)
        self.node_b.blockchain.mine("x")
        self.node_b.blockchain.add_transaction("x", "y", 2)
        self.node_b.blockchain.mine("x")

        replaced = self.node_b.resolve_conflicts()
        assert replaced is False   # node_b is already longer

    def test_repr(self):
        assert "node_a" in repr(self.node_a)
