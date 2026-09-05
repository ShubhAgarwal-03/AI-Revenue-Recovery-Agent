import argparse
import json
import random
import uuid


DECLINE_CODES = ["insufficient_funds", "do_not_honor", "expired_card", "invalid_cvv", "issuer_timeout", "risk_block", "unknown_code_xyz"]
GATEWAY_ERRORS = ["timeout", "5xx", None, None, None]

GROUND_TRUTH_FOR_DECLINE = {
    "insufficient_funds": "insufficient_funds",
    "do_not_honor": "hard_decline",
    "expired_card": "hard_decline",
    "invalid_cvv": "soft_decline",
    "issuer_timeout": "soft_decline",
    "risk_block": "hard_decline",
    "unknown_code_xyz": "soft_decline",
}


def gen_payment_failure(rng):
    gateway_error = rng.choice(GATEWAY_ERRORS)
    decline_code = None if gateway_error else rng.choice(DECLINE_CODES)
    ground_truth = "gateway_error" if gateway_error else GROUND_TRUTH_FOR_DECLINE[decline_code]
    return {
        "event_type": "payment_failure",
        "amount_inr": round(rng.uniform(200, 15000), 2),
        "customer_id": f"cust_{rng.randint(1, 400)}",
        "decline_code": decline_code,
        "gateway_error": gateway_error,
        "context": {"segment": rng.choice(["retail", "premium", "default"])},
        "ground_truth_category": ground_truth,
    }


def gen_checkout_abandonment(rng):
    return {
        "event_type": "checkout_abandonment",
        "amount_inr": round(rng.uniform(200, 8000), 2),
        "customer_id": f"cust_{rng.randint(1, 400)}",
        "decline_code": None,
        "gateway_error": None,
        "time_of_abandonment_sec": rng.randint(5, 600),
        "context": {"segment": rng.choice(["retail", "premium", "default"])},
        "ground_truth_category": "genuine_abandonment",
    }


def gen_mandate_failure(rng):
    return {
        "event_type": "mandate_failure",
        "amount_inr": round(rng.uniform(500, 5000), 2),
        "customer_id": f"cust_{rng.randint(1, 400)}",
        "decline_code": None,
        "gateway_error": None,
        "context": {"segment": rng.choice(["retail", "premium", "default"])},
        "ground_truth_category": "mandate_expiry",
    }


def gen_overdue_invoice(rng):
    days_overdue = rng.randint(1, 120)
    past_rate = round(rng.uniform(0, 1), 2)
    return {
        "event_type": "overdue_invoice",
        "amount_inr": round(rng.uniform(5000, 200000), 2),
        "customer_id": f"cust_{rng.randint(1, 400)}",
        "decline_code": None,
        "gateway_error": None,
        "context": {
            "segment": "b2b",
            "days_overdue": days_overdue,
            "past_on_time_payment_rate": past_rate,
            "opted_out": rng.random() < 0.05,
        },
        "ground_truth_category": "willful_non_payment",
    }


GENERATORS = [gen_payment_failure, gen_checkout_abandonment, gen_mandate_failure, gen_overdue_invoice]


def generate(n, seed=None):
    rng = random.Random(seed)
    events = []
    for _ in range(n):
        gen = rng.choice(GENERATORS)
        events.append(gen(rng))
    return events


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=120)
    parser.add_argument("--out", type=str, required=True)
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()

    events = generate(args.n, args.seed)
    with open(args.out, "w") as f:
        json.dump(events, f, indent=2)
    print(f"Wrote {len(events)} events to {args.out}")


if __name__ == "__main__":
    main()