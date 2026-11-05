# Fresh Install Guide — Debian 13 LXC on Proxmox

## 1. Create the LXC

From Proxmox host:

```bash
pct create 10050 local:vztmpl/debian-13-standard_13.0-1_amd64.tar.zst \
  --hostname ai-factory-pilot \
  --storage local-lvm \
  --rootfs 32 \
  --memory 4096 \
  --cores 4 \
  --net0 name=eth0,bridge=vmbr0,ip=dhcp \
  --features nesting=1,keyctl=1
pct start 10050
pct enter 10050
```

Enable user namespaces:

```bash
echo "kernel.unprivileged_userns_clone=1" >> /etc/sysctl.d/99-factory.conf
sysctl --system
```

## 2. Install base packages

Inside the LXC:

```bash
apt-get update
apt-get install -y git python3 python3-pip python3-venv curl util-linux
```

## 3. Install OpenCode

```bash
# Option A: npm (if Node.js is available)
apt-get install -y npm
npm install -g @opencode/cli@2.2.5

# Option B: download the binary from opencode.ai and place it in /usr/local/bin
```

Verify:

```bash
opencode --version
```

## 4. Configure provider

Edit `~/.bashrc` or `/etc/profile.d/factory.sh`:

```bash
export OPENCODE_API_KEY="your-key"
```

## 5. Install Factory

```bash
cd /opt
curl -L -o install.sh https://raw.githubusercontent.com/SantillanMJoseM/AI-Project-Factory/feature/r5.2a-implementation/install/scripts/install.sh
bash install.sh /opt/ai-project-factory
```

## 6. Verify

```bash
cd /opt/ai-project-factory
bash install/scripts/verify.sh
python3 tests/run_all.py
```

## 7. Run preflight

```bash
python3 -m orchestration.preflight
```
