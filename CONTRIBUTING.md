# Contributing to Bravo AAC Application

## Git Workflow

This project uses a **trunk-based development** workflow with feature branches for collaborative development.

### Branch Strategy

- **`main`** - Production-ready code. All deployments to GCP are triggered automatically from this branch.
- **Feature Branches** - Short-lived branches for new features or fixes (e.g., `feature/spell-page-improvements`)

### Development Workflow

#### 1. Starting New Work

```bash
# Ensure you're on main and up to date
git checkout main
git pull origin main

# Create a feature branch (use descriptive names)
git checkout -b feature/your-feature-name
```

**Branch Naming Conventions:**
- `feature/` - New features (e.g., `feature/mood-selection-ui`)
- `fix/` - Bug fixes (e.g., `fix/settings-persistence`)
- `refactor/` - Code refactoring (e.g., `refactor/api-cleanup`)
- `docs/` - Documentation updates (e.g., `docs/deployment-guide`)

#### 2. Making Changes

```bash
# Make your changes, test locally with Minikube
# Cloud Code development: skaffold dev --profile cloud-run-dev-internal

# Stage your changes
git add .

# Commit with descriptive messages
git commit -m "Add mood selection button styling improvements"
```

**Commit Message Guidelines:**
- Use present tense ("Add feature" not "Added feature")
- First line should be a brief summary (50 chars or less)
- Include details in the body if needed

#### 3. Pushing and Creating Pull Requests

```bash
# Push your feature branch to GitHub
git push origin feature/your-feature-name
```

Then on GitHub:
1. Navigate to the repository
2. Click "Compare & pull request"
3. Fill out the PR template with:
   - What changes were made
   - Why they were made
   - How to test them
4. Request a review from your collaborator

#### 4. Code Review Process

**For Reviewers:**
- Check for code quality and consistency
- Test the changes locally if needed
- Leave constructive feedback
- Approve when ready or request changes

**For Authors:**
- Address all review comments
- Push additional commits to the same branch
- Re-request review after making changes

#### 5. Merging

Once approved:
1. Click "Merge pull request" on GitHub
2. Choose "Squash and merge" for cleaner history (optional but recommended)
3. Delete the feature branch after merging

**Important:** Merging to `main` will automatically trigger a deployment to GCP Cloud Run.

### Local Development

#### Setup
```bash
# Start Minikube development environment
skaffold dev --profile cloud-run-dev-internal
```

#### Testing Before Pushing
- Test all changes locally using Minikube
- Verify functionality works as expected
- Check browser console for errors
- Test on different screen sizes if UI changes were made

### Deployment

**Automatic Deployment:**
- Any merge to `main` triggers Cloud Build
- Cloud Build builds the Docker image
- Image is deployed to Cloud Run automatically
- Monitor deployment in GCP Console > Cloud Build

**Manual Deployment (Emergency Only):**
```bash
# Only use if automated deployment fails
./deploy.sh
```

### Rollback Procedure

If a deployment causes issues:
```bash
# Option 1: Revert the commit
git revert <commit-hash>
git push origin main

# Option 2: Roll back to previous Cloud Run revision
gcloud run services update-traffic bravogcpcopilot --to-revisions=REVISION_ID=100
```

### Best Practices

1. **Keep branches small** - Feature branches should be merged within 1-2 days
2. **Pull frequently** - Keep your branch up to date with `main`
3. **Test thoroughly** - Always test locally before pushing
4. **Write clear commits** - Future you will thank present you
5. **Communicate** - Use PR descriptions to explain context
6. **Review promptly** - Don't let PRs sit for days
7. **Delete old branches** - Clean up merged branches regularly

### Project-Specific Guidelines

#### File Structure
- `/static/` - Frontend HTML, CSS, JavaScript
- `/server.py` - FastAPI backend
- `/requirements.txt` - Python dependencies
- `/Dockerfile.cloudrun` - Production container configuration

#### Key Configuration Files
- `config.py` - Application configuration (DO NOT commit API keys)
- `config_secure.py` - Secure credentials (gitignored)
- `model_config.json` - AI model settings
- `audio_config.json` - Speech synthesis settings

#### Testing Checklist
Before opening a PR, verify:
- [ ] Local development works with Minikube
- [ ] No console errors in browser
- [ ] Changes work for both admin and regular users
- [ ] Auditory scanning still functions (if applicable)
- [ ] Settings persist correctly in Firestore
- [ ] No hardcoded credentials or API keys

### Getting Help

- Check existing documentation in project root
- Review closed PRs for examples
- Ask questions in PR comments
- Reference `DEPLOYMENT.md` for deployment details

### Emergency Contacts

- Primary: Blake Thomas
- Issues: GitHub Issues tab
- Urgent: [Add contact method]

---

**Remember:** The `main` branch deploys automatically to production. Always test thoroughly before merging!
