# Cloud Run Local Development Setup

## Docker Configuration

This project uses different Dockerfiles for different environments to optimize build size and speed:

### Files

1. **`Dockerfile`** - Production deployment (includes all dependencies)
   - Used by Cloud Build for production deployments
   - Includes GPU/CUDA dependencies for full functionality
   
2. **`Dockerfile.cloudrun`** - Local Cloud Run debugging
   - Used by VS Code Cloud Code for "Debug Locally"
   - Excludes GPU/CUDA dependencies (~1.8 GB saved)
   - Uses `requirements-cloud-run.txt`
   
3. **`requirements.txt`** - Full production dependencies
   - Includes NVIDIA CUDA packages for PyTorch
   - Used for production Cloud Run deployments
   
4. **`requirements-cloud-run.txt`** - Lightweight dependencies
   - Excludes GPU packages (Cloud Run doesn't support GPU)
   - Excludes torch (large package, use on-demand)
   - Used for local development/debugging

### Cloud Run Local Debugging

When using **"Cloud Run: Debug Locally"** in VS Code:

1. Cloud Code automatically uses `Dockerfile.cloudrun` (configured in `.vscode/cloudcode.json`)
2. Build size is reduced from ~3 GB to under 1 GB
3. Works with Docker Desktop's 8 GB disk limit

### Docker Resource Requirements

**Minimum Docker Settings:**
- Disk: 8 GB (for local development)
- Memory: 4 GB
- CPUs: 2

**Recommended for Production Builds:**
- Disk: 20-25 GB
- Memory: 8 GB
- CPUs: 4

### Troubleshooting

**"No space left on device" during build:**

1. Clean up Docker:
   ```bash
   docker system prune -a --volumes -f
   ```

2. Stop any running containers:
   ```bash
   docker stop $(docker ps -aq)
   docker rm $(docker ps -aq)
   ```

3. Increase Docker disk limit:
   - Docker Desktop → Settings → Resources → Disk image size → 20 GB

**Build fails with package conflicts:**
- Ensure you're using the correct Dockerfile for your environment
- Local debug: `Dockerfile.cloudrun`
- Production: `Dockerfile`

### Key Differences

| Feature | Production | Local Debug |
|---------|-----------|-------------|
| NVIDIA CUDA | ✅ Included | ❌ Excluded |
| PyTorch | ✅ Included | ❌ Excluded |
| Build Size | ~3 GB | ~1 GB |
| Build Time | ~5-10 min | ~2-3 min |
| Docker Disk | 20+ GB | 8 GB |

### Notes

- Cloud Run does not support GPU, so CUDA packages are only needed for local development with GPU
- The lightweight version is sufficient for most development and debugging tasks
- Production deployments on Cloud Run use the full `Dockerfile` via Cloud Build which has more resources
