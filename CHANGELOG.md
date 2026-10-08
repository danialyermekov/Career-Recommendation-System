# Changelog

## 1.1 — Public Beta candidate

- Add clean public About, Feedback, Changelog and Roadmap paths, moderated publication with explicit consent, and authenticated feature voting.
- Keep the public release timeline limited to the owner-confirmed 2026-10-07 MVP launch; this candidate is not listed as shipped.

- Replace shared SQLite persistence with private Supabase PostgreSQL accounts and Alembic migrations.
- Add Supabase Google/GitHub OAuth with PKCE, session refresh, guest access and account management.
- Check ownership for history, result state, roadmap progress, course preferences and AI context.
- Keep guest recommendations temporary and separate from registered accounts.
- Add real anonymous/authenticated feedback, basic abuse limits and a local export command.
- Add localized About, Contact, Privacy, Terms and Disclaimer pages and a shared footer.
- Pass public Supabase configuration at Docker build time; keep backend secrets at runtime.
- Preserve legacy SQLite for archival backup and rollback, without assigning anonymous history to new users.

This is a release candidate. Real provider login, optional administrator-key configuration and production promotion remain explicit release checks; this changelog is not evidence of deployment.
