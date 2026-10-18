# Flight Logbook

A personal Django flight logbook for tracking flight time, currency, and license
progress. Data entry and dashboards run in Django, backed by PostgreSQL.

## Local development

Create an untracked `.env` file with local values:

```dotenv
SECRET_KEY=replace-with-a-local-development-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://localhost:8080
CARTO_API_KEY=your-carto-key
POSTGRES_DB=flightlogbook
POSTGRES_USER=flightlogbook
POSTGRES_PASSWORD=replace-with-a-local-password
POSTGRES_HOST=db
POSTGRES_PORT=5432
POSTGRES_HOST_PORT=5433
```

Start the application:

```sh
sh start.sh
```

The development Compose override builds the local image, mounts the source, and
runs Django's development server. The entrypoint applies migrations. Open
<http://localhost:8080/> or <http://localhost:8080/admin/>.

To create an administrator:

```sh
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec web python manage.py createsuperuser
```

Add the pilot record through the admin before using dashboards that expect it.

`POSTGRES_PORT` is the port Django connects to, normally `5432` within Docker.
`POSTGRES_HOST_PORT` controls the database port published on the host and defaults
to `5433`. Set a different host port for each project sharing the same server.
Separate Compose projects can all use `db:5432` internally.

## Production deployment

`.github/workflows/deploy.yml` calls
`beirern/django-deploy/.github/workflows/deploy.yml@v1.0.0` on pushes to `main` or
manual runs on `main`. `.releaserc.json` configures this application's releases:
breaking changes bump major versions, `feat` bumps minor, and other included
commits bump patch. With no previous release tags, the first release normally
starts at `1.0.0`. Versions are independent of the shared workflow's version.

The workflow creates a Git tag and GitHub release, builds the released commit,
pushes version and `sha-<full-sha>` image tags to ECR, and deploys the versioned
image through SSH and Docker Compose. It does not publish a `latest` image tag.
No new release means no build or deployment. Production merges
`docker-compose.yml` with `docker-compose.prod.yml`, which requires the released
`IMAGE`. Development keeps the local image default without needing `IMAGE`.

Configure these **repository secrets** in this application repository:

- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION`
- `ECR_REGISTRY`
- `ECR_REPOSITORY`

Configure these secrets in the **production environment**:

- `SERVER_HOST`
- `SERVER_USER`
- `SERVER_SSH_KEY`
- `SERVER_KNOWN_HOSTS`: verified OpenSSH host-key entry matching `SERVER_HOST`.
- `APP_ENV`: complete multiline production dotenv contents, using the settings
  above with production credentials, `DEBUG=False`, and the production domain.
  Do not include `IMAGE`; the workflow supplies it.

The caller grants the GitHub token release permissions. No personal access token
is needed. Preserve existing database credentials when moving them to `APP_ENV`.

The server must have Docker and a Compose plugin supporting `up --wait`, and the
SSH account must run Docker without sudo. The caller uses the absolute directory
`/home/ubuntu/flight-logbook`; confirm that this matches the existing deployment
account's home directory. Keep the existing directory and Compose project name
to retain the existing PostgreSQL volume. Back up the database before the first
deployment with the new workflow.

The application entrypoint runs migrations and collects static files. Deployment
waits for PostgreSQL readiness and an HTTP 200 from Django's admin login page.
The HTTP check uses a configured allowed host; it does not verify public DNS,
the reverse proxy, or TLS. Configure those on the server separately.

A GitHub release is created before build/deployment and does not prove deployment
succeeded. After a failed build or deployment, use **Re-run failed jobs** to keep
the release outputs. A new manual run does not force a release. There is no
automatic rollback, and migrations may already have run when deployment fails.

See [django-deploy](https://github.com/beirern/django-deploy) for the shared
workflow contract. Updating the pinned workflow version is an explicit change.

## Static export

The optional `python manage.py export_static` command generates `static_site/`.
That directory is ignored by Git and is not deployed by the production workflow.
