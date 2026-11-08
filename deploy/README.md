# Ship Court — hosting options

## Free public preview on Render

The zero-cost deployment path is a **read-only static product preview**, built with:

~~~bash
node deploy/build-preview.mjs
~~~

Create a Render **Static Site** from this repository, branch `main`, build command `node deploy/build-preview.mjs`, publish directory `.runtime/public-preview`, and environment variable `SKIP_INSTALL_DEPS=true`. No API keys, bot tokens or application databases belong in this site. The build copies only three explicit public source files and the two screenshots already published in the README. It does not publish the checkout or the runtime directory as a whole.

This preview presents the workspace, evidence and setup instructions; it cannot run missions, agents, voice or approvals. The functional runtime remains local until migrated.

**Free-only is not a verified always-on full deployment.** [Render free web services](https://render.com/docs/free) sleep after 15 minutes without inbound traffic, erase local SQLite data on restart/redeploy/spin-down, and cannot attach persistent disks. Free Render Postgres expires after 30 days. A separate durable datastore and a supported runtime for the official Switch server and Discord gateways are required before moving the working workspace. Do not upload the existing SQLite state to an ephemeral service and treat it as durable.

## Complete runtime on a Linux host

The optional package below runs the existing application, official Switch, Discord text gateway and optional voice gateway on one Linux host. It is a single-server deployment for a small workspace, not a high-availability cluster. A sleeping free web service or static page host cannot run this complete Python/Node/SQLite/Discord stack unchanged. No paid server has been provisioned.

**Prepared is not deployed.** A server account, selected plan, SSH access and a DNS hostname are still required. Do not call the cloud deployment verified until containers, HTTPS, real Switch clients and Discord are checked on that server.

## Server choice and network

Start with Ubuntu 24.04 LTS, x86-64, 2 vCPU, 4 GB RAM and at least 40 GB disk; monitor the actual workload before increasing capacity. Groq provides inference remotely; there is no local model/GPU. Hetzner's CX23 is a low-cost starting option when available. Check the actual checkout price, IPv4, taxes and backups before purchasing. DigitalOcean or an existing Ubuntu VPS can use the same files.

Allow inbound SSH only from your administration IP, plus TCP 80 and 443 publicly. Allow outbound HTTPS/WSS and Discord voice UDP. Only Caddy listens publicly. Switch binds to host loopback; access its operator UI through `ssh -L 8000:127.0.0.1:8000 USER@SERVER` and open `http://127.0.0.1:8000`. Keep Postgres off the public internet. These ports are bound explicitly, rather than relying only on UFW to protect published Docker ports.

Point a DNS A record, such as `shipcourt.yourdomain.com`, at the VPS public IPv4. Add AAAA only if the VPS IPv6 is configured. Caddy obtains and renews HTTPS certificates once DNS and ports 80/443 work. If you do not own a domain, choose a hostname before deployment; do not expose an HTTP login as a substitute.

## Files and service boundaries

| File | Purpose |
| --- | --- |
| `backend.Dockerfile` | Python 3.12, one nonroot backend process, runtime data outside image, health check |
| `voice.Dockerfile` | Node 24.18 voice gateway, separate scoped environment, channel map mounted read-only |
| `compose.yaml` | Restart policies, one backend, persistent state, optional voice, Caddy, bounded logs |
| `Caddyfile` | HTTPS, request limits, clickjacking protection, reverse proxy; private/legacy paths are not publicly proxied |
| `host.env.example` | Nonsecret hostname and absolute config/state paths |
| `switch.override.yaml` | Reviewed official Switch Compose override: restart policies, invite-only signup, loopback operator access |
| `backup.py` | Consistent SQLite snapshot with integrity check; never copies a live DB as a plain file |

Linux host networking lets the application and voice gateway use loopback for authenticated internal requests. The backend binds `127.0.0.1:8080`; Caddy exposes the same API/dashboard under one HTTPS origin. The official Switch API binds `127.0.0.1:8000`. Only one backend/voice set runs for a given bot/agent configuration. Sessions are in memory and require sign-in after restart; SQLite, channel IDs, contexts and cursors persist.

## 1. Install and stage source

Install Docker Engine and the Compose plugin using the [official Ubuntu instructions](https://docs.docker.com/engine/install/ubuntu/). Install Git and Python 3.12. Do not replace an existing server's firewall or Docker installation blindly.

```bash
sudo mkdir -p /opt/shipcourt
sudo git clone --branch main https://github.com/GaneshNair007/switch-AI.git /opt/shipcourt/source
sudo install -d -m 700 /opt/shipcourt/config
sudo install -d -m 700 -o 10001 -g 10001 /opt/shipcourt/state
```

Build contexts exclude `.env`, runtime databases, SSH/key files, Git history, local environments and node_modules. Credentials are provided at runtime; they are not baked into images.

## 2. Preserve the existing workspace

**Uploading only the app is insufficient:** Switch's agents, room IDs, Discord bridge and encrypted service credentials live in its Postgres database. Copying Ship Court SQLite alone would leave a hosted dashboard pointing at a Switch server still on the laptop.

Before final migration, stop the laptop backend and voice gateway so no active native job or live meeting is cut over halfway. Keep Switch/Postgres running long enough to create a consistent Postgres dump. Keep a local backup and the original working server until restoration is verified; do not delete local data.

Prepare a private export locally, substituting your real hostname and certificate contact:

```powershell
.\.runtime\venv\Scripts\python.exe -m server.hosting --prepare --domain shipcourt.yourdomain.com --email you@example.com --output .runtime/hosting-export --switch-env "$env:APPDATA\switchdash\local-switch-server\native\run\switch-core.env"
```

This copies only whitelisted backend/voice variables into separate mode-600 files, creates a consistent SQLite backup, preserves channel/agent mappings, and rewrites the **Switch API URL** to VPS loopback. It does not print keys. The optional Switch environment export preserves encryption/signing keys; it does **not** contain the Switch database. The export directory is gitignored and contains credentials: transfer it only to your chosen private server through SSH.

Use a `pg_dump` client compatible with the running Switch Postgres server, with password supplied through its environment, to create a custom-format dump of the actual Switch database. Never paste the password into shell arguments or this guide. Match the destination Postgres image to a version that can restore that dump; preserve `SECRET_KEYS` and any legacy `JWT_SECRET_KEY`. Keep the original ID server name so observed transport identities remain valid. A source schema newer than the destination Switch build must not be downgraded.

Transfer `config/`, `state/` and the Postgres dump privately into `/opt/shipcourt/`. On the VPS:

```bash
sudo chmod 700 /opt/shipcourt/config /opt/shipcourt/state
sudo chmod 600 /opt/shipcourt/config/*.env
sudo chown -R 10001:10001 /opt/shipcourt/state
```

Use `MIGRATION.json` to verify what was exported. It explicitly says whether Switch secrets were included and that the Switch database must be restored separately. Do not start the new gateways while the laptop gateways still run.

## 3. Bring up the matching official Switch

Use the [reviewed official Switch source](https://github.com/sandbox-quantum/switch/tree/7bf37f8f82b45865b0f0bb207857fd9c25796172) and its standalone Compose contract. The published runtime version used by this project is 0.31.0. Restore the existing database and encryption keys into a compatible runtime; do not reset the volume or generate replacement keys for a database you are restoring.

```bash
sudo git clone https://github.com/sandbox-quantum/switch.git /opt/shipcourt/switch-source
sudo git -C /opt/shipcourt/switch-source checkout 7bf37f8f82b45865b0f0bb207857fd9c25796172
```

Use this command prefix for the official stack (the short `sw` function keeps its identity/volume name stable):

```bash
sw() {
  sudo docker compose --project-name shipcourt-switch \
    --env-file /opt/shipcourt/config/switch.env \
    -f /opt/shipcourt/switch-source/deploy/local/standalone-docker-compose.yml \
    -f /opt/shipcourt/source/deploy/switch.override.yaml "$@"
}
sw config --quiet
sw up -d postgres init-db
```

Restore the dump with `pg_restore --no-owner --no-privileges` into the intended database, using the private owner credential environment; verify the source/destination versions first. Then `sw up -d switch`. Verify the official readiness endpoint and room/agent identities through the SSH tunnel before starting Ship Court. If an image/schema is incompatible, use the reviewed source build override rather than guessing a different release or bypassing migration errors. A fresh Switch install requires new registration, room membership, sender mapping and Discord bridge setup instead of pretending old IDs exist there.

## 4. Build and start Ship Court

The exported `host.env` already specifies your hostname and `/opt/shipcourt/{config,state}` paths. Inspect those nonsecret settings. Do not publish the backend/voice `.env` values.

```bash
cd /opt/shipcourt/source
dc() { sudo docker compose --env-file /opt/shipcourt/config/host.env -f deploy/compose.yaml "$@"; }
dc config --quiet
dc build backend voice
dc up -d backend caddy
# Enable only after the separate voice credentials and channel map are ready:
dc --profile voice up -d voice
dc ps
```

The application fails startup if `SHIPCOURT_PUBLIC_ORIGIN` is not an HTTPS origin. Browser cookies are Secure on the public hostname; CSRF/origin checks still apply. Caddy blocks the public voice-service endpoint; the voice gateway uses loopback and its scoped service credential. Do not run multiple backend replicas with this SQLite/in-memory-session design.

## 5. Verify the hosted workflow

1. `https://YOUR-HOST/health` returns a healthy backend. This alone is not proof that Switch or Discord connected.
2. Sign in at the HTTPS dashboard. Confirm the title/branding **Ship Court**, five real Switch transports, existing missions and case history.
3. Inspect authenticated readiness and the actual Discord Mission Control panel. Confirm one gateway set; no duplicate replies or connection evictions.
4. Send one real human task and observe native handoff receipts and a persisted advisory. No GitHub write is implied by that check.
5. Test voice UDP connectivity with the human microphone/floor/recap sequence. Keep that gate explicitly unverified until the call succeeds on the VPS.
6. Restart the backend container. Confirm persisted missions/tasks and automatic Switch reconnection. Test the saved backup in a separate location before declaring recovery complete.

## Maintenance and backups

```bash
sudo python3 /opt/shipcourt/source/deploy/backup.py
# Separate private backup of Switch, encryption keys and channel configuration:
# pg_dump -Fc … (use environment-based credentials; no passwords in arguments)
dc logs --tail 100 backend
dc --profile voice logs --tail 100 voice
```

Logs do not print API keys, but may contain project content; keep access restricted. Copy database backups and encryption-key backups off this server to a private destination. No scheduled backup or retention policy is claimed until an actual schedule and restore test are configured. Updating the repo requires a consistent backup, reviewed commit, rebuild and one controlled restart; `docker compose down -v` must not be used for routine updates.

References: [Caddy HTTPS](https://caddyserver.com/docs/automatic-https), [Docker firewall behavior](https://docs.docker.com/engine/install/ubuntu/#firewall-limitations), [Hetzner server setup](https://docs.hetzner.com/cloud/servers/getting-started/creating-a-server/).
