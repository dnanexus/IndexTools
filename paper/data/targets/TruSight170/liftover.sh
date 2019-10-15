#wget https://support.illumina.com/content/dam/illumina-support/documents/downloads/productfiles/trusight/trusight-tumor-170/trusight-tumor-170-dna-manifest-file.zip
#unzip trusight-tumor-170-dna-manifest-file.zip
tail -n +8 trusight-tumor-170-dna-manifest-file.txt | \
  cut -f 2-4 | \
  awk 'BEGIN {OFS="\t"} {print $1, $2-1, $3}' > trusight-tumor-170-dna-manifest-file.bed
CrossMap.py bed \
  ../hg19ToHg38.over.chain.gz \
  trusight-tumor-170-dna-manifest-file.bed \
  trusight-tumor-170-GRCh38.bed
