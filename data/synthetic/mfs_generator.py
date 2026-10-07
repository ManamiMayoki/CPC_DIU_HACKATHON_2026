"""Large labelled synthetic MFS (mobile financial services) dataset for model evaluation.

Simulates a Bangladesh-style MFS network: personal wallets, cash-in/cash-out agents and
merchants, with send-money, cash-in, cash-out, merchant-payment, payroll and settlement traffic.
On top of that normal traffic it plants six laundering/fraud typologies and labels every account
a perpetrator controls.

The normal traffic deliberately contains look-alikes of the fraud patterns (payroll fan-out,
merchant fan-in, agents that turn money around quickly, friends settling debts in a loop,
salary earners cashing out within the hour, legitimate near-threshold transfers), because a
detector that has never seen those will look far better on paper than it would in production.

Everything is synthetic. Amounts are in BDT. THRESHOLD is the prototype monitoring threshold
used across this project, not an official regulatory limit.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

THRESHOLD = 10000.0
BASE_TIME = datetime.datetime(2026, 3, 1, 0, 0, 0)

TYPOLOGIES = [
    "mule_ring",
    "digital_hundi",
    "structuring",
    "circular_layering",
    "scam_collection",
    "low_slow_mule_chain",
]

TYPOLOGY_LABELS = {
    "mule_ring": "Mule ring with agent cash-out",
    "digital_hundi": "Digital hundi (informal remittance payout)",
    "structuring": "Structuring under the threshold",
    "circular_layering": "Circular layering",
    "scam_collection": "Scam / betting collection account",
    "low_slow_mule_chain": "Low-and-slow mule chain",
}


@dataclass
class MFSDataset:
    transactions: List[Dict[str, Any]]
    accounts: Dict[str, Dict[str, Any]]
    config: Dict[str, Any] = field(default_factory=dict)

    @property
    def labels(self) -> Dict[str, int]:
        return {acc: info["label"] for acc, info in self.accounts.items()}

    def summary(self) -> Dict[str, Any]:
        by_typology: Dict[str, int] = {}
        by_tier: Dict[str, int] = {}
        for info in self.accounts.values():
            by_tier[info["tier"]] = by_tier.get(info["tier"], 0) + 1
            if info["label"]:
                by_typology[info["typology"]] = by_typology.get(info["typology"], 0) + 1
        suspicious = sum(by_typology.values())
        return {
            "transactions": len(self.transactions),
            "accounts": len(self.accounts),
            "suspicious_accounts": suspicious,
            "suspicious_rate": round(suspicious / max(len(self.accounts), 1), 4),
            "accounts_by_tier": by_tier,
            "suspicious_by_typology": by_typology,
            "total_volume_bdt": round(sum(t["amount"] for t in self.transactions), 2),
            "days": self.config.get("n_days"),
        }


class MFSNetworkGenerator:
    """Generates the labelled network. One seed gives one fully reproducible dataset."""

    def __init__(
        self,
        seed: int = 7,
        n_personal: int = 6000,
        n_agents: int = 240,
        n_merchants: int = 320,
        n_days: int = 14,
        fraud_scale: float = 1.0,
        exclude_typologies: Optional[List[str]] = None,
    ) -> None:
        self.rng = np.random.default_rng(seed)
        self.seed = seed
        self.n_days = n_days
        self.fraud_scale = fraud_scale
        self.exclude = set(exclude_typologies or [])
        self.horizon = n_days * 86400

        self.personal = [f"ACC_P_{i:06d}" for i in range(n_personal)]
        self.agents = [f"ACC_AGENT_{i:04d}" for i in range(n_agents)]
        self.merchants = [f"ACC_MERCH_{i:04d}" for i in range(n_merchants)]
        n_corp = max(6, n_personal // 240)
        self.corporates = [f"ACC_MERCH_CORP_{i:03d}" for i in range(n_corp)]

        self.n_districts = 14
        self.accounts: Dict[str, Dict[str, Any]] = {}
        for group, tier in ((self.personal, "personal"), (self.agents, "agent"),
                            (self.merchants, "merchant"), (self.corporates, "merchant")):
            for acc in group:
                self.accounts[acc] = {
                    "tier": tier,
                    "district": int(self.rng.integers(0, self.n_districts)),
                    "label": 0,
                    "typology": None,
                    "role": None,
                    "evasive": False,
                }
        self.by_district: Dict[str, Dict[int, List[str]]] = {"personal": {}, "agent": {}, "merchant": {}}
        for acc, info in self.accounts.items():
            if acc in self.corporates:
                continue
            self.by_district[info["tier"]].setdefault(info["district"], []).append(acc)

        self.tx: List[Tuple[float, str, str, float, str]] = []
        self._used_for_fraud: set = set()

    # ------------------------------------------------------------------ helpers
    def _add(self, t: float, sender: str, receiver: str, amount: float, tx_type: str) -> None:
        if sender == receiver or amount <= 0 or not (0 <= t < self.horizon):
            return
        self.tx.append((float(t), sender, receiver, round(float(amount), 2), tx_type))

    def _daytime(self, n: int = 1) -> np.ndarray:
        """Random times with a daytime peak (most activity 09:00-22:00, a little at night)."""
        day = self.rng.integers(0, self.n_days, n)
        night = self.rng.random(n) < 0.04
        hour = np.where(night, self.rng.uniform(0, 6, n), np.clip(self.rng.normal(15.5, 3.6, n), 6.0, 23.99))
        return day * 86400 + hour * 3600

    def _amount(self, median: float, sigma: float, low: float, high: float, n: int = 1) -> np.ndarray:
        raw = self.rng.lognormal(np.log(median), sigma, n)
        raw = np.clip(raw, low, high)
        rounded = self.rng.random(n) < 0.45
        return np.where(rounded, np.maximum(np.round(raw / 50) * 50, low), np.round(raw, 2))

    def _local(self, tier: str, district: int) -> List[str]:
        pool = self.by_district[tier].get(district)
        return pool if pool else self.by_district[tier][next(iter(self.by_district[tier]))]

    def _pick_clean_personal(self, n: int) -> List[str]:
        picked: List[str] = []
        while len(picked) < n:
            acc = self.personal[int(self.rng.integers(0, len(self.personal)))]
            if acc not in self._used_for_fraud:
                self._used_for_fraud.add(acc)
                picked.append(acc)
        return picked

    def _victims(self, n: int) -> List[str]:
        idx = self.rng.choice(len(self.personal), size=n, replace=False)
        return [self.personal[i] for i in idx if self.personal[i] not in self._used_for_fraud]

    def _mark(self, acc: str, typology: str, role: str, evasive: bool = False) -> None:
        self._used_for_fraud.add(acc)
        self.accounts[acc].update({"label": 1, "typology": typology, "role": role, "evasive": evasive})

    def _start(self, margin_hours: float = 60.0) -> float:
        day = self.rng.integers(0, max(1, self.n_days - int(margin_hours // 24) - 1))
        return float(day * 86400 + self.rng.uniform(8, 21) * 3600)

    # ------------------------------------------------------------ normal traffic
    def _normal_traffic(self) -> None:
        rng = self.rng
        scale = self.n_days / 14.0
        for acc in self.personal:
            district = self.accounts[acc]["district"]
            local_people = self._local("personal", district)
            n_contacts = int(rng.integers(2, 7))
            contacts = [
                local_people[int(rng.integers(0, len(local_people)))] if rng.random() < 0.8
                else self.personal[int(rng.integers(0, len(self.personal)))]
                for _ in range(n_contacts)
            ]
            activity = rng.lognormal(0.0, 0.6)

            n_p2p = rng.poisson(3.2 * activity * scale)
            for t, amount in zip(self._daytime(n_p2p), self._amount(900, 0.9, 20, 25000, n_p2p)):
                self._add(t, acc, contacts[int(rng.integers(0, n_contacts))], amount, "send_money")

            local_agents = self._local("agent", district)
            home_agents = [local_agents[int(rng.integers(0, len(local_agents)))] for _ in range(2)]
            n_in = rng.poisson(1.3 * activity * scale)
            for t, amount in zip(self._daytime(n_in), self._amount(2500, 0.8, 100, 30000, n_in)):
                self._add(t, home_agents[int(rng.integers(0, 2))], acc, amount, "cash_in")
            n_out = rng.poisson(1.3 * activity * scale)
            for t, amount in zip(self._daytime(n_out), self._amount(3000, 0.8, 100, 30000, n_out)):
                self._add(t, acc, home_agents[int(rng.integers(0, 2))], amount, "cash_out")

            local_merchants = self._local("merchant", district)
            n_pay = rng.poisson(2.6 * activity * scale)
            # a few popular shops take most payments
            ranks = np.minimum(rng.zipf(1.6, n_pay) - 1, len(local_merchants) - 1)
            for t, amount, rank in zip(self._daytime(n_pay), self._amount(450, 0.8, 20, 15000, n_pay), ranks):
                self._add(t, acc, local_merchants[int(rank)], amount, "payment")

        # Payroll: one employer pays many wallets in a short burst (legitimate fan-out), and many
        # employees cash most of it out within hours (legitimate rapid movement).
        for corp in self.corporates:
            staff_n = int(rng.integers(20, 80))
            staff = [self.personal[i] for i in rng.choice(len(self.personal), size=staff_n, replace=False)]
            for payday in (1, 8) if self.n_days >= 10 else (1,):
                start = payday * 86400 + rng.uniform(9, 17) * 3600
                for worker in staff:
                    salary = float(np.round(rng.uniform(6500, 24000) / 500) * 500)
                    t = start + rng.uniform(0, 1800)
                    self._add(t, corp, worker, salary, "salary")
                    if rng.random() < 0.4:
                        agents = self._local("agent", self.accounts[worker]["district"])
                        self._add(t + rng.uniform(600, 6 * 3600), worker, agents[int(rng.integers(0, len(agents)))],
                                  salary * rng.uniform(0.6, 0.97), "cash_out")
                    elif rng.random() < 0.3:
                        family = self.personal[int(rng.integers(0, len(self.personal)))]
                        self._add(t + rng.uniform(900, 5 * 3600), worker, family, salary * rng.uniform(0.3, 0.8), "send_money")

        # Remittance households: regular near-threshold cash-ins, partly passed on to family.
        for acc_i in rng.choice(len(self.personal), size=max(1, len(self.personal) // 40), replace=False):
            acc = self.personal[acc_i]
            agents = self._local("agent", self.accounts[acc]["district"])
            agent = agents[int(rng.integers(0, len(agents)))]
            family = self.personal[int(rng.integers(0, len(self.personal)))]
            for week in range(max(1, self.n_days // 7)):
                for _ in range(int(rng.integers(1, 3))):
                    t = week * 7 * 86400 + rng.uniform(1, 6) * 86400 + rng.uniform(9, 20) * 3600
                    amount = rng.uniform(0.86, 0.995) * THRESHOLD
                    self._add(t, agent, acc, amount, "cash_in")
                    if rng.random() < 0.5:
                        self._add(t + rng.uniform(300, 3 * 3600), acc, family, amount * rng.uniform(0.4, 0.9), "send_money")

        # Friends settling shared expenses in a loop (legitimate small cycles).
        for _ in range(max(4, len(self.personal) // 150)):
            group = [self.personal[i] for i in rng.choice(len(self.personal), size=int(rng.integers(3, 5)), replace=False)]
            t = float(self._daytime(1)[0])
            amount = float(rng.uniform(300, 2500))
            for i, member in enumerate(group):
                t += rng.uniform(600, 5 * 3600)
                self._add(t, member, group[(i + 1) % len(group)], amount * rng.uniform(0.85, 1.1), "send_money")

        # Merchants settle to suppliers; agents rebalance float with distributors (large legitimate transfers).
        for merchant in self.merchants:
            supplier = self.corporates[int(rng.integers(0, len(self.corporates)))]
            for day in range(self.n_days):
                if rng.random() < 0.35:
                    self._add(day * 86400 + rng.uniform(20, 23.5) * 3600, merchant, supplier,
                              float(rng.uniform(4000, 60000)), "settlement")
        for agent in self.agents:
            distributor = self.corporates[int(rng.integers(0, len(self.corporates)))]
            for day in range(self.n_days):
                if rng.random() < 0.3:
                    self._add(day * 86400 + rng.uniform(9, 12) * 3600, distributor, agent,
                              float(rng.uniform(20000, 150000)), "float_topup")
                if rng.random() < 0.25:
                    self._add(day * 86400 + rng.uniform(19, 23) * 3600, agent, distributor,
                              float(rng.uniform(20000, 120000)), "float_return")

    # ------------------------------------------------------------------- fraud
    def _mule_ring(self) -> None:
        rng = self.rng
        n_mules = int(rng.integers(3, 7))
        collector, *mules = self._pick_clean_personal(1 + n_mules)
        self._mark(collector, "mule_ring", "collector")
        for m in mules:
            self._mark(m, "mule_ring", "mule")
        agents = self._local("agent", self.accounts[collector]["district"])
        if rng.random() < 0.7:
            agent = agents[int(rng.integers(0, len(agents)))]
            if self.accounts[agent]["label"] == 0:
                self._mark(agent, "mule_ring", "complicit_agent")
            cash_agents = [agent]
        else:
            cash_agents = [self.agents[int(rng.integers(0, len(self.agents)))] for _ in range(2)]
        t = self._start()
        for i, victim in enumerate(self._victims(int(rng.integers(5, 13)))):
            t += rng.uniform(120, 1500)
            amount = float(rng.uniform(2000, 24000))
            self._add(t, victim, collector, amount, "send_money")
            mule = mules[i % n_mules]
            t_fwd = t + rng.uniform(60, 600)
            forwarded = amount * rng.uniform(0.94, 0.99)
            self._add(t_fwd, collector, mule, forwarded, "send_money")
            self._add(t_fwd + rng.uniform(300, 2400), mule, cash_agents[int(rng.integers(0, len(cash_agents)))],
                      forwarded * rng.uniform(0.95, 0.99), "cash_out")

    def _digital_hundi(self) -> None:
        rng = self.rng
        n_feeders = int(rng.integers(2, 4))
        operator, *feeders = self._pick_clean_personal(1 + n_feeders)
        self._mark(operator, "digital_hundi", "operator")
        for f in feeders:
            self._mark(f, "digital_hundi", "feeder")
        t0 = self._start()
        pool = 0.0
        for feeder in feeders:
            for _ in range(int(rng.integers(3, 7))):
                amount = float(rng.uniform(12000, 25000))
                self._add(t0 + rng.uniform(0, 8 * 3600), feeder, operator, amount, "send_money")
                pool += amount
        beneficiaries = self._victims(int(rng.integers(10, 30)))
        share = pool * 0.96 / max(len(beneficiaries), 1)
        for b in beneficiaries:
            t = t0 + 8 * 3600 + rng.uniform(600, 6 * 3600)
            amount = share * rng.uniform(0.7, 1.3)
            self._add(t, operator, b, amount, "send_money")
            if rng.random() < 0.6:
                agents = self._local("agent", self.accounts[b]["district"])
                self._add(t + rng.uniform(900, 8 * 3600), b, agents[int(rng.integers(0, len(agents)))], amount * 0.97, "cash_out")

    def _structuring(self, evasive: bool) -> None:
        rng = self.rng
        if not evasive:
            n_recv = int(rng.integers(1, 3))
            source, *receivers = self._pick_clean_personal(1 + n_recv)
            self._mark(source, "structuring", "splitter")
            for r in receivers:
                self._mark(r, "structuring", "collector")
            t = self._start()
            for _ in range(int(rng.integers(4, 9))):
                t += rng.uniform(900, 5400)
                receiver = receivers[int(rng.integers(0, n_recv))]
                amount = rng.uniform(0.86, 0.995) * THRESHOLD
                self._add(t, source, receiver, amount, "send_money")
                if rng.random() < 0.6:
                    agents = self._local("agent", self.accounts[receiver]["district"])
                    self._add(t + rng.uniform(900, 4 * 3600), receiver, agents[int(rng.integers(0, len(agents)))], amount * 0.97, "cash_out")
            return
        # Evasive: amounts well under the near-threshold band, spread over days and receivers,
        # then consolidated with one beneficiary.
        n_recv = int(rng.integers(3, 5))
        source, beneficiary, *receivers = self._pick_clean_personal(2 + n_recv)
        self._mark(source, "structuring", "splitter", True)
        self._mark(beneficiary, "structuring", "beneficiary", True)
        for r in receivers:
            self._mark(r, "structuring", "collector", True)
        t = self._start(96)
        for _ in range(int(rng.integers(7, 13))):
            t += rng.uniform(2 * 3600, 9 * 3600)
            receiver = receivers[int(rng.integers(0, n_recv))]
            amount = rng.uniform(0.58, 0.83) * THRESHOLD
            self._add(t, source, receiver, amount, "send_money")
            self._add(t + rng.uniform(2 * 3600, 12 * 3600), receiver, beneficiary, amount * rng.uniform(0.95, 0.99), "send_money")

    def _circular(self, evasive: bool) -> None:
        rng = self.rng
        members = self._pick_clean_personal(int(rng.integers(3, 7)))
        for m in members:
            self._mark(m, "circular_layering", "loop_member", evasive)
        t = self._start()
        amount = float(rng.uniform(5000, 22000))
        for _ in range(int(rng.integers(1, 4))):
            for i, member in enumerate(members):
                t += rng.uniform(3 * 3600, 10 * 3600) if evasive else rng.uniform(300, 2400)
                amount *= rng.uniform(0.93, 0.99)
                self._add(t, member, members[(i + 1) % len(members)], amount, "send_money")
            t += rng.uniform(3600, 20 * 3600)

    def _scam_collection(self) -> None:
        rng = self.rng
        collector, boss = self._pick_clean_personal(2)
        self._mark(collector, "scam_collection", "collector")
        self._mark(boss, "scam_collection", "boss")
        t0 = self._start(72)
        duration = rng.uniform(8, 40) * 3600
        balance = 0.0
        events = sorted(float(t0 + rng.uniform(0, duration)) for _ in self._victims(int(rng.integers(15, 60))))
        agents = [self.agents[int(rng.integers(0, len(self.agents)))] for _ in range(2)]
        victims = self._victims(len(events) + 5)
        last_sweep = t0
        for i, t in enumerate(events):
            if i >= len(victims):
                break
            amount = float(rng.uniform(300, 3000))
            self._add(t, victims[i], collector, amount, "send_money")
            balance += amount
            if balance > rng.uniform(6000, 14000) and t - last_sweep > 1800:
                sweep_t = t + rng.uniform(120, 1800)
                self._add(sweep_t, collector, agents[int(rng.integers(0, 2))], balance * 0.6, "cash_out")
                self._add(sweep_t + rng.uniform(60, 900), collector, boss, balance * 0.35, "send_money")
                balance *= 0.05
                last_sweep = t
        if balance > 500:
            self._add(events[-1] + 1200, collector, boss, balance * 0.9, "send_money")

    def _low_slow_chain(self) -> None:
        rng = self.rng
        mules = self._pick_clean_personal(int(rng.integers(6, 11)))
        for m in mules:
            self._mark(m, "low_slow_mule_chain", "mule", True)
        for _ in range(int(rng.integers(6, 16))):
            path_len = int(rng.integers(3, 5))
            path = [mules[i] for i in rng.choice(len(mules), size=path_len, replace=False)]
            source = self._victims(1)
            if not source:
                continue
            t = self._start(72)
            amount = float(rng.uniform(2000, 7000))
            hops = [source[0]] + path
            for a, b in zip(hops[:-1], hops[1:]):
                self._add(t, a, b, amount, "send_money")
                t += rng.uniform(1.5 * 3600, 8 * 3600)
                amount *= rng.uniform(0.95, 1.0)
            agents = self._local("agent", self.accounts[path[-1]]["district"])
            self._add(t, path[-1], agents[int(rng.integers(0, len(agents)))], amount, "cash_out")

    def _fraud_traffic(self) -> None:
        size = len(self.personal) / 6000.0 * self.fraud_scale
        plan = [
            ("mule_ring", 14, self._mule_ring),
            ("digital_hundi", 8, self._digital_hundi),
            ("structuring", 9, lambda: self._structuring(False)),
            ("structuring", 8, lambda: self._structuring(True)),
            ("circular_layering", 9, lambda: self._circular(False)),
            ("circular_layering", 6, lambda: self._circular(True)),
            ("scam_collection", 10, self._scam_collection),
            ("low_slow_mule_chain", 7, self._low_slow_chain),
        ]
        for typology, count, make in plan:
            if typology in self.exclude:
                continue
            for _ in range(max(1, int(round(count * size)))):
                make()

    # ------------------------------------------------------------------- build
    def generate(self) -> MFSDataset:
        self._fraud_traffic()  # fraud first so perpetrators also get ordinary activity as cover
        self._normal_traffic()
        self.tx.sort(key=lambda row: row[0])
        transactions = []
        seen = set()
        for i, (t, sender, receiver, amount, tx_type) in enumerate(self.tx, start=1):
            seen.add(sender)
            seen.add(receiver)
            transactions.append({
                "transaction_id": f"TX_{i:08d}",
                "sender_id": sender,
                "receiver_id": receiver,
                "amount": amount,
                "timestamp": (BASE_TIME + datetime.timedelta(seconds=int(t))).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "tx_type": tx_type,
            })
        accounts = {acc: info for acc, info in self.accounts.items() if acc in seen}
        return MFSDataset(
            transactions=transactions,
            accounts=accounts,
            config={
                "seed": self.seed,
                "n_days": self.n_days,
                "n_personal": len(self.personal),
                "n_agents": len(self.agents),
                "n_merchants": len(self.merchants) + len(self.corporates),
                "threshold_bdt": THRESHOLD,
                "excluded_typologies": sorted(self.exclude),
            },
        )


def generate_mfs_dataset(seed: int = 7, **kwargs: Any) -> MFSDataset:
    return MFSNetworkGenerator(seed=seed, **kwargs).generate()


if __name__ == "__main__":
    import json

    print(json.dumps(generate_mfs_dataset().summary(), indent=2))
