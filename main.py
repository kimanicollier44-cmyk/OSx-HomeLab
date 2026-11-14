#!/usr/bin/env python3
"""OSx-HomeLab — validator and planner for the blueprint stack.

Pure Python stdlib. Dry-run only: this tool NEVER touches a network,
a real host, Docker, Terraform or Ansible. It validates the files that
describe the stack (compose, OpenTofu, Ansible, service configs),
checks the registry / VLAN / phase model from the blueprint, and
prints the plan a human would apply by hand on their own hardware.

HOLD gates: every real-world action is held by default.
"""
import argparse, ipaddress, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SERVICES = ROOT / "services"

REGISTRY = [
    {"slug": "osx", "name": "OSx", "port": 8115, "namespace": "osx-mesh", "repo": "credkellar/OSx"},
    {"slug": "s3lf-c0n8ci0us", "name": "S3lf-c0n8ci0us", "port": 8090, "namespace": "cognitive-mesh", "repo": "credkellarboop/S3lf-c0n8ci0us"},
    {"slug": "agents-xcrops", "name": "Agents-xCrops", "port": 8110, "namespace": "agents-xcrops-mesh", "repo": "ddkellar01/Agents-xCrops"},
    {"slug": "quantum-traderx", "name": "Quantum-TraderX", "port": 8130, "namespace": "quantum-trader-mesh", "repo": "ddkellar01/Quantum-TraderX"},
    {"slug": "autonomous-tech-infrastructure", "name": "Autonomous-Tech-Infrastructure-Platform", "port": 8105, "namespace": "autonomous-rnd-mesh", "repo": "ddkellar01/Autonomous-Tech-Infrastructure-Platform"},
    {"slug": "advanced-medical-institution", "name": "Advanced-Natural-Medical-Institution", "port": 8095, "namespace": "advanced-medical-mesh", "repo": "ddkellar01/Advanced-Natural-Medical-Institution"},
    {"slug": "crypto-recovery-forensics", "name": "Crypto-Recovery-Forensics", "port": 8100, "namespace": "crypto-forensics-mesh", "repo": "ddkellar01/Crypto-Recovery-Forensics"},
    {"slug": "creator-pipeline", "name": "PLAN-TEST-DEPLOY-PROMOTE-MONETIZE", "port": 8120, "namespace": "creator-pipeline-mesh", "repo": "ddkellar01/PLAN-TEST-DEPLOY-PROMOTE-MONETIZE"},
    {"slug": "sysadmin-footprint-mask", "name": "sysadmin-footprint-mask", "port": 8125, "namespace": "sysadmin-mask-mesh", "repo": "ddkellar01/sysadmin-footprint-mask"},
]
CORE_SERVICES = ["gitea", "minio", "nats", "zot", "infisical", "qdrant", "valkey"]
VLANS = [
    {"id": 10, "name": "LAN", "cidr": "10.1.10.0/24"},
    {"id": 15, "name": "Cameras-IoT", "cidr": "10.1.15.0/24"},
    {"id": 18, "name": "Media", "cidr": "10.1.18.0/24"},
    {"id": 99, "name": "Lab-Sandbox-Management", "cidr": "10.1.99.0/24"},
]
TALOS_NODES = ["10.1.10.31", "10.1.10.32", "10.1.10.33"]
SUPERSERVER = "10.1.10.20"
PHASES = [
    {"n": 1, "name": "Immediate Resilience", "goal": "Secondary DNS VIP, UPS/NUT telemetry, VLAN 99 isolation, self-hosted Gitea/Woodpecker/Zot/MinIO/Infisical/Authentik, Loki, Alertmanager, NATS, Valkey, Qdrant, pgBackRest."},
    {"n": 2, "name": "10G Core & K8s HA", "goal": "UniFi Cloud Gateway Fiber, 10G SFP+ DAC uplinks, LTE/5G WAN failover, 3-node Talos Linux immutable Kubernetes, Cilium eBPF, Longhorn, OpenTofu, Ansible, ArgoCD, Renovate."},
    {"n": 3, "name": "AI/HPC & Autonomous R&D", "goal": "Dual-24GB GPU node, Coder workspaces, SPAN + Suricata/Zeek, Tetragon, Trivy, Dependency-Track, Cosign, OpenTelemetry/Tempo/Pyroscope, Temporal, Chaos Mesh, OSx microkernel nodes, netboot.xyz."},
]
HOLD_GATES = ["apply_terraform_to_real_proxmox", "run_ansible_on_real_hosts", "bootstrap_real_talos_cluster",
              "connect_real_dual_wan", "store_real_secrets_in_infisical", "push_images_to_real_registry",
              "enable_live_trading_in_quantum_traderx", "expose_any_service_to_internet"]

def held(action): return action in HOLD_GATES

