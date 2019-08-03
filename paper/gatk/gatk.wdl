version 1.0

task index_bam {
  input {
    File bam
    String docker_image
  }

  command <<<
  samtools index ~{bam}
  >>>

  runtime {
    docker: "${docker_image}"
  }

  output {
    File bai = "${bam}.bai"
  }
}

task haplotype_caller {
  input {
    File bam
    File bai
    File reference_targz
    File intervals_bed
    String output_prefix
    String docker_image
    Int? concurrent_intervals
    Int? cpu_per_interval
    Int? memory_gb_per_interval
    Int? disk_gb
  }

  # TODO: when mem1_ssd1_x36 instances are generally avaialble, this task should be
  #  configured to use it specifically, as these are C5 instances which provide AVX
  #  instruction set that enables acceleration of the PairHMM algorithm.
  Int default_concurrent_intervals = select_first([concurrent_intervals, 8])
  Int default_memory_gb_per_interval = select_first([memory_gb_per_interval, 7])
  Int xmx_per_interval = ceil(default_memory_gb_per_interval * 0.8)
  Int total_memory = default_memory_gb_per_interval * default_concurrent_intervals
  Int default_cpu_per_interval = select_first([cpu_per_interval, 4])
  Int total_cpu = default_cpu_per_interval * default_concurrent_intervals
  Float disk_multiplier = 1.5
  Int default_disk_gb = select_first([
    disk_gb, ceil(disk_multiplier * (size(reference_targz, "G") + size(bam, "G")))
  ])

  command <<<
  set -uexo pipefail

  mkdir reference_genome
  tar xvfz ~{reference_targz} -C reference_genome --strip-components=1
  genome_reference_basename=$(basename ~{reference_targz} .tar.gz)
  genome_reference=reference_genome/$genome_reference_basename.fa

  mkdir results
  cat ~{intervals_bed} | \
    awk -F $'\t' 'BEGIN {OFS = FS} {print $1":"$2+1"-"$3}' > regions.txt
  cat regions.txt | xargs -n1 -P~{default_concurrent_intervals} -I'{}' java \
    -Xmx~{xmx_per_interval}g -jar /gatk/gatk.jar \
    HaplotypeCaller \
      -R $genome_reference \
      -I ~{bam} \
      -L '{}' \
      -O results/'{}.vcf.gz' \
      --native-pair-hmm-threads ~{default_cpu_per_interval}

  awk '{print "results/"$1".vcf.gz"}' regions.txt > results_files.txt
  bcftools concat -f results_files.txt | bgzip -c > ~{output_prefix}.gatk.vcf.gz
  tabix -p vcf ~{output_prefix}.gatk.vcf.gz
  >>>

  runtime  {
    docker: docker_image
    cpu: "${total_cpu}"
    memory: "${total_memory} GB"
    disks: "local-disk ${default_disk_gb} SSD"
  }

  meta {
    description: "Call variants using GATK HaplotypeCaller."
  }

  parameter_meta {
    reference_targz: {
      description: "Tarball of reference genome and BWA index",
      stream: true,
      localization_optional: true
    }
  }

  output  {
    File vcf = "${output_prefix}.gatk.vcf.gz"
    File tbi = "${output_prefix}.gatk.vcf.gz.tbi"
  }
}

workflow gatk {
  input {
    File bam
    File? bai
    File reference_targz
    File intervals_bed
    String? output_prefix
    String? docker_image
  }

  String default_output_prefix = select_first([
    output_prefix, basename(bam, ".bam")
  ])
  String default_docker_image = select_first([
    docker_image, "indextools/gatk:gatk-4.1.2.0-hts-1.9"
  ])

  if (!defined(bai)) {
    call index_bam {
      input:
        bam = bam,
        docker_image = docker_image
    }
  }

  File bai_actual = select_first([bai, index_bam.bai])

  call haplotype_caller as gatk_hc {
    input:
      bam = bam,
      bai = bai_actual,
      reference_targz = reference_targz,
      intervals_bed = intervals_bed,
      output_prefix = default_output_prefix,
      docker_image = docker_image
  }

  output {
    File vcf = gatk_hc.vcf
    File tbi = gatk_hc.tbi
  }
}
