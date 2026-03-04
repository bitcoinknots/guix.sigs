# PoW Blockchain Network

A self-contained **Proof-of-Work (PoW) blockchain** implemented in pure Python,
modelling the core mechanics of a Bitcoin-like network.

---

## Features

| Feature | Details |
|---------|---------|
| **PoW mining** | SHA-256 hash with configurable leading-zero difficulty |
| **Chain validation** | Hash integrity + previous-hash linkage + PoW target checks |
| **Transactions** | Simple sender → recipient value transfers |
| **Mining reward** | Configurable coinbase reward per mined block |
| **P2P nodes** | In-process nodes with peer registry and broadcast |
| **Consensus** | Longest valid chain wins (Nakamoto consensus) |

---

## Quick start

```python
from blockchain.blockchain import Blockchain

# Create a chain (difficulty=4 means hashes must start with "0000")
bc = Blockchain(difficulty=4)

# Queue some transactions
bc.add_transaction("alice", "bob", 10)
bc.add_transaction("bob",   "carol", 3)

# Mine a block – returns the new Block or None if nothing is pending
block = bc.mine(miner_address="miner1")
print(block.hash)            # starts with "0000..."
print(bc.is_valid_chain())   # True

print(bc.get_balance("bob"))    # 10 - 3 = 7.0
print(bc.get_balance("miner1")) # 50.0 (default mining reward)
```

### Running a two-node network

```python
from blockchain.node import Node

node_a = Node("node_a", difficulty=3)
node_b = Node("node_b", difficulty=3)

node_a.register_peer(node_b)
node_b.register_peer(node_a)

node_a.blockchain.add_transaction("alice", "bob", 5)
node_a.mine("alice")          # mines + broadcasts to node_b

print(len(node_b.blockchain.chain))  # 2 – node_b adopted node_a's chain
```

---

## Project layout

```
blockchain/
├── blockchain.py       # Transaction, Block, Blockchain classes
├── node.py             # P2P Node with peer management & consensus
└── tests/
    └── test_blockchain.py  # 23 unit tests
```

---

## Running the tests

```bash
pip install pytest
python -m pytest blockchain/tests/ -v
```

---

## How PoW works here

1. A new `Block` is created with `nonce = 0` and the current pending transactions.
2. `proof_of_work()` increments `nonce` and recomputes `SHA-256(block_data)` until
   the result starts with `difficulty` zeros (e.g. `"0000…"` for `difficulty=4`).
3. The winning hash is stored in `block.hash` and the block is appended to the chain.
4. Any node that receives the block verifies `is_valid_proof()` before accepting it.
5. If two nodes have conflicting chains, `resolve_conflicts()` keeps the **longest
   valid chain** (Nakamoto consensus).

## Adjusting difficulty

```python
# Easy (fast, good for tests)
bc = Blockchain(difficulty=2)

# Bitcoin-like (very slow – don't use in tests)
bc = Blockchain(difficulty=20)
```
