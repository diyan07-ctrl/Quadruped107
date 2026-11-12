set -eu
session=$(cat /tmp/quadruped107-phase6-session-path)
mkdir -p "$session/tools" "$session/arduino-data" "$session/arduino-downloads" "$session/arduino-user"
archive="$session/tools/arduino-cli_1.5.1_Linux_ARM64.tar.gz"
curl --fail --location --max-time 180 --output "$archive" https://github.com/arduino/arduino-cli/releases/download/v1.5.1/arduino-cli_1.5.1_Linux_ARM64.tar.gz
printf '1e69e077479f300614d4551334e0a33f08ee40b04315d83b8e7e0e94f0d0ee62  %s\n' "$archive" | sha256sum --check -
tar -xzf "$archive" -C "$session/tools" arduino-cli
cat > "$session/arduino-cli.yaml" <<EOF
directories:
  data: $session/arduino-data
  downloads: $session/arduino-downloads
  user: $session/arduino-user
EOF
export XDG_CACHE_HOME="$session/cache"
cli="$session/tools/arduino-cli"
"$cli" version
"$cli" --config-file "$session/arduino-cli.yaml" core update-index > "$session/arduino-index.log" 2>&1
"$cli" --config-file "$session/arduino-cli.yaml" core install arduino:avr@1.8.8 --skip-post-install --skip-pre-uninstall > "$session/arduino-core-install.log" 2>&1
"$cli" --config-file "$session/arduino-cli.yaml" core list
"$cli" --config-file "$session/arduino-cli.yaml" upload --help > "$session/uploader-help.txt"
echo 'Uploader prepared in session directory only. No board discovery, serial open, upload or post-install scripts executed.'
