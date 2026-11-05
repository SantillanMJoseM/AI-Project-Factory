# LXC Requirements

## Host (Proxmox)

- Proxmox VE 8.x
- Storage: local-lvm or equivalent with at least 32 GB for container rootfs
- Network bridge with DHCP or static IP allocation
- Access to the internet for package installation and model provider

## Container

| Resource | Minimum | Recommended |
|---|---|---|
| OS | Debian 13 | Debian 13 |
| RAM | 2 GB | 4 GB |
| CPU | 2 cores | 4 cores |
| Disk | 16 GB | 32 GB |

## Required features

```bash
--features nesting=1,keyctl=1
```

`nesting=1` is required for mount namespaces inside the container.
`keyctl=1` may be required by some OpenCode dependencies.

## Required packages

```bash
apt-get install -y git python3 python3-pip python3-venv curl util-linux
```

## Network

The container needs outbound access to:
- GitHub (clone repository)
- PyPI (Python packages)
- NPM registry or opencode.ai (OpenCode binary)
- Model provider endpoint (Beam/OpenCode)

No inbound ports are required by default.