def run_checks():
    checks = []
    def ok(name, cond, detail=""): checks.append((name, bool(cond), detail))
    ports = [e["port"] for e in REGISTRY]; ns = [e["namespace"] for e in REGISTRY]
    ok("registry_has_9_engines", len(REGISTRY) == 9, str(len(REGISTRY)))
    ok("registry_ports_unique", len(set(ports)) == len(ports))
    ok("registry_ports_in_blueprint_range", all(8000 <= p <= 8999 for p in ports))
    ok("registry_namespaces_unique", len(set(ns)) == len(ns))
    nets = [ipaddress.ip_network(v["cidr"]) for v in VLANS]
    ok("vlans_4", len(VLANS) == 4)
    ok("vlans_do_not_overlap", all(not nets[i].overlaps(nets[j]) for i in range(len(nets)) for j in range(i+1, len(nets))))
    ok("vlan99_is_lab_sandbox", any(v["id"] == 99 and "Lab" in v["name"] for v in VLANS))
    ok("talos_3_nodes_in_vlan10", len(TALOS_NODES) == 3 and all(ipaddress.ip_address(x) in ipaddress.ip_network("10.1.10.0/24") for x in TALOS_NODES))
    ok("phases_1_2_3_in_order", [p["n"] for p in PHASES] == [1, 2, 3])
    ok("hold_gates_8_all_held", len(HOLD_GATES) == 8 and all(held(a) for a in HOLD_GATES))
    ok("unknown_action_not_held_by_list", held("read_a_file") is False)
    for f in ["docker-compose.yml", ".env.example", "terraform/main.tf", "terraform/variables.tf",
              "ansible/inventory/hosts.yml", "ansible/playbooks/deploy-talos.yml", "ansible/playbooks/deploy-core-stack.yml"]:
        ok(f"file_exists:{f}", (ROOT / f).is_file())
    compose = (ROOT / "docker-compose.yml").read_text() if (ROOT / "docker-compose.yml").exists() else ""
    for s in CORE_SERVICES: ok(f"compose_has_core:{s}", f"\n  {s}:" in compose or compose.startswith(f"  {s}:"))
    for e in REGISTRY: ok(f"compose_has_engine:{e['slug']}", str(e["port"]) in compose)
    tf = (ROOT / "terraform/main.tf").read_text() if (ROOT / "terraform/main.tf").exists() else ""
    for token in ['bpg/proxmox', 'talos', 'count = 3', 'osx-custom-microkernel-node']: ok(f"terraform_has:{token}", token in tf)
    inv = (ROOT / "ansible/inventory/hosts.yml").read_text() if (ROOT / "ansible/inventory/hosts.yml").exists() else ""
    for ip in [SUPERSERVER] + TALOS_NODES: ok(f"inventory_has:{ip}", ip in inv)
    for e in REGISTRY:
        cfg = SERVICES / e["slug"] / "config.json"
        ok(f"config_exists:{e['slug']}", cfg.is_file())
        if cfg.is_file():
            try:
                d = json.loads(cfg.read_text()); good = d.get("port") == e["port"] and d.get("namespace") == e["namespace"]
            except Exception: good = False
            ok(f"config_matches_registry:{e['slug']}", good)
    for s in CORE_SERVICES: ok(f"core_dir_exists:{s}", (SERVICES / s).is_dir())
    toml_cfg = SERVICES / "s3lf-c0n8ci0us" / "config.toml"
    ok("s3lf_config_toml_exists", toml_cfg.is_file() and "S3lf-c0n8ci0us" in toml_cfg.read_text() if toml_cfg.exists() else False)
    env = (ROOT / ".env.example").read_text() if (ROOT / ".env.example").exists() else ""
    ok("env_example_no_real_secret_values", "CHANGE_ME" in env and len(env) > 50)
    passed = sum(1 for _, c, _ in checks if c)
    for name, c, detail in checks: print(f"{'PASS' if c else 'FAIL'}  {name}  {detail}")
    print(f"CHECKS {passed}/{len(checks)}")
    return 0 if passed == len(checks) else 1

def main(argv=None):
    ap = argparse.ArgumentParser(prog="osx-homelab")
    ap.add_argument("cmd", nargs="?", default="checks", choices=["checks", "plan", "phases", "registry", "vlans", "demo"])
    a = ap.parse_args(argv)
    if a.cmd == "checks": return run_checks()
    if a.cmd == "registry":
        for e in REGISTRY: print(f"{e['port']}  {e['namespace']:<28} {e['name']}  ({e['repo']})")
        return 0
    if a.cmd == "vlans":
        for v in VLANS: print(f"VLAN {v['id']:<3} {v['name']:<26} {v['cidr']}")
        return 0
    if a.cmd == "phases":
        for p in PHASES: print(f"Phase {p['n']}: {p['name']} — {p['goal']}")
        return 0
    if a.cmd in ("plan", "demo"):
        print("OSx-HomeLab DRY-RUN PLAN (nothing is applied to real hardware)")
        for p in PHASES: print(f"  Phase {p['n']} {p['name']}")
        print(f"  Superserver {SUPERSERVER} · Talos control plane {', '.join(TALOS_NODES)}")
        print(f"  Core services: {', '.join(CORE_SERVICES)}")
        print(f"  Engines: {len(REGISTRY)} on ports {min(e['port'] for e in REGISTRY)}-{max(e['port'] for e in REGISTRY)}")
        print(f"  HOLD gates ({len(HOLD_GATES)}): " + ", ".join(HOLD_GATES))
        return 0
    return 2

if __name__ == "__main__": sys.exit(main())
