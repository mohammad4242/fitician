FROM ubuntu:24.04@sha256:33ceb71981b602c1a7443a53469e4dba065f7503eab3078a2d7a57a2ab987517
ARG SQUID_VERSION=6.14-0ubuntu0.24.04.5
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install --no-install-recommends -y \
       squid=${SQUID_VERSION} ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /run/squid \
    && chown 13:13 /run/squid
USER 13:13
ENTRYPOINT ["/usr/sbin/squid"]
CMD ["-N", "-f", "/etc/squid/squid.conf"]
