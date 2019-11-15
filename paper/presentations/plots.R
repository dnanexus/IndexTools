# TODO: convert these to Altair

library(ggplot2)
library(cowplot)
theme_set(theme_cowplot())

library(dplyr)
library(rjson)
library(readr)

cost_per_sec = 0.000659

plot_results = function(prefix, scale_colors, log_scale=FALSE, jitter=0) {
  results = fromJSON(read_file(paste(prefix, "json", sep=".")))
  results_tab = na.omit(melt(
    rbindlist(results, fill=TRUE, idcol=TRUE),
    id.vars=".id"
  ))
  colnames(results_tab) = c("DataType", "PartitionType", "RuntimeSecs")
  results_tab$Cost = results_tab$RuntimeSecs * cost_per_sec
  if (log_scale) {
    scale_fn = scale_x_log10
    scale_lab = "Runtime (Log10(Sec))"
  }
  else {
    scale_fn = scale_x_continuous
    scale_lab = "Runtime (Sec)"
  }
  p = ggplot(results_tab, aes(x=RuntimeSecs, y=DataType, color=PartitionType)) +
    geom_point(position=position_jitter(width=0, height=jitter), size=3) +
    scale_fn(scale_lab, sec.axis = sec_axis(~ . * cost_per_sec, name = "Cost ($)")) +
    ylab("Data Type") +
    scale_color_manual(values=scale_colors)
  ggsave(paste(prefix, "pdf", sep="."), p, width=8, height=3, units="in")
  results_tab
}

targ_res = plot_results("results/targeted", c("orange", "gray", "blue"))
targ_res %>% group_by(PartitionType) %>% summarize(duration=sum(RuntimeSecs), cost=sum(Cost))
targ_res %>% group_by(DataType) %>% summarize(duration=sum(RuntimeSecs), cost=sum(Cost))

whol_res = plot_results("results/whole", c("blue", "purple", "orange", "grey"), TRUE, 0.1)
whol_res %>% group_by(PartitionType) %>% summarize(duration=sum(RuntimeSecs), cost=sum(Cost))
whol_res %>% group_by(DataType) %>% summarize(duration=sum(RuntimeSecs), cost=sum(Cost))

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