import json
import math
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

INPUT_DIR = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
OUTPUT_DIR = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))

LEVELS = [0.05, 0.25, 0.5, 0.75, 0.95]
Z = [-1.645, -0.674, 0.0, 0.674, 1.645]

DIURNAL_PRIOR = {
    1: 1.00,  2: 0.87,  3: 0.75,  4: 0.73,  5: 0.75,  6: 0.79,
    7: 0.80,  8: 0.89,  9: 0.88, 10: 0.91, 11: 0.93, 12: 0.98,
   13: 1.06, 14: 1.18, 15: 1.52, 16: 1.65, 17: 1.77, 18: 1.95,
   19: 2.35, 20: 2.37, 21: 2.33, 22: 2.30, 23: 2.18, 24: 2.04
}

def round2(x: float) -> float | int:
    scaled = x * 100
    whole = math.floor(scaled)
    if scaled - whole >= 0.5:
        whole += 1
    val = whole / 100
    return int(val) if val.is_integer() else val

def compute_comparable_deltas(comparables):
    deltas = {h: [] for h in range(2, 25)}
    for comp in comparables:
        day_start = comp.get("day_start", "")
        if not day_start:
            continue
        prefix = day_start[:10]
        h_map = {}
        for row in comp.get("hourly", []):
            t = row.get("from", "")
            if t.startswith(prefix):
                try:
                    hr = int(t[11:13]) + 1
                    vw = row.get("viewers", 0)
                    if vw > 0:
                        h_map[hr] = vw
                except Exception:
                    pass
        if 1 in h_map and h_map[1] > 0:
            base = h_map[1]
            for h in range(2, 25):
                if h in h_map and h_map[h] > 0:
                    deltas[h].append(math.log(h_map[h]) - math.log(base))
    return deltas

def median(arr):
    if not arr:
        return 0.0
    s = sorted(arr)
    n = len(s)
    mid = n // 2
    if n % 2 == 1:
        return s[mid]
    return (s[mid - 1] + s[mid]) / 2.0

def forecast_case(case: dict, name: str) -> dict:
    if case.get("levels") != LEVELS:
        raise ValueError(f"{name} invalid levels")
    first = next((k for k in case.get("known", []) if k.get("hour") == 1), None)
    if first is None:
        raise ValueError(f"{name} has no hour 1 print")
    p1 = max(1.0, float(first.get("viewers", 1)))

    comparables = case.get("comparables", [])
    deltas = compute_comparable_deltas(comparables)

    hours_output = []
    for row in case.get("forecast", []):
        h = row["hour"]
        vals = deltas.get(h, [])
        
        if len(vals) >= 5:
            med = median(vals)
            mad = median([abs(x - med) for x in vals])
            sigma = max(0.15, min(1.2, 1.4826 * mad))
        else:
            mult = DIURNAL_PRIOR.get(h, 1.0)
            med = math.log(mult)
            sigma = 0.15 * math.sqrt(h - 1)

        q_vals = [max(1.0, p1 * math.exp(med + z * sigma)) for z in Z]

        for i in range(1, len(q_vals)):
            if q_vals[i] < q_vals[i - 1]:
                q_vals[i] = q_vals[i - 1]

        hours_output.append({
            "hour": h,
            "q": [round2(v) for v in q_vals]
        })

    return {"hours": hours_output}

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for path in sorted(INPUT_DIR.glob("*.in")):
        case = json.loads(path.read_text(encoding="utf-8"))
        forecast = forecast_case(case, path.name)
        out_file = OUTPUT_DIR / f"{path.stem}.out"
        out_file.write_text(json.dumps(forecast, separators=(",", ":")) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
