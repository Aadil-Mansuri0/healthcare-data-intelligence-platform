# Helm-Managed Components

Hand-writing raw Kubernetes YAML for stateful, complex systems like Airflow or
a full Prometheus stack is not how this is done in practice — the community
Helm charts encode years of hard-won operational knowledge (HA Postgres,
proper PVC sizing, sane defaults). This project uses Helm for those two;
`infra/k8s/api` and `infra/k8s/frontend` stay as raw manifests since they're
simple, custom, stateless apps where a chart would be overkill.

## 1. Apache Airflow (official community chart)

```bash
helm repo add apache-airflow https://airflow.apache.org
helm repo update

helm install airflow apache-airflow/airflow \
  --namespace healthcare \
  --create-namespace \
  -f infra/helm/airflow-values.yaml
```

This deploys: webserver, scheduler, triggerer, a dedicated HA Postgres
(via the chart's bundled subchart), and Redis (for the Celery executor —
swap to KubernetesExecutor in values if you want pod-per-task isolation
instead, see the commented alternative in airflow-values.yaml).

Upgrade after changing DAGs (if not using a Git-sync sidecar):
```bash
helm upgrade airflow apache-airflow/airflow -n healthcare -f infra/helm/airflow-values.yaml
```

## 2. kube-prometheus-stack (Prometheus + Grafana + Alertmanager)

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

helm install monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace \
  -f infra/helm/monitoring-values.yaml
```

This replaces the docker-compose Prometheus/Grafana services for the K8s
deployment target — it auto-discovers pods via ServiceMonitor CRDs instead
of the static `prometheus.yml` scrape config used in local Docker Compose.

Import `monitoring/grafana/healthcare_dashboard.json` into the deployed
Grafana manually (Dashboards → Import), or provision it automatically via
a ConfigMap labeled `grafana_dashboard: "1"` (see monitoring-values.yaml).

## Why not Helm-ify the API/Frontend too?

They're simple 12-factor stateless apps with no complex dependency graph —
a raw Deployment + Service + HPA + Ingress is ~150 lines total and easier
to read/review in a PR than an equivalent parameterized chart. Helm earns
its complexity budget for Airflow/Prometheus because those systems have
dozens of interdependent components; it doesn't for two Deployments.
