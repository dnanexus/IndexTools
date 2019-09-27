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
    String output_prefix
    String indextools_docker_image
    String gatk_docker_image
  }

  if (!defined(bai)) {
    call index_bam {
      input:
        bam = bam,
        docker_image = gatk_docker_image
    }
  }

  File actual_bai = select_first([bai, index_bam.bai])

  if (!defined(intervals_bed)) {
    if (defined(contig_sizes)) {
      call indextools_partition as partition_bai {
        input:
          bai = actual_bai,
          contig_sizes = contig_sizes,
          partitions = 36,
          output_prefix = output_prefix,
          docker_image = indextools_docker_image
      }
    }
    if (!defined(contig_sizes)) {
      call indextools_partition as partition_bam {
        input:
          bai = actual_bai,
          bam = bam,
          partitions = 36,
          output_prefix = output_prefix,
          docker_image = indextools_docker_image
      }
    }
  }

  File actual_intervals_bed = select_first([
    intervals_bed, partition_bai.bed, partition_bam.bed
  ])

  call gatk.gatk {
    input:
      bam = bam,
      bai = actual_bai,
      reference_genome_id = reference_genome_id,
      reference_fasta_targz = reference_fasta_targz,
      intervals_bed = actual_intervals_bed,
      output_prefix = output_prefix,
      docker_image = gatk_docker_image
  }

  output {
    File vcf = gatk.vcf
    File tbi = gatk.tbi
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
    String? output_prefix
    String? docker_image
  }

  String default_output_prefix = select_first([output_prefix, basename(bai, ".bam.bai")])
  String default_docker_image = "dnanexus/indextools:0.1.2"

  command <<<
  indextools partition -I ~{bai} \
    ~{if defined(bam) then "-i " + bam else ""} \
    ~{if defined(contig_sizes) then "-z " + contig_sizes else ""} \
    -n ~{partitions} \
    -o ~{output_prefix}.bed
  >>>

  output {
    File bed = "${output_prefix}.bed"
  }

  runtime {
    docker: default_docker_image
  }
}
