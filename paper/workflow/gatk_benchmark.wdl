version 1.0

import "gatk/gatk.wdl"

workflow gatk_benchmark {
  input {
    File bam
    File? bai
    File? contig_sizes
    String reference_genome_id
    File reference_fasta_targz
    File? intervals_bed
    File? targets_bed
    Int? split_column
    Int? padding
    String output_prefix
    Int? gatk_concurrent_intervals
    Int? gatk_cpu_per_interval
    String? indextools_docker_image
    String? gatk_docker_image
  }

  String default_indextools_docker_image = select_first([
    indextools_docker_image, "dnanexus/indextools:0.1.3"
  ])
  String default_gatk_docker_image = select_first([
    gatk_docker_image, "dnanexus/gatk:gatk-4.1.3.0_hts-1.9"
  ])

  if (!defined(bai)) {
    call index_bam {
      input:
        bam = bam,
        docker_image = default_gatk_docker_image
    }
  }

  File actual_bai = select_first([bai, index_bam.bai])

  if (!defined(intervals_bed)) {
    call indextools_partition as partition {
      input:
        bai = actual_bai,
        bam = bam,
        contig_sizes = contig_sizes,
        partitions = 36,
        targets_bed = targets_bed,
        output_prefix = output_prefix,
        docker_image = default_indextools_docker_image
    }
  }

  File actual_intervals_bed = select_first([
    intervals_bed, partition.bed
  ])

  call gatk.gatk {
    input:
      bam = bam,
      bai = actual_bai,
      reference_genome_id = reference_genome_id,
      reference_fasta_targz = reference_fasta_targz,
      intervals_bed = actual_intervals_bed,
      split_column = split_column,
      padding = padding,
      output_prefix = output_prefix,
      concurrent_intervals = gatk_concurrent_intervals,
      cpu_per_interval = gatk_cpu_per_interval,
      docker_image = default_gatk_docker_image
  }

  output {
    File vcf = gatk.vcf
    File tbi = gatk.tbi
    File intervals = actual_intervals_bed
  }
}

task index_bam {
  input {
    File bam
    String docker_image
  }

  command <<<
  samtools index ~{bam}
  >>>

  output {
    File bai = "${bam}.bai"
  }

  runtime {
    docker: docker_image
  }
}

task indextools_partition {
  input {
    File bai
    File? bam
    File? contig_sizes
    Int partitions
    File? targets_bed
    String? output_prefix
    String docker_image
    Int? memory_gb
  }

  String default_output_prefix = select_first([output_prefix, basename(bai, ".bam.bai")])
  Int default_memory_gb = select_first([memory_gb, 8])

  command <<<
  indextools partition -I ~{bai} \
    ~{if defined(contig_sizes) then "-z " + contig_sizes else "-i " + bam} \
    ~{if defined(targets_bed) then "-t " + targets_bed else ""} \
    -n ~{partitions} \
    -o ~{output_prefix}.bed
  >>>

  output {
    File bed = "${output_prefix}.bed"
  }

  runtime {
    docker: docker_image
    memory: "${default_memory_gb} GB"
  }
}
