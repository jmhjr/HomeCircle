FROM docker.io/library/ubuntu@sha256:a2d43bffc46670d7108bb3c0468c67c5557c4c92e83e1e34cbff1322ad1b94dc
ENV DEBIAN_FRONTEND=noninteractive
RUN set -eu; \
    printf 'glibc_build_stage=apt\n'; \
    apt-get update -qq; \
    apt-get install -y -qq --no-install-recommends \
      ca-certificates curl git xz-utils tzdata build-essential pkg-config libssl-dev zlib1g-dev libbz2-dev \
      libreadline-dev libsqlite3-dev libffi-dev liblzma-dev libgdbm-dev libncurses-dev uuid-dev libexpat1-dev libzstd-dev; \
    rm -rf /var/lib/apt/lists/*; \
    mkdir -m 700 /python-build; \
    printf 'glibc_build_stage=source_download\n'; \
    curl --disable --fail --silent --show-error --proto '=https' --tlsv1.2 --connect-timeout 15 --max-time 180 \
      --max-filesize 40000000 https://www.python.org/ftp/python/3.14.6/Python-3.14.6.tar.xz \
      --output /python-build/Python-3.14.6.tar.xz; \
    printf 'glibc_build_stage=source_verify\n'; \
    printf '%s  %s\n' 143b1dddefaec3bd2e21e3b839b34a2b7fb9842272883c576420d605e9f30c63 \
      /python-build/Python-3.14.6.tar.xz | sha256sum --check --strict; \
    tar -xJf /python-build/Python-3.14.6.tar.xz --no-same-owner -C /python-build; \
    cd /python-build/Python-3.14.6; \
    printf 'glibc_build_stage=configure\n'; \
    ./configure --prefix=/opt/python --enable-shared --with-ensurepip=install; \
    printf 'glibc_build_stage=make\n'; \
    make -j2; \
    printf 'glibc_build_stage=install\n'; \
    make install; \
    printf '%s\n' /opt/python/lib >/etc/ld.so.conf.d/homecircle-python.conf; \
    ldconfig; \
    printf 'glibc_build_stage=import\n'; \
    /opt/python/bin/python3.14 -I -B -c 'import ssl,sqlite3,bz2,lzma,ctypes,readline,compression.zstd,zoneinfo,platform,sys; libc=ctypes.CDLL(None); libc.gnu_get_libc_version.restype=ctypes.c_char_p; assert sys.version_info[:3]==(3,14,6); assert platform.machine()=="x86_64"; assert libc.gnu_get_libc_version()==b"2.39"; assert zoneinfo.ZoneInfo("UTC").key=="UTC"'; \
    cd /; \
    rm -rf /python-build
