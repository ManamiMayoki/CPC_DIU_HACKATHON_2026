"""Synthetic Transaction Generator for Hackathon Testing.

NOTE: This generator produces synthetic test transactions for graph and ML algorithm
evaluation. These synthetic scenarios (NORMAL, FAN_IN, FAN_OUT, RAPID_MOVEMENT,
CHAIN, CIRCULAR_FLOW, COORDINATED_NETWORK) are testing artifacts and do NOT represent
real-world financial-crime labels, banking definitions, or proof of illegal activity.
"""

from __future__ import annotations

import datetime
import json
import random
from typing import Any, Dict, List, Optional


class SyntheticDataGenerator:
    """Generates synthetic financial transaction streams with controlled topology scenarios."""

    def __init__(self, seed: int = 42) -> None:
        self.seed = seed
        self.rng = random.Random(seed)
        self.tx_counter = 0

    def _next_tx_id(self) -> str:
        self.tx_counter += 1
        return f"TX_{self.tx_counter:06d}"

    def _format_time(self, dt: datetime.datetime) -> str:
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    def generate_normal_transactions(
        self,
        num_accounts: int = 20,
        num_transactions: int = 100,
        base_time: Optional[datetime.datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Generate normal baseline peer-to-peer / merchant transactions.

        Characteristics: dispersed counterparties, moderate transaction amounts,
        natural time gaps.
        """
        if base_time is None:
            base_time = datetime.datetime(2026, 3, 1, 9, 0, 0)

        accounts = [f"ACC_NORM_{i:03d}" for i in range(1, num_accounts + 1)]
        transactions: List[Dict[str, Any]] = []
        current_time = base_time

        for _ in range(num_transactions):
            sender, receiver = self.rng.sample(accounts, 2)
            amount = round(self.rng.uniform(10.0, 500.0), 2)
            current_time += datetime.timedelta(seconds=self.rng.randint(60, 1800))
            transactions.append(
                {
                    "transaction_id": self._next_tx_id(),
                    "sender_id": sender,
                    "receiver_id": receiver,
                    "amount": amount,
                    "timestamp": self._format_time(current_time),
                }
            )

        return transactions

    def generate_fan_in_scenario(
        self,
        target_account: str = "ACC_FANIN_HUB",
        num_senders: int = 8,
        base_time: Optional[datetime.datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Many accounts sending funds to a single collector account."""
        if base_time is None:
            base_time = datetime.datetime(2026, 3, 1, 10, 0, 0)

        transactions: List[Dict[str, Any]] = []
        current_time = base_time

        for i in range(num_senders):
            sender = f"ACC_FANIN_SRC_{i:03d}"
            amount = round(self.rng.uniform(400.0, 950.0), 2)
            current_time += datetime.timedelta(seconds=self.rng.randint(30, 240))
            transactions.append(
                {
                    "transaction_id": self._next_tx_id(),
                    "sender_id": sender,
                    "receiver_id": target_account,
                    "amount": amount,
                    "timestamp": self._format_time(current_time),
                }
            )

        return transactions

    def generate_fan_out_scenario(
        self,
        source_account: str = "ACC_FANOUT_HUB",
        num_receivers: int = 8,
        base_time: Optional[datetime.datetime] = None,
    ) -> List[Dict[str, Any]]:
        """A single account dispersing funds to multiple destination accounts."""
        if base_time is None:
            base_time = datetime.datetime(2026, 3, 1, 11, 0, 0)

        transactions: List[Dict[str, Any]] = []
        current_time = base_time

        for i in range(num_receivers):
            receiver = f"ACC_FANOUT_DST_{i:03d}"
            amount = round(self.rng.uniform(300.0, 800.0), 2)
            current_time += datetime.timedelta(seconds=self.rng.randint(20, 180))
            transactions.append(
                {
                    "transaction_id": self._next_tx_id(),
                    "sender_id": source_account,
                    "receiver_id": receiver,
                    "amount": amount,
                    "timestamp": self._format_time(current_time),
                }
            )

        return transactions

    def generate_rapid_movement_scenario(
        self,
        intermediary_account: str = "ACC_RAPID_MID",
        source_account: str = "ACC_RAPID_IN",
        destination_account: str = "ACC_RAPID_OUT",
        base_time: Optional[datetime.datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Inflow received and immediately forwarded onwards within minutes (passthrough)."""
        if base_time is None:
            base_time = datetime.datetime(2026, 3, 1, 12, 0, 0)

        in_amount = 5000.0
        # Intermediary forwards 95% of incoming funds shortly after
        out_amount = 4750.0

        t1 = base_time
        t2 = t1 + datetime.timedelta(minutes=5)

        return [
            {
                "transaction_id": self._next_tx_id(),
                "sender_id": source_account,
                "receiver_id": intermediary_account,
                "amount": in_amount,
                "timestamp": self._format_time(t1),
            },
            {
                "transaction_id": self._next_tx_id(),
                "sender_id": intermediary_account,
                "receiver_id": destination_account,
                "amount": out_amount,
                "timestamp": self._format_time(t2),
            },
        ]

    def generate_chain_scenario(
        self,
        chain_length: int = 5,
        prefix: str = "ACC_CHAIN",
        base_time: Optional[datetime.datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Multi-hop transaction sequence: A -> B -> C -> D -> E."""
        if base_time is None:
            base_time = datetime.datetime(2026, 3, 1, 13, 0, 0)

        transactions: List[Dict[str, Any]] = []
        current_time = base_time
        current_amount = 8000.0

        for i in range(chain_length - 1):
            sender = f"{prefix}_{i:02d}"
            receiver = f"{prefix}_{i+1:02d}"
            # Small fee deduction at each hop
            current_amount = round(current_amount * 0.96, 2)
            current_time += datetime.timedelta(minutes=10)
            transactions.append(
                {
                    "transaction_id": self._next_tx_id(),
                    "sender_id": sender,
                    "receiver_id": receiver,
                    "amount": current_amount,
                    "timestamp": self._format_time(current_time),
                }
            )

        return transactions

    def generate_circular_flow_scenario(
        self,
        cycle_nodes: Optional[List[str]] = None,
        base_time: Optional[datetime.datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Circular transaction path: A -> B -> C -> A."""
        if base_time is None:
            base_time = datetime.datetime(2026, 3, 1, 14, 0, 0)

        if cycle_nodes is None:
            cycle_nodes = ["ACC_CYCLE_A", "ACC_CYCLE_B", "ACC_CYCLE_C"]

        transactions: List[Dict[str, Any]] = []
        current_time = base_time
        base_amount = 3500.0

        n = len(cycle_nodes)
        for i in range(n):
            sender = cycle_nodes[i]
            receiver = cycle_nodes[(i + 1) % n]
            amount = round(base_amount - (i * 50), 2)
            current_time += datetime.timedelta(minutes=15)
            transactions.append(
                {
                    "transaction_id": self._next_tx_id(),
                    "sender_id": sender,
                    "receiver_id": receiver,
                    "amount": amount,
                    "timestamp": self._format_time(current_time),
                }
            )

        return transactions

    def generate_coordinated_network_scenario(
        self,
        network_size: int = 5,
        prefix: str = "ACC_COORD",
        base_time: Optional[datetime.datetime] = None,
    ) -> List[Dict[str, Any]]:
        """A dense cluster of accounts transacting heavily among themselves."""
        if base_time is None:
            base_time = datetime.datetime(2026, 3, 1, 15, 0, 0)

        accounts = [f"{prefix}_{i:02d}" for i in range(network_size)]
        transactions: List[Dict[str, Any]] = []
        current_time = base_time

        # Create multiple bidirectional or interlocking paths
        for sender in accounts:
            for receiver in accounts:
                if sender != receiver and self.rng.random() > 0.35:
                    amount = round(self.rng.uniform(1200.0, 4000.0), 2)
                    current_time += datetime.timedelta(minutes=self.rng.randint(3, 20))
                    transactions.append(
                        {
                            "transaction_id": self._next_tx_id(),
                            "sender_id": sender,
                            "receiver_id": receiver,
                            "amount": amount,
                            "timestamp": self._format_time(current_time),
                        }
                    )

        return transactions

    def generate_comprehensive_dataset(self) -> List[Dict[str, Any]]:
        """Generates a complete dataset combining normal transactions and each controlled scenario."""
        all_tx: List[Dict[str, Any]] = []
        all_tx.extend(self.generate_normal_transactions(num_accounts=25, num_transactions=120))
        all_tx.extend(self.generate_fan_in_scenario(num_senders=7))
        all_tx.extend(self.generate_fan_out_scenario(num_receivers=7))
        all_tx.extend(self.generate_rapid_movement_scenario())
        all_tx.extend(self.generate_chain_scenario(chain_length=5))
        all_tx.extend(self.generate_circular_flow_scenario())
        all_tx.extend(self.generate_coordinated_network_scenario(network_size=5))

        # Sort chronologically
        all_tx.sort(key=lambda x: x["timestamp"])
        return all_tx


def main() -> None:
    generator = SyntheticDataGenerator(seed=42)
    dataset = generator.generate_comprehensive_dataset()
    output_path = "b:/Ai hackthon/CPC_DIU_HACKATHON_2026/data/synthetic/transactions_sample.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2)
    print(f"Generated {len(dataset)} synthetic transactions into {output_path}")


if __name__ == "__main__":
    main()
