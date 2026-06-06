#!/usr/bin/env bash
# =============================================================================
# Agora Firecracker microVM Setup Script
# -----------------------------------------------------------------------------
# This script installs and configures Firecracker for use with Agora's
# agent sandboxing system. Firecracker provides lightweight microVMs for
# running agent code in isolated environments.
#
# Prerequisites:
#   - Linux (x86_64 or aarch64) with KVM support
#   - /dev/kvm must be accessible
#   - root or sudo privileges for installation
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info()  { echo -e "${CYAN}[INFO]${NC}  $1"; }
log_ok()    { echo -e "${GREEN}[OK]${NC}    $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Configuration
FIRECRACKER_VERSION="${FIRECRACKER_VERSION:-1.8.1}"
INSTALL_DIR="${FIRECRACKER_INSTALL_DIR:-/usr/local/bin}"
KERNEL_DIR="$PROJECT_ROOT/firecracker/kernel"
ROOTFS_DIR="$PROJECT_ROOT/firecracker/rootfs"
CONFIG_DIR="$PROJECT_ROOT/firecracker/config"

# Detect architecture
ARCH="$(uname -m)"
case "$ARCH" in
    x86_64)  FIRECRACKER_ARCH="x86_64"  ;;
    aarch64) FIRECRACKER_ARCH="aarch64" ;;
    arm64)   FIRECRACKER_ARCH="aarch64" ;;
    *)
        log_error "Unsupported architecture: $ARCH"
        log_info "Firecracker supports x86_64 and aarch64 only."
        exit 1
        ;;
esac

# ---------------------------------------------------------------------------
# Step 1: Check prerequisites
# ---------------------------------------------------------------------------
log_info "Step 1/6: Checking prerequisites..."

# Check for KVM
if [ ! -c /dev/kvm ] 2>/dev/null; then
    log_error "/dev/kvm not found. KVM is required for Firecracker."
    log_info "Ensure you are running on a Linux host with hardware virtualization."
    log_info "Check with: kvm-ok (from cpu-checker package)"
    exit 1
fi
log_ok "KVM device found at /dev/kvm"

# Check for sudo
if ! command -v sudo &>/dev/null; then
    log_error "sudo is required for installation. Please install it first."
    exit 1
fi

# ---------------------------------------------------------------------------
# Step 2: Download Firecracker binary (if not present)
# ---------------------------------------------------------------------------
log_info "Step 2/6: Checking for existing Firecracker installation..."

FIRECRACKER_BIN="$INSTALL_DIR/firecracker"
FIRECRACKER_VERSION_CURRENT=""
if [ -f "$FIRECRACKER_BIN" ]; then
    FIRECRACKER_VERSION_CURRENT="$("$FIRECRACKER_BIN" --version 2>/dev/null | head -1 || true)"
fi

if [ -n "$FIRECRACKER_VERSION_CURRENT" ] && echo "$FIRECRACKER_VERSION_CURRENT" | grep -q "$FIRECRACKER_VERSION"; then
    log_ok "Firecracker v$FIRECRACKER_VERSION already installed at $FIRECRACKER_BIN"
else
    log_info "Downloading Firecracker v$FIRECRACKER_VERSION ($FIRECRACKER_ARCH)..."

    DOWNLOAD_URL="https://github.com/firecracker-microvm/firecracker/releases/download/v${FIRECRACKER_VERSION}/firecracker-v${FIRECRACKER_VERSION}-${FIRECRACKER_ARCH}.tgz"
    TMP_DIR="$(mktemp -d)"
    TARBALL="$TMP_DIR/firecracker.tgz"

    curl -fsSL "$DOWNLOAD_URL" -o "$TARBALL" || {
        log_error "Failed to download Firecracker from $DOWNLOAD_URL"
        rm -rf "$TMP_DIR"
        exit 1
    }

    tar -xzf "$TARBALL" -C "$TMP_DIR" || {
        log_error "Failed to extract Firecracker tarball."
        rm -rf "$TMP_DIR"
        exit 1
    }

    # Install the binary
    sudo mv "$TMP_DIR/release-v${FIRECRACKER_VERSION}-${FIRECRACKER_ARCH}/firecracker-v${FIRECRACKER_VERSION}-${FIRECRACKER_ARCH}" "$FIRECRACKER_BIN" || {
        log_error "Failed to move Firecracker binary to $INSTALL_DIR."
        rm -rf "$TMP_DIR"
        exit 1
    }
    sudo chmod +x "$FIRECRACKER_BIN"

    # Cleanup
    rm -rf "$TMP_DIR"

    log_ok "Firecracker v$FIRECRACKER_VERSION installed at $FIRECRACKER_BIN"
