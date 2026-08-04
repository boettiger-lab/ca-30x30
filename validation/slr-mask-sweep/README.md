# Sea-level-rise mask sweep — ca-30x30#104

Why our CA 5 ft SLR extent (3.90M ac) differs from the 2025 Biodiversity
Assessment's `slr5ft` (642,610 ac). Both jobs run on NRP, pull from
`coast.noaa.gov` over HTTPS, and write nothing to S3 — no credentials, and they
cannot disturb the published dataset.

## `sweep.R` — every published level (complete)

Measures all 42 layers per region (connected + low-lying, 0.0–10.0 ft in
half-foot steps) across the 7 California regions, in EPSG:3310.
Results: `sweep-results.tsv`.

**Conclusion: no choice of inundation level reproduces 642,610.** The two clean
NOAA-only definitions bracket it and nothing in between is a natural datum —
the target sits between subtracting the 0.5 ft and 1.0 ft connected surfaces,
which is not a definition anyone would choose.

## `clip.R` — land clip (complete, hypothesis rejected)

Tested whether the assessment removed existing open water with a *spatial land
clip* instead of by subtracting NOAA's 0 ft surface. Clips against the CA-Nature
ecoregion extent — the app's own definition of California, and the same one
behind the pinned 101,498,000-ac denominator. Results: `clip-results.tsv`.

**Conclusion: the land clip is nearly a no-op and does not explain the gap.**
Once the 0 ft surface is subtracted, clipping changes the total by 0.6%
(427,260 clipped vs 429,804 unclipped) — the subtraction has already removed the
ocean. Clipping the raw 5 ft surface to land gives 889,511 ac (+38%), also not
the target.

Both self-testable hypotheses — level choice and land clip — are therefore
eliminated. The closest reproducible definition stays `connected(5−0) +
low-lying 5 ft` at 692,275 ac, **+7.7%** vs the assessment's 642,610.

NOAA's connected levels are strictly nested (verified in `sweep-results.tsv`)
and low-lying is disjoint from connected, so the script needs only three plain
intersections per region — no `st_union`, no `st_difference`. The first version
did use those, spent all its time there, and was reaped before finishing;
results now also get captured locally while the job runs, because **NRP reaps
completed Jobs and their logs go with them**.

The mask ships in the ConfigMap as GeoJSON: **the `ml-spatial` image's GDAL has
no Parquet driver**, so reading the catalog's `.parquet` boundaries over
`/vsicurl` fails (silently, if you let it — the first run produced only
unclipped rows). It validates on load at 101,501,429 ac, 0.003% off the pin.

## Running

```bash
kubectl create configmap slr-mask-sweep --from-file=sweep.R -n biodiversity
kubectl apply -f job.yaml -n biodiversity
kubectl logs -f job/slr-mask-sweep -n biodiversity

kubectl create configmap slr-land-clip --from-file=clip.R --from-file=ca-ecoregion-mask.geojson -n biodiversity
kubectl apply -f job-clip.yaml -n biodiversity
kubectl logs -f job/slr-land-clip -n biodiversity
```

Both emit tab-separated `RESULT` lines. Delta and SFBay carry the heavy geometry
and dominate runtime (~30 min for the clip job).
