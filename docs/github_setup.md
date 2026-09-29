# Publish to GitHub

## Create the repository

Create a new empty GitHub repository named `enterprise-infrastructure-monitoring`. Do not initialize it with a README, license, or `.gitignore`, because those files are already included.

## Push this project

Run these commands from the project folder, replacing `YOUR-USERNAME`:

```bash
git init
git add .
git commit -m "Build enterprise infrastructure monitoring lab"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/enterprise-infrastructure-monitoring.git
git push -u origin main
```

If the folder is already a Git repository, skip `git init`. If `origin` already exists, check it with `git remote -v` before changing anything.

## Recommended repository settings

1. Add the description: `Infrastructure monitoring, incident management, SLA escalation, and Power BI operations reporting lab.`
2. Add topics: `python`, `infrastructure-monitoring`, `incident-management`, `power-bi`, `powershell`, `bash`, `sqlite`, `vmware`, `azure`, `aws`, `devops`.
3. Keep the repository public only after checking that `.env`, database files, credentials, IP addresses, and production exports are absent.
4. Enable branch protection after the first push if you want to demonstrate pull-request practice.
5. Confirm the Actions tab shows a successful CI run.

## Suggested first release

After CI succeeds:

```bash
git tag -a v1.0.0 -m "Initial portfolio release"
git push origin v1.0.0
```

