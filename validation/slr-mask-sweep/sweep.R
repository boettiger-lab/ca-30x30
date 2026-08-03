# Sea-level-rise mask sweep — ca-30x30#104
#
# The 2025 Biodiversity Assessment reports a CA 5 ft SLR extent of 642,610 ac.
# Our published layer (NOAA ocean-connected 5.0 ft surface) is 3.90M ac because
# the connected surface includes the existing ocean. Two clean reconstructions of
# "newly-inundated land" bracket the target but miss it:
#     connected 5ft - connected 0ft            = 429,804 ac  (-33%)
#     connected (5-0) + low-lying 5ft          = 694,828 ac  (+8%)
#
# So the open parameter is the *water-level mask*: which surface counts as
# "already water". This sweeps every level NOAA publishes, connected and
# low-lying, for all 7 California regions, so the combination that lands on
# 642,610 can be identified directly instead of asked for.
#
# Emits one tab-separated RESULT line per (region, layer) for downstream analysis.

suppressPackageStartupMessages(library(sf))
sf_use_s2(FALSE)

BASE    <- "https://coast.noaa.gov/slrdata/Sea_Level_Rise_Vectors/CA"
REGIONS <- c("Catalina", "Central", "Delta", "North1", "North2", "SFBay", "South")
ACRE_M2 <- 4046.8564224
SCRATCH <- "/scratch"

dir.create(SCRATCH, showWarnings = FALSE, recursive = TRUE)
cat("RESULT\tregion\tlayer\tkind\tlevel_ft\tacres\n")

for (r in REGIONS) {
  fname <- sprintf("CA_%s_slr_data_dist.zip", r)
  dest  <- file.path(SCRATCH, fname)
  exdir <- file.path(SCRATCH, "ex", r)

  message("=== ", r, ": downloading ", fname)
  ok <- tryCatch({
    download.file(file.path(BASE, fname), dest, quiet = TRUE, mode = "wb")
    TRUE
  }, error = function(e) { message("  DOWNLOAD FAILED: ", conditionMessage(e)); FALSE })
  if (!ok) next

  dir.create(exdir, recursive = TRUE, showWarnings = FALSE)
  tryCatch(unzip(dest, exdir = exdir), error = function(e) message("  UNZIP FAILED"))

  # Format varies by region vintage: newer = GeoPackage, older = Esri File GDB.
  src <- list.files(exdir, pattern = "\\.gpkg$", recursive = TRUE, full.names = TRUE)
  if (!length(src)) {
    dirs <- list.dirs(exdir, recursive = TRUE)
    src  <- dirs[grepl("\\.gdb$", dirs)]
  }
  if (!length(src)) { message("  NO OGR SOURCE FOUND"); next }
  src <- src[1]

  lyrs <- tryCatch(st_layers(src)$name, error = function(e) character(0))
  message("  source: ", basename(src), " (", length(lyrs), " layers)")

  for (ln in lyrs) {
    # NOAA naming: *_slr_<N>_<M>ft (ocean-connected) and *_low_<N>_<M>ft (low-lying).
    # Older vintages use *_slr_<N>ft. Levee-modelled variants are recorded too.
    m <- regmatches(ln, regexec("_(slr|low)_([0-9]+)(?:_([0-9]+))?ft", ln))[[1]]
    if (!length(m)) next
    kind  <- if (m[2] == "slr") "connected" else "lowlying"
    level <- as.numeric(m[3]) + (if (nzchar(m[4])) as.numeric(m[4]) / 10 else 0)

    acres <- tryCatch({
      g <- st_read(src, ln, quiet = TRUE)
      g <- st_transform(g, 3310)
      g <- st_make_valid(g)
      sum(as.numeric(st_area(g))) / ACRE_M2
    }, error = function(e) { message("  layer ", ln, " FAILED: ", conditionMessage(e)); NA_real_ })

    cat(sprintf("RESULT\t%s\t%s\t%s\t%.1f\t%.1f\n", r, ln, kind, level, acres))
    flush(stdout())
    suppressWarnings(rm(g)); gc(verbose = FALSE)
  }

  unlink(dest); unlink(exdir, recursive = TRUE)
}

message("=== sweep complete")
