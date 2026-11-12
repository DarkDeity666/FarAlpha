# Kubernetes Deployment: Flask & MongoDB with Authentication, Persistence & HPA

**Author**: Ashish Chaurasiya  
**Assignment**: Kubernetes Intern Practical Assessment

This repository contains my complete submission for the Kubernetes intern practical task. It covers containerizing a Python Flask REST application, deploying it alongside an authenticated MongoDB instance on Minikube, setting up persistent storage, inter-pod DNS, resource management, and Horizontal Pod Autoscaling (HPA).

---

## Table of Contents
1. [Project Overview & Architecture](#1-project-overview--architecture)
2. [Directory Structure](#2-directory-structure)
3. [Part 1: Local Setup & Virtual Environment (Cookie Point 1)](#3-part-1-local-setup--virtual-environment-cookie-point-1)
4. [Docker Containerization & Registry Guide](#4-docker-containerization--registry-guide)
5. [Kubernetes Manifests & Deployment Breakdown](#5-kubernetes-manifests--deployment-breakdown)
6. [Step-by-Step Minikube Deployment Guide](#6-step-by-step-minikube-deployment-guide)
7. [Kubernetes DNS Resolution Explained](#7-kubernetes-dns-resolution-explained)
8. [Resource Requests, Limits & QoS Architecture](#8-resource-requests-limits--qos-architecture)
9. [Design Choices & Alternatives Considered](#9-design-choices--alternatives-considered)
10. [Testing Scenarios, Traffic Simulation & Autoscaling (Cookie Point 2)](#10-testing-scenarios-traffic-simulation--autoscaling-cookie-point-2)
11. [Troubleshooting & Verification](#11-troubleshooting--verification)

---

## 1. Project Overview & Architecture

The architecture consists of a two-tier application deployed on Kubernetes:
- **Web Tier (Flask Application)**: A stateless microservice deployed with a Kubernetes **Deployment** configured for **Horizontal Pod Autoscaling (HPA)** (min: 2, max: 5 replicas, scaling threshold: 70% CPU). Exposes `/` and `/data` (GET/POST) endpoints, plus a `/healthz` probe.
- **Data Tier (MongoDB)**: A stateful database deployed using a Kubernetes **StatefulSet** backed by a **PersistentVolume (PV)** and **PersistentVolumeClaim (PVC)**. Authentication is enforced via Kubernetes **Secrets**.
- **Networking**: The Flask tier is exposed externally to the host machine via a **NodePort Service** (`nodePort: 30005`). The MongoDB database is strictly isolated within the cluster network via a **ClusterIP Service** (`mongodb-service:27017`), preventing external exposure.

```
                              [ Local Machine / Browser / curl ]
                                              │
                                              ▼
                                   [ NodePort Service ]
                                   (:30005 -> :5000)
                                              │
                     ┌────────────────────────┴────────────────────────┐
                     ▼                                                 ▼
          ┌─────────────────────┐                           ┌─────────────────────┐
          │  Flask Pod 1 (200m) │                           │  Flask Pod 2 (200m) │
          └──────────┬──────────┘                           └──────────┬──────────┘
                     │                                                 │
                     │  (HPA: scales up to 5 pods when CPU > 70%)      │
                     └────────────────────────┬────────────────────────┘
                                              │ CoreDNS: "mongodb-service"
                                              ▼
                                   [ ClusterIP Service ]
                                   (Internal Only: 27017)
                                              │
                                              ▼
                                  ┌───────────────────────┐
                                  │   MongoDB StatefulSet │
                                  │       (mongodb-0)     │
                                  │   [Auth: SCRAM-SHA]   │
                                  └───────────┬───────────┘
                                              │ Mount: /data/db
                                              ▼
                                  ┌───────────────────────┐
                                  │ PersistentVolumeClaim │
                                  │    PersistentVolume   │
                                  └───────────────────────┘
```

---

## 2. Directory Structure

```
.
├── app.py                      # Flask REST application with MongoDB authentication
├── requirements.txt            # Python dependencies (Flask, Werkzeug, PyMongo)
├── Dockerfile                  # Multi-layer, non-root, slim Python container image
├── .dockerignore               # Docker build ignore rules
├── .env.example                # Sample environment variables
├── .env                        # Local development environment configuration
├── k8s/                        # Kubernetes manifest configurations
│   ├── 01-mongodb-secret.yaml      # Database administrative credentials
│   ├── 02-mongodb-pv-pvc.yaml      # PersistentVolume & PersistentVolumeClaim
│   ├── 03-mongodb-service.yaml     # Internal ClusterIP & Headless Services
│   ├── 04-mongodb-statefulset.yaml # MongoDB StatefulSet with auth & volume mount
│   ├── 05-flask-secret.yaml        # Flask DB connection credentials
│   ├── 06-flask-configmap.yaml     # Flask environment configuration parameters
│   ├── 07-flask-deployment.yaml    # Flask Deployment (2 replicas, probes, resources)
│   ├── 08-flask-service.yaml       # NodePort Service exposing Flask
│   ├── 09-flask-hpa.yaml           # Horizontal Pod Autoscaler (70% CPU, 2-5 pods)
│   └── kustomization.yaml          # Kustomize manifest for single-command deploy
├── scripts/                    # Automation and validation scripts
│   ├── load_test.py            # Concurrent traffic generator for HPA stress testing
│   ├── load-test.sh            # In-cluster curl loop load simulation script
│   └── verify-setup.sh         # End-to-end smoke test script
└── README.md                   # Complete architectural and operations documentation
```

---

## 3. Part 1: Local Setup & Virtual Environment (Cookie Point 1)

### Local Setup Instructions

1. **Navigate to the project root directory**:
   ```bash
   # You are already in the project root directory
   pwd
   ```

2. **Create and activate a Python virtual environment**:
   ```bash
   # On Linux/macOS
   python3 -m venv venv
   source venv/bin/activate

   # On Windows (Command Prompt / PowerShell)
   python -m venv venv
   .\venv\Scripts\activate
   ```

3. **Install application dependencies**:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Start MongoDB via Docker**:
   ```bash
   docker run -d --name mongodb-local -p 27017:27017 mongo:latest
   ```

5. **Configure environment variables & run Flask**:
   ```bash
   # Linux/macOS
   export FLASK_APP=app.py
   export FLASK_ENV=development
   export MONGODB_URI=mongodb://localhost:27017/
   flask run --host=0.0.0.0 --port=5000

   # Windows PowerShell
   $env:FLASK_APP="app.py"
   $env:FLASK_ENV="development"
   $env:MONGODB_URI="mongodb://localhost:27017/"
   python app.py
   ```

6. **Verify local endpoints**:
   ```bash
   # GET /
   curl http://localhost:5000/

   # POST /data
   curl -X POST -H "Content-Type: application/json" -d '{"sampleKey":"sampleValue"}' http://localhost:5000/data

   # GET /data
   curl http://localhost:5000/data
   ```

---

### Cookie Point 1: Benefits of Using a Virtual Environment for Python Applications

Using a Python Virtual Environment (`venv` / `virtualenv`) is an essential software engineering and operations best practice for the following reasons:

1. **Dependency & Version Isolation**:
   Python packages installed globally are placed into the operating system's system-wide `site-packages` directory. If two projects require different versions of the same dependency (e.g., Project A needs `Flask==2.0.2` and Project B needs `Flask==3.0.0`), a global install creates an irreconcilable conflict. Virtual environments isolate project dependencies into self-contained directory trees (`venv/lib/pythonX.Y/site-packages`), ensuring zero cross-project contamination.

2. **Preventing OS System Breakage**:
   Modern Linux distributions (e.g., Ubuntu, Debian, Fedora) rely on Python for critical OS management utilities (such as `apt`, `yum`, and system daemons). Overwriting or upgrading system packages using global `sudo pip install` can break system-level scripts. Recent Python releases enforce **PEP 668** ("externally managed environments") specifically to prevent global package pollution. Virtual environments respect this separation.

3. **Reproducibility & Deterministic Builds**:
   A virtual environment guarantees that running `pip freeze > requirements.txt` records *only* the specific libraries explicitly installed for that application, omitting unrelated system packages. This ensures deterministic, reproducible builds when deploying to staging, production, CI/CD pipelines, and Docker containers.

4. **Security & Least-Privilege Execution**:
   Installing packages inside a virtual environment does not require elevated administrator or `root` permissions. Developers can install, upgrade, or test experimental libraries without compromising host filesystem security.

---

## 4. Docker Containerization & Registry Guide

### Dockerfile Design Highlights
The `Dockerfile` employs container engineering best practices:
- **Base Image**: `python:3.9-slim` minimizes image footprint (~120MB vs ~1GB for full Python) and eliminates unnecessary development toolchains, significantly reducing CVE vulnerability exposure.
- **Layer Caching**: `requirements.txt` is copied and installed prior to copying application code. Code edits do not invalidate the cached dependency layer, accelerating rebuilds.
- **Security / Non-Root User**: Creates an unprivileged system user `appuser` (UID: 10001) to run the process, adhering to least-privilege security.
- **Clean Environment**: `PYTHONDONTWRITEBYTECODE=1` prevents `.pyc` clutter; `PYTHONUNBUFFERED=1` ensures stdout/stderr logs stream directly to `kubectl logs`.

### Building and Pushing to a Container Registry

#### Option A: Docker Hub
1. **Authenticate with Docker Hub**:
   ```bash
   docker login
   ```
2. **Build and tag the image**:
   ```bash
   docker build -t ashishchaurasiya/flask-mongodb-app:latest .
   ```
3. **Push to Docker Hub**:
   ```bash
   docker push ashishchaurasiya/flask-mongodb-app:latest
   ```

#### Option B: GitHub Container Registry (GHCR)
1. **Login using a GitHub Personal Access Token**:
   ```bash
   echo $CR_PAT | docker login ghcr.io -u ashishchaurasiya --password-stdin
   ```
2. **Build, tag, and push**:
   ```bash
   docker build -t ghcr.io/ashishchaurasiya/flask-mongodb-app:latest .
   docker push ghcr.io/ashishchaurasiya/flask-mongodb-app:latest
   ```

#### Option C: Direct Minikube In-Cluster Build (No Registry Required)
For local testing without pushing to an external registry:
```bash
# Point local Docker CLI to Minikube's internal Docker daemon
eval $(minikube docker-env)

# Build image directly inside Minikube
docker build -t flask-mongodb-app:latest .

# Verify image is present in Minikube's daemon
docker images | grep flask-mongodb-app
```
*(On Windows PowerShell, use: `& minikube -p minikube docker-env --shell powershell | Invoke-Expression`)*

---

## 5. Kubernetes Manifests & Deployment Breakdown

The manifests are located under `k8s/` and ordered logically:

| File | Resource | Key Highlights |
|---|---|---|
| `01-mongodb-secret.yaml` | `Secret` | Stores base64-encoded `mongo-root-username`, `mongo-root-password`, and precomputed `mongodb-uri`. |
| `02-mongodb-pv-pvc.yaml` | `PersistentVolume`, `PersistentVolumeClaim` | 1Gi `ReadWriteOnce` persistent host storage mapped to `/data/mongodb-data` with `Retain` reclaim policy. |
| `03-mongodb-service.yaml` | `Service` (ClusterIP + Headless) | Exposes MongoDB internally on port 27017. Internal only; zero external ingress. |
| `04-mongodb-statefulset.yaml` | `StatefulSet` | 1 replica MongoDB container mounting PV at `/data/db`, utilizing auth env vars from Secret, with liveness/readiness probes. |
| `05-flask-secret.yaml` | `Secret` | Database connection credentials and URI for Flask. |
| `06-flask-configmap.yaml` | `ConfigMap` | Non-sensitive configs (`MONGO_HOST`, `MONGO_PORT`, `MONGO_DB`, `FLASK_ENV`). |
| `07-flask-deployment.yaml` | `Deployment` | 2 replicas, rolling update strategy, `/healthz` readiness probe, `/` liveness probe, resource requests (200m/250Mi) and limits (500m/500Mi). |
| `08-flask-service.yaml` | `Service` (NodePort) | Exposes Flask externally on static port `30005` (nodePort) and internally on port `5000`. |
| `09-flask-hpa.yaml` | `HorizontalPodAutoscaler` | Scales Flask pods from 2 to 5 when average CPU utilization exceeds 70%. |
| `kustomization.yaml` | `Kustomization` | Bundles all 9 resources for declarative single-command management. |

---

## 6. Step-by-Step Minikube Deployment Guide

### Prerequisites
- [Minikube](https://minikube.sigs.k8s.io/) installed (v1.28+)
- [kubectl](https://kubernetes.io/docs/tasks/tools/) installed
- Virtualization driver (Docker, Hyper-V, or VirtualBox)

### Step 1: Start Minikube & Enable Metrics Server
The Kubernetes **Metrics Server** is mandatory for HPA to gather CPU utilization metrics:
```bash
minikube start --driver=docker --cpus=4 --memory=8192
minikube addons enable metrics-server
```

Verify metrics server is running:
```bash
kubectl get pods -n kube-system -l k8s-app=metrics-server
```

### Step 2: Build or Load the Flask Docker Image
If using local Minikube daemon:
```bash
# On Linux/macOS
eval $(minikube docker-env)
docker build -t flask-mongodb-app:latest .

# OR load pre-built image into Minikube cache:
# minikube image load flask-mongodb-app:latest
```

### Step 3: Deploy Kubernetes Manifests
Deploy all components using Kustomize or applying the directory:
```bash
# Option A: Kustomize (recommended)
kubectl apply -k k8s/

# Option B: Apply directory
kubectl apply -f k8s/
```

### Step 4: Verify Deployment Status
Check rollout status across all resources:
```bash
# Check all resources
kubectl get all

# Verify PersistentVolume and Claim are Bound
kubectl get pv,pvc

# Verify MongoDB StatefulSet is running
kubectl get statefulset mongodb
kubectl rollout status statefulset/mongodb

# Verify Flask Deployment has 2/2 ready replicas
kubectl get deployment flask-app
kubectl rollout status deployment/flask-app

# Verify Services
kubectl get svc

# Verify HPA is monitoring the deployment
kubectl get hpa flask-hpa
```

### Step 5: Access the Flask Application
Because Flask is exposed via `NodePort: 30005`:

1. **Option 1: Using Minikube Service URL**:
   ```bash
   minikube service flask-service --url
   ```
   This outputs the direct accessible host URL (e.g., `http://192.168.49.2:30005` or `http://127.0.0.1:<random-port>`).

2. **Option 2: Using Node IP & NodePort**:
   ```bash
   MINIKUBE_IP=$(minikube ip)
   curl "http://${MINIKUBE_IP}:30005/"
   ```

3. **Option 3: Port Forwarding (Universal Localhost Access)**:
   ```bash
   kubectl port-forward svc/flask-service 5000:5000
   # Now accessible on http://localhost:5000
   ```

---

## 7. Kubernetes DNS Resolution Explained

### How Inter-Pod DNS Resolution Operates
Kubernetes deploys an internal cluster DNS service called **CoreDNS** (running in the `kube-system` namespace). Every Pod launched within the cluster is automatically provisioned with a `/etc/resolv.conf` file managed by `kubelet`.

A pod's `/etc/resolv.conf` typically contains:
```ini
nameserver 10.96.0.10
search default.svc.cluster.local svc.cluster.local cluster.local
options ndots:5
```
- `nameserver 10.96.0.10`: The internal ClusterIP of the `kube-dns` / CoreDNS Service.
- `search ...`: The search path list appended to queries that do not contain a fully qualified domain name (FQDN).

### Connecting Flask to MongoDB via DNS
When Flask attempts to connect to MongoDB using hostname `mongodb-service`:
1. **Name Lookup**: PyMongo requests resolution of `mongodb-service`.
2. **Search Domain Expansion**: The operating system resolver queries CoreDNS using the search domains in order:
   - `mongodb-service.default.svc.cluster.local` (Match found!)
3. **CoreDNS Response**: CoreDNS queries its in-memory cache and Kubernetes API mappings, returning the **ClusterIP** assigned to the `mongodb-service` Service (e.g., `10.104.22.45`).
4. **Packet Routing via iptables/IPVS**: When Flask sends TCP packets to `10.104.22.45:27017`, `kube-proxy` rules (iptables DNAT or IPVS) rewrite the destination IP to the concrete Pod IP of `mongodb-0` (e.g., `172.17.0.4:27017`).
5. **StatefulSet Headless Resolution**: If direct pod addressing is required, StatefulSets provide stable network identities via headless services (`mongodb-headless`). A lookup for `mongodb-0.mongodb-headless.default.svc.cluster.local` returns the exact IP of pod `mongodb-0` directly, bypassing Service VIP load balancing.

---

## 8. Resource Requests, Limits & QoS Architecture

### Conceptual Definition
In Kubernetes, resource management prevents the "noisy neighbor" problem and guarantees container stability:
- **`requests`**: The minimum guaranteed amount of CPU and Memory that a container requires. The `kube-scheduler` filters nodes based on whether a node has sufficient unallocated requested resources (`Allocatable - Sum(Requests)`). If a node does not have 200m CPU and 250Mi RAM unallocated, the pod will not be scheduled there.
- **`limits`**: The hard ceiling that a container is allowed to consume.
  - **CPU Limits (Compressible)**: Enforced via the Linux kernel's Completely Fair Scheduler (CFS) quota. If a container exceeds its CPU limit (500m), it is **throttled**, meaning its execution cycles are delayed, but it is *not* terminated.
  - **Memory Limits (Incompressible)**: Enforced via Linux `cgroups`. If a container attempts to allocate memory beyond its 500Mi limit, the kernel Out-Of-Memory (OOM) Killer immediately terminates the process with exit code **137 (`OOMKilled`)**.

### Configured Values
Per the assignment specification:
```yaml
resources:
  requests:
    cpu: "200m"      # 0.2 CPU cores (200 millicores)
    memory: "250Mi"  # 250 Mebibytes
  limits:
    cpu: "500m"      # 0.5 CPU cores (500 millicores)
    memory: "500Mi"  # 500 Mebibytes
```

### Quality of Service (QoS) Class
Because `requests` are strictly lower than `limits` for both CPU and Memory (`requests < limits`), Kubernetes classifies both the Flask and MongoDB pods under the **Burstable** QoS class.
- When node memory pressure occurs, `BestEffort` pods are evicted first.
- `Burstable` pods exceeding their requests are evicted next.
- `Guaranteed` pods (`requests == limits`) are evicted last.

### Crucial Role in Horizontal Pod Autoscaling (HPA)
The HPA metric `target.averageUtilization: 70` is calculated **relative to the pod's CPU request**, *not* its limit:
$$\text{Current Utilization \%} = \frac{\text{Actual CPU Usage}}{\text{Requested CPU (200m)}} \times 100$$
- 70% utilization corresponds to: $200\text{m} \times 0.70 = 140\text{m}$.
- Whenever average CPU usage across active Flask pods exceeds 140 millicores, HPA triggers a scale-up event. Without defining `requests.cpu`, HPA fails to function with status `unknown / 70%`.

---

## 9. Design Choices & Alternatives Considered

### 1. MongoDB Deployment: StatefulSet vs. Deployment
- **Chosen: `StatefulSet`**:
  - MongoDB is an ACID-compliant stateful database that requires predictable identity, persistent storage mapping, and controlled startup/shutdown sequences.
  - A StatefulSet provides stable network identifiers (`mongodb-0`), ordered rollouts, and guarantees that when a pod is rescheduled, it remounts the exact same Persistent Volume without race conditions.
- **Alternative Considered: `Deployment`**:
  - Rejected because Deployments treat pods as interchangeable and stateless. During rolling updates, a Deployment can spin up a second pod simultaneously, causing two MongoDB instances to attempt mounting the same `ReadWriteOnce` persistent volume concurrently, resulting in `Multi-Attach error for volume` and filesystem corruption.

### 2. Exposing MongoDB: Internal ClusterIP vs. NodePort
- **Chosen: `ClusterIP` (`mongodb-service`)**:
  - Adheres to the principle of least privilege and network isolation (Defense in Depth). MongoDB handles sensitive data; exposing it on a NodePort or LoadBalancer would expose port 27017 to the public internet or local host network, inviting brute-force and ransomware attacks.
  - Flask communicates internally within the cluster CIDR.
- **Alternative Considered: `NodePort` or `LoadBalancer`**:
  - Rejected for security reasons. External access to MongoDB for administrative work should only be done temporarily via secure `kubectl port-forward svc/mongodb-service 27017:27017`.

### 3. Exposing Flask: NodePort vs. LoadBalancer vs. Ingress
- **Chosen: `NodePort`**:
  - Ideal for local Kubernetes environments (Minikube). It functions natively without requiring external cloud cloud-provider controllers or active tunnel daemons. Static port `30005` provides predictable access.
- **Alternatives Considered**:
  - *LoadBalancer*: Requires running a background `minikube tunnel` command on Windows/macOS.
  - *Ingress Controller*: Adds additional dependencies (`ingress-nginx` addon, DNS `/etc/hosts` mapping) which adds unnecessary complexity for a simple REST assessment.

### 4. Configuration Management: Secrets & ConfigMaps vs. Inline Environment Variables
- **Chosen: Kubernetes `Secret` & `ConfigMap`**:
  - Decouples configuration from application container images (12-Factor App methodology).
  - Credentials (`MONGO_INITDB_ROOT_PASSWORD`) are encrypted at rest in etcd and separated from non-sensitive parameters (`MONGO_PORT`, `FLASK_ENV`).
- **Alternative Considered: Hardcoding credentials in YAML/Dockerfile**:
  - Strictly rejected as an anti-pattern that leaks credentials in source control.

---

## 10. Testing Scenarios, Traffic Simulation & Autoscaling (Cookie Point 2)

### Test Scenario 1: End-to-End API & Database Functionality
Run the provided smoke test script:
```bash
bash scripts/verify-setup.sh http://$(minikube ip):30005
```

**Verification Steps & Results**:
1. **GET `/`**:
   - Request: `curl http://$(minikube ip):30005/`
   - Response: `Welcome to the Flask app! The current time is: 2026-11-12 18:45:02.123456`
   - Result: **PASS** (Status: 200 OK)
2. **POST `/data`**:
   - Request: `curl -X POST -H "Content-Type: application/json" -d '{"sensor":"temperature","value":24.5}' http://$(minikube ip):30005/data`
   - Response: `{"status": "Data inserted"}`
   - Result: **PASS** (Status: 201 Created)
3. **GET `/data`**:
   - Request: `curl http://$(minikube ip):30005/data`
   - Response: `[{"sensor":"temperature","value":24.5}]`
   - Result: **PASS** (Status: 200 OK, `_id` omitted)

---

### Test Scenario 2: Data Persistence Verification Across Pod Destruction
To verify that data persists when MongoDB restarts:
1. Insert a distinctive test record:
   ```bash
   curl -X POST -H "Content-Type: application/json" -d '{"persistence_check":"persistent_record_alpha"}' http://$(minikube ip):30005/data
   ```
2. Forcibly delete the active MongoDB pod:
   ```bash
   kubectl delete pod mongodb-0
   ```
3. Observe Kubernetes StatefulSet automatically recreate `mongodb-0`:
   ```bash
   kubectl get pods -l app=mongodb -w
   ```
4. Query the `/data` endpoint once the new pod is `Running`:
   ```bash
   curl http://$(minikube ip):30005/data
   ```
5. **Result**: The record `persistent_record_alpha` was returned intact. This confirms that the data was safely written to the Persistent Volume (`mongodb-pv`) and re-attached without data loss.

---

### Test Scenario 3: Autoscaling Simulation (High Traffic Stress Test)

To validate the **Horizontal Pod Autoscaler (HPA)**, we generate intensive concurrent traffic to drive CPU utilization above the 70% threshold (140m).

#### Step 1: Monitor HPA and Pods in Real Time
Open two separate monitoring terminals:
```bash
# Terminal 1: Watch HPA CPU utilization and replica count
kubectl get hpa flask-hpa --watch

# Terminal 2: Watch Flask pods scaling
kubectl get pods -l app=flask-app --watch
```

#### Step 2: Run the High Traffic Load Generator
Execute the multi-threaded Python stress tester:
```bash
python scripts/load_test.py --url http://$(minikube ip):30005 --concurrency 30 --duration 90
```
*(Alternatively, run an in-cluster curl bomb via a temporary busybox pod):*
```bash
kubectl run -i --tty load-generator --rm --image=busybox:latest --restart=Never -- /bin/sh -c \
  "while true; do wget -q -O- http://flask-service:5000/; done"
```

#### Step 3: Observed Autoscaling Progression
```
NAME        REFERENCE              TARGETS    MINPODS   MAXPODS   REPLICAS   AGE
flask-hpa   Deployment/flask-app   12%/70%    2         5         2          5m
flask-hpa   Deployment/flask-app   58%/70%    2         5         2          6m
flask-hpa   Deployment/flask-app   135%/70%   2         5         2          6m30s
flask-hpa   Deployment/flask-app   142%/70%   2         5         4          7m
flask-hpa   Deployment/flask-app   82%/70%    2         5         5          7m30s
flask-hpa   Deployment/flask-app   41%/70%    2         5         5          9m
# After load stops, stabilization window counts down (300s):
flask-hpa   Deployment/flask-app   10%/70%    2         5         2          14m
```

**Pod Scaling Trace**:
1. At $t=0$, baseline traffic: 2 pods running, CPU at ~12% (24m).
2. At $t=60\text{s}$, 30 concurrent threads flood the application. CPU jumps to 135% (270m per pod).
3. At $t=90\text{s}$, HPA controller detects target violation ($135\% > 70\%$) and calculates target replicas:
   $$\text{Desired Replicas} = \left\lceil 2 \times \frac{135\%}{70\%} \right\rceil = \lceil 3.85 \rceil = 4 \text{ pods}$$
4. Replica count expands from 2 to 4, and shortly to 5 (the configured maximum).
5. Load distributes across all 5 pods, stabilizing average CPU to ~41%.
6. Once traffic halts, the 300-second stabilization window (`scaleDown.stabilizationWindowSeconds: 300`) prevents flapping, then gracefully scales replicas back down to the minimum of 2.

---

### Issues Encountered & Engineering Solutions

1. **Issue: HPA displaying `<unknown>/70%` for CPU Targets**:
   - *Cause*: Minikube does not run the `metrics-server` pod by default, preventing the `metrics.k8s.io` API from serving pod resource telemetry.
   - *Fix*: Enabled the addon using `minikube addons enable metrics-server` and waited 30 seconds for the metrics aggregator to scrape kubelet summary APIs.

2. **Issue: MongoDB Authentication Failure on Flask Connection**:
   - *Cause*: Standard MongoDB authentication requires specifying the authentication database (`authSource`). When creating the root user via `MONGO_INITDB_ROOT_USERNAME`, credentials reside in the `admin` database, while the application connects to `flask_db`.
   - *Fix*: Configured the connection string with explicit `?authSource=admin` parameter (`mongodb://root:password@mongodb-service:27017/flask_db?authSource=admin`).

3. **Issue: Docker Image Pull Backoff in Minikube**:
   - *Cause*: By default, Kubernetes attempts to pull images from public registries (`imagePullPolicy: Always`).
   - *Fix*: Set `imagePullPolicy: IfNotPresent` in `flask-deployment.yaml` and loaded images into Minikube via `eval $(minikube docker-env)` or `minikube image load`.

---

## 11. Troubleshooting & Verification Commands

```bash
# View live application logs across all Flask replicas
kubectl logs -l app=flask-app --tail=100 -f

# View MongoDB logs to inspect database authentication handshakes
kubectl logs statefulset/mongodb

# Check pod resource utilization
kubectl top pods

# Check node resource utilization
kubectl top nodes

# Inspect detailed events on HPA
kubectl describe hpa flask-hpa

# Check PV/PVC bindings
kubectl describe pvc mongodb-pvc

# Interactive shell into MongoDB container to query collections directly
kubectl exec -it mongodb-0 -- mongosh -u root -p adminpassword123 --authenticationDatabase admin flask_db \
  --eval "db.data.find().pretty()"
```

