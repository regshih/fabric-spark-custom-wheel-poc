# Environment deployment

The automation uses the stable Fabric Environment APIs to:

1. find or create the configured Environment;
2. set the requested Spark runtime in staging;
3. upload the wheel bytes as `application/octet-stream`;
4. publish with `beta=false`; and
5. wait until the published libraries and Spark settings succeed.

For the included sample, the resulting custom-library path is:

```text
Libraries/CustomLibraries/fabric_custom_wheel_sample-0.1.0-py3-none-any.whl
```

A custom wheel is never committed. Change its filename/version when replacing
its contents so Fabric can distinguish the new staged artifact.
