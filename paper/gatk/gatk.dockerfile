ARG HTS_VERSION
ARG GATK_VERSION
FROM dnanexus/htslib:${HTS_VERSION} as hts
FROM broadinstitute/gatk:${GATK_VERSION}

ENV LANG C.UTF-8

RUN apt update \
  && apt install -y libcurl4-openssl-dev libncurses-dev

COPY --from=hts /usr/local/bin/samtools /usr/local/bin
COPY --from=hts /usr/local/bin/bcftools /usr/local/bin
COPY --from=hts /usr/local/bin/bgzip /usr/local/bin
COPY --from=hts /usr/local/bin/tabix /usr/local/bin
