# Critical/high triage ledger

Every baseline occurrence is retained below, including repeated binary/library rows. Counts are scanner occurrences, not independent exploitable defects. Fixed versions are the frozen scanner’s values; an empty value means none supplied, not that no upstream patch exists. Current exposure is configuration-specific, not proof of non-exploitability.

Full structured conditions, current exposure, paths, source duplicate groups and reasons for deferral: [triage.json](triage.json). Public advisory links retain each scanner title even where metadata needs correction. No finding is suppressed.

## api

CH occurrences: 19 → 2; distinct CH CVEs: 18 → 2.

| Advisory | Package (before → after) | Scanner fix | Upstream fix (when separately reviewed) | Disposition |
|---|---|---|---|---|
| [CVE-2026-109518](https://ubuntu.com/security/CVE-2026-109518) (HIGH) | apt 2.4.14 → 2.4.15ubuntu0.1 | 2.4.15ubuntu0.1 | see scanner fix | not detected in updated package |
| [CVE-2026-109518](https://ubuntu.com/security/CVE-2026-109518) (HIGH) | libapt-pkg6.0 2.4.14 → 2.4.15ubuntu0.1 | 2.4.15ubuntu0.1 | see scanner fix | not detected in updated package |
| [CVE-2026-106451](https://github.com/yawkat/lz4-java/security/advisories/GHSA-mcr4-qmvw-px4g) (HIGH) | at.yawk.lz4:lz4-java 1.10.1 → 1.11.4 | 1.11.4 | see scanner fix | not detected in updated package |
| [CVE-2026-89407](https://github.com/FasterXML/jackson-core/security/advisories/GHSA-p6pp-m3f8-5c89) (HIGH) | com.fasterxml.jackson.core:jackson-core 2.21.4 → 2.21.8 | 2.18.11, 2.21.7, 2.22.3 | see scanner fix | not detected in updated package |
| [CVE-2026-89425](https://github.com/FasterXML/jackson-core/security/advisories/GHSA-7hhh-6rmp-j9qf) (HIGH) | com.fasterxml.jackson.core:jackson-core 2.21.4 → 2.21.8 | 2.21.7, 2.22.3, 2.18.11 | see scanner fix | not detected in updated package |
| [CVE-2026-68497](https://github.com/FasterXML/jackson-databind/security/advisories/GHSA-q4xh-88c3-wmh7) (HIGH) | com.fasterxml.jackson.core:jackson-databind 2.21.4 → 2.21.8 | 2.18.10, 2.21.6, 2.22.2 | see scanner fix | not detected in updated package |
| [CVE-2026-91776](https://github.com/FasterXML/jackson-databind/security/advisories/GHSA-wv8q-qhhj-9h54) (HIGH) | com.fasterxml.jackson.core:jackson-databind 2.21.4 → 2.21.8 | 2.18.11, 2.21.7, 2.22.3 | see scanner fix | not detected in updated package |
| [CVE-2026-91777](https://github.com/FasterXML/jackson-databind/security/advisories/GHSA-cxp5-3px4-pw24) (HIGH) | com.fasterxml.jackson.core:jackson-databind 2.21.4 → 2.21.8 | 2.21.7, 2.18.11, 2.22.3 | see scanner fix | not detected in updated package |
| [CVE-2026-55276](https://nvd.nist.gov/vuln/detail/CVE-2026-55276) (CRITICAL) | org.apache.tomcat.embed:tomcat-embed-core 10.1.55 → 10.1.61 | 11.0.23, 10.1.56, 9.0.119 | see scanner fix | not detected in updated package |
| [CVE-2026-65182](https://nvd.nist.gov/vuln/detail/CVE-2026-65182) (CRITICAL) | org.apache.tomcat.embed:tomcat-embed-core 10.1.55 → 10.1.61 | 11.0.25, 10.1.58, 9.0.121 | see scanner fix | not detected in updated package |
| [CVE-2026-65637](https://nvd.nist.gov/vuln/detail/CVE-2026-65637) (CRITICAL) | org.apache.tomcat.embed:tomcat-embed-core 10.1.55 → 10.1.61 | 11.0.25, 10.1.59, 9.0.121 | see scanner fix | not detected in updated package |
| [CVE-2026-65905](https://nvd.nist.gov/vuln/detail/CVE-2026-65905) (CRITICAL) | org.apache.tomcat.embed:tomcat-embed-core 10.1.55 → 10.1.61 | 11.0.25, 10.1.58, 9.0.121 | see scanner fix | not detected in updated package |
| [CVE-2026-68525](https://nvd.nist.gov/vuln/detail/CVE-2026-68525) (CRITICAL) | org.apache.tomcat.embed:tomcat-embed-core 10.1.55 → 10.1.61 | 11.0.25, 10.1.58, 9.0.121 | see scanner fix | not detected in updated package |
| [CVE-2026-53404](https://nvd.nist.gov/vuln/detail/CVE-2026-53404) (HIGH) | org.apache.tomcat.embed:tomcat-embed-core 10.1.55 → 10.1.61 | 11.0.23, 10.1.56, 9.0.119 | see scanner fix | not detected in updated package |
| [CVE-2026-54291](https://github.com/pgjdbc/pgjdbc/security/advisories/GHSA-j92g-9f8w-j867) (HIGH) | org.postgresql:postgresql 42.7.11 → 42.7.12 | 42.7.12 | see scanner fix | not detected in updated package |
| [CVE-2026-47884](https://nvd.nist.gov/vuln/detail/CVE-2026-47884) (CRITICAL) | org.springframework:spring-webmvc 6.2.19 → 6.2.19 | 7.0.9 | 7.0.9 (public), 6.2.20 (enterprise only) | present |
| [CVE-2026-47890](https://nvd.nist.gov/vuln/detail/CVE-2026-47890) (CRITICAL) | org.springframework:spring-webmvc 6.2.19 → 6.2.19 | 7.0.9 | 7.0.9 (public), 6.2.20 (enterprise only) | present |
| [CVE-2026-108106](https://github.com/xerial/snappy-java/security/advisories/GHSA-q233-g92q-qxp6) (HIGH) | org.xerial.snappy:snappy-java 1.1.10.5 → 1.1.10.9 | 1.1.10.9 | see scanner fix | not detected in updated package |
| [CVE-2026-93451](https://github.com/xerial/snappy-java/security/advisories/GHSA-gwq9-9ffj-mvrv) (HIGH) | org.xerial.snappy:snappy-java 1.1.10.5 → 1.1.10.9 | 1.1.10.9 | see scanner fix | not detected in updated package |

### Conditions and deferrals

- **CVE-2026-109518**: APT retries downloads into attacker-influenced paths/hardlinks during package installation. Build/update tool; non-root API does not run APT.
- **CVE-2026-106451**: A local attacker wins a predictable native-library path race in a shared temporary directory. Transitive Kafka compression library; patched even though application container has a separate temporary directory.
- **CVE-2026-89407**: Attacker-provided extremely long numeric JSON triggers expensive pre-validation. REST JSON parser is reachable; bounded DTO validation occurs after parsing, so patch is important.
- **CVE-2026-89425**: Malformed JSON tokens through DataInput parsing grow diagnostic StringBuilder without bounds. MVC uses the standard HTTP stream path, not a custom DataInput reader; patch applied.
- **CVE-2026-68497**: Very large numeric input reaches XML duration/calendar deserializers. Incident DTOs contain no XML duration/calendar types; parser patched.
- **CVE-2026-91776**: Attacker-controlled polymorphic fallback types grow a deserializer cache. No default typing or attacker-controlled JsonTypeInfo configured; patched.
- **CVE-2026-91777**: Many unresolved JsonIdentityInfo forward references trigger quadratic processing. No JsonIdentityInfo incident DTOs; patched.
- **CVE-2026-55276**: Web application security constraints are omitted from effective web.xml logging. REST application has no web.xml security-constraint policy; Tomcat patched.
- **CVE-2026-65182**: Overlapping servlet URL security constraints depend on matching order. No servlet security-constraint based authorization configured; Tomcat patched.
- **CVE-2026-65637**: HTTP/2 requests omit authority under strict TLS SNI routing. Local API uses plain HTTP/1, without configured TLS/HTTP2 strict SNI; patched.
- **CVE-2026-65905**: DIGEST authentication replay-window handling permits reuse. No servlet DIGEST authentication; patched.
- **CVE-2026-68525**: FORM authentication redirects permit bypass of method-based servlet constraints. No FORM authentication or servlet web.xml constraints; patched.
- **CVE-2026-53404**: RewriteValve rules use OR-linked conditions in vulnerable combinations. No RewriteValve configured; patched.
- **CVE-2026-54291**: An active network attacker downgrades SCRAM-PLUS when TLS channel binding is required. Compose uses a local plain PostgreSQL connection; patch protects future TLS deployments.
- **CVE-2026-47884**: XsltView with /** view mapping and implicit view names permits unintended stylesheet access and SSRF/RCE. REST controllers return JSON; no XsltView, view resolver or implicit template names. Reachability inspection is not an exploit proof. Deferred: Public fixed branch is Spring 7.0.9; 6.2.20 is enterprise-only. Boot 3.5.16 manages 6.2.19. Defer to a separately verified Boot 4/Spring 7 migration; do not fetch paid enterprise artifacts or mix incompatible Spring majors. Upstream severity MEDIUM differs from scanner CRITICAL.
- **CVE-2026-47890**: Attacker-controlled view fragments are streamed using server-sent events. No SSE endpoints or fragment views in this REST API. Deferred: Same public-major/enterprise maintenance constraint as CVE-2026-47884. Upstream severity LOW differs from scanner CRITICAL. Retain finding.
- **CVE-2026-108106**: Malformed compressed input reaches native Snappy decoding or excessive output allocation. Kafka compression dependency; publisher defaults to uncompressed events and broker is local. Added Snappy and LZ4 round-trip tests check compatibility of the patched codecs.
- **CVE-2026-93451**: Malformed compressed input reaches native Snappy decoding or excessive output allocation. Kafka compression dependency; publisher defaults to uncompressed events and broker is local. Added Snappy and LZ4 round-trip tests check compatibility of the patched codecs.

## worker

CH occurrences: 61 → 48; distinct CH CVEs: 25 → 12.

| Advisory | Package (before → after) | Scanner fix | Upstream fix (when separately reviewed) | Disposition |
|---|---|---|---|---|
| [CVE-2026-76642](https://security-tracker.debian.org/tracker/CVE-2026-76642) (HIGH) | bsdutils 1:2.41.5-0+deb13u1 → 1:2.41.5-0+deb13u1 | not supplied | 2.41.6, 2.42.3 | present |
| [CVE-2026-78408](https://security-tracker.debian.org/tracker/CVE-2026-78408) (HIGH) | bsdutils 1:2.41.5-0+deb13u1 → 1:2.41.5-0+deb13u1 | not supplied | 2.41.6, 2.42.3 | present |
| [CVE-2026-78409](https://security-tracker.debian.org/tracker/CVE-2026-78409) (HIGH) | bsdutils 1:2.41.5-0+deb13u1 → 1:2.41.5-0+deb13u1 | not supplied | 2.41.6, 2.42.3 | present |
| [CVE-2026-78410](https://security-tracker.debian.org/tracker/CVE-2026-78410) (HIGH) | bsdutils 1:2.41.5-0+deb13u1 → 1:2.41.5-0+deb13u1 | not supplied | 2.41.6, 2.42.3 | present |
| [CVE-2026-54369](https://security-tracker.debian.org/tracker/CVE-2026-54369) (HIGH) | libacl1 2.3.2-2+b1 → 2.3.2-2+b1 | not supplied | 2.4.0 (ACL upstream) | present |
| [CVE-2026-76642](https://security-tracker.debian.org/tracker/CVE-2026-76642) (HIGH) | libblkid1 2.41.5-0+deb13u1 → 2.41.5-0+deb13u1 | not supplied | 2.41.6, 2.42.3 | present |
| [CVE-2026-78408](https://security-tracker.debian.org/tracker/CVE-2026-78408) (HIGH) | libblkid1 2.41.5-0+deb13u1 → 2.41.5-0+deb13u1 | not supplied | 2.41.6, 2.42.3 | present |
| [CVE-2026-78409](https://security-tracker.debian.org/tracker/CVE-2026-78409) (HIGH) | libblkid1 2.41.5-0+deb13u1 → 2.41.5-0+deb13u1 | not supplied | 2.41.6, 2.42.3 | present |
| [CVE-2026-78410](https://security-tracker.debian.org/tracker/CVE-2026-78410) (HIGH) | libblkid1 2.41.5-0+deb13u1 → 2.41.5-0+deb13u1 | not supplied | 2.41.6, 2.42.3 | present |
| [CVE-2026-76642](https://security-tracker.debian.org/tracker/CVE-2026-76642) (HIGH) | liblastlog2-2 2.41.5-0+deb13u1 → 2.41.5-0+deb13u1 | not supplied | 2.41.6, 2.42.3 | present |
| [CVE-2026-78408](https://security-tracker.debian.org/tracker/CVE-2026-78408) (HIGH) | liblastlog2-2 2.41.5-0+deb13u1 → 2.41.5-0+deb13u1 | not supplied | 2.41.6, 2.42.3 | present |
| [CVE-2026-78409](https://security-tracker.debian.org/tracker/CVE-2026-78409) (HIGH) | liblastlog2-2 2.41.5-0+deb13u1 → 2.41.5-0+deb13u1 | not supplied | 2.41.6, 2.42.3 | present |
| [CVE-2026-78410](https://security-tracker.debian.org/tracker/CVE-2026-78410) (HIGH) | liblastlog2-2 2.41.5-0+deb13u1 → 2.41.5-0+deb13u1 | not supplied | 2.41.6, 2.42.3 | present |
| [CVE-2026-76642](https://security-tracker.debian.org/tracker/CVE-2026-76642) (HIGH) | libmount1 2.41.5-0+deb13u1 → 2.41.5-0+deb13u1 | not supplied | 2.41.6, 2.42.3 | present |
| [CVE-2026-78408](https://security-tracker.debian.org/tracker/CVE-2026-78408) (HIGH) | libmount1 2.41.5-0+deb13u1 → 2.41.5-0+deb13u1 | not supplied | 2.41.6, 2.42.3 | present |
| [CVE-2026-78409](https://security-tracker.debian.org/tracker/CVE-2026-78409) (HIGH) | libmount1 2.41.5-0+deb13u1 → 2.41.5-0+deb13u1 | not supplied | 2.41.6, 2.42.3 | present |
| [CVE-2026-78410](https://security-tracker.debian.org/tracker/CVE-2026-78410) (HIGH) | libmount1 2.41.5-0+deb13u1 → 2.41.5-0+deb13u1 | not supplied | 2.41.6, 2.42.3 | present |
| [CVE-2025-69720](https://security-tracker.debian.org/tracker/CVE-2025-69720) (HIGH) | libncursesw6 6.5+20250216-2 → 6.5+20250216-2 | not supplied | 6.5-20251213 (ncurses upstream snapshot) | present |
| [CVE-2026-76642](https://security-tracker.debian.org/tracker/CVE-2026-76642) (HIGH) | libsmartcols1 2.41.5-0+deb13u1 → 2.41.5-0+deb13u1 | not supplied | 2.41.6, 2.42.3 | present |
| [CVE-2026-78408](https://security-tracker.debian.org/tracker/CVE-2026-78408) (HIGH) | libsmartcols1 2.41.5-0+deb13u1 → 2.41.5-0+deb13u1 | not supplied | 2.41.6, 2.42.3 | present |
| [CVE-2026-78409](https://security-tracker.debian.org/tracker/CVE-2026-78409) (HIGH) | libsmartcols1 2.41.5-0+deb13u1 → 2.41.5-0+deb13u1 | not supplied | 2.41.6, 2.42.3 | present |
| [CVE-2026-78410](https://security-tracker.debian.org/tracker/CVE-2026-78410) (HIGH) | libsmartcols1 2.41.5-0+deb13u1 → 2.41.5-0+deb13u1 | not supplied | 2.41.6, 2.42.3 | present |
| [CVE-2026-119373](https://security-tracker.debian.org/tracker/CVE-2026-119373) (HIGH) | libsqlite3-0 3.46.1-7+deb13u2 → 3.46.1-7+deb13u2 | not supplied | 3.54.0 (SQLite upstream) | present |
| [CVE-2026-119374](https://security-tracker.debian.org/tracker/CVE-2026-119374) (HIGH) | libsqlite3-0 3.46.1-7+deb13u2 → 3.46.1-7+deb13u2 | not supplied | 3.54.0 (SQLite upstream) | present |
| [CVE-2026-119379](https://security-tracker.debian.org/tracker/CVE-2026-119379) (HIGH) | libsqlite3-0 3.46.1-7+deb13u2 → 3.46.1-7+deb13u2 | not supplied | 3.54.0 (SQLite upstream) | present |
| [CVE-2026-16742](https://security-tracker.debian.org/tracker/CVE-2026-16742) (HIGH) | libsystemd0 257.13-1~deb13u1 → 257.13-1~deb13u1 | not supplied | 258.10, 259.8, 260.4, 261.2, 262 | present |
| [CVE-2025-69720](https://security-tracker.debian.org/tracker/CVE-2025-69720) (HIGH) | libtinfo6 6.5+20250216-2 → 6.5+20250216-2 | not supplied | 6.5-20251213 (ncurses upstream snapshot) | present |
| [CVE-2026-16742](https://security-tracker.debian.org/tracker/CVE-2026-16742) (HIGH) | libudev1 257.13-1~deb13u1 → 257.13-1~deb13u1 | not supplied | 258.10, 259.8, 260.4, 261.2, 262 | present |
| [CVE-2026-76642](https://security-tracker.debian.org/tracker/CVE-2026-76642) (HIGH) | libuuid1 2.41.5-0+deb13u1 → 2.41.5-0+deb13u1 | not supplied | 2.41.6, 2.42.3 | present |
| [CVE-2026-78408](https://security-tracker.debian.org/tracker/CVE-2026-78408) (HIGH) | libuuid1 2.41.5-0+deb13u1 → 2.41.5-0+deb13u1 | not supplied | 2.41.6, 2.42.3 | present |
| [CVE-2026-78409](https://security-tracker.debian.org/tracker/CVE-2026-78409) (HIGH) | libuuid1 2.41.5-0+deb13u1 → 2.41.5-0+deb13u1 | not supplied | 2.41.6, 2.42.3 | present |
| [CVE-2026-78410](https://security-tracker.debian.org/tracker/CVE-2026-78410) (HIGH) | libuuid1 2.41.5-0+deb13u1 → 2.41.5-0+deb13u1 | not supplied | 2.41.6, 2.42.3 | present |
| [CVE-2026-76642](https://security-tracker.debian.org/tracker/CVE-2026-76642) (HIGH) | login 1:4.16.0-2+really2.41.5-0+deb13u1 → 1:4.16.0-2+really2.41.5-0+deb13u1 | not supplied | 2.41.6, 2.42.3 | present |
| [CVE-2026-78408](https://security-tracker.debian.org/tracker/CVE-2026-78408) (HIGH) | login 1:4.16.0-2+really2.41.5-0+deb13u1 → 1:4.16.0-2+really2.41.5-0+deb13u1 | not supplied | 2.41.6, 2.42.3 | present |
| [CVE-2026-78409](https://security-tracker.debian.org/tracker/CVE-2026-78409) (HIGH) | login 1:4.16.0-2+really2.41.5-0+deb13u1 → 1:4.16.0-2+really2.41.5-0+deb13u1 | not supplied | 2.41.6, 2.42.3 | present |
| [CVE-2026-78410](https://security-tracker.debian.org/tracker/CVE-2026-78410) (HIGH) | login 1:4.16.0-2+really2.41.5-0+deb13u1 → 1:4.16.0-2+really2.41.5-0+deb13u1 | not supplied | 2.41.6, 2.42.3 | present |
| [CVE-2026-76642](https://security-tracker.debian.org/tracker/CVE-2026-76642) (HIGH) | mount 2.41.5-0+deb13u1 → 2.41.5-0+deb13u1 | not supplied | 2.41.6, 2.42.3 | present |
| [CVE-2026-78408](https://security-tracker.debian.org/tracker/CVE-2026-78408) (HIGH) | mount 2.41.5-0+deb13u1 → 2.41.5-0+deb13u1 | not supplied | 2.41.6, 2.42.3 | present |
| [CVE-2026-78409](https://security-tracker.debian.org/tracker/CVE-2026-78409) (HIGH) | mount 2.41.5-0+deb13u1 → 2.41.5-0+deb13u1 | not supplied | 2.41.6, 2.42.3 | present |
| [CVE-2026-78410](https://security-tracker.debian.org/tracker/CVE-2026-78410) (HIGH) | mount 2.41.5-0+deb13u1 → 2.41.5-0+deb13u1 | not supplied | 2.41.6, 2.42.3 | present |
| [CVE-2025-69720](https://security-tracker.debian.org/tracker/CVE-2025-69720) (HIGH) | ncurses-base 6.5+20250216-2 → 6.5+20250216-2 | not supplied | 6.5-20251213 (ncurses upstream snapshot) | present |
| [CVE-2025-69720](https://security-tracker.debian.org/tracker/CVE-2025-69720) (HIGH) | ncurses-bin 6.5+20250216-2 → 6.5+20250216-2 | not supplied | 6.5-20251213 (ncurses upstream snapshot) | present |
| [CVE-2026-9538](https://security-tracker.debian.org/tracker/CVE-2026-9538) (HIGH) | perl-base 5.40.1-6+deb13u1 → 5.40.1-6+deb13u1 | not supplied | 3.10 (Perl Archive::Tar module; not Perl interpreter version) | present |
| [CVE-2026-76642](https://security-tracker.debian.org/tracker/CVE-2026-76642) (HIGH) | util-linux 2.41.5-0+deb13u1 → 2.41.5-0+deb13u1 | not supplied | 2.41.6, 2.42.3 | present |
| [CVE-2026-78408](https://security-tracker.debian.org/tracker/CVE-2026-78408) (HIGH) | util-linux 2.41.5-0+deb13u1 → 2.41.5-0+deb13u1 | not supplied | 2.41.6, 2.42.3 | present |
| [CVE-2026-78409](https://security-tracker.debian.org/tracker/CVE-2026-78409) (HIGH) | util-linux 2.41.5-0+deb13u1 → 2.41.5-0+deb13u1 | not supplied | 2.41.6, 2.42.3 | present |
| [CVE-2026-78410](https://security-tracker.debian.org/tracker/CVE-2026-78410) (HIGH) | util-linux 2.41.5-0+deb13u1 → 2.41.5-0+deb13u1 | not supplied | 2.41.6, 2.42.3 | present |
| [CVE-2026-76844](https://security-tracker.debian.org/tracker/CVE-2026-76844) (HIGH) | zlib1g 1:1.3.dfsg+really1.3.1-1+b1 → 1:1.3.dfsg+really1.3.1-1+deb13u1 | 1:1.3.dfsg+really1.3.1-1+deb13u1 | see scanner fix | not detected in updated package |
| [CVE-2026-85091](https://security-tracker.debian.org/tracker/CVE-2026-85091) (HIGH) | zlib1g 1:1.3.dfsg+really1.3.1-1+b1 → 1:1.3.dfsg+really1.3.1-1+deb13u1 | 1:1.3.dfsg+really1.3.1-1+deb13u1 | see scanner fix | not detected in updated package |
| [CVE-2026-23949](https://github.com/jaraco/jaraco.context/security/advisories/GHSA-58pv-8j8x-9vj2) (HIGH) | jaraco.context 5.3.0 → 6.1.0 | 6.1.0 | see scanner fix | not detected in updated package |
| [CVE-2026-10142](https://nvd.nist.gov/vuln/detail/CVE-2026-10142) (HIGH) | kafka-python 2.2.15 → 2.3.2 | 2.3.2 | see scanner fix | not detected in updated package |
| [CVE-2026-10143](https://nvd.nist.gov/vuln/detail/CVE-2026-10143) (HIGH) | kafka-python 2.2.15 → 2.3.2 | 2.3.2 | see scanner fix | not detected in updated package |
| [CVE-2026-45134](https://github.com/langchain-ai/langsmith-sdk/security/advisories/GHSA-3644-q5cj-c5c7) (HIGH) | langchain 0.3.27 → 0.3.30 | 0.3.30 | see scanner fix | not detected in updated package |
| [CVE-2026-34070](https://github.com/langchain-ai/langchain/security/advisories/GHSA-qh6h-p6c9-ff54) (HIGH) | langchain-core 0.3.86 → 0.3.86 | 1.2.22 | 1.2.22 | present |
| [CVE-2026-68770](https://nvd.nist.gov/vuln/detail/CVE-2026-68770) (CRITICAL) | sentence-transformers 3.4.1 → 5.6.0 | 5.6.0 | see scanner fix | not detected in updated package |
| [CVE-2025-47273](https://github.com/pypa/setuptools/security/advisories/GHSA-5rjg-fvgr-3xxf) (HIGH) | setuptools 78.1.0 → 84.2.1 | 78.1.1 | see scanner fix | not detected in updated package |
| [CVE-2026-24747](https://github.com/pytorch/pytorch/security/advisories/GHSA-63cw-57p8-fm3p) (HIGH) | torch 2.6.0+cpu → 2.10.0+cpu | 2.10.0 | see scanner fix | not detected in updated package |
| [CVE-2026-4372](https://nvd.nist.gov/vuln/detail/CVE-2026-4372) (HIGH) | transformers 4.48.3 → 5.10.0 | 5.3.0 | see scanner fix | not detected in updated package |
| [CVE-2026-5241](https://nvd.nist.gov/vuln/detail/CVE-2026-5241) (HIGH) | transformers 4.48.3 → 5.10.0 | 5.5.0 | see scanner fix | not detected in updated package |
| [CVE-2026-9856](https://nvd.nist.gov/vuln/detail/CVE-2026-9856) (HIGH) | transformers 4.48.3 → 5.10.0 | 5.10.0 | see scanner fix | not detected in updated package |
| [CVE-2026-24049](https://github.com/pypa/wheel/security/advisories/GHSA-8rrh-rw8j-w5fx) (HIGH) | wheel 0.45.1 → 0.46.3 | 0.46.2 | see scanner fix | not detected in updated package |

### Conditions and deferrals

- **CVE-2026-76642**: Failed external mount helpers still execute privileged X-mount post-hooks. Worker runs as uid 999, has no SYS_ADMIN capability and does not invoke mount helpers. Deferred: No Debian 13 fixed version in the frozen database. Retain Debian 13 support and essential package dependencies; do not mix unstable packages or delete libraries merely to reduce counts. Upstream releases 2.41.6/2.42.3 are fixed, but are not an available Debian 13 package fix in this snapshot.
- **CVE-2026-78408**: Privileged nsenter --join-cgroup leaks cgroup migration authority. Worker does not invoke nsenter, join host namespaces or use privileged mode. Deferred: No Debian 13 fixed version in snapshot. Nine util-linux binary package rows per CVE share one source advisory; not nine independent defects. Upstream releases 2.41.6/2.42.3 are fixed, but are not an available Debian 13 package fix in this snapshot.
- **CVE-2026-78409**: On Linux >=6.15, an fstab-authorized X-mount.subdir entry follows an intermediate symlink/procfs path outside the detached mounted tree. Worker has no mount privileges or mount calls; actual Docker kernel is 6.6.87.2-microsoft-standard-WSL2. Upstream GHSA affected range starts at 2.42 while Debian flags 2.41.5: retain the source-level finding pending vendor clarification, not a verified false positive. Deferred: No Debian 13 fixed version in snapshot; defer vendor update, keep duplicate source-package rows visible. Upstream releases 2.41.6/2.42.3 are fixed, but are not an available Debian 13 package fix in this snapshot.
- **CVE-2026-78410**: Restricted bind-mount sources can be redirected before ownership/mode actions. Worker is non-root, without mount privileges or bind-mount operations in its code. Deferred: No Debian 13 fixed version in snapshot; do not replace supported system libraries with unstable builds. Upstream releases 2.41.6/2.42.3 are fixed, but are not an available Debian 13 package fix in this snapshot.
- **CVE-2026-54369**: Privileged ACL operations follow attacker-controlled symlinks. Worker does not change ACLs or operate with elevated filesystem privileges. Deferred: No Debian 13 fixed version in snapshot; retain required base library pending vendor fix.
- **CVE-2025-69720**: Malformed terminal capability strings reach infocmp analyze_string (stack overflow); library source-package matches do not establish that a daemon or remote parser is running. No interactive terminal or user-controlled TERM capability files in worker processing. Deferred: No Debian 13 fix in snapshot; four binary rows are one ncurses source advisory.
- **CVE-2026-119373**: FTS5 detail=none prefix doclists with invalid row IDs trigger heap corruption. Application persists to PostgreSQL; no untrusted SQLite FTS input. Deferred: Debian 13 has no fixed package in snapshot. Upstream 3.54.0/sid 3.54.1-1 fixes are not a compatible stable distribution update.
- **CVE-2026-119374**: A corrupted SQLite FTS5 index triggers unsafe memory handling. No SQLite database ingestion or FTS5 queries in the application. Deferred: No Debian 13 fixed package in snapshot; avoid custom/unstable libsqlite replacing Python base ABI.
- **CVE-2026-119379**: Crafted SQLite session changesets reach unsafe session extension code. No SQLite session changeset APIs or untrusted SQLite files accepted. Deferred: No Debian 13 fixed package in snapshot; retain base dependency and track vendor update.
- **CVE-2026-16742**: systemd-homed accepts an incorrectly verified home record during privileged account operations. Only libsystemd0/libudev1 are installed; actual systemd-homed executable is absent (verified in candidate). Container entrypoint is Python, not systemd. Deferred: Source-level matching creates two rows for libraries without the homed daemon; retain scanner output and record reachability limitation instead of suppressing.
- **CVE-2026-9538**: Perl Archive::Tar parses an attacker-crafted header declaring a huge entry size. Worker never invokes Perl Archive::Tar or accepts tar archives. Deferred: No Debian 13 fixed version in snapshot; perl-base is a base-package dependency, not application functionality.
- **CVE-2026-76844**: zlib gzip write-error handling can overflow a heap buffer. Runtime compression paths are not fed attacker-selected filesystem write failures; base package patched. CVE-2026-76844 scanner title incorrectly refers to webpack; Debian identifies zlib, and these IDs share the remedial commit.
- **CVE-2026-85091**: zlib gzip write-error handling can overflow a heap buffer. Runtime compression paths are not fed attacker-selected filesystem write failures; base package patched. CVE-2026-76844 scanner title incorrectly refers to webpack; Debian identifies zlib, and these IDs share the remedial commit.
- **CVE-2026-23949**: Archive extraction helpers process attacker-controlled member paths. jaraco.context is vendored inside setuptools, not an application import; fixed by replacing setuptools and verifying vendor metadata.
- **CVE-2026-10142**: A malicious Kafka broker supplies invalid or excessive response frame sizes. Local broker is trusted but decoder dependency patched.
- **CVE-2026-10143**: A malicious SCRAM broker chooses an excessive iteration count causing CPU denial of service. Local Kafka is PLAINTEXT, without SCRAM; dependency patched for future authentication.
- **CVE-2026-45134**: Pulling untrusted LangSmith Hub prompts reaches unsafe deserialization paths. No Hub prompt pulls; tracing is disabled. Compatible LangChain 0.3.30 patch applied.
- **CVE-2026-34070**: Legacy load_prompt/load_prompt_from_config resolves attacker-controlled filesystem paths. Application uses locally constructed ChatPromptTemplate and runnable parsing; neither vulnerable legacy loader is called. Deferred: Fixed core 1.2.22 conflicts with LangChain 0.3.30 core<1 constraint. Defer coordinated LangChain 1 migration with retrieval/RAG regression coverage; no suppression.
- **CVE-2026-68770**: An attacker supplies a model directory whose custom Python modules execute despite trust_remote_code=False. Fixed sentence-transformers 5.6.0 verified with the exact pinned MiniLM revision, offline loading, unchanged weight hash and measured embedding parity. Never load arbitrary local models.
- **CVE-2025-47273**: PackageIndex processes malicious package archive paths. setuptools is required by Torch on Python 3.12; kept and patched rather than uninstalling a required dependency.
- **CVE-2026-24747**: Malicious serialized checkpoint reaches the weights_only unpickler. Pinned MiniLM uses safetensors, not an untrusted checkpoint; CPU Torch patched to 2.10.0.
- **CVE-2026-4372**: Attacker-controlled model configuration selects an unsafe attention implementation. Only baked, pinned MiniLM model is loaded offline; Transformers updated.
- **CVE-2026-5241**: LightGlue model loading bypasses trust_remote_code checks. MiniLM is not LightGlue. Advisory description identifies the 5.2.0 implementation while baseline is 4.48.3: scanner range is potentially overbroad. Do not silently discard the row; candidate is above fixed 5.5.0.
- **CVE-2026-9856**: Attacker-controlled chat template filenames reach save_pretrained output paths. Runtime only embeds pinned MiniLM; no user-selected model saving. Transformers patched to 5.10.0.
- **CVE-2026-24049**: Unpacking a malicious wheel trusts the original archive name during chmod after extraction path sanitization, modifying permissions outside the destination. Vulnerable wheel is the setuptools-vendored copy; updated vendor metadata is 0.46.3, not just a top-level wheel installation.

## frontend

CH occurrences: 64 → 0; distinct CH CVEs: 48 → 0.

| Advisory | Package (before → after) | Scanner fix | Upstream fix (when separately reviewed) | Disposition |
|---|---|---|---|---|
| [CVE-2026-111497](https://security.alpinelinux.org/vuln/CVE-2026-111497) (CRITICAL) | brotli-libs 1.1.0-r2 → absent | 1.1.1-r0 | see scanner fix | package absent from inventory |
| [CVE-2026-33630](https://security.alpinelinux.org/vuln/CVE-2026-33630) (HIGH) | c-ares 1.34.5-r0 → absent | 1.34.8-r0 | see scanner fix | package absent from inventory |
| [CVE-2026-5773](https://security.alpinelinux.org/vuln/CVE-2026-5773) (HIGH) | curl 8.14.1-r2 → absent | 8.14.1-r3 | see scanner fix | package absent from inventory |
| [CVE-2026-6276](https://security.alpinelinux.org/vuln/CVE-2026-6276) (HIGH) | curl 8.14.1-r2 → absent | 8.14.1-r3 | see scanner fix | package absent from inventory |
| [CVE-2026-8286](https://security.alpinelinux.org/vuln/CVE-2026-8286) (HIGH) | curl 8.14.1-r2 → absent | 8.14.1-r3 | see scanner fix | package absent from inventory |
| [CVE-2026-8927](https://security.alpinelinux.org/vuln/CVE-2026-8927) (HIGH) | curl 8.14.1-r2 → absent | 8.14.1-r3 | see scanner fix | package absent from inventory |
| [CVE-2026-92392](https://security.alpinelinux.org/vuln/CVE-2026-92392) (HIGH) | curl 8.14.1-r2 → absent | 8.14.1-r3 | see scanner fix | package absent from inventory |
| [CVE-2026-31789](https://security.alpinelinux.org/vuln/CVE-2026-31789) (CRITICAL) | libcrypto3 3.3.5-r0 → 3.5.9-r0 | 3.3.7-r0 | see scanner fix | not detected in updated package |
| [CVE-2025-15467](https://security.alpinelinux.org/vuln/CVE-2025-15467) (HIGH) | libcrypto3 3.3.5-r0 → 3.5.9-r0 | 3.3.6-r0 | see scanner fix | not detected in updated package |
| [CVE-2025-69421](https://security.alpinelinux.org/vuln/CVE-2025-69421) (HIGH) | libcrypto3 3.3.5-r0 → 3.5.9-r0 | 3.3.6-r0 | see scanner fix | not detected in updated package |
| [CVE-2026-28387](https://security.alpinelinux.org/vuln/CVE-2026-28387) (HIGH) | libcrypto3 3.3.5-r0 → 3.5.9-r0 | 3.3.7-r0 | see scanner fix | not detected in updated package |
| [CVE-2026-28388](https://security.alpinelinux.org/vuln/CVE-2026-28388) (HIGH) | libcrypto3 3.3.5-r0 → 3.5.9-r0 | 3.3.7-r0 | see scanner fix | not detected in updated package |
| [CVE-2026-28389](https://security.alpinelinux.org/vuln/CVE-2026-28389) (HIGH) | libcrypto3 3.3.5-r0 → 3.5.9-r0 | 3.3.7-r0 | see scanner fix | not detected in updated package |
| [CVE-2026-28390](https://security.alpinelinux.org/vuln/CVE-2026-28390) (HIGH) | libcrypto3 3.3.5-r0 → 3.5.9-r0 | 3.3.7-r0 | see scanner fix | not detected in updated package |
| [CVE-2026-45447](https://security.alpinelinux.org/vuln/CVE-2026-45447) (HIGH) | libcrypto3 3.3.5-r0 → 3.5.9-r0 | 3.3.7-r1 | see scanner fix | not detected in updated package |
| [CVE-2026-84782](https://security.alpinelinux.org/vuln/CVE-2026-84782) (HIGH) | libcrypto3 3.3.5-r0 → 3.5.9-r0 | 3.3.7-r2 | see scanner fix | not detected in updated package |
| [CVE-2026-5773](https://security.alpinelinux.org/vuln/CVE-2026-5773) (HIGH) | libcurl 8.14.1-r2 → absent | 8.14.1-r3 | see scanner fix | package absent from inventory |
| [CVE-2026-6276](https://security.alpinelinux.org/vuln/CVE-2026-6276) (HIGH) | libcurl 8.14.1-r2 → absent | 8.14.1-r3 | see scanner fix | package absent from inventory |
| [CVE-2026-8286](https://security.alpinelinux.org/vuln/CVE-2026-8286) (HIGH) | libcurl 8.14.1-r2 → absent | 8.14.1-r3 | see scanner fix | package absent from inventory |
| [CVE-2026-8927](https://security.alpinelinux.org/vuln/CVE-2026-8927) (HIGH) | libcurl 8.14.1-r2 → absent | 8.14.1-r3 | see scanner fix | package absent from inventory |
| [CVE-2026-92392](https://security.alpinelinux.org/vuln/CVE-2026-92392) (HIGH) | libcurl 8.14.1-r2 → absent | 8.14.1-r3 | see scanner fix | package absent from inventory |
| [CVE-2026-113351](https://security.alpinelinux.org/vuln/CVE-2026-113351) (HIGH) | libexpat 2.7.3-r0 → absent | 2.10.0-r0 | see scanner fix | package absent from inventory |
| [CVE-2026-115506](https://security.alpinelinux.org/vuln/CVE-2026-115506) (HIGH) | libexpat 2.7.3-r0 → absent | 2.10.0-r0 | see scanner fix | package absent from inventory |
| [CVE-2026-117610](https://security.alpinelinux.org/vuln/CVE-2026-117610) (HIGH) | libexpat 2.7.3-r0 → absent | 2.10.0-r0 | see scanner fix | package absent from inventory |
| [CVE-2026-118370](https://security.alpinelinux.org/vuln/CVE-2026-118370) (HIGH) | libexpat 2.7.3-r0 → absent | 2.10.0-r0 | see scanner fix | package absent from inventory |
| [CVE-2026-25210](https://security.alpinelinux.org/vuln/CVE-2026-25210) (HIGH) | libexpat 2.7.3-r0 → absent | 2.7.4-r0 | see scanner fix | package absent from inventory |
| [CVE-2026-45186](https://security.alpinelinux.org/vuln/CVE-2026-45186) (HIGH) | libexpat 2.7.3-r0 → absent | 2.8.1-r0 | see scanner fix | package absent from inventory |
| [CVE-2026-66046](https://security.alpinelinux.org/vuln/CVE-2026-66046) (HIGH) | libexpat 2.7.3-r0 → absent | 2.8.4-r0 | see scanner fix | package absent from inventory |
| [CVE-2026-76641](https://security.alpinelinux.org/vuln/CVE-2026-76641) (HIGH) | libexpat 2.7.3-r0 → absent | 2.8.4-r0 | see scanner fix | package absent from inventory |
| [CVE-2026-76956](https://security.alpinelinux.org/vuln/CVE-2026-76956) (HIGH) | libexpat 2.7.3-r0 → absent | 2.8.4-r0 | see scanner fix | package absent from inventory |
| [CVE-2026-76957](https://security.alpinelinux.org/vuln/CVE-2026-76957) (HIGH) | libexpat 2.7.3-r0 → absent | 2.8.4-r0 | see scanner fix | package absent from inventory |
| [CVE-2026-77214](https://security.alpinelinux.org/vuln/CVE-2026-77214) (HIGH) | libexpat 2.7.3-r0 → absent | 2.9.0-r0 | see scanner fix | package absent from inventory |
| [CVE-2026-93990](https://security.alpinelinux.org/vuln/CVE-2026-93990) (HIGH) | libexpat 2.7.3-r0 → absent | 2.8.5-r0 | see scanner fix | package absent from inventory |
| [CVE-2025-64720](https://security.alpinelinux.org/vuln/CVE-2025-64720) (HIGH) | libpng 1.6.47-r0 → absent | 1.6.53-r0 | see scanner fix | package absent from inventory |
| [CVE-2025-65018](https://security.alpinelinux.org/vuln/CVE-2025-65018) (HIGH) | libpng 1.6.47-r0 → absent | 1.6.53-r0 | see scanner fix | package absent from inventory |
| [CVE-2025-66293](https://security.alpinelinux.org/vuln/CVE-2025-66293) (HIGH) | libpng 1.6.47-r0 → absent | 1.6.53-r0 | see scanner fix | package absent from inventory |
| [CVE-2026-22695](https://security.alpinelinux.org/vuln/CVE-2026-22695) (HIGH) | libpng 1.6.47-r0 → absent | 1.6.54-r0 | see scanner fix | package absent from inventory |
| [CVE-2026-22801](https://security.alpinelinux.org/vuln/CVE-2026-22801) (HIGH) | libpng 1.6.47-r0 → absent | 1.6.54-r0 | see scanner fix | package absent from inventory |
| [CVE-2026-25646](https://security.alpinelinux.org/vuln/CVE-2026-25646) (HIGH) | libpng 1.6.47-r0 → absent | 1.6.55-r0 | see scanner fix | package absent from inventory |
| [CVE-2026-31789](https://security.alpinelinux.org/vuln/CVE-2026-31789) (CRITICAL) | libssl3 3.3.5-r0 → 3.5.9-r0 | 3.3.7-r0 | see scanner fix | not detected in updated package |
| [CVE-2025-15467](https://security.alpinelinux.org/vuln/CVE-2025-15467) (HIGH) | libssl3 3.3.5-r0 → 3.5.9-r0 | 3.3.6-r0 | see scanner fix | not detected in updated package |
| [CVE-2025-69421](https://security.alpinelinux.org/vuln/CVE-2025-69421) (HIGH) | libssl3 3.3.5-r0 → 3.5.9-r0 | 3.3.6-r0 | see scanner fix | not detected in updated package |
| [CVE-2026-28387](https://security.alpinelinux.org/vuln/CVE-2026-28387) (HIGH) | libssl3 3.3.5-r0 → 3.5.9-r0 | 3.3.7-r0 | see scanner fix | not detected in updated package |
| [CVE-2026-28388](https://security.alpinelinux.org/vuln/CVE-2026-28388) (HIGH) | libssl3 3.3.5-r0 → 3.5.9-r0 | 3.3.7-r0 | see scanner fix | not detected in updated package |
| [CVE-2026-28389](https://security.alpinelinux.org/vuln/CVE-2026-28389) (HIGH) | libssl3 3.3.5-r0 → 3.5.9-r0 | 3.3.7-r0 | see scanner fix | not detected in updated package |
| [CVE-2026-28390](https://security.alpinelinux.org/vuln/CVE-2026-28390) (HIGH) | libssl3 3.3.5-r0 → 3.5.9-r0 | 3.3.7-r0 | see scanner fix | not detected in updated package |
| [CVE-2026-45447](https://security.alpinelinux.org/vuln/CVE-2026-45447) (HIGH) | libssl3 3.3.5-r0 → 3.5.9-r0 | 3.3.7-r1 | see scanner fix | not detected in updated package |
| [CVE-2026-84782](https://security.alpinelinux.org/vuln/CVE-2026-84782) (HIGH) | libssl3 3.3.5-r0 → 3.5.9-r0 | 3.3.7-r2 | see scanner fix | not detected in updated package |
| [CVE-2025-49794](https://security.alpinelinux.org/vuln/CVE-2025-49794) (HIGH) | libxml2 2.13.4-r6 → absent | 2.13.9-r0 | see scanner fix | package absent from inventory |
| [CVE-2025-49795](https://security.alpinelinux.org/vuln/CVE-2025-49795) (HIGH) | libxml2 2.13.4-r6 → absent | 2.13.9-r0 | see scanner fix | package absent from inventory |
| [CVE-2025-49796](https://security.alpinelinux.org/vuln/CVE-2025-49796) (HIGH) | libxml2 2.13.4-r6 → absent | 2.13.9-r0 | see scanner fix | package absent from inventory |
| [CVE-2026-6732](https://security.alpinelinux.org/vuln/CVE-2026-6732) (HIGH) | libxml2 2.13.4-r6 → absent | 2.13.9-r1 | see scanner fix | package absent from inventory |
| [CVE-2026-107891](https://security.alpinelinux.org/vuln/CVE-2026-107891) (HIGH) | musl 1.2.5-r9 → 1.2.5-r24 | 1.2.5-r12 | see scanner fix | not detected in updated package |
| [CVE-2026-40200](https://security.alpinelinux.org/vuln/CVE-2026-40200) (HIGH) | musl 1.2.5-r9 → 1.2.5-r24 | 1.2.5-r11 | see scanner fix | not detected in updated package |
| [CVE-2026-107891](https://security.alpinelinux.org/vuln/CVE-2026-107891) (HIGH) | musl-utils 1.2.5-r9 → 1.2.5-r24 | 1.2.5-r12 | see scanner fix | not detected in updated package |
| [CVE-2026-40200](https://security.alpinelinux.org/vuln/CVE-2026-40200) (HIGH) | musl-utils 1.2.5-r9 → 1.2.5-r24 | 1.2.5-r11 | see scanner fix | not detected in updated package |
| [CVE-2026-27135](https://security.alpinelinux.org/vuln/CVE-2026-27135) (HIGH) | nghttp2-libs 1.64.0-r0 → absent | 1.68.1 | see scanner fix | package absent from inventory |
| [CVE-2026-103111](https://security.alpinelinux.org/vuln/CVE-2026-103111) (HIGH) | pcre2 10.43-r0 → 10.49-r0 | 10.43-r1 | see scanner fix | not detected in updated package |
| [CVE-2026-86145](https://security.alpinelinux.org/vuln/CVE-2026-86145) (HIGH) | pcre2 10.43-r0 → 10.49-r0 | 10.43-r1 | see scanner fix | not detected in updated package |
| [CVE-2026-89157](https://security.alpinelinux.org/vuln/CVE-2026-89157) (HIGH) | pcre2 10.43-r0 → 10.49-r0 | 10.43-r1 | see scanner fix | not detected in updated package |
| [CVE-2026-89161](https://security.alpinelinux.org/vuln/CVE-2026-89161) (HIGH) | pcre2 10.43-r0 → 10.49-r0 | 10.43-r1 | see scanner fix | not detected in updated package |
| [CVE-2026-4775](https://security.alpinelinux.org/vuln/CVE-2026-4775) (HIGH) | tiff 4.7.1-r0 → absent | 4.7.2-r0 | see scanner fix | package absent from inventory |
| [CVE-2026-22184](https://security.alpinelinux.org/vuln/CVE-2026-22184) (HIGH) | zlib 1.3.1-r2 → 1.4-r0 | 1.3.2-r0 | see scanner fix | not detected in updated package |
| [CVE-2026-85091](https://security.alpinelinux.org/vuln/CVE-2026-85091) (HIGH) | zlib 1.3.1-r2 → 1.4-r0 | 1.3.2-r1 | see scanner fix | not detected in updated package |

### Conditions and deferrals

- **CVE-2026-111497**: Crafted Brotli compressed input reaches vulnerable decoding. Brotli library came from the full image dependency chain; slim image inventory verifies removal, not merely absence of a CVE row.
- **CVE-2026-33630**: A c-ares query-completion callback frees query/channel state still linked or accessed by resend/finish handling, causing use-after-free/double-free. Base-image transitive resolver library; slim inventory verifies removal.
- **CVE-2026-5773**: Sequential SMB transfers reuse a live connection for a different share on the same server, reading/writing the wrong path with the same credentials. Frontend uses nginx proxying and wget health checks, not application curl transfers. Full-image curl/libcurl removed in slim inventory; each duplicate library/tool finding remains counted before.
- **CVE-2026-6276**: A custom Host header is removed on a reused curl easy handle, but stale cookie-routing state leaks first-host cookies. Frontend uses nginx proxying and wget health checks, not application curl transfers. Full-image curl/libcurl removed in slim inventory; each duplicate library/tool finding remains counted before.
- **CVE-2026-8286**: A STARTTLS transfer reuses a live connection despite a mismatching requested TLS configuration. Frontend uses nginx proxying and wget health checks, not application curl transfers. Full-image curl/libcurl removed in slim inventory; each duplicate library/tool finding remains counted before.
- **CVE-2026-8927**: Reusing curl handles with environment-selected proxies leaks Digest Proxy-Authorization state between different proxies. Frontend uses nginx proxying and wget health checks, not application curl transfers. Full-image curl/libcurl removed in slim inventory; each duplicate library/tool finding remains counted before.
- **CVE-2026-92392**: During HTTP/2 upload, a peer sends RST_STREAM with HTTP_1_1_REQUIRED/REFUSED_STREAM and triggers Curl_easy use-after-free. Frontend uses nginx proxying and wget health checks, not application curl transfers. Full-image curl/libcurl removed in slim inventory; each duplicate library/tool finding remains counted before.
- **CVE-2026-31789**: Large X.509 processing on affected 32-bit targets reaches memory corruption. Image is amd64; frontend currently uses HTTP, without certificate upload. OpenSSL libraries patched.
- **CVE-2025-15467**: Unauthenticated CMS AuthEnvelopedData/EnvelopedData contains oversized AEAD IV parameters copied into a fixed stack buffer. HTTP-only static frontend does not configure these protocol/parser features; OpenSSL still patched rather than treating this as immunity.
- **CVE-2025-69421**: Malformed PKCS#12 files reach PKCS12_item_decrypt_d2i_ex with a NULL octet parameter, causing a crash. HTTP-only static frontend does not configure these protocol/parser features; OpenSSL still patched rather than treating this as immunity.
- **CVE-2026-28387**: A DANE client accepts a mixed TLSA RRset with PKIX and DANE-TA usages; uncommon client/server record combinations trigger use-after-free/double-free. HTTP-only static frontend does not configure these protocol/parser features; OpenSSL still patched rather than treating this as immunity.
- **CVE-2026-28388**: Delta-CRL validation with X509_V_FLAG_USE_DELTAS processes a delta CRL missing the CRL Number extension. HTTP-only static frontend does not configure these protocol/parser features; OpenSSL still patched rather than treating this as immunity.
- **CVE-2026-28389**: CMS_decrypt processes unauthenticated KeyAgreeRecipientInfo without optional algorithm parameters and dereferences NULL. HTTP-only static frontend does not configure these protocol/parser features; OpenSSL still patched rather than treating this as immunity.
- **CVE-2026-28390**: CMS_decrypt processes unauthenticated RSA-OAEP KeyTransportRecipientInfo without optional algorithm parameters and dereferences NULL. HTTP-only static frontend does not configure these protocol/parser features; OpenSSL still patched rather than treating this as immunity.
- **CVE-2026-45447**: PKCS7_verify processes a SignedData empty digestAlgorithms set, frees a caller-owned BIO and causes use-after-free during subsequent BIO use. HTTP-only static frontend does not configure these protocol/parser features; OpenSSL still patched rather than treating this as immunity.
- **CVE-2026-84782**: A DTLS handshake-message write fails during retransmission and the retransmission state is handled incorrectly, disclosing memory or crashing. HTTP-only static frontend does not configure these protocol/parser features; OpenSSL still patched rather than treating this as immunity.
- **CVE-2026-113351**: Repeated XML_ParserReset clears byte accounting without resetting tracked allocations; a large document poisons later memory-budget checks on the reused parser. No XML transformation/upload handlers. libexpat removed with unused full-image dependencies, confirmed from package inventory.
- **CVE-2026-115506**: A moderately sized XML DTD with nested entities delays amplification detection, consuming excessive CPU before protection triggers. No XML transformation/upload handlers. libexpat removed with unused full-image dependencies, confirmed from package inventory.
- **CVE-2026-117610**: An attacker controls external-entity stream chunking so an empty nonfinal first parse leaves invalid state and a later parse dereferences NULL. No XML transformation/upload handlers. libexpat removed with unused full-image dependencies, confirmed from package inventory.
- **CVE-2026-118370**: A multi-gigabyte start tag with over 2^30 attributes overflows storeAtts counters and writes out of bounds. No XML transformation/upload handlers. libexpat removed with unused full-image dependencies, confirmed from package inventory.
- **CVE-2026-25210**: An oversized XML tag causes unchecked integer overflow while reallocating its tag buffer. No XML transformation/upload handlers. libexpat removed with unused full-image dependencies, confirmed from package inventory.
- **CVE-2026-45186**: Crafted XML attribute names trigger expensive collision checking and CPU denial of service. No XML transformation/upload handlers. libexpat removed with unused full-image dependencies, confirmed from package inventory.
- **CVE-2026-66046**: Many nonnormalized specified attributes trigger a quadratic default-attribute scan during ordinary XML parsing. No XML transformation/upload handlers. libexpat removed with unused full-image dependencies, confirmed from package inventory.
- **CVE-2026-76641**: An external-entity parser has a mismatched ELEMENT_TYPE layout during attribute handling, causing out-of-bounds access; associated with an earlier complexity fix. No XML transformation/upload handlers. libexpat removed with unused full-image dependencies, confirmed from package inventory.
- **CVE-2026-76956**: Crafted XML hash collisions exploit insufficient entropy caused by incorrect getentropy return-code handling. No XML transformation/upload handlers. libexpat removed with unused full-image dependencies, confirmed from package inventory.
- **CVE-2026-76957**: A custom encoding callback re-enters parser handlers without correct call-depth tracking, causing use-after-free. No XML transformation/upload handlers. libexpat removed with unused full-image dependencies, confirmed from package inventory.
- **CVE-2026-77214**: Repeated XML_ParseBuffer calls use unvalidated lengths after a buffer exists, advancing beyond allocation and exposing adjacent heap contents. No XML transformation/upload handlers. libexpat removed with unused full-image dependencies, confirmed from package inventory.
- **CVE-2026-93990**: Malformed UTF-16 with an unpaired high surrogate consumes the next code unit, corrupting the XML character stream passed to the application. No XML transformation/upload handlers. libexpat removed with unused full-image dependencies, confirmed from package inventory.
- **CVE-2025-64720**: PNG simplified API processes palette compositing with PNG_FLAG_OPTIMIZE_ALPHA, violating the component/alpha invariant and reading out of bounds. Nginx serves image bytes without decoding; libpng removed with unused image transform modules, inventory verified.
- **CVE-2025-65018**: PNG simplified API decodes interlaced 16-bit PNG into 8-bit output and writes beyond heap bounds. Nginx serves image bytes without decoding; libpng removed with unused image transform modules, inventory verified.
- **CVE-2025-66293**: Valid palette PNG with partial transparency/gamma correction reaches an invalid simplified-API state and reads beyond png_sRGB_base. Nginx serves image bytes without decoding; libpng removed with unused image transform modules, inventory verified.
- **CVE-2026-22695**: Interlaced 16-bit PNG decoded to 8-bit output with nonminimal row stride triggers a simplified-API over-read; regression associated with an earlier PNG fix. Nginx serves image bytes without decoding; libpng removed with unused image transform modules, inventory verified.
- **CVE-2026-22801**: Simplified PNG write APIs receive negative or greater-than-65535 row stride and truncate integer values before reading memory. Nginx serves image bytes without decoding; libpng removed with unused image transform modules, inventory verified.
- **CVE-2026-25646**: png_set_quantize with no histogram and too many palette colors can loop beyond the palette allocation. Nginx serves image bytes without decoding; libpng removed with unused image transform modules, inventory verified.
- **CVE-2025-49794**: XML Schematron sch:name path XPath processing triggers use-after-free. No XSLT/XML transformation configured; libxml2 removed in slim runtime inventory.
- **CVE-2025-49795**: Crafted XML XPath expressions trigger a NULL dereference. No XSLT/XML transformation configured; libxml2 removed in slim runtime inventory.
- **CVE-2025-49796**: XML sch:name schema elements trigger memory corruption. No XSLT/XML transformation configured; libxml2 removed in slim runtime inventory.
- **CVE-2026-6732**: A crafted XSD-validated document with an internal entity reference triggers type confusion. No XSLT/XML transformation configured; libxml2 removed in slim runtime inventory.
- **CVE-2026-107891**: Attacker-supplied regular expressions reach musl regex compilation. No endpoint accepts regular expression source; base musl patched.
- **CVE-2026-40200**: musl qsort of extremely large arrays corrupts stack state; practical threshold is about seven million elements on 32-bit, but vastly larger/impractical on 64-bit. Core libc remains required; patched from same supported Alpine branch.
- **CVE-2026-27135**: HTTP/2 frames reach nghttp2 after a session has terminated. Local frontend HTTP/1 configuration; unused nghttp2 library removed in slim runtime inventory.
- **CVE-2026-103111**: Attacker-controlled regular expressions and affected PCRE2 JIT API usage permit an arbitrary-data out-of-bounds write. Nginx uses fixed configuration patterns, not user-provided regex. PCRE2 retained and patched.
- **CVE-2026-86145**: Recursive DFA matching reuses an undersized cached workspace block; requires attacker-controlled regex or recursive patterns with a small heap limit. Nginx uses fixed configuration patterns, not user-provided regex. PCRE2 retained and patched.
- **CVE-2026-89157**: On 32-bit platforms, pcre2_pattern_convert receives an attacker-supplied large pattern and writes out of bounds; current image is amd64. Nginx uses fixed configuration patterns, not user-provided regex. PCRE2 retained and patched.
- **CVE-2026-89161**: pcre2_jit_match receives a previously copied subject through matching context and incorrectly frees memory. Nginx uses fixed configuration patterns, not user-provided regex. PCRE2 retained and patched.
- **CVE-2026-4775**: Malformed TIFF image reaches libtiff processing. No image decoding or TIFF transformation configured; libtiff removed in slim inventory.
- **CVE-2026-22184**: An excessively long archive filename is supplied to contrib/untgz demonstration utility; the core zlib compression library itself is not affected. No application untgz usage; retained zlib patched. Library-level source matching does not establish utility presence.
- **CVE-2026-85091**: zlib gzip write-error handling can overflow a heap buffer. Runtime compression paths are not fed attacker-selected filesystem write failures; base package patched. CVE-2026-76844 scanner title incorrectly refers to webpack; Debian identifies zlib, and these IDs share the remedial commit.
