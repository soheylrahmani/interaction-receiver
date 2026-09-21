# PostgreSQL

Compose uses the public `postgres:16-alpine` image. No private registry is required.

Optional SQL in `postgres/init/` is mounted to `/docker-entrypoint-initdb.d` and runs **only on first boot** of an empty volume.

- Keep dumps and production SQL out of git (see root `.gitignore`)
- Application tables are created by SQLAlchemy `create_all` when the API starts
