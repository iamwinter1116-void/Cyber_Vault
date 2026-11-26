"""Storage ladder arguments (docs/08 section 4). The chosen method and every Docker/mkfs call need the Linux host."""

import tempfile
import unittest
from pathlib import Path

from services.runner import storage
from services.runner.launch import EnvRow, build_create_kwargs, choose_runtime

ENV = EnvRow("0b6f0c1e-1111-4222-8333-444455556666", "7d2a4f00-aaaa-4bbb-8ccc-dddddddddddd", "app-target",
             500, 256, 128, 128)
GV = choose_runtime("runsc", {"runsc"}, allow_degraded=False)


class Ladder(unittest.TestCase):
    def test_v1_loop_image(self) -> None:
        k = storage.volume_create_kwargs(ENV, "V1", "/var/lib/abhedya/vol")
        assert k is not None
        self.assertEqual(k["name"], f"abh-vol-{ENV.id}")
        self.assertEqual(k["driver"], "local")
        self.assertEqual(k["driver_opts"], {"type": "ext4", "device": str(Path("/var/lib/abhedya/vol") /
                                                                            f"{ENV.id}.img"), "o": "loop"})
        self.assertEqual(k["labels"]["abh.env_id"], ENV.id)  # type: ignore[index]

    def test_v2_tmpfs_volume(self) -> None:
        k = storage.volume_create_kwargs(ENV, "V2", "/unused")
        assert k is not None
        self.assertEqual(k["driver_opts"], {"type": "tmpfs", "device": "tmpfs", "o": "size=128m,uid=1000,gid=1000"})

    def test_v3_has_no_volume(self) -> None:
        self.assertIsNone(storage.volume_create_kwargs(ENV, "V3", "/unused"))

    def test_each_workspace_passes_the_launch_profile(self) -> None:
        for method in storage.METHODS:
            k = build_create_kwargs(ENV, _spec(), GV, storage.workspace(ENV, method))
            if method == "V3":
                self.assertEqual(k["tmpfs"]["/workspace"], "size=128m,uid=1000,gid=1000")  # type: ignore[index]
                self.assertEqual(k["mounts"], [])
            else:
                self.assertEqual(k["mounts"], [{"Target": "/workspace", "Source": f"abh-vol-{ENV.id}",
                                                "Type": "volume", "ReadOnly": False}])

    def test_refuses_without_a_chosen_method(self) -> None:
        self.assertIsNone(storage.CHOSEN_METHOD)  # B0 check 8 has not run on the Linux host
        for m in (None, "V4", ""):
            with self.assertRaises(storage.StorageUnavailable):
                storage.workspace(ENV, m)  # type: ignore[arg-type]
            with self.assertRaises(storage.StorageUnavailable):
                storage.volume_create_kwargs(ENV, m, "/x")  # type: ignore[arg-type]


class ImageFiles(unittest.TestCase):
    def test_remove_image_only_for_canonical_ids(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            victim = Path(d) / "keep.img"
            victim.write_bytes(b"x")
            for bad in ("../keep", "keep", ENV.id.upper(), "", f"{ENV.id}/../keep"):
                with self.assertRaises(ValueError):
                    storage.remove_image(d, bad)
            self.assertTrue(victim.exists())
            img = Path(d) / f"{ENV.id}.img"
            img.write_bytes(b"x")
            (Path(d) / f"{ENV.id}.img.tmp").write_bytes(b"x")
            storage.remove_image(d, ENV.id)
            self.assertEqual(sorted(p.name for p in Path(d).iterdir()), ["keep.img"])
            storage.remove_image(d, ENV.id)  # already gone: no error

    def test_make_image_keeps_an_existing_image(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            img = Path(d) / f"{ENV.id}.img"
            img.write_bytes(b"existing")
            storage.make_image(d, ENV)  # returns before mkfs because the image is already in place
            self.assertEqual(img.read_bytes(), b"existing")


def _spec():  # type: ignore[no-untyped-def]
    from services.runner.launch import ContainerSpec

    return ContainerSpec("target", "sha256:" + "ab" * 32, 300, 153)


if __name__ == "__main__":
    unittest.main()
