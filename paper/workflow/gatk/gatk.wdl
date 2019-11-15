version 1.0

workflow gatk {
  input {
    File bam
    File bai
    String reference_genome_id
    File reference_fasta_targz
    File intervals_bed
    Int? split_column
    Int? padding
    String? output_prefix
    Int? concurrent_intervals
    Int? cpu_per_interval
    String docker_image
  }

  String default_output_prefix = select_first([
    output_prefix, basename(bam, ".bam")
  ])

  if (!defined(split_column)) {
    call haplotype_caller as gatk_hc {
      input:
        bam = bam,
        bai = bai,
        reference_genome_id = reference_genome_id,
        reference_fasta_targz = reference_fasta_targz,
        intervals_bed = intervals_bed,
        output_prefix = default_output_prefix,
        concurrent_intervals = concurrent_intervals,
        cpu_per_interval = cpu_per_interval,
        docker_image = docker_image
    }
  }
  if (defined(split_column)) {
    call haplotype_caller_split as gatk_hc_split {
      input:
        bam = bam,
        bai = bai,
        reference_genome_id = reference_genome_id,
        reference_fasta_targz = reference_fasta_targz,
        intervals_bed = intervals_bed,
        split_column = select_first([split_column]),
        padding = padding,
        output_prefix = default_output_prefix,
        concurrent_intervals = concurrent_intervals,
        cpu_per_interval = cpu_per_interval,
        docker_image = docker_image
    }
  }

  output {
    File vcf = select_first([gatk_hc.vcf, gatk_hc_split.vcf])
    File tbi = select_first([gatk_hc.tbi, gatk_hc_split.tbi])
  }
}

task haplotype_caller {
  input {
    File bam
    File bai
    String reference_genome_id
    File reference_fasta_targz
    File intervals_bed
    String output_prefix
    String docker_image
    Int? concurrent_intervals
    Int? cpu_per_interval
    Int? memory_gb_per_interval
    Int? disk_gb
  }

  Int default_concurrent_intervals = select_first([concurrent_intervals, 8])
  Int default_memory_gb_per_interval = select_first([memory_gb_per_interval, 7])
  Int xmx_per_interval = default_memory_gb_per_interval / 2
  Int total_memory = default_memory_gb_per_interval * default_concurrent_intervals
  Int default_cpu_per_interval = select_first([cpu_per_interval, 4])
  Int total_cpu = default_cpu_per_interval * default_concurrent_intervals
  Float disk_multiplier = 1.5
  Int default_disk_gb = select_first([
    disk_gb, ceil(disk_multiplier * (size(reference_fasta_targz, "G") + size(bam, "G")))
  ])
  # Hard-code instance type to ensure same instance is used for all experiments.
  String instance_type = "mem1_ssd1_v2_x36"

  command <<<
  set -uexo pipefail

  mkdir reference_genome results

  # Unpack the reference genome
  tar xvfz ~{reference_fasta_targz} -C reference_genome --strip-components=1
  genome_reference=reference_genome/~{reference_genome_id}.fa

  # Convert BED intervals to regions
  cat ~{intervals_bed} | \
    awk -F $'\t' 'BEGIN {OFS = FS} {print $1":"$2+1"-"$3}' > regions.txt

  date -Ins

  cat regions.txt | xargs -n1 -P~{default_concurrent_intervals} -I'{}' java \
    -Xmx~{xmx_per_interval}g -jar /gatk/gatk.jar \
    HaplotypeCaller \
      -R $genome_reference \
      -I ~{bam} \
      -L '{}' \
      -O results/'{}.vcf.gz' \
      --native-pair-hmm-threads ~{default_cpu_per_interval}

  date -Ins

  awk '{print "results/"$1".vcf.gz"}' regions.txt > results_files.txt
  bcftools concat -a -Ov -f results_files.txt | \
    bcftools sort -Oz -o ~{output_prefix}.gatk.vcf.gz -
  tabix -p vcf ~{output_prefix}.gatk.vcf.gz
  >>>

  output {
    File vcf = "${output_prefix}.gatk.vcf.gz"
    File tbi = "${output_prefix}.gatk.vcf.gz.tbi"
  }

  runtime {
    docker: docker_image
    dx_instance_type: instance_type
    cpu: "${total_cpu}"
    memory: "${total_memory} GB"
    disks: "local-disk ${default_disk_gb} SSD"
  }

  meta {
    description: "Call variants using GATK HaplotypeCaller."
    output_parameter_meta: {
      vcf: "Variant calls in VCF format",
      tbi: "VCF index file"
    }
  }

  parameter_meta {
    bam: {
      description: "Aligned reads in BAM format",
      stream: true
    }
    bai: "BAM file index"
    reference_genome_id: "Name of the reference genome"
    reference_fasta_targz: {
      description: "Reference genome tarball",
      stream: true,
      localization_optional: true
    }
    intervals_bed: "BED file with intervals in which to perform variant calling"
    output_prefix: "Output file prefix"
    docker_image: "Docker image to use"
    concurrent_intervals: "Concurrent number of intervals to call (1 cpu per interval); defaults to 8"
    cpu_per_interval: "Number of cpu to use peer interval; defaults to 4"
    memory_gb_per_interval: "Required number of GB of memory per interval; defaults to 7"
    disk_gb: "Required number of GB of disk space; defaults to 1.5 * (reference_targz size + bam size)"
  }
}

