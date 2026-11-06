> Current outbox/worker results: [event-verification.md](event-verification.md).

> Historical infrastructure verification. For the implemented API and current test results, see [api-verification.md](api-verification.md).

# Environment and executed verification — 2026-11-05 (America/Chicago)

## Inspection and changes

Read AGENTS.md, compose.yaml, api/pom.xml, application.yml, startup script and SQL initialization before making changes. The existing compose.yaml is the canonical Compose file; no duplicate docker-compose.yml was created. Application Java source was not changed and no incident API was implemented.

Added api/Dockerfile (Maven 3.9.11/Java 21 build → non-root Java 21 JRE runtime), api/.dockerignore and scripts/verify-infra.sh. Updated README.md and AGENTS.md with Docker-only build commands.

Docker is now installed, unlike the initial scaffold session. Restricted execution initially could not access the Docker socket and rejected workspace writes as read-only; approved elevated execution succeeded. This does not establish that the user's own interactive WSL shell has the same restriction.

## Commands and actual output excerpts

`docker --version`:

```text
Docker version 29.9.2, build a82e528
```

`docker compose version`:

```text
Docker Compose version v5.6.1
```

`docker info --format '{{.ServerVersion}}'` (elevated):

```text
29.9.2
```

`docker compose -f compose.yaml config --quiet`: exit 0, no output. Repeated successfully after the port change.

Initial `docker compose -f compose.yaml up -d --wait postgres kafka kafka-init` failed:

```text
Error response from daemon: ports are not available: exposing port TCP 127.0.0.1:5432 -> 127.0.0.1:0: /forwards/expose returned unexpected status: 500
```

Created ignored .env from .env.example and set POSTGRES_PORT=55432. Retried `docker compose up -d --wait postgres kafka kafka-init`: exit 0. Only the PostgreSQL container was recreated to apply its port mapping; no volumes were deleted.

`docker compose ps -a` reported:

```text
incidentiq-kafka-1       Up (healthy)   127.0.0.1:9092->9092/tcp
incidentiq-postgres-1    Up (healthy)   127.0.0.1:55432->5432/tcp
incidentiq-kafka-init-1  Exited (0)
```

`bash -n scripts/verify-infra.sh`: exit 0.

`./scripts/verify-infra.sh`: exit 0. Uses container-provided tools; no host psql or Kafka installation. PostgreSQL TCP/password connection inside container returned:

```text
 current_database | current_user
 incidentiq       | incidentiq
 extname | extversion
 vector  | 0.8.7
 vector_distance
 1
```

The vector operation was `SELECT '[1,2,3]'::vector <-> '[1,2,4]'::vector AS vector_distance;`. Both Kafka application topics reported PartitionCount: 1, ReplicationFactor: 1, Leader: 1, Replicas: 1, Isr: 1. A fresh temporary topic was created; producer used acks=all, consumer read the expected record, and the topic was deleted by cleanup:

```text
Processed a total of 1 messages
Consumed: incidentiq-smoke-ok
```

A Python socket.create_connection check from WSL returned:

```text
WSL TCP 127.0.0.1:55432: connected
WSL TCP 127.0.0.1:9092: connected
```

This verifies host port TCP reachability; SQL authentication was tested inside the container, and Kafka produce/consume used its internal listener.

`docker build --progress=plain -t incidentiq-api:local ./api`: exit 0. Output included:

```text
Compiling 1 source file with javac [debug parameters release 21] to target/classes
No tests to run.
BUILD SUCCESS
naming to docker.io/library/incidentiq-api:local done
```

Maven dependency resolution and executable Spring Boot JAR packaging succeeded inside Docker. No host Java or Maven was used. There are no application tests yet, so this is a successful build, not an application test-suite pass.

## Remaining scope

Infrastructure remains running. No cloud resources or remote repository were created. Existing volumes were preserved. Spring Boot HTTP runtime, worker dependency resolution and frontend build have not been tested in this continuation. Incident ingestion, AI analysis and retrieval remain unimplemented. Docker image/dependency downloads require network access; runtime remains local.
