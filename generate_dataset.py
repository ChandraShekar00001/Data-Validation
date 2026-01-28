from __future__ import annotations

import random
from pathlib import Path

import numpy as np
import pandas as pd

DOMAINS = [
    "example.com",
    "domain.com",
    "mail.org",
    "company.io",
    "service.net",
]


def synthesize_row(i: int) -> dict:
    # Base valid values
    age = int(np.clip(np.random.normal(loc=35, scale=12), 0, 120))
    user = f"user{i}"
    email = f"{user}@{random.choice(DOMAINS)}"
    salary = int(np.clip(np.random.normal(loc=65000, scale=20000), 0, 200000))

    # Introduce anomalies with ~35% chance, distributed
    r = random.random()
    if r < 0.12:
        age = random.choice([-5, -1, 130, 200])
    elif r < 0.24:
        email = random.choice(["", "bademail", "none@invalid", None])
    elif r < 0.35:
        salary = random.choice([-100, -1, None])

    return {"id": i, "age": age, "email": email, "salary": salary}


def generate(n_rows: int = 1000, output: str | Path = "data/input_large.csv") -> Path:
    rows = [synthesize_row(i) for i in range(1, n_rows + 1)]
    df = pd.DataFrame(rows, columns=["id", "age", "email", "salary"])  # ensure order
    out_path = Path(output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    return out_path


if __name__ == "__main__":
    p = generate()
    print(f"Wrote synthetic dataset to {p}")
