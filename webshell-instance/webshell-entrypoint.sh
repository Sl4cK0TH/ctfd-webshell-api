#!/bin/bash
set -e

# Create user with provided username
USERNAME=${USERNAME:-ctfplayer}
TEAM_NAME=${TEAM_NAME:-team}

# Create user if it doesn't exist
if ! id "$USERNAME" &>/dev/null; then
    useradd -m -s /bin/bash "$USERNAME"
    echo "$USERNAME ALL=(ALL) NOPASSWD: /usr/bin/apt, /usr/bin/apt-get, /usr/bin/pip3" >> /etc/sudoers
fi

# Set up home directory
USER_HOME="/home/$USERNAME"

# Create workspace directory for the user to work in
mkdir -p "$USER_HOME/workspace"

# Create symlink to challenges for easy access
ln -sf /challenges "$USER_HOME/challenges"

# Create welcome message
cat > "$USER_HOME/.motd" << EOF
═══════════════════════════════════════════════════════════════

   🏴 Welcome to RSU CTF 2026 Webshell! 🏴

   Team: $TEAM_NAME
   User: $USERNAME

   Available Tools:
   • Python 3 + pwntools, requests, pycryptodome
   • nmap, netcat, socat, tcpdump
   • gdb, binutils, ropper
   • vim, nano, tmux

   Challenge Files: ~/challenges (read-only)
   Your Workspace:   ~/workspace (work here!)
   
   Tip: Copy challenge files to workspace before working:
        cp -r ~/challenges/PWN/Doors ~/workspace/
   
   Good luck and have fun!

═══════════════════════════════════════════════════════════════

EOF

# Add motd to bashrc
if ! grep -q ".motd" "$USER_HOME/.bashrc" 2>/dev/null; then
    echo 'cat ~/.motd 2>/dev/null' >> "$USER_HOME/.bashrc"
fi

# Set proper ownership
chown -R "$USERNAME:$USERNAME" "$USER_HOME"

# Start ttyd with the user's shell (no authentication - handled by CTFd token)
exec ttyd \
    --port 7681 \
    --writable \
    --max-clients 3 \
    su - "$USERNAME"
