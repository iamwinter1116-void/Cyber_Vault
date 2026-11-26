"""Template validation and limit split. The digests below are test inputs, not real images."""

import copy
import unittest

from services.runner.launch import EnvRow, ProfileError
from services.runner.templates import container_specs, parse_template, split

D1, D2 = "sha256:" + "1" * 64, "sha256:" + "2" * 64
APP = {
    "name": "app-target",
    "title": "Vulnerable web application",
    "description": "[T0.H2.N2] target plus toolbox on one internal network",
    "sizes": ["S", "M", "L"],
    "containers": [
        {"name": "target", "image": D1, "share_pct": 60},
        {"name": "toolbox", "image": D2, "share_pct": 40, "command": ["sleep", "infinity"]},
    ],
}


def env(size_cpu: int, size_mem: int, template: str = "app-target") -> EnvRow:
    return EnvRow("e", "t", template, size_cpu, size_mem, 128, 128)


class Parse(unittest.TestCase):
    def bad(self, mutate: object) -> None:
        d = copy.deepcopy(APP)
        mutate(d)  # type: ignore[operator]
        with self.assertRaises(ProfileError):
            parse_template(d)

    def test_valid(self) -> None:
        t = parse_template(APP)
        self.assertEqual([c.name for c in t.containers], ["target", "toolbox"])
        self.assertEqual(t.containers[1].command, ("sleep", "infinity"))

    def test_refusals(self) -> None:
        self.bad(lambda d: d.update(description="target plus toolbox"))  # no D12 profile
        self.bad(lambda d: d.update(name="custom"))
        self.bad(lambda d: d.update(extra=1))
        self.bad(lambda d: d.update(sizes=["XL"]))
        self.bad(lambda d: d.update(sizes=[]))
        self.bad(lambda d: d["containers"][0].update(image="nginx:latest"))
        self.bad(lambda d: d["containers"][0].update(share_pct=70))  # sums to 110
        self.bad(lambda d: d["containers"][0].update(privileged=True))  # unknown key
        self.bad(lambda d: d["containers"][0].update(network="host"))
        self.bad(lambda d: d["containers"][1].update(name="shell"))
        self.bad(lambda d: d["containers"].pop())
        self.bad(lambda d: d["containers"][1].update(command="sleep infinity"))

    def test_file_analysis_requires_network_none(self) -> None:
        fa = {"name": "file-analysis", "title": "f", "description": "[T0.H2.N2] f", "sizes": ["S"],
              "containers": [{"name": "analyzer", "image": D1, "share_pct": 50, "network": "none"},
                             {"name": "detonator", "image": D2, "share_pct": 50, "network": "env"}]}
        with self.assertRaises(ProfileError):
            parse_template(fa)
        fa["containers"][1]["network"] = "none"  # type: ignore[index]
        self.assertTrue(all(c.network_none for c in parse_template(fa).containers))


class Split(unittest.TestCase):
    def test_sizes_sum_exactly(self) -> None:
        t = parse_template(APP)
        for cpu, mem in ((500, 256), (1000, 512), (2000, 1024)):  # S, M, L of section 4
            specs = container_specs(t, env(cpu, mem))
            self.assertEqual(sum(s.cpu_millis for s in specs), cpu)
            self.assertEqual(sum(s.mem_mb for s in specs), mem)
        s = container_specs(t, env(500, 256))
        self.assertEqual([(x.cpu_millis, x.mem_mb) for x in s], [(300, 153), (200, 103)])

    def test_refuses_zero_part_and_wrong_template(self) -> None:
        with self.assertRaises(ProfileError):
            split(1, [60, 40])
        with self.assertRaises(ProfileError):
            container_specs(parse_template(APP), env(500, 256, "ai-redteam"))


if __name__ == "__main__":
    unittest.main()
