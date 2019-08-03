# Installs samtools, bcftools, and htslib tools.
FROM debian:stretch-slim as hts

ARG HTS_VERSION

ADD https://github.com/samtools/samtools/releases/download/${HTS_VERSION}/samtools-${HTS_VERSION}.tar.bz2 /tmp/apps/samtools.tar.bz2
ADD https://github.com/samtools/bcftools/releases/download/${HTS_VERSION}/bcftools-${HTS_VERSION}.tar.bz2 /tmp/apps/bcftools.tar.bz2
ADD https://github.com/samtools/htslib/releases/download/${HTS_VERSION}/htslib-${HTS_VERSION}.tar.bz2 /tmp/apps/htslib.tar.bz2

RUN apt update \
  && apt -y install \
		g++ make libc-dev curl git wget \
		zlib1g-dev libbz2-dev bzip2 liblzma-dev libncurses-dev \
	&& cd /tmp/apps \
	&& mkdir htslib \
	&& tar xjvf htslib.tar.bz2 -C htslib --strip-components=1 \
	&& cd htslib \
	&& ./configure \
	&& make \
	&& make install \
	&& cd /tmp/apps \
	&& mkdir samtools \
	&& tar xjvf samtools.tar.bz2 -C samtools --strip-components=1 \
	&& cd samtools \
	&& ./configure \
	&& make \
	&& make install \
	&& cd /tmp/apps \
	&& mkdir bcftools \
	&& tar xjvf bcftools.tar.bz2 -C bcftools --strip-components=1 \
	&& cd bcftools \
	&& ./configure \
	&& make \
	&& make install \
	&& cd / \
	&& cp -r /tmp/apps/htslib /usr/local \
	&& rm -Rf /tmp/apps

ARG GATK_VERSION

FROM broadinstitute/gatk:${GATK_VERSION}

ENV LANG C.UTF-8

RUN apt update \
  && apt install -y libcurl4-openssl-dev libncurses-dev

COPY --from=hts /usr/local/bin/samtools /usr/local/bin
COPY --from=hts /usr/local/bin/bcftools /usr/local/bin
COPY --from=hts /usr/local/bin/bgzip /usr/local/bin
COPY --from=hts /usr/local/bin/tabix /usr/local/bin
