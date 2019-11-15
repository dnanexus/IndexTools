version 1.0

struct ReadGroup {
  String ID
  String LB
  String SM
}

task addreplacerg {
  input {
    File bam
    ReadGroup read_group
    Int? cpu
    Int? disk_gb
    String? docker_image
  }

  String output_prefix = basename(bam, ".bam")
  Int default_cpu = select_first([cpu, 8])
  Int default_disk_gb = select_first([disk_gb, ceil(2.5 * size(bam, "G"))])
  String default_docker_image = select_first([docker_image, "dnanexus/htslib:1.9"])

  command <<<
  set -uexo pipefail
  samtools addreplacerg \
    -r ID:~{read_group.ID} \
    -r LB:~{read_group.LB} \
    -r SM:~{read_group.SM} \
    -@ ~{default_cpu-1} \
    -o ~{output_prefix}.withrg.bam \
    ~{bam}
  samtools index ~{output_prefix}.withrg.bam
  >>>

  output {
    File bam_withrg = "${output_prefix}.withrg.bam"
    File bai_withrg = "${output_prefix}.withrg.bam.bai"
  }

  runtime {
    docker: default_docker_image
    cpu: "${default_cpu}"
    disks: "local-disk ${default_disk_gb} SSD"
  }

  parameter_meta {
    bam: {
      description: "BAM file",
      stream: true
    }
  }
}
