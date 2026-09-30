# Deploying and operating the dashboard

Everything here costs $0 on free tiers.

```
viewer ──> dashboard.aims-umich.com (Vercel Hobby, static React build)
              │ /api/* is proxied by Vercel
              ▼
           api.dashboard.aims-umich.com (Oracle Cloud Always Free VM, arm64)
              caddy (HTTPS) ─> api ─> postgres <─ ingest (collectors)
                                          ▲
                                          └── scorer (BERT on CPU)
```

The first-time setup is below, in order.
Steps marked **(you)** need an account login or a decision, so only a person can do them.

---

## 1. Oracle Cloud VM (you)

1. Sign up at <https://signup.oraclecloud.com/> for an **Always Free** account.
   A card is needed for identity verification.
   Do not upgrade to Pay As You Go.
   Choose the home region carefully, because it is permanent: a US region close to Michigan, such as US Midwest (Chicago) or US East (Ashburn).
2. **Compute → Instances → Create instance**:
   - Image: **Canonical Ubuntu 24.04** (the aarch64 build is picked automatically for Ampere).
   - Shape: **Ampere VM.Standard.A1.Flex**, **1 OCPU, 6 GB** memory.
     The free allowance is 2 OCPU and 12 GB in total, so a second identical VM can be the staging machine.
   - Networking: create a new VCN with a public subnet, and assign a public IPv4 address.
   - SSH keys: upload your public key.
   - Boot volume: 100 GB (the free allowance is 200 GB in total).
   - If creation fails with "Out of host capacity" (common for free A1), let `deploy/oci-wait-for-capacity.sh` retry for you.
     It checks each availability domain with Oracle's capacity report and launches with these same settings once one has room.
     Run `deploy/oci-wait-for-capacity.sh --dry-run` first, then `caffeinate -i deploy/oci-wait-for-capacity.sh`.
     What worked on 2026-09-29, when Chicago had no A1 capacity at all: launch the same VM as A2.Flex (which had
     capacity; this uses trial credit for a few minutes), then change its shape right away:
     `SHAPE=VM.Standard.A2.Flex SHAPE_CONFIGS=1:6 MAX_HOURS=0 deploy/oci-wait-for-capacity.sh`, then
     `oci compute instance update --instance-id <ocid> --shape VM.Standard.A1.Flex --shape-config '{"ocpus": 1, "memoryInGBs": 6}' --force`.
     Confirm the result reports `VM.Standard.A1.Flex` (processor "Ampere Altra").
3. Make the public IP stable: **Networking → IP management → Reserved public IPs**, reserve one, and attach it to the instance's VNIC.
   The DNS record points at this address.
