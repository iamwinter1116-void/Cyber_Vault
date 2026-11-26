"""Section 8 profile as produced by build_create_kwargs. Local policy check only: T-ISO-02 needs docker inspect."""

import unittest

from services.runner.launch import (
    ContainerSpec,
    EnvRow,
    IsolationUnavailable,
    ProfileError,
    build_create_kwargs,
    choose_runtime,
    network_create_kwargs,
)

ENV = EnvRow("0b6f0c1e-1111-4222-8333-444455556666", "7d2a4f00-aaaa-4bbb-8ccc-dddddddddddd", "app-target",
             500, 256, 128, 128)
IMG = "sha256:" + "ab" * 32
VOL = {"Target": "/workspace", "Source": f"abh-vol-{ENV.id}", "Type": "volume", "ReadOnly": False}
GV = choose_runtime("runsc", {"runc", "runsc"}, allow_degraded=False)


def spec(**kw: object) -> ContainerSpec:
    base: dict[str, object] = {"name": "target", "image": IMG, "cpu_millis": 300, "mem_mb": 153}
    base.update(kw)
    return ContainerSpec(**base)  # type: ignore[arg-type]


class ProfileRows(unittest.TestCase):
    def setUp(self) -> None:
        self.k = build_create_kwargs(ENV, spec(), GV, VOL)

    def test_runtime_user_caps_privilege(self) -> None:
        self.assertEqual(self.k["runtime"], "runsc")
        self.assertEqual(self.k["user"], "1000:1000")
        self.assertEqual(self.k["cap_drop"], ["ALL"])
        self.assertNotIn("cap_add", self.k)
        self.assertEqual(self.k["security_opt"], ["no-new-privileges"])
        self.assertIs(self.k["privileged"], False)
        for absent in ("devices", "pid_mode", "ipc_mode", "uts_mode", "userns_mode", "ports", "publish_all_ports",
                       "volumes", "cap_add"):
            self.assertNotIn(absent, self.k)

    def test_filesystem_and_mounts(self) -> None:
        self.assertIs(self.k["read_only"], True)
        self.assertEqual(self.k["tmpfs"], {"/tmp": "rw,noexec,nosuid,size=64m"})
        self.assertEqual(self.k["mounts"], [VOL])

    def test_limits(self) -> None:
        self.assertEqual(self.k["nano_cpus"], 300 * 1_000_000)
        self.assertEqual(self.k["mem_limit"], "153m")
        self.assertEqual(self.k["memswap_limit"], "153m")
        self.assertEqual(self.k["pids_limit"], 128)

    def test_network_labels_names(self) -> None:
        self.assertEqual(self.k["network"], f"abh-env-{ENV.id}")
        self.assertNotIn("network_mode", self.k)
        self.assertEqual(self.k["name"], f"abh-{ENV.id}-target")
        self.assertEqual(self.k["image"], IMG)
        self.assertEqual(self.k["labels"], {"abh.managed": "true", "abh.env_id": ENV.id,
                                            "abh.team_id": ENV.team_id, "abh.template": "app-target"})

    def test_network_none_for_detonation(self) -> None:
        k = build_create_kwargs(ENV, spec(network_none=True), GV, VOL)
        self.assertEqual(k["network_mode"], "none")
        self.assertNotIn("network", k)

    def test_env_network(self) -> None:
        n = network_create_kwargs(ENV)
        self.assertEqual(n["name"], f"abh-env-{ENV.id}")
        self.assertEqual(n["driver"], "bridge")
        self.assertIs(n["internal"], True)
        self.assertEqual(n["options"], {"com.docker.network.bridge.gateway_mode_ipv4": "isolated"})
        self.assertEqual(n["labels"]["abh.managed"], "true")


class Refusals(unittest.TestCase):
    def refuse(self, s: ContainerSpec, ws: dict[str, object] = VOL) -> None:
        with self.assertRaises(ProfileError):
            build_create_kwargs(ENV, s, GV, ws)

    def test_image_must_be_digest(self) -> None:
        for image in ("busybox", "busybox:latest", "sha256:abc", "Busybox@sha256:" + "0" * 64):
            self.refuse(spec(image=image))
        build_create_kwargs(ENV, spec(image="reg/x:1@sha256:" + "0" * 64), GV, VOL)

    def test_no_abh_variables(self) -> None:
        self.refuse(spec(env={"ABH_DB_DSN": "postgresql://x"}))
        self.refuse(spec(env={"abh_x": "1"}))

    def test_bad_limits(self) -> None:
        self.refuse(spec(cpu_millis=0))
        self.refuse(spec(mem_mb=-1))
        self.refuse(spec(cpu_millis=True))

    def test_workspace_never_a_host_directory(self) -> None:
        self.refuse(spec(), {"Target": "/workspace", "Source": "/etc", "Type": "bind", "ReadOnly": False})
        self.refuse(spec(), {"Target": "/", "Source": "v", "Type": "volume"})
        self.refuse(spec(), {**VOL, "Source": "abh-vol-other-env"})
        self.refuse(spec(), {**VOL, "BindOptions": {}})
        self.refuse(spec(), {"Target": "/workspace", "Type": "tmpfs", "Options": "size=16m"})  # no uid/gid
        self.refuse(spec(), {"Target": "/workspace", "Type": "tmpfs", "Options": "size=16m,uid=1000,gid=1000,exec"})

    def test_tmpfs_workspace_v3(self) -> None:
        ws = {"Target": "/workspace", "Type": "tmpfs", "Options": "size=128m,uid=1000,gid=1000"}
        k = build_create_kwargs(ENV, spec(), GV, ws)
        self.assertEqual(k["mounts"], [])
        self.assertEqual(k["tmpfs"], {"/tmp": "rw,noexec,nosuid,size=64m", "/workspace": "size=128m,uid=1000,gid=1000"})

    def test_bad_container_name(self) -> None:
        self.refuse(spec(name="../x"))


class Runtime(unittest.TestCase):
    def test_runsc_is_gvisor(self) -> None:
        self.assertEqual((GV.runtime, GV.isolation_tier, GV.degraded), ("runsc", "gvisor", False))

    def test_refuses_without_runsc_by_default(self) -> None:
        with self.assertRaises(IsolationUnavailable):
            choose_runtime("runsc", {"runc"}, allow_degraded=False)
        with self.assertRaises(IsolationUnavailable):
            choose_runtime("no-such-runtime", {"runc", "runsc"}, allow_degraded=False)

    def test_degraded_is_explicit(self) -> None:
        c = choose_runtime("runsc", {"runc"}, allow_degraded=True)
        self.assertEqual((c.runtime, c.isolation_tier, c.degraded), ("runc", "runc-hardened", True))
        with self.assertRaises(IsolationUnavailable):
            choose_runtime("runsc", set(), allow_degraded=True)


if __name__ == "__main__":
    unittest.main()
