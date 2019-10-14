# Required:
# pip install CrossMap
# gsort (https://github.com/brentp/gsort/releases)
# bedtools (https://bedtools.readthedocs.io)
wget ftp://ftp-trace.ncbi.nlm.nih.gov/giab/ftp/data/AshkenazimTrio/analysis/OsloUniversityHospital_Exome_GATK_jointVC_11242015/wex_Agilent_SureSelect_v05_b37.baits.slop50.merged.list
wget -c http://hgdownload.cse.ucsc.edu/goldenPath/hg19/liftOver/hg19ToHg38.over.chain.gz
grep -v ^@ wex_Agilent_SureSelect_v05_b37.baits.slop50.merged.list | \
  sed "s/^\([0-9]\+\)\t/chr\1\t/g" | \
  sed "s/^MT/chrM/g" | \
  sed "s/^X/chrX/g" | \
  sed "s/^Y/chrY/g" | \
  CrossMap.py bed hg19ToHg38.over.chain.gz /dev/stdin Exome-Agilent-raw.bed
grep -v '_alt' Exome-Agilent-raw.bed > Exome-Agilent-raw-noalt.bed
gsort Exome-Agilent-raw-noalt.bed ../../GRCh38.no_alt_analysis_set.fa.fai \
  > Exome-Agilent-SureSelect-v05-hg38.bed
cut -f 1-3 Exome-Agilent-SureSelect-v05-hg38.bed | \
  bedtools merge -d 500 > Exome-Agilent-SureSelect-v05-hg38-merged.bed