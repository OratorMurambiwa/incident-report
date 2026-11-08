# Build and test entirely inside Docker; no host Maven or JDK required.
FROM maven:3.9.11-eclipse-temurin-21 AS build
WORKDIR /workspace
COPY pom.xml .
RUN mvn --batch-mode --no-transfer-progress dependency:go-offline
COPY src ./src
RUN mvn --batch-mode --no-transfer-progress verify

FROM eclipse-temurin:21-jre-jammy AS runtime
WORKDIR /app
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
RUN groupadd --system incidentiq && useradd --system --gid incidentiq incidentiq
COPY --from=build --chown=incidentiq:incidentiq /workspace/target/incidentiq-api-*.jar /app/app.jar
USER incidentiq
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "/app/app.jar"]
