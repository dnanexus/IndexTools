version 1.0

task bam2fastq {
  input {
    File bam
    Int? disk_gb
    String? docker_image
  }

  String output_prefix = basename(bam, ".bam")
  Int default_disk_gb = select_first([disk_gb, ceil(2.5 * size(bam, "G"))])
  String default_docker_image = select_first([docker_image, "dnanexus/htslib:1.9"])

  command <<<
  set -uexo pipefail
  samtools collate -O ~{bam} | \
  samtools fastq \
    -n \
    -1 ~{output_prefix}_R1.fq.gz \
    -2 ~{output_prefix}_R2.fq.gz \
    -0 ~{output_prefix}_invalid.fq.gz \
    -s ~{output_prefix}_singletons.fq.gz \
    /dev/stdin
  >>>

  output {
    File read1_fq_gz = "${output_prefix}_R1.fq.gz"
    File read2_fq_gz = "${output_prefix}_R2.fq.gz"
    File? invalid_fq_gz = "${output_prefix}_invalid.fq.gz"
    File? singleton_fq_gz = "${output_prefix}_singletons.fq.gz"
  }

  runtime {
    docker: default_docker_image
    disks: "local-disk ${default_disk_gb} SSD"
  }

  parameter_meta {
    bam: {
      description: "BAM file",
      stream: true
    }
  }
}
