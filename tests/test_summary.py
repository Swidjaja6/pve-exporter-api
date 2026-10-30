from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import homelab_api
from homelab_api import parse

# Filtered /metrics output captured from the real exporter (no VM names).
SAMPLE = (Path(__file__).parent / "metrics_sample.txt").read_text()

# No `with` block: lifespan does not run, so no real poll starts during tests.
client = TestClient(homelab_api.app)


# --- helpers: make one precise change to the sample ---------------------------

def drop(text, metric, id=None):
    """Remove lines of `metric`. With `id`, only the line whose id label matches exactly."""
    def matches(line):
        if not line.startswith(metric + "{") and not line.startswith(metric + " "):
            return False
        return id is None or f'id="{id}"' in line
    return "\n".join(l for l in text.splitlines() if not matches(l)) + "\n"


def set_value(text, metric, value, id=None):
    """Replace the value of `metric` (the line with `id`, if given)."""
    out = []
    for l in text.splitlines():
        is_metric = l.startswith(metric + "{") or l.startswith(metric + " ")
        if is_metric and (id is None or f'id="{id}"' in l):
            l = l.rsplit(" ", 1)[0] + f" {value}"
        out.append(l)
    return "\n".join(out) + "\n"


# --- parse: valid input -> Summary --------------------------------------------

def test_happy_path():
    output = parse(SAMPLE)
    assert output.model_dump() == pytest.approx({
        "running_vms": 2,
        "cpu_raw": 0.00952380952380952,
        "cpu_computed": 0.95,
        "memory_used_raw": 8173903872,
        "memory_used": 7.61,
        "memory_total": 33527832576,
        "storage_used_raw": 142347871092,
        "storage_used": 132.57,
        "total_storage": 1.0086172672e11 + 3.73553102848e11
    })

def test_idle_cpu_is_valid():
    text = set_value(SAMPLE, "pve_cpu_usage_ratio", 0.0, id="node/pve")
    output = parse(text)
    assert output.cpu_raw == 0.0


def test_zero_storage_used_is_valid():
    text = set_value(SAMPLE, "pve_disk_usage_bytes", 0.0, "storage/pve/local")
    text = set_value(text, "pve_disk_usage_bytes", 0.0, "storage/pve/local-lvm")
    output = parse(text)
    assert output.storage_used_raw == 0.0


# --- parse: each fail rule raises ---------------------------------------------

def test_scrape_success_zero():
    text = set_value(SAMPLE, "pve_exporter_scrape_success", 0.0)
    with pytest.raises(ValueError):
        parse(text)


def test_scrape_line_missing():
    text = drop(SAMPLE, "pve_exporter_scrape_success")
    with pytest.raises(ValueError):
        parse(text)


def test_node_metric_missing():
    text = drop(SAMPLE, "pve_memory_usage_bytes", id="node/pve")
    with pytest.raises(ValueError):
        parse(text)


def test_no_storage():
    text = drop(SAMPLE, "pve_disk_usage_bytes", id="storage/pve/local")
    text = drop(text, "pve_disk_usage_bytes", id="storage/pve/local-lvm")
    text = drop(text, "pve_disk_size_bytes", id="storage/pve/local")
    text = drop(text, "pve_disk_size_bytes", id="storage/pve/local-lvm")
    with pytest.raises(ValueError):
        parse(text)


def test_size_without_usage():
    text = drop(SAMPLE, "pve_disk_usage_bytes", id="storage/pve/local-lvm")
    with pytest.raises(ValueError):
        parse(text)


def test_mismatched_storage():
    text =drop(SAMPLE, "pve_disk_usage_bytes", id="storage/pve/local")
    text = drop(text, "pve_disk_size_bytes", id="storage/pve/local-lvm")
    with pytest.raises(ValueError):
        parse(text)


# --- /summary route ----------------------------------------------------------

def test_summary_503_when_no_data(monkeypatch):
    monkeypatch.setattr(homelab_api, "latest", None)
    response = client.get("/summary")
    assert response.status_code == 503


def test_summary_200_with_data(monkeypatch):
    monkeypatch.setattr(homelab_api, "latest", parse(SAMPLE))
    response = client.get("/summary")
    assert response.status_code == 200
