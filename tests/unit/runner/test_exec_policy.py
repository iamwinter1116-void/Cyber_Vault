"""Exec job rules (services/runner/exec_policy.py). No Docker: the in-sandbox run of a hostile command, the
70 s sleep and the 200000-byte output need the Linux host (B5 done-when)."""

import unittest

from services.runner import exec_policy as ep
from services.runner.launch import EnvRow

APP = EnvRow("0b6f0c1e-1111-4222-8333-444455556666", "7d2a4f00-aaaa-4bbb-8ccc-dddddddddddd", "app-target",
             500, 256, 128, 128)
FILES = EnvRow(APP.id, APP.team_id, "file-analysis", 500, 256, 128, 128)
HOSTILE = "a'b\"c; rm -rf / ; `id` $(whoami) && echo \\$HOME | cat > /tmp/x\n# end"


class Argv(unittest.TestCase):
    def test_hostile_command_is_one_argument_inside_the_sandbox(self) -> None:
        argv = ep.exec_argv(HOSTILE)
        self.assertEqual(argv, ["timeout", "-s", "KILL", "60", "sh", "-c", HOSTILE])
        self.assertIs(argv[-1], HOSTILE)  # passed through untouched, never joined or quoted into a host string

    def test_target_resolves_this_envs_container(self) -> None:
        self.assertEqual(ep.target(APP, "running", {"command": HOSTILE, "container": "toolbox"}),
                         (f"abh-{APP.id}-toolbox", HOSTILE))
        self.assertEqual(ep.target(APP, "running", {"command": "id", "container": "target"})[0], f"abh-{APP.id}-target")
        self.assertEqual(ep.target(APP, "running", {"command": "id"})[0], f"abh-{APP.id}-toolbox")  # R17 default

    def test_target_refusals(self) -> None:
        for env, observed, data in (
            (APP, "stopped", {"command": "id"}),
            (APP, "provisioning", {"command": "id"}),
            (APP, "running", {"command": "id", "container": "analyzer"}),
            (FILES, "running", {"command": "id", "container": "toolbox"}),
            (APP, "running", {"command": "id", "container": "../x"}),
            (APP, "running", {"command": "id", "container": 7}),
            (APP, "running", {"command": ""}),
            (APP, "running", {"command": "x" * 4097}),
            (APP, "running", {"command": ["sh", "-c", "id"]}),
            (APP, "running", {}),
        ):
            with self.assertRaises(ValueError):
                ep.target(env, observed, data)
        self.assertEqual(len(ep.target(APP, "running", {"command": "x" * 4096})[1]), 4096)


class Output(unittest.TestCase):
    def test_cap_and_truncated_flag(self) -> None:
        out, truncated = ep.clean_output(b"a" * 65536, True)  # caller read more than it kept
        self.assertEqual((len(out.encode()), truncated), (65536, True))
        self.assertEqual(ep.clean_output(b"hello\n", False), ("hello\n", False))

    def test_never_more_than_cap_bytes_of_valid_utf8(self) -> None:
        for data in (b"\xff" * 65536, ("é" * 40000).encode()[:65535], b"\x00" * 10):
            out, _ = ep.clean_output(data, False)
            self.assertLessEqual(len(out.encode("utf-8")), ep.OUTPUT_CAP)
            self.assertNotIn("\x00", out)  # jsonb rejects U+0000
        self.assertEqual(ep.clean_output(b"\xff" * 65536, False)[1], True)  # replacement grew past the cap


class Status(unittest.TestCase):
    def test_status_rules(self) -> None:
        self.assertEqual(ep.status(0, 10, False), "done")
        self.assertEqual(ep.status(2, 10, False), "done")  # a failing command still finished
        self.assertEqual(ep.status(137, 60_000, False), "timeout")  # timeout -s KILL fired
        self.assertEqual(ep.status(137, 500, False), "done")  # killed early (e.g. OOM), not the deadline
        self.assertEqual(ep.status(None, 100, False), "error")
        self.assertEqual(ep.status(None, 65_500, True), "timeout")


if __name__ == "__main__":
    unittest.main()