fi

# Also install jailer if available (used for Firecracker's microVM sandboxing)
JAILER_BIN="$INSTALL_DIR/jailer"
if [ ! -f "$JAILER_BIN" ]; then
    log_info "Downloading jailer binary..."
    JAILER_URL="https://github.com/firecracker-microvm/firecracker/releases/download/v${FIRECRACKER_VERSION}/jailer-v${FIRECRACKER_VERSION}-${FIRECRACKER_ARCH}.tgz"
    TMP_DIR="$(mktemp -d)"

    if curl -fsSL "$JAILER_URL" -o "$TMP_DIR/jailer.tgz" 2>/dev/null; then
        tar -xzf "$TMP_DIR/jailer.tgz" -C "$TMP_DIR"
        sudo mv "$TMP_DIR/release-v${FIRECRACKER_VERSION}-${FIRECRACKER_ARCH}/jailer-v${FIRECRACKER_VERSION}-${FIRECRACKER_ARCH}" "$JAILER_BIN" 2>/dev/null || true
        sudo chmod +x "$JAILER_BIN" 2>/dev/null || true
        log_ok "Jailer installed at $JAILER_BIN"
    else
        log_warn "Jailer binary not available for download. Skipping."
    fi
    rm -rf "$TMP_DIR"
else
    log_ok "Jailer already installed."
fi

# ---------------------------------------------------------------------------
# Step 3: Set up kernel and rootfs directories
# ---------------------------------------------------------------------------
log_info "Step 3/6: Creating Firecracker resource directories..."

mkdir -p "$KERNEL_DIR" "$ROOTFS_DIR" "$CONFIG_DIR"
log_ok "Directories created:"
log_info "  Kernel images: $KERNEL_DIR"
log_info "  Root filesystems: $ROOTFS_DIR"
log_info "  VM configs: $CONFIG_DIR"

# ---------------------------------------------------------------------------
# Step 4: Download a default kernel and rootfs (if not present)
# ---------------------------------------------------------------------------
log_info "Step 4/6: Downloading default kernel and rootfs..."

KERNEL_IMAGE="$KERNEL_DIR/vmlinux-${FIRECRACKER_VERSION}.bin"
if [ ! -f "$KERNEL_IMAGE" ]; then
    log_info "Downloading kernel image (this may take a moment)..."
    KERNEL_URL="https://s3.amazonaws.com/spec.ccfc.min/img/quickstart_guide/${ARCH}/kernels/vmlinux.bin"
    curl -fsSL "$KERNEL_URL" -o "$KERNEL_IMAGE" || {
        log_warn "Failed to download default kernel image."
        log_info "You can provide your own kernel at: $KERNEL_DIR"
    }
    log_ok "Kernel image saved to $KERNEL_IMAGE"
else
    log_ok "Kernel image already exists."
fi

ROOTFS_IMAGE="$ROOTFS_DIR/rootfs.ext4"
if [ ! -f "$ROOTFS_IMAGE" ]; then
    log_info "Downloading root filesystem (this may take a moment)..."
    ROOTFS_URL="https://s3.amazonaws.com/spec.ccfc.min/img/quickstart_guide/${ARCH}/rootfs/bionic.rootfs.ext4"
    curl -fsSL "$ROOTFS_URL" -o "$ROOTFS_IMAGE" || {
        log_warn "Failed to download default rootfs image."
        log_info "You can provide your own rootfs at: $ROOTFS_DIR"
    }
    log_ok "Root filesystem saved to $ROOTFS_IMAGE"
else
    log_ok "Root filesystem already exists."
fi

# ---------------------------------------------------------------------------
# Step 5: Configure networking for Firecracker
# ---------------------------------------------------------------------------
log_info "Step 5/6: Configuring Firecracker networking..."

# Create a dedicated bridge for Firecracker microVMs if it doesn't exist
BRIDGE_NAME="agora-fcbr0"
BRIDGE_SUBNET="172.20.0.0/16"
TAP_PREFIX="fc-tap"

