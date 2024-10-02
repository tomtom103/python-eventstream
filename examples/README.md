# How to use examples

They are mostly visual, however we can test out the behavior by running the `fastapi_publisher.py` in one terminal, `worker_consumer.py` in another and making requests to the API.

This will look like the following:

API:

```bash
$ python examples/fastapi_publisher.py 
INFO:     Started server process [18317]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8080 (Press CTRL+C to quit)
Publishing message on channel: api-header-publisher
Publishing message on channel: api-call-counter
INFO:     127.0.0.1:49948 - "GET /foo HTTP/1.1" 200 OK

```

Consumer:

```bash
$ python examples/worker_consumer.py 
Received event: {"headers": {"host": "0.0.0.0:8080", "accept": "*/*", "accept-encoding": "gzip, deflate", "connection": "keep-alive", "user-agent": "python-httpx/0.27.2"}} from channel: api-header-publisher
Received event: 7 from channel: api-call-counter
```

Running multiple consumers at once will lead to all consumers receiving the published messages

API call:

```bash
$ httpx http://0.0.0.0:8080/foo
HTTP/1.1 200 OK
date: Wed, 02 Oct 2024 03:57:11 GMT
server: uvicorn
content-length: 15
content-type: application/json

{
    "status": "ok"
}
```
