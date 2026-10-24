#!/bin/sh
set -eu

asset_url='https://github.com/Oma100-tech/Zorqi-Shell/releases/latest/download/Zorqi-Setup-Linux'
temp_dir=$(mktemp -d "${TMPDIR:-/tmp}/zorqi-setup.XXXXXX")

cleanup() {
    rm -rf -- "$temp_dir"
}
trap cleanup EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM

installer="$temp_dir/Zorqi-Setup-Linux"
if command -v curl >/dev/null 2>&1; then
    curl --fail --location --silent --show-error "$asset_url" --output "$installer"
elif command -v wget >/dev/null 2>&1; then
    wget --quiet --output-document="$installer" "$asset_url"
else
    printf '%s\n' 'Install failed: curl or wget is required to download Zorqi.' >&2
    exit 1
fi

chmod 755 "$installer"
"$installer" "$@"
