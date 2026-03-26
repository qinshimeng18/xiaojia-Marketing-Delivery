#!/usr/bin/env python3
import unittest

from _common import get_marketing_payment_url


class MarketingPaymentUrlTests(unittest.TestCase):
    def test_returns_fixed_marketing_url(self):
        self.assertEqual(
            get_marketing_payment_url(),
            "https://dev.justailab.xyz/marketing",
        )


if __name__ == "__main__":
    unittest.main()
