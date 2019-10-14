BED files used in the experiments.

# WGS

## Split chromosomes

The reference genome is split into complete chromosomes.

## Split on N's

The reference genome is split into regions not containing an N's.

```commandline
$ java -jar picard.jar ScatterIntervalsByNs \
  R=GRCh38.no_alt_analysis_set.fa \
  OT=ACGT \
  O=split_on_Ns.interval_list \
  MAX_TO_MERGE=1000000
# Remove decoy chromosome, convert to BED
$ grep -vP '^@' split_on_Ns.interval_list | \
  grep -v chrEBV | \
  awk -v OFS='\t' '{print $1, $2-1, $3}' > split_on_Ns.bed
```

## 1 Mb intervals

Split the genome into consecutive, non-overlapping windows of up to 1 Mb.

# RNA-seq: split by GENCODE region

Regions <= 500 bp apart are merged

# Targeted: split by capture interval

Regions <= 500 bp apart are merged
