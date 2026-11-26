"""Every (observed, desired, expired) combination allowed by the schema CHECK lists."""

import itertools
import unittest

from services.runner.state import DESIRED, OBSERVED, Work, decide

ACTIONS_7_6 = {"env.provisioned", "env.stopped", "env.destroyed", "env.expired", "env.failed"}
KINDS_6 = {"env.state_changed": "info", "env.failed": "warn", "env.expired": "info"}


class Decide(unittest.TestCase):
    def test_table(self) -> None:
        cases = {
            ("requested", "running", False): ("running", "env.provisioned"),
            ("provisioning", "running", False): ("running", "env.provisioned"),
            ("running", "running", False): None,
            ("requested", "stopped", False): ("stopped", "env.stopped"),
            ("running", "stopped", False): ("stopped", "env.stopped"),
            ("stopped", "stopped", False): None,
            ("stopped", "running", False): None,  # no start operation exists in the API
            ("running", "destroyed", False): ("destroyed", "env.destroyed"),
            ("failed", "destroyed", False): ("destroyed", "env.destroyed"),
            ("running", "running", True): ("destroyed", "env.expired"),
            ("stopped", "stopped", True): ("destroyed", "env.expired"),
            ("failed", "running", True): ("destroyed", "env.expired"),
            ("failed", "running", False): None,
            ("destroyed", "destroyed", True): None,
            ("running", "destroyed", True): ("destroyed", "env.destroyed"),  # explicit destroy wins
        }
        for (o, d, e), want in cases.items():
            step = decide(o, d, e)
            got = None if step is None else (step.target_state, step.audit_action)
            self.assertEqual(got, want, (o, d, e))

    def test_every_combination_is_closed_list(self) -> None:
        for o, d, e in itertools.product(OBSERVED, DESIRED, (False, True)):
            step = decide(o, d, e)
            if step is None:
                continue
            self.assertIn(step.audit_action, ACTIONS_7_6)
            self.assertEqual(step.activity[0], ("env.state_changed", "info"))
            for kind, sev in step.activity:
                self.assertEqual(KINDS_6[kind], sev)
            if step.target_state == "destroyed":
                self.assertIs(step.work, Work.DESTROY)
        self.assertIsNone(decide("destroyed", "running", False))

    def test_rejects_unknown_states(self) -> None:
        with self.assertRaises(ValueError):
            decide("deleted", "running", False)
        with self.assertRaises(ValueError):
            decide("running", "paused", False)


if __name__ == "__main__":
    unittest.main()
