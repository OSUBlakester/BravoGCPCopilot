# Cloud Code Local Development Setup

This guide will help you and your collaborators set up local development using Google Cloud Code in VS Code.

## Prerequisites

### 1. Install Docker Desktop
Download and install Docker Desktop for Mac:
- Visit: https://www.docker.com/products/docker-desktop
- Download the Mac version (Apple Silicon or Intel)
- Install and launch Docker Desktop
- Verify installation: `docker --version`

### 2. Install Google Cloud Code Extension (Already Installed ✓)
You already have the Cloud Code extension installed in VS Code.

## Running the Application Locally

### Option 1: Using Cloud Code UI (Recommended)
1. Open VS Code in this project folder
2. Click the **Cloud Code** icon in the left sidebar (cloud icon)
3. Click **Run on Cloud Run Emulator**
4. Select the configuration: **"Cloud Run: Run/Debug Locally"**
5. The application will:
   - Build the Docker image from `Dockerfile`
   - Start the container with your application
   - Make it available at `http://localhost:8080`
6. Open your browser to `http://localhost:8080`

### Option 2: Using VS Code Debug Panel
1. Click the **Run and Debug** icon (play icon with bug) in the left sidebar
2. Select **"Cloud Run: Run/Debug Locally"** from the dropdown
3. Click the green play button
4. Same behavior as Option 1

### Option 3: Using Command Palette
1. Press `Cmd+Shift+P` (Mac) or `Ctrl+Shift+P` (Windows/Linux)
2. Type "Cloud Code: Run on Cloud Run Emulator"
3. Press Enter
4. Select the configuration when prompted

## Configuration Details

The configuration is defined in `.vscode/launch.json`:

```json
{
  "name": "Cloud Run: Run/Debug Locally",
  "type": "cloudcode.cloudrun",
  "request": "launch",
  "build": {
    "docker": {
      "path": "Dockerfile"
    }
  },
  "image": "bravo-aac-local",
  "service": {
    "name": "bravo-aac-local",
    "containerPort": 8080,
    "env": [
      {
        "name": "ENVIRONMENT",
        "value": "development"
      }
    ],
    "resources": {
      "limits": {
        "memory": "2Gi"
      }
    }
  },
  "watch": true
}
```

### What This Does:
- **Builds** your Docker image using the `Dockerfile`
- **Runs** the container locally (not on GCP)
- **Maps** port 8080 to your localhost
- **Sets** environment to "development"
- **Watches** for file changes (hot reload enabled)

## Benefits of Cloud Code Local Development

1. **No GCP Deployment Required**: Test changes instantly without deploying
2. **Faster Iteration**: Build → Test → Debug cycle in seconds
3. **Cost Effective**: No cloud resources consumed during development
4. **Identical Environment**: Same Docker container that runs in production
5. **Hot Reload**: Changes to code trigger automatic rebuilds (watch mode)
6. **Debugging**: Full VS Code debugging capabilities with breakpoints

## Accessing the Application

Once running, access at:
- **Main App**: http://localhost:8080
- **Gridpage**: http://localhost:8080/static/gridpage.html
- **Tap Interface**: http://localhost:8080/static/tap_interface.html
- **Admin Settings**: http://localhost:8080/static/admin_settings.html

## Stopping the Application

- Click the **Stop** button in the Cloud Code output panel
- Or press `Cmd+C` in the integrated terminal

## Troubleshooting

### Docker Not Running
**Error**: "Cannot connect to Docker daemon"
**Solution**: Make sure Docker Desktop is running (check menu bar for Docker icon)

### Port Already in Use
**Error**: "Port 8080 is already allocated"
**Solution**: Stop other services using port 8080, or change port in `launch.json`

### Build Failures
**Error**: Various Docker build errors
**Solution**: 
1. Check `Dockerfile` syntax
2. Ensure all files in `requirements.txt` are valid
3. Clear Docker cache: `docker system prune -a`

### Memory Issues
**Error**: Container crashes or hangs
**Solution**: Increase memory limit in `launch.json` (currently 2Gi)

## Collaboration Workflow

### For Team Members:
1. Get the project files from the project owner
2. Install Docker Desktop
3. Open project in VS Code
4. Run using Cloud Code (steps above)
5. Make changes and test locally
6. Commit changes when ready

### For Project Owner:
When you deploy to GCP dev/prod, use your existing scripts:
```bash
./deploy.sh dev   # Deploy to dev environment
./deploy.sh prod  # Deploy to production
```

## Next Steps

1. **Install Docker Desktop** if not already installed
2. **Try running the app** using Cloud Code
3. **Make a small change** to test hot reload
4. **Share this guide** with your collaborators

## Additional Resources

- [Cloud Code Documentation](https://cloud.google.com/code/docs)
- [Docker Desktop Documentation](https://docs.docker.com/desktop/)
- [VS Code Debugging](https://code.visualstudio.com/docs/editor/debugging)