task haplotype_caller_split {
  input {
    File bam
    File bai
    String reference_genome_id
    File reference_fasta_targz
    File intervals_bed
    Int split_column
    Int? padding
    String output_prefix
    String docker_image
    Int? concurrent_intervals
    Int? cpu_per_interval
    Int? memory_gb_per_interval
    Int? disk_gb
  }

  Int default_concurrent_intervals = select_first([concurrent_intervals, 8])
  Int default_memory_gb_per_interval = select_first([memory_gb_per_interval, 7])
  Int xmx_per_interval = default_memory_gb_per_interval / 2
  Int total_memory = default_memory_gb_per_interval * default_concurrent_intervals
  Int default_cpu_per_interval = select_first([cpu_per_interval, 4])
  Int total_cpu = default_cpu_per_interval * default_concurrent_intervals
  Float disk_multiplier = 1.5
  Int default_disk_gb = select_first([
    disk_gb, ceil(disk_multiplier * (size(reference_fasta_targz, "G") + size(bam, "G")))
  ])
  # Hard-code instance type to ensure same instance is used for all experiments.
  String instance_type = "mem1_ssd1_v2_x36"

  command <<<
  set -uexo pipefail

  mkdir reference_genome regions results

  # unpack the reference genome
  tar xvfz ~{reference_fasta_targz} -C reference_genome --strip-components=1
  genome_reference=reference_genome/~{reference_genome_id}.fa

  # Split intervals file into one file per partition
  cat ~{intervals_bed} | awk '{print $1":"$2+1"-"$3 > "regions/"$~{split_column}".intervals"}'
  # Create files with 1) all the partition names and 2) result file names
  cat ~{intervals_bed} | cut -f ~{split_column} | sort | uniq | tee partitions.txt | \
    awk '{print "results/"$1".vcf.gz"}' > results_files.txt

  date -Ins

  cat partitions.txt | xargs -n1 -P~{default_concurrent_intervals} -I'{}' \
    java -Xmx~{xmx_per_interval}g -jar /gatk/gatk.jar HaplotypeCaller \
      -R $genome_reference \
      -I ~{bam} \
      -L regions/'{}.intervals' \
      -O results/'{}.vcf.gz' \
      ~{if defined(padding) then "--interval-padding " + padding else ""} \
      --native-pair-hmm-threads ~{default_cpu_per_interval}

  date -Ins

  bcftools concat -a -Ov -f results_files.txt | \
    bcftools sort -Oz -o ~{output_prefix}.gatk.vcf.gz -
  tabix -p vcf ~{output_prefix}.gatk.vcf.gz
  >>>

  output {
    File vcf = "${output_prefix}.gatk.vcf.gz"
    File tbi = "${output_prefix}.gatk.vcf.gz.tbi"
  }

  runtime {
    docker: docker_image
    dx_instance_type: instance_type
    cpu: "${total_cpu}"
    memory: "${total_memory} GB"
    disks: "local-disk ${default_disk_gb} SSD"
  }

  meta {
    description: "Call variants using GATK HaplotypeCaller, splitting targets on a specified column."
    output_parameter_meta: {
      vcf: "Variant calls in VCF format",
      tbi: "VCF index file"
    }
  }

  parameter_meta {
    bam: {
      description: "Aligned reads in BAM format",
      stream: true
    }
    bai: "BAM file index"
    reference_genome_id: "Name of the reference genome"
    reference_fasta_targz: {
      description: "Reference genome tarball",
      stream: true,
      localization_optional: true
    }
    intervals_bed: "BED file with intervals in which to perform variant calling"
    split_column: "Column of the intervals BED file on which to split"
    output_prefix: "Output file prefix"
    docker_image: "Docker image to use"
    concurrent_intervals: "Concurrent number of intervals to call (1 cpu per interval); defaults to 8"
    cpu_per_interval: "Number of cpu to use peer interval; defaults to 4"
    memory_gb_per_interval: "Required number of GB of memory per interval; defaults to 7"
    disk_gb: "Required number of GB of disk space; defaults to 1.5 * (reference_targz size + bam size)"
  }
}
