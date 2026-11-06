# Disk exhaustion, full volumes and inode pressure

## Symptoms and impact
Processes report No space left on device, PostgreSQL cannot write WAL, Kafka cannot append log segments, or containers fail to start. Disk space may appear available while inodes are exhausted. A read-only filesystem or I/O error is a different condition from a full filesystem and needs storage investigation. Record the affected mount, free bytes, inode usage and whether writes are failing.

## Inspect the correct storage layer
Check host/WSL/Docker Desktop storage as well as container filesystems and named volumes. Use df -h and df -i in the relevant environment. Inspect Docker disk usage without deleting anything. Determine which filesystem holds PostgreSQL data, Kafka log segments, image layers, build cache and application logs. A container's root filesystem can fill independently from its persistent volume.

## Find the growth source
Review recent log volume, heap dumps, model downloads, image builds, database WAL retention and Kafka topic retention. Compare file growth rate and retention settings with the incident start. PostgreSQL WAL can grow when a replication slot or archiving path is stalled; deleting WAL manually risks corruption. Kafka log segments are broker-managed and must not be removed by hand to reclaim space. Check for deleted-but-open files if reported free space does not match directory sizes.

## Safe mitigation
Pause the source of uncontrolled growth and restore storage capacity when possible. Rotate or archive application logs using the supported logging mechanism. Remove only verified disposable build artifacts after identifying them; do not run a blanket Docker volume prune. Fix blocked WAL archiving or retention configuration through the database's supported procedure. Change Kafka retention only with an explicit understanding of which events will expire.

## Recovery and rollback
Verify free space and inodes recover, writes succeed, database readiness returns and Kafka append/consume operations work. Check for crash recovery messages and delayed outbox processing. Revert a retention change if it threatens required recovery history, while ensuring enough capacity remains. Preserve existing named volumes and backups.

## Prevention and escalation
Alert on both free capacity and time-to-full based on growth rate. Set log rotation and storage budgets for models, Docker builds and durable event retention. Escalate storage errors, read-only mounts or database recovery failures with mount-level measurements and recent growth evidence, not just an application restart count.
