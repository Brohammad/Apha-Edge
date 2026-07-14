# Deploy AlphaEdge to https://alphaedge.brohammad.tech

Hostinger gives you the **domain** (`brohammad.tech`). The app itself needs a small **Linux server with Docker** — shared Hostinger web hosting cannot run this stack.

**Free server option (recommended):** [Oracle Cloud Always Free](https://www.oracle.com/cloud/free/) — 1 ARM VM, forever free, enough for AlphaEdge.

**Paid alternative:** Hostinger VPS (~$4–6/mo) if you already have one.

---

## Overview

```
Internet → alphaedge.brohammad.tech (Hostinger DNS)
         → Your VPS public IP
         → Caddy (free HTTPS via Let's Encrypt)
         → AlphaEdge gateway (React + API proxy)
         → API + Celery + Postgres + Redis
```

---

## Step 1 — Hostinger DNS

1. Log in to **Hostinger hPanel** → **Domains** → `brohammad.tech` → **DNS / Nameservers**.
2. Add an **A record**:

| Type | Name | Points to | TTL |
|------|------|-----------|-----|
| A | `alphaedge` | `YOUR_VPS_PUBLIC_IP` | 300 |

3. Wait 5–30 minutes. Check:

```bash
dig +short alphaedge.brohammad.tech
# should print your VPS IP
```

---

## Step 2 — Oracle Cloud free VM (if you don't have a VPS)

1. Create an [Oracle Cloud free account](https://www.oracle.com/cloud/free/).
2. Create a **VM.Standard.A1.Flex** instance (Ampere, Ubuntu 22.04, 2 OCPU / 12 GB RAM is plenty).
3. Download your SSH private key.
4. In Oracle **Security List**, allow inbound **TCP 22, 80, 443**.
5. Note the instance **public IP** — use it in Hostinger DNS (Step 1).

SSH in:

```bash
ssh ubuntu@YOUR_VPS_IP
```

Install Docker:

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# log out and back in
```

---

## Step 3 — Deploy on the server

```bash
git clone https://github.com/Brohammad/Apha-Edge.git alpha-edge
cd alpha-edge

cp .env.prod.example .env.prod
# Edit secrets (required):
nano .env.prod
```

Generate secrets:

```bash
python3 -c "import secrets; print('APP_SECRET_KEY=' + secrets.token_hex(32))"
python3 -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_hex(32))"
```

Paste into `.env.prod`, save.

Start production stack:

```bash
make prod
```

First boot takes ~2–3 minutes (migrations + seed + HTTPS cert).

---

## Step 4 — Verify

Open **https://alphaedge.brohammad.tech**

| Field | Value |
|-------|-------|
| Email | `demo@example.com` |
| Password | `DemoAlphaEdge1!` |

Health check:

```bash
curl -s https://alphaedge.brohammad.tech/api/v1/health/ready
```

---

## Makefile commands (on VPS)

| Command | Action |
|---------|--------|
| `make prod` | Build and start HTTPS production stack |
| `make prod-down` | Stop production stack |
| `make prod-logs` | Tail API logs |

---

## Hostinger shared hosting?

**Not supported.** AlphaEdge needs Docker, PostgreSQL, Redis, and a background worker. Use Oracle free VM or Hostinger **VPS**, not WordPress/shared hosting.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| DNS not resolving | Wait longer; confirm A record name is `alphaedge` not `@` |
| HTTPS certificate pending | Ensure ports 80 and 443 reach the VM; Caddy needs HTTP for ACME |
| 502 Bad Gateway | `docker compose -p alphaedge-prod ... logs api` — wait for migrations |
| Login fails | Re-seed: `docker compose -p alphaedge-prod -f infrastructure/docker-compose.prod.yml exec api sh -c 'PYTHONPATH=/app/src:/app python -m scripts.seed_demo_user'` |

---

## Cost summary

| Item | Cost |
|------|------|
| Domain `brohammad.tech` | You already have (Hostinger) |
| Subdomain DNS | Free |
| Oracle Cloud VM | **Free** (Always Free tier) |
| HTTPS (Caddy + Let's Encrypt) | **Free** |
| AlphaEdge demo (mock AI, paper only) | **Free** |

**Total for public demo: $0/mo** (excluding domain renewal you already pay).

---

After deploy, add the live URL to your README and LinkedIn:

> **Live demo:** https://alphaedge.brohammad.tech
