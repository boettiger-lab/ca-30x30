# Sea-level-rise land-clip test — ca-30x30#104
#
# The level sweep (sweep.R) ruled out any pure choice of inundation level: no
# `connected(5) - connected(N)` combination lands on the assessment's 642,610 ac.
# Remaining hypothesis: the assessment removed existing open water with a *spatial
# land clip* rather than by subtracting NOAA's 0 ft connected surface.
#
# Known reference points (CA totals, acres):
#     connected 5 ft, unclipped                       3,901,527
#     connected 5 ft - connected 0 ft                   429,804
#     connected (5-0) + low-lying 5 ft                  694,828
#     TARGET (2025 Biodiversity Assessment slr5ft)      642,610
#
# This measures each of those three definitions clipped to two candidate land
# masks, so the combination reproducing 642,610 can be named exactly.

suppressPackageStartupMessages({library(sf)})
sf_use_s2(FALSE)

BASE    <- "https://coast.noaa.gov/slrdata/Sea_Level_Rise_Vectors/CA"
REGIONS <- c("Catalina", "Central", "Delta", "North1", "North2", "SFBay", "South")
ACRE_M2 <- 4046.8564224
EPSG    <- 3310
SCRATCH <- "/scratch"
dir.create(SCRATCH, showWarnings = FALSE, recursive = TRUE)

acres <- function(g) if (is.null(g) || !length(g)) 0 else sum(as.numeric(st_area(g))) / ACRE_M2
clean <- function(g) st_make_valid(st_transform(st_geometry(g), EPSG))

message("=== loading land masks")
# Masks ship in the ConfigMap as GeoJSON: this image's GDAL has no Parquet driver,
# so reading the catalog's .parquet boundaries over /vsicurl silently fails.
masks <- list()
masks$ca_ecoregion <- tryCatch(
  st_union(clean(st_read("/scripts/ca-ecoregion-mask.geojson", quiet = TRUE))),
  error = function(err) { message("  ecoregion mask FAILED: ", conditionMessage(err)); NULL })

for (m in names(masks)) {
  message(sprintf("  mask %-13s %s", m,
                  if (is.null(masks[[m]])) "UNAVAILABLE" else sprintf("%.0f ac", acres(masks[[m]]))))
}
if (!length(Filter(Negate(is.null), masks))) stop("no usable land mask — aborting")

cat("RESULT\tregion\tdefinition\tmask\tacres\n")
emit <- function(reg, defn, mask, g) {
  cat(sprintf("RESULT\t%s\t%s\t%s\t%.1f\n", reg, defn, mask, acres(g))); flush(stdout())
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
  src <- src[1]
  lyrs <- st_layers(src)$name

  pick <- function(pat) { h <- lyrs[grepl(pat, lyrs)]; if (length(h)) h[1] else NA_character_ }
  l5   <- pick("_slr_5_0ft$"); l0 <- pick("_slr_0_0ft$"); lo5 <- pick("_low_5_0ft$")
  message(sprintf("  layers: 5ft=%s 0ft=%s low5=%s", l5, l0, lo5))

  g5  <- if (!is.na(l5))  clean(st_read(src, l5,  quiet = TRUE)) else NULL
  g0  <- if (!is.na(l0))  clean(st_read(src, l0,  quiet = TRUE)) else NULL
  glo <- if (!is.na(lo5)) clean(st_read(src, lo5, quiet = TRUE)) else NULL

  defs <- list()
  defs[["connected5"]] <- if (!is.null(g5)) st_union(g5) else NULL
  defs[["connected5_minus_0"]] <- tryCatch(
    if (!is.null(g5) && !is.null(g0)) st_difference(st_union(g5), st_union(g0)) else NULL,
    error = function(e) { message("  difference failed: ", conditionMessage(e)); NULL })
  defs[["connected5_minus_0_plus_low5"]] <- tryCatch(
    if (!is.null(defs[["connected5_minus_0"]]) && !is.null(glo))
      st_union(defs[["connected5_minus_0"]], st_union(glo)) else defs[["connected5_minus_0"]],
    error = function(e) { message("  union failed: ", conditionMessage(e)); NULL })

  for (dn in names(defs)) {
    g <- defs[[dn]]
    if (is.null(g)) next
    emit(r, dn, "none", g)
    for (mn in names(masks)) {
      if (is.null(masks[[mn]])) next
      gi <- tryCatch(st_intersection(g, masks[[mn]]),
                     error = function(e) { message("  clip ", dn, "/", mn, " failed"); NULL })
      if (!is.null(gi)) emit(r, dn, mn, gi)
    }
  }

  rm(g5, g0, glo, defs); gc(verbose = FALSE)
  unlink(dest); unlink(exdir, recursive = TRUE)
}

message("=== clip test complete")
