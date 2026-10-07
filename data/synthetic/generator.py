"""Synthetic Transaction Generator for Hackathon Testing.

NOTE: This generator produces synthetic test transactions for graph and ML algorithm
evaluation. These synthetic scenarios (NORMAL, FAN_IN, FAN_OUT, RAPID_MOVEMENT,
CHAIN, CIRCULAR_FLOW, COORDINATED_NETWORK, STRUCTURING, MULE_RING, HUNDI, ACCOUNT_TAKEOVER) are testing artifacts and do NOT represent
real-world financial-crime labels, banking definitions, or proof of illegal activity.
"""

from __future__ import annotations

import datetime
import json
import os
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
        """Inflows received and forwarded onwards within minutes, three times in one afternoon (passthrough)."""
        if base_time is None:
            base_time = datetime.datetime(2026, 3, 1, 12, 0, 0)

        # (minutes after base_time, amount received, minutes until 95% is forwarded)
        rounds = [(0, 5000.0, 5), (90, 8000.0, 4), (180, 6500.0, 3)]

        transactions = []
        for offset, in_amount, delay in rounds:
            t_in = base_time + datetime.timedelta(minutes=offset)
            t_out = t_in + datetime.timedelta(minutes=delay)
            transactions.append({
                "transaction_id": self._next_tx_id(),
                "sender_id": source_account,
                "receiver_id": intermediary_account,
                "amount": in_amount,
                "timestamp": self._format_time(t_in),
            })
            transactions.append({
                "transaction_id": self._next_tx_id(),
                "sender_id": intermediary_account,
                "receiver_id": destination_account,
                "amount": round(in_amount * 0.95, 2),
                "timestamp": self._format_time(t_out),
            })
        return transactions

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

    def _tx(self, sender: str, receiver: str, amount: float, when: datetime.datetime) -> Dict[str, Any]:
        return {
            "transaction_id": self._next_tx_id(),
            "sender_id": sender,
            "receiver_id": receiver,
            "amount": round(amount, 2),
            "timestamp": self._format_time(when),
        }

    def generate_structuring_scenario(
        self,
        source_account: str = "ACC_STRUCT_SRC",
        destination_account: str = "ACC_STRUCT_DST",
        num_transfers: int = 5,
        threshold: float = 10000.0,
        base_time: Optional[datetime.datetime] = None,
    ) -> List[Dict[str, Any]]:
        """A large sum split into several transfers that each stay just under a threshold."""
        if base_time is None:
            base_time = datetime.datetime(2026, 3, 1, 18, 0, 0)

        transactions: List[Dict[str, Any]] = []
        current_time = base_time
        for _ in range(num_transfers):
            current_time += datetime.timedelta(minutes=self.rng.randint(40, 80))
            amount = self.rng.uniform(0.94, 0.995) * threshold
            transactions.append(self._tx(source_account, destination_account, amount, current_time))
        return transactions

    def generate_mule_ring_scenario(
        self,
        prefix: str = "ACC_MULE",
        num_feeders: int = 8,
        num_mules: int = 4,
        threshold: float = 10000.0,
        base_time: Optional[datetime.datetime] = None,
    ) -> List[Dict[str, Any]]:
        """An MFS money-mule ring that combines several typologies in one network.

        1. Feeder wallets send near-threshold amounts to a collector hub within minutes
           (fan-in + structuring).
        2. The hub forwards each receipt almost immediately to a set of mule wallets
           (rapid movement + fan-out).
        3. The mules pass the funds on to a cash-out agent wallet (multi-hop chain).
        4. The agent returns part of the money to the hub, closing a loop (circular flow).
        """
        if base_time is None:
            base_time = datetime.datetime(2026, 3, 1, 16, 0, 0)

        hub = f"{prefix}_HUB"
        cashout = f"{prefix}_CASHOUT"
        mules = [f"{prefix}_{i + 1:02d}" for i in range(num_mules)]
        transactions: List[Dict[str, Any]] = []
        current_time = base_time

        mule_received: Dict[str, List[float]] = {m: [] for m in mules}
        for i in range(num_feeders):
            current_time += datetime.timedelta(minutes=self.rng.randint(2, 5))
            in_amount = self.rng.uniform(0.93, 0.99) * threshold
            transactions.append(self._tx(f"{prefix}_SRC_{i:03d}", hub, in_amount, current_time))

            # Hub forwards most of each receipt within a few minutes
            mule = mules[i % num_mules]
            out_amount = in_amount * self.rng.uniform(0.96, 0.99)
            transactions.append(
                self._tx(hub, mule, out_amount, current_time + datetime.timedelta(minutes=self.rng.randint(1, 3)))
            )
            mule_received[mule].append(out_amount)

        # Mules pass funds on to the cash-out agent shortly after
        current_time += datetime.timedelta(minutes=5)
        for mule in mules:
            for amount in mule_received[mule]:
                current_time += datetime.timedelta(minutes=self.rng.randint(2, 6))
                transactions.append(self._tx(mule, cashout, amount * self.rng.uniform(0.95, 0.98), current_time))

        # Part of the money comes back to the hub, closing the loop
        current_time += datetime.timedelta(minutes=20)
        transactions.append(self._tx(cashout, hub, mule_received[mules[0]][0] * 0.9, current_time))
        return transactions

    def generate_hundi_scenario(
        self,
        agent: str = "ACC_HUNDI_AGENT",
        num_funders: int = 2,
        num_families: int = 6,
        base_time: Optional[datetime.datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Hundi (informal remittance) run through an agent wallet, repeated a week apart.

        Local funders send large informal transfers to the agent; within hours the agent pays
        the same families. No licensed inward-remittance transaction is involved.
        """
        if base_time is None:
            base_time = datetime.datetime(2026, 3, 2, 10, 0, 0)
        funders = [f"ACC_HUNDI_FUNDER_{i + 1:02d}" for i in range(num_funders)]
        families = [f"ACC_HUNDI_FAMILY_{i + 1:02d}" for i in range(num_families)]
        transactions: List[Dict[str, Any]] = []
        for cycle in range(2):
            start = base_time + datetime.timedelta(days=7 * cycle)
            pool = 0.0
            for funder in funders:
                for k in range(2):
                    amount = self.rng.uniform(18000.0, 24000.0)
                    pool += amount
                    when = start + datetime.timedelta(minutes=self.rng.randint(0, 90) + 45 * k)
                    transactions.append({**self._tx(funder, agent, amount, when), "tx_type": "send_money",
                                         "location": "Zone-05", "device_id": f"DEV-{funder[4:]}-1"})
            share = pool * 0.95 / num_families
            for family in families:
                when = start + datetime.timedelta(hours=3, minutes=self.rng.randint(0, 240))
                transactions.append({**self._tx(agent, family, share * self.rng.uniform(0.85, 1.15), when), "tx_type": "cash_in",
                                     "location": "Zone-05", "device_id": f"DEV-{agent[4:]}-1"})
        return transactions

    def generate_takeover_scenario(
        self,
        collector: str = "ACC_TKO_COLLECTOR",
        num_victims: int = 3,
        risk_area: str = "Zone-13",
        base_time: Optional[datetime.datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Risk-area account takeover: wallets that always transact from their home area are
        suddenly emptied from a risk area on a new handset, into one collector wallet.

        ACC_TKO_RESIDENT lives in the risk area and transacts there all the time; it must not be flagged.
        """
        if base_time is None:
            base_time = datetime.datetime(2026, 3, 2, 11, 0, 0)
        transactions: List[Dict[str, Any]] = []

        def add(sender, receiver, amount, when, tx_type, area, device):
            transactions.append({**self._tx(sender, receiver, amount, when), "tx_type": tx_type, "location": area, "device_id": device})

        takeover_day = base_time + datetime.timedelta(days=4)
        for i in range(num_victims):
            victim = f"ACC_TKO_VICTIM_{i + 1:02d}"
            home, own = f"Zone-0{i + 2}", f"DEV-{victim[4:]}-1"
            for day in range(4):  # ordinary history from the home area
                when = base_time + datetime.timedelta(days=day, minutes=self.rng.randint(0, 300))
                add(victim, "ACC_TKO_SHOP", self.rng.uniform(150.0, 900.0), when, "payment", home, own)
            when = takeover_day + datetime.timedelta(minutes=20 * i)
            for _ in range(2):
                when += datetime.timedelta(minutes=self.rng.randint(4, 15))
                amount = self.rng.uniform(7000.0, 12000.0)
                add(victim, collector, amount, when, "send_money", risk_area, f"DEV-{victim[4:]}-X7")
                add(collector, "ACC_TKO_AGENT", amount * 0.97, when + datetime.timedelta(minutes=self.rng.randint(5, 20)),
                    "cash_out", risk_area, f"DEV-{collector[4:]}-1")
        for day in range(5):  # a customer who lives in the risk area
            when = base_time + datetime.timedelta(days=day, minutes=self.rng.randint(0, 300))
            add("ACC_TKO_RESIDENT", "ACC_TKO_SHOP", self.rng.uniform(200.0, 1200.0), when, "payment", risk_area, "DEV-TKO_RESIDENT-1")
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
        # Added after the original scenarios so their random draws (and transactions) are unchanged
        all_tx.extend(self.generate_structuring_scenario())
        all_tx.extend(self.generate_mule_ring_scenario())
        # Phase 2 context scenarios (carry tx_type, location and device_id)
        all_tx.extend(self.generate_hundi_scenario())
        all_tx.extend(self.generate_takeover_scenario())

        # Sort chronologically
        all_tx.sort(key=lambda x: x["timestamp"])
        return all_tx


def main() -> None:
    generator = SyntheticDataGenerator(seed=42)
    dataset = generator.generate_comprehensive_dataset()
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "transactions_sample.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2)
    print(f"Generated {len(dataset)} synthetic transactions into {output_path}")


if __name__ == "__main__":
    main()
