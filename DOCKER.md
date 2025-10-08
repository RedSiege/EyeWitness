# EyeWitness Docker Guide

> **⚠️ Docker Support Status: In Development**
> 
> Docker functionality is currently under development and may not work as expected. 
> For reliable usage, please use the native installation options documented in README.md.
> 
> This documentation is maintained for future Docker implementation.

This guide covers running EyeWitness in a Docker container, which eliminates the need to install Python, Chromium, or any dependencies on your host system.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Building the Image](#building-the-image)
- [Running EyeWitness](#running-eyewitness)
- [Platform-Specific Examples](#platform-specific-examples)
- [Docker Compose](#docker-compose)
- [Troubleshooting](#troubleshooting)
- [Advanced Usage](#advanced-usage)

## Prerequisites

- Docker installed on your system
  - **Linux**: `sudo apt install docker.io` or follow [Docker's official guide](https://docs.docker.com/engine/install/)
  - **Windows**: Install [Docker Desktop](https://www.docker.com/products/docker-desktop/)
  - **macOS**: Install [Docker Desktop](https://www.docker.com/products/docker-desktop/)

That's it! No Python, Chromium, or other dependencies needed.

## Quick Start

```bash
# Clone the repository
git clone https://github.com/RedSiege/EyeWitness.git
cd EyeWitness

# Build the Docker image
docker build -t eyewitness .

# Run EyeWitness
docker run --rm -v $(pwd):/data eyewitness -f /data/urls.txt -d /data/output
```

## Building the Image

### Standard Build
```bash
docker build -t eyewitness .
```

### Build with Custom Tag
```bash
docker build -t eyewitness:latest .
docker build -t mycompany/eyewitness:v1.0 .
```

### Build Arguments
```bash
# Build with custom image name
docker build -t mycompany/eyewitness:chromium .
```

## Running EyeWitness

### Basic Usage

The key to using Docker with EyeWitness is understanding volume mounts. You need to mount:
- Your input files (URLs, XML files) into the container
- An output directory for results

#### Linux/macOS:
```bash
# Single URL
docker run --rm eyewitness --single https://example.com -d /output

# File input - current directory
docker run --rm -v $(pwd):/data eyewitness -f /data/urls.txt -d /data/output

# File input - specific paths
docker run --rm \
  -v /path/to/urls.txt:/data/urls.txt \
  -v /path/to/output:/output \
  eyewitness -f /data/urls.txt -d /output
```

#### Windows (PowerShell):
```powershell
# Single URL
docker run --rm eyewitness --single https://example.com -d /output

# File input - current directory
docker run --rm -v ${PWD}:/data eyewitness -f /data/urls.txt -d /data/output

# File input - specific paths
docker run --rm `
  -v C:\path\to\urls.txt:/data/urls.txt `
  -v C:\path\to\output:/output `
  eyewitness -f /data/urls.txt -d /output
```

#### Windows (Command Prompt):
```cmd
# File input - current directory
docker run --rm -v %cd%:/data eyewitness -f /data/urls.txt -d /data/output

# File input - specific paths
docker run --rm ^
  -v C:\path\to\urls.txt:/data/urls.txt ^
  -v C:\path\to\output:/output ^
  eyewitness -f /data/urls.txt -d /output
```

### Common Options

```bash
# Process Nmap XML
docker run --rm -v $(pwd):/data eyewitness -x /data/nmap_scan.xml -d /data/output

# Custom timeout and threads
docker run --rm -v $(pwd):/data eyewitness \
  -f /data/urls.txt \
  -d /data/output \
  --timeout 60 \
  --threads 5

# With proxy
docker run --rm -v $(pwd):/data eyewitness \
  -f /data/urls.txt \
  -d /data/output \
  --proxy-ip 127.0.0.1 \
  --proxy-port 8080

# Resume a scan
docker run --rm -v $(pwd):/data eyewitness \
  --resume /data/output/ew.db \
  -d /data/output
```

## Platform-Specific Examples

### Linux Examples

```bash
# Create test file
echo -e "https://example.com\nhttps://google.com" > urls.txt

# Run scan
docker run --rm -v $(pwd):/data eyewitness -f /data/urls.txt -d /data/output

# View results
xdg-open output/report.html  # Linux
# google-chrome output/report.html  # Alternative
```

### Windows PowerShell Examples

```powershell
# Create test file
@"
https://example.com
https://google.com
"@ | Out-File -FilePath urls.txt

# Run scan
docker run --rm -v ${PWD}:/data eyewitness -f /data/urls.txt -d /data/output

# View results
Start-Process output\report.html
```

### Creating an Alias

#### Linux/macOS (.bashrc or .zshrc):
```bash
alias eyewitness='docker run --rm -v $(pwd):/data eyewitness'

# Usage after alias:
eyewitness -f /data/urls.txt -d /data/output
```

#### Windows PowerShell ($PROFILE):
```powershell
function eyewitness {
    docker run --rm -v ${PWD}:/data eyewitness $args
}

# Usage after function:
eyewitness -f /data/urls.txt -d /data/output
```

## Docker Compose

For easier usage, create a `docker-compose.yml` file:

```yaml
version: '3.8'

services:
  eyewitness:
    build: .
    image: eyewitness:latest
    volumes:
      - ./input:/data
      - ./output:/output
    command: ["-f", "/data/urls.txt", "-d", "/output"]
```

Usage:
```bash
# Place urls.txt in ./input directory
mkdir input output
cp urls.txt input/

# Run with docker-compose
docker-compose run --rm eyewitness

# Or with different arguments
docker-compose run --rm eyewitness --single https://example.com -d /output
```

## Troubleshooting

### Permission Issues

If output files are owned by root:

#### Option 1: Run container as your user
```bash
# Linux/macOS
docker run --rm --user $(id -u):$(id -g) -v $(pwd):/data eyewitness -f /data/urls.txt -d /data/output

# Windows (typically not needed)
docker run --rm --user 1000:1000 -v ${PWD}:/data eyewitness -f /data/urls.txt -d /data/output
```

#### Option 2: Fix permissions after
```bash
# Linux/macOS
sudo chown -R $USER:$USER output/

# Windows (PowerShell as Admin)
takeown /r /f output
```

### Network Issues

If container can't reach targets:

```bash
# Use host network (Linux only)
docker run --rm --network host -v $(pwd):/data eyewitness -f /data/urls.txt -d /data/output

# Check DNS
docker run --rm eyewitness --single https://8.8.8.8 -d /output
```

### Display Issues

If you see Xvfb errors:

```bash
# Increase Xvfb wait time (rebuild image)
# Edit Dockerfile entrypoint sleep time

# Or run with specific display
docker run --rm -e DISPLAY=:99 -v $(pwd):/data eyewitness -f /data/urls.txt -d /data/output
```

### Container Logs

```bash
# Run with logs
docker run --rm -v $(pwd):/data eyewitness -f /data/urls.txt -d /data/output 2>&1 | tee eyewitness.log

# Debug mode
docker run --rm -it --entrypoint /bin/bash eyewitness
# Then manually run: /entrypoint.sh -f /data/urls.txt -d /data/output
```

## Advanced Usage

### Building for Different Architectures

```bash
# Build for ARM64 (Apple Silicon, ARM servers)
docker buildx build --platform linux/arm64 -t eyewitness:arm64 .

# Build for multiple platforms
docker buildx build --platform linux/amd64,linux/arm64 -t eyewitness:multiarch .
```

### Using Pre-built Images

If pre-built images are available on Docker Hub:

```bash
# Pull instead of building
docker pull redsiege/eyewitness:latest

# Run using pulled image
docker run --rm -v $(pwd):/data redsiege/eyewitness -f /data/urls.txt -d /data/output
```

### Resource Limits

```bash
# Limit memory and CPU
docker run --rm \
  --memory="2g" \
  --cpus="2" \
  -v $(pwd):/data \
  eyewitness -f /data/urls.txt -d /data/output
```

### Batch Processing

```bash
#!/bin/bash
# Process multiple URL files

for file in url_lists/*.txt; do
    output_dir="output/$(basename $file .txt)"
    echo "Processing $file -> $output_dir"
    docker run --rm \
        -v $(pwd)/url_lists:/data \
        -v $(pwd)/$output_dir:/output \
        eyewitness -f /data/$(basename $file) -d /output
done
```

## Security Considerations

1. **Container Isolation**: EyeWitness runs in an isolated container, protecting your host system
2. **Non-root User**: Container runs as non-root user by default (can be overridden)
3. **Read-only Filesystem**: You can add `--read-only` flag for extra security:
   ```bash
   docker run --rm --read-only -v $(pwd):/data eyewitness -f /data/urls.txt -d /data/output
   ```

## FAQ

**Q: Why is the image so large (~800MB)?**
A: The image includes Chromium, Python, and all dependencies. This is a one-time download and optimized for the Chromium-only architecture.

**Q: Can I run multiple instances?**
A: Yes! Docker provides isolation between containers:
```bash
# Terminal 1
docker run --rm -v $(pwd):/data eyewitness -f /data/urls1.txt -d /data/output1

# Terminal 2
docker run --rm -v $(pwd):/data eyewitness -f /data/urls2.txt -d /data/output2
```

**Q: How do I update EyeWitness?**
A: Pull the latest code and rebuild:
```bash
git pull
docker build -t eyewitness .
```

**Q: Can I use this in CI/CD pipelines?**
A: Yes! Docker makes it perfect for CI/CD:
```yaml
# GitLab CI example
eyewitness:
  image: eyewitness:latest
  script:
    - python /app/EyeWitness.py -f urls.txt -d output
  artifacts:
    paths:
      - output/
```

## Support

For issues specific to Docker:
1. Check this guide's [Troubleshooting](#troubleshooting) section
2. Ensure Docker is properly installed: `docker --version`
3. Check Docker daemon is running: `docker ps`
4. Review container logs for errors

For EyeWitness functionality issues, see the main README.md.