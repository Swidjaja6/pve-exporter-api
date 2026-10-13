from pydantic import BaseModel, computed_field
from prometheus_client.parser import text_string_to_metric_families

class Summary(BaseModel):
    running_vms: int
    cpu_raw: float
    memory_used_raw: float
    memory_total: float
    storage_used: float
    total_storage: float

    @computed_field
    def cpu_computed(self) -> float:
        return round(self.cpu_raw * 100, 2)
    @computed_field
    def memory_used(self) -> float:
        return round(self.memory_used_raw / 1024 ** 3, 2)

def parse(text):
    scrape_success = False
    running_vms = 0
    cpu_raw, memory_used_raw, memory_total = None, None, None
    storage_used, total_storage = 0.0, 0.0
    storage_used_instances, total_storage_instances = set(), set()
    for family in text_string_to_metric_families(text):
        for sample in family.samples:
            match sample.name:
                case "pve_exporter_scrape_success":
                    if sample.value == 1:
                        scrape_success = True
                case "pve_up":
                    if(sample.labels["id"].startswith("qemu/") and sample.value == 1):
                        running_vms += 1
                case "pve_cpu_usage_ratio":
                    if(sample.labels["id"].startswith("node/")):
                        cpu_raw = sample.value
                case "pve_memory_usage_bytes":
                    if(sample.labels["id"].startswith("node/")):
                        memory_used_raw = sample.value
                case "pve_memory_size_bytes":
                    if(sample.labels["id"].startswith("node/")):
                        memory_total = sample.value
                case "pve_disk_usage_bytes":
                    if(sample.labels["id"].startswith("storage/")):
                        storage_used += sample.value
                        storage_used_instances.add(sample.labels["id"])
                case "pve_disk_size_bytes":
                    if(sample.labels["id"].startswith("storage/")):
                        total_storage += sample.value
                        total_storage_instances.add(sample.labels["id"])

    if not scrape_success:
        raise ValueError("Scrape was not successful")

    if cpu_raw is None or memory_used_raw is None or memory_total is None:
        raise ValueError("Missing required memory or CPU metrics")

    if total_storage == 0.0:
        raise ValueError("Missing or inconsistent storage metrics")

    if storage_used_instances != total_storage_instances:
        raise ValueError("Inconsistent storage metrics")

    return Summary(
        running_vms=running_vms,
        cpu_raw=cpu_raw,
        memory_used_raw=memory_used_raw,
        memory_total=memory_total,
        storage_used=storage_used,
        total_storage=total_storage
    )

