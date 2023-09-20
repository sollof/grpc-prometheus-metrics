import asyncio
import logging
import sys
import time

import grpc
from grpc.aio import insecure_channel
from prometheus_client import start_http_server

import tests.integration.hello_world.hello_world_pb2 as hello_world_pb2
import tests.integration.hello_world.hello_world_pb2_grpc as hello_world_grpc
from grpc_prometheus_metrics.aio.prometheus_aio_client_interceptor import PromAioUnaryUnaryClientInterceptor


_ONE_DAY_IN_SECONDS = 60 * 60 * 24
_LOGGER = logging.getLogger(__name__)


async def call_server():
    channel = insecure_channel("localhost:50051", interceptors=[
        PromAioUnaryUnaryClientInterceptor(enable_client_handling_time_histogram=True)
    ])
    stub = hello_world_grpc.GreeterStub(channel)

    # Call the unary-unary.
    names = ['Bob', 'Tom', 'Jack', 'Peter', 'Alice']
    for name in names:
        request = hello_world_pb2.HelloRequest(name=name)
        try:
            response = await stub.SayHello(request)
            _LOGGER.info(f"Unary response: {response=}")
        except grpc.RpcError:
            _LOGGER.error("Got an exception from server")
    _LOGGER.info("")


def run():
    logging.basicConfig(level=logging.INFO, format="%(asctime)-15s %(message)s")
    _LOGGER.info("Starting py-grpc-promtheus hello word server")
    asyncio.run(call_server())
    start_http_server(50053)
    _LOGGER.info("Started py-grpc-promtheus async client, metrics is located at http://localhost:50053")
    try:
        while True:
            time.sleep(_ONE_DAY_IN_SECONDS)
    except KeyboardInterrupt:
        sys.exit()


if __name__ == "__main__":
    run()
