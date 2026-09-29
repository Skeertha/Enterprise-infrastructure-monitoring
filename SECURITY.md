# Security Policy

This project is a lab. Do not connect it to production systems without an organizational review.

## Credential handling

- Never commit `.env`, cloud access keys, vCenter passwords, tokens, or connection strings.
- Use read-only service accounts with the minimum required permissions.
- Prefer environment variables or an approved secrets manager.
- Rotate any credential that is accidentally committed; deleting the file is not sufficient.

## Data handling

- Use synthetic asset names, IP addresses, incidents, and exports in a public portfolio.
- Remove production logs and screenshots before committing.
- Review generated CSV files because they may contain hostnames, owners, or incident details.

## Reporting a vulnerability

Open a private security advisory in the GitHub repository. Do not include live credentials or sensitive production evidence.

