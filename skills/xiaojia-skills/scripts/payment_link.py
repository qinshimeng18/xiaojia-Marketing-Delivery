#!/usr/bin/env python3
import json

from _common import get_marketing_payment_url


def main() -> int:
    print(
        json.dumps(
            {
                "payment_url": get_marketing_payment_url(),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
