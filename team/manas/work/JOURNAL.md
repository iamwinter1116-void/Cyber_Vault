# Bug journal · Manas (role D)

## 2026-11-26 · G0 host handoff review

Parth pushed B0 at `55e7d96`. Static review of `host/preflight.sh` found the `res` helper compares its second
argument numerically with `-gt 5`, while checks 7a, 7b, and 7c call it with alphanumeric IDs. A failure in one
of those checks can therefore exit at the numeric comparison instead of continuing through checks 8–10 as the
script header promises. This is a review finding, not a claim from an executed Ubuntu preflight. Parth owns the fix.

Local host inspection: `Get-CimInstance Win32_ComputerSystem` reported MSI Vector A18 HX A9WHG, 32 logical CPUs,
33,438,138,368 bytes RAM, and a present hypervisor. VMware Workstation's `vmrun.exe` is installed; `vmrun list`
reported zero running VMs. No VMX or Ubuntu ISO was found in the inspected Documents, Downloads, or `N:\virtual-lab`
paths. An Ubuntu VM may exist elsewhere; no VM or runtime security claim follows from this inspection.

The owned instruction-template repair is in PR #1, `work/manas` → `integration`; it remains open for review.