if ! ip link show "$BRIDGE_NAME" &>/dev/null 2>&1; then
    log_info "Creating bridge network: $BRIDGE_NAME ($BRIDGE_SUBNET)"
    sudo ip link add name "$BRIDGE_NAME" type bridge 2>/dev/null || {
        log_warn "Could not create bridge. You may need to run with sudo or configure manually."
    }
    sudo ip addr add "${BRIDGE_SUBNET%.*}.1/16" dev "$BRIDGE_NAME" 2>/dev/null || true
    sudo ip link set "$BRIDGE_NAME" up 2>/dev/null || true

    # Create a default tap device
    TAP_DEV="${TAP_PREFIX}-0"
    sudo ip tuntap add dev "$TAP_DEV" mode tap 2>/dev/null || true
    sudo ip link set "$TAP_DEV" master "$BRIDGE_NAME" 2>/dev/null || true
    sudo ip link set "$TAP_DEV" up 2>/dev/null || true

    log_ok "Bridge $BRIDGE_NAME created with TAP device $TAP_DEV"
else
    log_ok "Bridge $BRIDGE_NAME already exists."
fi

# Enable IP forwarding (required for microVM networking)
if [ "$(cat /proc/sys/net/ipv4/ip_forward)" != "1" ]; then
    log_info "Enabling IP forwarding..."
    sudo sysctl -w net.ipv4.ip_forward=1 2>/dev/null || true
    # Make it persistent
    echo "net.ipv4.ip_forward=1" | sudo tee -a /etc/sysctl.d/99-agora-firecracker.conf >/dev/null 2>&1 || true
    log_ok "IP forwarding enabled."
fi

# Set up iptables NAT for microVM internet access
if ! sudo iptables -t nat -C POSTROUTING -s "$BRIDGE_SUBNET" -j MASQUERADE 2>/dev/null; then
    log_info "Setting up iptables NAT for microVM outbound traffic..."
    sudo iptables -t nat -A POSTROUTING -s "$BRIDGE_SUBNET" -j MASQUERADE 2>/dev/null || true
    log_ok "NAT rule added."
fi

# ---------------------------------------------------------------------------
# Step 6: Create a default Firecracker config
# ---------------------------------------------------------------------------
log_info "Step 6/6: Creating default Firecracker configuration..."

DEFAULT_CONFIG="$CONFIG_DIR/default_vm.json"
if [ ! -f "$DEFAULT_CONFIG" ]; then
    cat > "$DEFAULT_CONFIG" << 'VMCONFIG'
{
  "boot-source": {
    "kernel_image_path": "../kernel/vmlinux-1.8.1.bin",
    "boot_args": "console=ttyS0 reboot=k panic=1 pci=off"
  },
  "drives": [
    {
      "drive_id": "rootfs",
      "path_on_host": "../rootfs/rootfs.ext4",
      "is_root_device": true,
      "is_read_only": false
    }
  ],
  "machine-config": {
    "vcpu_count": 2,
    "mem_size_mib": 512,
    "smt": false
  },
  "network-interfaces": [
    {
      "iface_id": "eth0",
      "guest_mac": "06:00:AC:10:00:02",
      "host_dev_name": "fc-tap-0"
    }
  ]
}
VMCONFIG
    log_ok "Default VM config created at $DEFAULT_CONFIG"
else
    log_ok "VM config already exists."
fi

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
echo ""
echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}  Firecracker setup complete!${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""
echo -e "  Firecracker binary:  ${CYAN}$FIRECRACKER_BIN${NC}"
echo -e "  Version:             ${CYAN}v$FIRECRACKER_VERSION (${FIRECRACKER_ARCH})${NC}"
echo -e "  Bridge network:      ${CYAN}$BRIDGE_NAME ($BRIDGE_SUBNET)${NC}"
echo -e "  Kernel directory:    ${CYAN}$KERNEL_DIR${NC}"
echo -e "  Rootfs directory:    ${CYAN}$ROOTFS_DIR${NC}"
echo -e "  Config directory:    ${CYAN}$CONFIG_DIR${NC}"
echo ""
echo -e "  Quick test:"
echo -e "    ${YELLOW}sudo $FIRECRACKER_BIN --api-sock /tmp/firecracker.socket${NC}"
echo ""
echo -e "  Note: Firecracker requires root or the 'firecracker' user"
echo -e "  group membership to access /dev/kvm and create TAP devices."
echo ""
