# Pipeline deployment

`PL_Custom_Wheel_POC` runs the three workload notebooks sequentially. Wheel
configuration is passed through documented notebook activity parameters. The
pipeline has no credentials and no tenant-specific IDs in source; deployment
renders notebook and workspace IDs into the Fabric definition at runtime.
