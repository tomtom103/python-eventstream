# Python event streaming with Redis Streams

Heavily inspired by https://github.com/encode/broadcaster. I re-implemented the logic since the library is still relatively alpha and doesn't exactly fit the use case.

Improvements to be done:

- Rewrite the redis backend to use stream groups (see https://redis-py.readthedocs.io/en/stable/examples/redis-stream-example.html#Stream-groups)
    - Add additional job that monitors the stream, if stream gets too large messages should be put in a DLQ
    - Add additional job that pulls from the DLQ to attempt to re-run the jobs
        - If DLQ consumer fails, message should be pushed to a more permanent storage solution
- Come up with a nicer way to interact with consumers
- Add an additional Pub/Sub backend too
