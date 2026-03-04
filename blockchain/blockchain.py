"""
Simple Proof-of-Work blockchain implementation.

Clones the core mechanics of a Bitcoin-like PoW blockchain:
  - SHA-256 block hashing
  - Adjustable difficulty (leading zeros)
  - Chain integrity validation
  - Basic transaction support
"""

import hashlib
import json
import time
from typing import List, Optional


class Transaction:
    """A simple value transfer between two addresses."""

    def __init__(self, sender: str, recipient: str, amount: float) -> None:
        self.sender = sender
        self.recipient = recipient
        self.amount = amount
        self.timestamp = time.time()

    def to_dict(self) -> dict:
        return {
            "sender": self.sender,
            "recipient": self.recipient,
            "amount": self.amount,
            "timestamp": self.timestamp,
        }


class Block:
    """
    A single block in the chain.

    Fields
    ------
    index       : position in the chain (genesis = 0)
    timestamp   : Unix time when the block was mined
    transactions: list of Transaction dicts included in the block
    previous_hash: SHA-256 hash of the preceding block
    nonce       : the value incremented during PoW mining
    hash        : SHA-256 hash of this block (set after mining)
    """

    def __init__(
        self,
        index: int,
        transactions: List[dict],
        previous_hash: str,
        timestamp: Optional[float] = None,
    ) -> None:
        self.index = index
        self.timestamp = timestamp if timestamp is not None else time.time()
        self.transactions = transactions
        self.previous_hash = previous_hash
        self.nonce = 0
        self.hash = self.compute_hash()

    def compute_hash(self) -> str:
        """Return the SHA-256 hash of the block contents (excluding hash field)."""
        data = {k: v for k, v in self.__dict__.items() if k != "hash"}
        block_string = json.dumps(data, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": self.transactions,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
            "hash": self.hash,
        }


class Blockchain:
    """
    A Proof-of-Work blockchain.

    Parameters
    ----------
    difficulty : number of leading zeros required in a valid block hash.
                 Increase to make mining harder (default: 4).
    mining_reward : coins awarded to the miner of each block (default: 50).
    """

    GENESIS_PREVIOUS_HASH = "0" * 64

    def __init__(self, difficulty: int = 4, mining_reward: float = 50.0) -> None:
        self.difficulty = difficulty
        self.mining_reward = mining_reward
        self.unconfirmed_transactions: List[dict] = []
        self.chain: List[Block] = []
        self._create_genesis_block()

    # ------------------------------------------------------------------
    # Chain construction
    # ------------------------------------------------------------------

    def _create_genesis_block(self) -> None:
        genesis = Block(0, [], self.GENESIS_PREVIOUS_HASH, timestamp=0.0)
        genesis.hash = genesis.compute_hash()
        self.chain.append(genesis)

    @property
    def last_block(self) -> Block:
        return self.chain[-1]

    # ------------------------------------------------------------------
    # Proof-of-Work
    # ------------------------------------------------------------------

    def proof_of_work(self, block: Block) -> str:
        """
        Increment block.nonce until the block hash starts with
        `self.difficulty` zeros.  Returns the winning hash.
        """
        block.nonce = 0
        computed = block.compute_hash()
        target = "0" * self.difficulty
        while not computed.startswith(target):
            block.nonce += 1
            computed = block.compute_hash()
        return computed

    def is_valid_proof(self, block: Block, block_hash: str) -> bool:
        """Return True if block_hash satisfies the difficulty target."""
        return (
            block_hash.startswith("0" * self.difficulty)
            and block_hash == block.compute_hash()
        )

    # ------------------------------------------------------------------
    # Adding blocks / transactions
    # ------------------------------------------------------------------

    def add_transaction(self, sender: str, recipient: str, amount: float) -> int:
        """
        Queue a transaction for inclusion in the next block.
        Returns the index of the block that will contain it.
        """
        tx = Transaction(sender, recipient, amount)
        self.unconfirmed_transactions.append(tx.to_dict())
        return self.last_block.index + 1

    def mine(self, miner_address: str) -> Optional[Block]:
        """
        Mine a new block that contains all pending transactions plus
        the mining-reward coinbase transaction.

        Returns the newly added Block, or None if there is nothing to mine.
        """
        if not self.unconfirmed_transactions:
            return None

        # Coinbase reward
        coinbase = Transaction("network", miner_address, self.mining_reward)
        transactions = self.unconfirmed_transactions + [coinbase.to_dict()]

        new_block = Block(
            index=self.last_block.index + 1,
            transactions=transactions,
            previous_hash=self.last_block.hash,
        )

        proof = self.proof_of_work(new_block)
        self._add_block(new_block, proof)
        self.unconfirmed_transactions = []
        return new_block

    def _add_block(self, block: Block, proof: str) -> bool:
        """Validate and append a block to the chain."""
        if block.previous_hash != self.last_block.hash:
            return False
        if not self.is_valid_proof(block, proof):
            return False
        block.hash = proof
        self.chain.append(block)
        return True

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def is_valid_chain(self) -> bool:
        """
        Walk the entire chain and verify:
          1. Each block's stored hash matches its computed hash.
          2. Each block's previous_hash matches the actual hash of the
             preceding block.
          3. Every non-genesis block hash satisfies the PoW target.
        """
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i - 1]

            if current.hash != current.compute_hash():
                return False
            if current.previous_hash != previous.hash:
                return False
            if not current.hash.startswith("0" * self.difficulty):
                return False
        return True

    def replace_chain(self, new_chain: list) -> None:
        """
        Replace the local chain with *new_chain* and clear any
        unconfirmed transactions that are already included in it.
        """
        confirmed_txids = {
            json.dumps(tx, sort_keys=True)
            for block in new_chain
            for tx in block.transactions
        }
        self.chain = new_chain
        self.unconfirmed_transactions = [
            tx for tx in self.unconfirmed_transactions
            if json.dumps(tx, sort_keys=True) not in confirmed_txids
        ]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def get_balance(self, address: str) -> float:
        """Return the confirmed balance for *address*."""
        balance = 0.0
        for block in self.chain:
            for tx in block.transactions:
                if tx["recipient"] == address:
                    balance += tx["amount"]
                if tx["sender"] == address:
                    balance -= tx["amount"]
        return balance

    def to_dict(self) -> dict:
        return {
            "difficulty": self.difficulty,
            "length": len(self.chain),
            "chain": [b.to_dict() for b in self.chain],
        }
