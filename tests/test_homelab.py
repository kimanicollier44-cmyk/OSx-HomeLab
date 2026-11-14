
import json, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import main as H

def test_registry_unique_ports_and_namespaces():
    assert len({e["port"] for e in H.REGISTRY}) == 9
    assert len({e["namespace"] for e in H.REGISTRY}) == 9
def test_registry_matches_blueprint_ports():
    assert {e["slug"]: e["port"] for e in H.REGISTRY}["osx"] == 8115
    assert {e["slug"]: e["port"] for e in H.REGISTRY}["quantum-traderx"] == 8130
    assert {e["slug"]: e["port"] for e in H.REGISTRY}["s3lf-c0n8ci0us"] == 8090
def test_vlans_do_not_overlap():
    import ipaddress
    nets = [ipaddress.ip_network(v["cidr"]) for v in H.VLANS]
    for i in range(len(nets)):
        for j in range(i+1, len(nets)): assert not nets[i].overlaps(nets[j])
def test_talos_nodes():
    assert H.TALOS_NODES == ["10.1.10.31", "10.1.10.32", "10.1.10.33"]
def test_phases_order(): assert [p["n"] for p in H.PHASES] == [1, 2, 3]
def test_hold_gates_all_held():
    for a in H.HOLD_GATES: assert H.held(a)
    assert not H.held("read_a_file")
def test_all_service_configs_parse_and_match():
    for e in H.REGISTRY:
        d = json.loads((ROOT/"services"/e["slug"]/"config.json").read_text())
        assert d["port"] == e["port"] and d["namespace"] == e["namespace"]
def test_core_service_dirs_exist():
    for s in H.CORE_SERVICES: assert (ROOT/"services"/s).is_dir()
def test_compose_covers_everything():
    c = (ROOT/"docker-compose.yml").read_text()
    for s in H.CORE_SERVICES: assert s in c
    for e in H.REGISTRY: assert str(e["port"]) in c
def test_terraform_and_ansible_content():
    tf = (ROOT/"terraform/main.tf").read_text(); inv = (ROOT/"ansible/inventory/hosts.yml").read_text()
    assert "count = 3" in tf and "osx-custom-microkernel-node" in tf
    for ip in ["10.1.10.20", "10.1.10.31", "10.1.10.33"]: assert ip in inv
def test_checks_cli_passes():
    r = subprocess.run([sys.executable, str(ROOT/"main.py"), "checks"], capture_output=True, text=True)
    assert r.returncode == 0 and "FAIL" not in r.stdout
def test_plan_is_dry_run():
    r = subprocess.run([sys.executable, str(ROOT/"main.py"), "plan"], capture_output=True, text=True)
    assert "DRY-RUN" in r.stdout and "HOLD" in r.stdout
