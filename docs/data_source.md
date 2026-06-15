# Data Source

The planned primary source is official NYC TLC Yellow Taxi Trip Record data:

```text
https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_YYYY-MM.parquet
```

The Taxi Zone Lookup source is:

```text
https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv
```

NYC TLC does not guarantee submitted record accuracy or completeness. Later ingestion phases
must handle schema drift, preserve raw files, and use deterministic bounded sample mode in CI.
No dataset is downloaded during Phase 1.
