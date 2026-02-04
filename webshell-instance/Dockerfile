# Webshell Instance Container
# This is the container that gets spawned for each team
# It runs ttyd with a bash shell and includes common CTF tools

FROM ubuntu:24.04

# Prevent interactive prompts during build
ENV DEBIAN_FRONTEND=noninteractive

# Install base packages and CTF tools
RUN apt-get update && apt-get install -y \
    # Essential tools
    curl \
    wget \
    git \
    vim \
    nano \
    tmux \
    htop \
    # Network tools
    netcat-openbsd \
    nmap \
    dnsutils \
    iputils-ping \
    traceroute \
    tcpdump \
    socat \
    # Development tools
    python3 \
    python3-pip \
    python3-venv \
    gcc \
    g++ \
    make \
    gdb \
    # CTF specific tools
    binutils \
    file \
    xxd \
    hexedit \
    # Crypto tools
    openssl \
    # Web tools
    jq \
    # Archive tools
    unzip \
    p7zip-full \
    # Misc
    sudo \
    locales \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Python CTF tools
RUN pip3 install --no-cache-dir --break-system-packages \
    pwntools \
    requests \
    beautifulsoup4 \
    pycryptodome \
    z3-solver \
    angr \
    ropper

# Install ttyd (web terminal)
RUN curl -L https://github.com/tsl0922/ttyd/releases/download/1.7.4/ttyd.x86_64 -o /usr/local/bin/ttyd \
    && chmod +x /usr/local/bin/ttyd

# Set up locale
RUN locale-gen en_US.UTF-8
ENV LANG=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8

# Create challenges directory and copy challenge files
RUN mkdir -p /challenges
COPY Challenges-Files/ /challenges/
# Flatten if nested Challenges-Files folder exists, then set permissions
RUN if [ -d "/challenges/Challenges-Files" ]; then \
        cp -r /challenges/Challenges-Files/* /challenges/ && \
        rm -rf /challenges/Challenges-Files; \
    fi && \
    chmod -R 755 /challenges && \
    find /challenges -type f -name "*.zip" -exec chmod 644 {} \;

# Create entrypoint script
COPY webshell-entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Default environment variables
ENV USERNAME=ctfplayer
ENV TEAM_NAME=team

# Expose ttyd port
EXPOSE 7681

# Run entrypoint
ENTRYPOINT ["/entrypoint.sh"]
