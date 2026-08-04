# Sea-level-rise land-clip test — ca-30x30#104
#
# sweep.R ruled out any pure choice of inundation level: no connected(5)-connected(N)
# combination lands on the assessment's 642,610 ac. Remaining hypothesis — existing
# water was removed by a *spatial land clip* rather than by subtracting NOAA's 0 ft
# connected surface, which would keep currently-tidal ground below MHHW.
#
# Reference points (CA totals, acres):
#     connected 5 ft, unclipped                       3,901,527
#     connected 5 ft - connected 0 ft                   429,804
#     connected (5-0) + low-lying 5 ft                  694,828
#     TARGET (2025 Biodiversity Assessment slr5ft)      642,610
#
# NOAA's connected levels are strictly nested (verified against sweep-results.tsv:
# connected area increases monotonically 0->10 ft), and NOAA builds low-lying as
# disjoint from connected. So every quantity we need follows from three plain
# intersections per region:
#     (conn5 - conn0) n CA  ==  area(conn5 n CA) - area(conn0 n CA)
# No st_union and no st_difference — the first version of this script spent its
# time there and was reaped before finishing.

suppressPackageStartupMessages({library(sf)})
sf_use_s2(FALSE)

BASE    <- "https://coast.noaa.gov/slrdata/Sea_Level_Rise_Vectors/CA"
REGIONS <- c("Catalina", "Central", "Delta", "North1", "North2", "SFBay", "South")
ACRE_M2 <- 4046.8564224
EPSG    <- 3310
SCRATCH <- "/scratch"
dir.create(SCRATCH, showWarnings = FALSE, recursive = TRUE)

clean <- function(g) st_make_valid(st_transform(st_geometry(g), EPSG))
acres <- function(g) if (is.null(g) || !length(g)) 0 else sum(as.numeric(st_area(g))) / ACRE_M2

message("=== loading land mask")
# Mask ships in the ConfigMap as GeoJSON: this image's GDAL has no Parquet driver,
# so /vsicurl reads of the catalog's .parquet boundaries fail (silently, if allowed).
MASK <- tryCatch(st_union(clean(st_read("/scripts/ca-ecoregion-mask.geojson", quiet = TRUE))),
                 error = function(e) NULL)
if (is.null(MASK)) stop("CA mask unavailable — aborting")
message(sprintf("  ca_ecoregion mask: %.0f ac (pinned CA extent is 101,498,000)", acres(MASK)))

cat("RESULT\tregion\tlayer_level\tmask\tacres\n")
emit <- function(reg, lvl, mask, v) {
  cat(sprintf("RESULT\t%s\t%s\t%s\t%.1f\n", reg, lvl, mask, v)); flush(stdout())
}

for (r in REGIONS) {
  fname <- sprintf("CA_%s_slr_data_dist.zip", r)
  dest  <- file.path(SCRATCH, fname)
  exdir <- file.path(SCRATCH, "ex", r)
  message("=== ", r)
  if (!tryCatch({ download.file(file.path(BASE, fname), dest, quiet = TRUE, mode = "wb"); TRUE },
                error = function(e) FALSE)) { message("  download failed"); next }
  dir.create(exdir, recursive = TRUE, showWarnings = FALSE)
  unzip(dest, exdir = exdir)
  src <- list.files(exdir, pattern = "\\.gpkg$", recursive = TRUE, full.names = TRUE)
  if (!length(src)) { d <- list.dirs(exdir, recursive = TRUE); src <- d[grepl("\\.gdb$", d)] }
  if (!length(src)) { message("  no OGR source"); next }
  src  <- src[1]
  lyrs <- st_layers(src)$name

  for (spec in list(c("conn0", "_slr_0_0ft$"), c("conn5", "_slr_5_0ft$"), c("low5", "_low_5_0ft$"))) {
    tag <- spec[1]; hit <- lyrs[grepl(spec[2], lyrs)]
    if (!length(hit)) { message("  no layer for ", tag); next }
    g <- tryCatch(clean(st_read(src, hit[1], quiet = TRUE)),
                  error = function(e) { message("  read ", tag, " failed"); NULL })
    if (is.null(g)) next
    emit(r, tag, "none", acres(g))
    gi <- tryCatch(st_intersection(g, MASK),
                   error = function(e) { message("  clip ", tag, " failed: ", conditionMessage(e)); NULL })
    if (!is.null(gi)) emit(r, tag, "ca_ecoregion", acres(gi))
    rm(g, gi); gc(verbose = FALSE)
  }
  unlink(dest); unlink(exdir, recursive = TRUE)
}

message("=== clip test complete")
