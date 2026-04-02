#!/usr/bin/env python3
import unittest

from _common import build_marketing_conversation_url, get_marketing_payment_url


class MarketingPaymentUrlTests(unittest.TestCase):
    def test_returns_fixed_marketing_url(self):
        self.assertEqual(
            get_marketing_payment_url(),
            "https://justailab.com/pages/agent/preview",
        )

    def test_builds_marketing_conversation_url(self):
        self.assertEqual(
            build_marketing_conversation_url("c7d34bf0-0bd5-4b2c-acd2-5dc2adf729b9"),
            "https://justailab.com/pages/agent/preview?conversation_id=c7d34bf0-0bd5-4b2c-acd2-5dc2adf729b9",
        )


if __name__ == "__main__":
    unittest.main()
