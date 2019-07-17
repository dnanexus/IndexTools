# TODO: convert these to Altair

library(dplyr)
library(ggplot2)
library(cowplot)

# Plot partition size vs volume
# Expect a BED file of at least 5 columns, with partition name in column 4 and
# partition volume in column 5.
plot_partitions = function(bed_path) {
    bed = read_bed(bed_path)
    tot = sum(bed$volume)
    bed %>%
        mutate(length=end-start) %>%
        select(partition, length, volume) %>%
        group_by(partition) %>%
        summarize(length=sum(length) / 1000000, volume=sum(volume) * 10000 / tot) %>%
        ggplot(aes(x=length, y=volume)) + 
          geom_point() +
          stat_smooth(method="lm", formula=y~1, se=FALSE) +
          xlab("Length (million bp)") +
          ylab("Volume (~ MB)")
}

# Plot partition volume vs number of features
# Expects a path to a BED file with 7 columns, and with partition name in column 4,
# partition volume in column 5, and number of features in column 7.
plot_volume_vs_features = function(bed_path) {
  bed = read_bed(bed_path)
  tot = sum(bed$volume)
  bed %>%
        select(partition, volume, features) %>%
        group_by(partition) %>%
        summarize(volume=sum(volume) * 10000 / tot, features=sum(features) / 1000000) %>%
        ggplot(aes(x=volume, y=features)) + 
          geom_point() +
          stat_smooth(method="lm") +
          xlab("Volume (~ MB)") +
          ylab("Read count (millions)")
  bed
}

read_bed = function(path) {
    bed = readr::read_tsv(path, col_names=FALSE)
    colnames(bed)[1:6] = c(
        "contig",
        "start",
        "end",
        "partition",
        "volume",
        "_"
    )
    if (ncol(bed) > 6) {
        colnames(bed)[7] = "features"
    }
    bed
}