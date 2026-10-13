# Homelab Custom pve-exporter API

The API in this repo serves to deliver homelab statistics to my personal website. The data begins at my custom [pve-exporter](https://github.com/Swidjaja6/pve-exporter), the API reads it, and then my website calls it and the metrics are displayed. 

Writing it in this manner helped simplify the flow of my metrics to the website.
## Now:
- Nginx maps a small allow-list of metric names to fixed PromQL queries and forwards them to Prometheus, which computes the values from node_exporter data. 

## Planned design:
- API does the math
- No exposure of VM names or IDs
- Polls every 30 seconds no matter how many visitors there are