4. Open the web ports: **Networking → Virtual cloud networks → your VCN → Security Lists → Default** and add ingress rules for source `0.0.0.0/0`:
   TCP 80, TCP 443, and UDP 443.
   (The bootstrap script opens the same ports in the VM's own firewall.)

## 2. Prepare the VM

From your laptop, in this repository:

```bash
VM=ubuntu@<reserved-ip>
scp -r compose.yaml deploy "$VM:/tmp/"
ssh "$VM" 'sudo mkdir -p /opt/dashboard && sudo chown ubuntu: /opt/dashboard && cp -r /tmp/compose.yaml /tmp/deploy /opt/dashboard/'
ssh "$VM" /opt/dashboard/deploy/bootstrap-vm.sh
```

The script installs Docker, automatic security updates, age, and rclone.
It also opens ports 80 and 443, adds 2 GB of swap, creates `/opt/dashboard/.env` (mode 600), and installs the nightly backup timer.

Then fill in the configuration on the VM:

```bash
ssh "$VM"
cp /opt/dashboard/deploy/env.example /tmp/env && nano /tmp/env   # fill in values
install -m 600 /tmp/env /opt/dashboard/.env && rm /tmp/env
```

Generate the database password with `openssl rand -hex 24`.
Keys that are not ready yet can stay empty: that collector reports "paused" and everything else runs.

## 3. DNS at Namecheap (you)

**Domain List → aims-umich.com → Manage → Advanced DNS → Add new record**:

| Type | Host | Value | TTL |
|---|---|---|---|
| A Record | `api.dashboard` | the VM's reserved public IP | Automatic |
| CNAME Record | `dashboard` | the value Vercel shows in step 5 (usually `cname.vercel-dns.com.`) | Automatic |

The existing `@`, `www`, and email records stay as they are, and the lab website is unaffected.
There are no CAA records, so Let's Encrypt can issue the API certificate.

## 4. GitHub: CI/CD (you)

In the repository's **Settings**:

1. **Environments → New environment → `production`**.
   Add yourself as a **required reviewer** so production deploys wait for approval.
   Add these environment secrets:
   - `VM_HOST`: the reserved IP.
   - `VM_USER`: `ubuntu`.
   - `VM_SSH_KEY`: a dedicated deploy key.
     Create it with `ssh-keygen -t ed25519 -f deploy_key -N ""`, paste the private key here, and append `deploy_key.pub` to `~/.ssh/authorized_keys` on the VM.
     Then delete both local files.
   - `VM_KNOWN_HOSTS`: the output of `ssh-keyscan -t ed25519 <reserved-ip>`.
2. Optional staging VM: create a `staging` environment with the same four secrets for the second VM.
   Then set the repository variable **`STAGING_ENABLED`** to `true` (Settings → Secrets and variables → Actions → Variables).
   On staging, leave `COMPOSE_PROFILES` empty in `.env`; it needs no domain.
3. After the first successful deploy, you can make the two container packages public (**Packages → aims-dashboard → Package settings → Change visibility**).
   This is not required, because the deploy logs the VM in to GHCR for each pull.

Then set the repository variable **`PRODUCTION_ENABLED`** to `true`.
Every push to `main` runs CI, builds `linux/arm64` images on GitHub's arm64 runners, and pushes them to GHCR.
With `PRODUCTION_ENABLED` set, it also deploys to staging (if enabled) and then to production (after your approval, if you added a reviewer).
Without it, pushes only build images, and you deploy on the VM with `deploy/deploy.sh <commit-sha>`.
To roll back, run **Actions → Deploy → Run workflow** with the commit SHA of a good build.

The first deploy (and any manual one) can also be started on the VM:

```bash
cd /opt/dashboard && deploy/deploy.sh latest
```

## 5. Vercel (you)

1. **Add New → Project → Import** `aims-umich/aims-dashboard`.
2. Set the **Root Directory** to `frontend`.
   The framework (Vite), build command, and output come from `frontend/vercel.json`.
   No environment variables are needed, because the site calls `/api/...` on its own origin and Vercel proxies that to the VM.
3. Deploy, then go to **Settings → Domains → Add** `dashboard.aims-umich.com` and create the CNAME from step 3 with the value Vercel shows.

Vercel's Hobby plan is for non-commercial use, which fits a non-commercial academic dashboard.

## 6. API keys (you, all free)

| Key | Where | Notes |
|---|---|---|
| `GUARDIAN_API_KEY` | <https://open-platform.theguardian.com/access/> → Developer key | The old key and the public `test` key both return 401 now. |
| `NYT_API_KEY` | <https://developer.nytimes.com/> → My Apps → New App, enable **Article Search API** and **Archive API** | Use the app's **Key**; the Secret is not needed. |
| `YOUTUBE_API_KEY` | Google Cloud Console → new project → enable **YouTube Data API v3** → Credentials → API key | Restrict the key to the YouTube Data API. The `youtube_refresh` job keeps stored data within YouTube's 30-day limit. |
| `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET` | Reddit's research-access request, then a "script" app at <https://www.reddit.com/prefs/apps> | Then add `reddit` to `ENABLED_SOURCES`. |

Enter each key with the helper, which hides the input, keeps it out of shell history, and restarts the collectors:

```bash
ssh -t -i ~/.ssh/aims_dashboard ubuntu@<vm> /opt/dashboard/deploy/set-secret.sh GUARDIAN_API_KEY
```

## 7. Historical data (one time)

The pre-2026 data lives only on the laptop that ran the old collectors, never in git.
Copy it to the VM and import it inside the stack:

```bash
# on the laptop, from backend/
tar czf legacy.tgz guardian/database/guardian.db mastodon/*.csv newyorktimes/var/dashdb.sqlite3
scp legacy.tgz "$VM:/tmp/" && rm legacy.tgz

# on the VM
mkdir -p /tmp/legacy && tar xzf /tmp/legacy.tgz -C /tmp/legacy
cd /opt/dashboard
docker compose run --rm -v /tmp/legacy:/legacy:ro ingest import-legacy guardian mastodon nyt --backend-dir /legacy
rm -rf /tmp/legacy /tmp/legacy.tgz
```

The scorer rescores everything with the pinned model, taking about 10 minutes for the roughly 1,000 relevant segments.
The scraped Threads data and the old YouTube comments (past YouTube's 30-day limit) are deliberately not importable.

## 8. Backups (you, then automatic)

1. On your laptop, create the backup key pair: `age-keygen -o dashboard-backup-key.txt`.
   Store the file in your password manager and delete it from disk.
   Only the **public** key (`age1...`) goes on the VM as `BACKUP_AGE_RECIPIENT`.
2. On the VM, run `rclone config` to add destinations:
   - OCI Object Storage: create a bucket and a **Customer Secret Key** (Profile → Customer secret keys).
     Then add an rclone "s3" remote with provider "Other" and endpoint `https://<namespace>.compat.objectstorage.<region>.oraclecloud.com`.
   - A lab-owned drive, for example the lab's Google Drive.
3. Set `BACKUP_REMOTES="oci:dashboard-backups gdrive:aims/dashboard-backups"` in `.env`.
4. Test it: `sudo systemctl start dashboard-backup.service && journalctl -u dashboard-backup -n 20`.
5. Test a restore on the staging VM with `deploy/restore.sh <file> <identity>`.
   A backup is only proven once it has been restored.

The timer runs nightly at 07:30 UTC.
The VM keeps 14 days of backups, and the remotes keep 60.

## 9. Monitoring (you, optional but recommended)

- **Healthchecks.io**: create a project, copy its **ping key** (Settings → Ping key) into `HEALTHCHECKS_PING_KEY`, and redeploy.
  Every job creates its own check on its first ping: `dashboard-bluesky`, `dashboard-mastodon`, `dashboard-youtube`, `dashboard-youtube_comments`, `dashboard-guardian`, `dashboard-nyt`, `dashboard-bluesky_metrics`, `dashboard-scorer`, and `dashboard-backup`.
  Then set each check's period to about 3 times its interval.
  Use 5 minutes for Bluesky, 10 for Mastodon and the scorer, 2 hours for the news and YouTube jobs, and 1 day for backups.
  Add an email integration.
- **Sentry**: create a Python project and put its DSN in `SENTRY_DSN`.
- `https://api.dashboard.aims-umich.com/api/v1/status` shows every collector's last success and the scoring backlog.
  The site's freshness badges read from it.

Oracle reclaims an Always Free VM that is idle for 7 days: CPU p95, network, and memory all under 20%.
BERT and Postgres keep memory above that, but check **Instance → Metrics** during the first week.

---

## Day-to-day operations

```bash
cd /opt/dashboard
docker compose ps                         # service health
docker compose logs -f --since 1h ingest  # collector logs (JSON)
docker compose restart scorer             # restart one service
docker compose run --rm ingest relevance --dry-run   # preview relevance-rule changes after a deploy
docker compose run --rm ingest relevance             # apply them
docker compose run --rm ingest models list           # models and prediction counts
```

- **A collector shows "Collection paused"**: its key is missing or rejected, or it keeps failing.
  Check `docker compose logs ingest | grep '"job": "<name>"'`.
  Secrets are redacted from errors.
- **Switching models** (for example to a fine-tuned Gemma on Modal): run a second scorer with that model's settings so it scores in shadow mode, compare the two, then `models activate NAME REVISION`.
  Keep the BERT scorer running as the fallback.
- **Handing the VM to the lab**: restore the latest backup into a lab-owned VM set up with the same steps.
  Then move the DNS A record and the GitHub environment secrets to it.
