"""Interceptor a client call with prometheus"""

from timeit import default_timer

import grpc
from prometheus_client.registry import REGISTRY

from grpc_prometheus_metrics import grpc_utils
from grpc_prometheus_metrics.client_metrics import init_metrics


async def build_generator(items):
    for item in items:
        yield item


class PromAioClientInterceptor(grpc.aio.UnaryUnaryClientInterceptor):
    """
    Intercept gRPC client requests.
    """

    def __init__(
        self,
        enable_client_handling_time_histogram=False,
        enable_client_stream_receive_time_histogram=False,
        enable_client_stream_send_time_histogram=False,
        legacy=False,
        registry=REGISTRY,
    ):
        self._enable_client_handling_time_histogram = enable_client_handling_time_histogram
        self._enable_client_stream_receive_time_histogram = (
            enable_client_stream_receive_time_histogram
        )
        self._enable_client_stream_send_time_histogram = enable_client_stream_send_time_histogram
        self._legacy = legacy
        self._metrics = init_metrics(registry)

    async def intercept_unary_unary(self, continuation, client_call_details, request):
        grpc_service_name, grpc_method_name, _ = grpc_utils.split_method_call(client_call_details)
        grpc_type = grpc_utils.UNARY

        self._metrics["grpc_client_started_counter"].labels(
            grpc_type=grpc_type, grpc_service=grpc_service_name, grpc_method=grpc_method_name
        ).inc()

        start = default_timer()
        handler = await continuation(client_call_details, request)
        code = await handler.code()

        if self._legacy:
            self._metrics["legacy_grpc_client_completed_latency_seconds_histogram"].labels(
                grpc_type=grpc_type, grpc_service=grpc_service_name, grpc_method=grpc_method_name
            ).observe(max(default_timer() - start, 0))
        elif self._enable_client_handling_time_histogram:
            self._metrics["grpc_client_handled_histogram"].labels(
                grpc_type=grpc_type, grpc_service=grpc_service_name, grpc_method=grpc_method_name
            ).observe(max(default_timer() - start, 0))

        if self._legacy:
            self._metrics["legacy_grpc_client_completed_counter"].labels(
                grpc_type=grpc_type,
                grpc_service=grpc_service_name,
                grpc_method=grpc_method_name,
                code=code.name,
            ).inc()
        else:
            self._metrics["grpc_client_handled_counter"].labels(
                grpc_type=grpc_type,
                grpc_service=grpc_service_name,
                grpc_method=grpc_method_name,
                grpc_code=code.name,
            ).inc()

        return handler


class PromAioUnaryStreamClientInterceptor(grpc.aio.UnaryStreamClientInterceptor):
    def __init__(
        self,
        enable_client_handling_time_histogram=False,
        enable_client_stream_receive_time_histogram=False,
        enable_client_stream_send_time_histogram=False,
        legacy=False,
        registry=REGISTRY,
    ):
        self._enable_client_handling_time_histogram = enable_client_handling_time_histogram
        self._enable_client_stream_receive_time_histogram = (
            enable_client_stream_receive_time_histogram
        )
        self._enable_client_stream_send_time_histogram = enable_client_stream_send_time_histogram
        self._legacy = legacy
        self._metrics = init_metrics(registry)

    async def intercept_unary_stream(self, continuation, client_call_details, request):
        grpc_service_name, grpc_method_name, _ = grpc_utils.split_method_call(client_call_details)
        grpc_type = grpc_utils.SERVER_STREAMING

        self._metrics["grpc_client_started_counter"].labels(
            grpc_type=grpc_type, grpc_service=grpc_service_name, grpc_method=grpc_method_name
        ).inc()

        start = default_timer()
        handler = await continuation(client_call_details, request)
        all_responses = []
        async for response in handler:
            self._metrics["grpc_client_stream_msg_received"].labels(
                grpc_type=grpc_type,
                grpc_service=grpc_service_name,
                grpc_method=grpc_method_name
            ).inc()
            all_responses.append(response)

        if self._legacy:
            self._metrics["legacy_grpc_client_completed_latency_seconds_histogram"].labels(
                grpc_type=grpc_type, grpc_service=grpc_service_name, grpc_method=grpc_method_name
            ).observe(max(default_timer() - start, 0))

        elif self._enable_client_handling_time_histogram:
            self._metrics["grpc_client_handled_histogram"].labels(
                grpc_type=grpc_type, grpc_service=grpc_service_name, grpc_method=grpc_method_name
            ).observe(max(default_timer() - start, 0))

        if self._enable_client_stream_receive_time_histogram and not self._legacy:
            self._metrics["grpc_client_stream_recv_histogram"].labels(
                grpc_type=grpc_type, grpc_service=grpc_service_name, grpc_method=grpc_method_name
            ).observe(max(default_timer() - start, 0))

        return build_generator(all_responses)


class PromAioStreamUnaryClientInterceptor(grpc.aio.StreamUnaryClientInterceptor):
    def __init__(
        self,
        enable_client_handling_time_histogram=False,
        enable_client_stream_receive_time_histogram=False,
        enable_client_stream_send_time_histogram=False,
        legacy=False,
        registry=REGISTRY,
    ):
        self._enable_client_handling_time_histogram = enable_client_handling_time_histogram
        self._enable_client_stream_receive_time_histogram = (
            enable_client_stream_receive_time_histogram
        )
        self._enable_client_stream_send_time_histogram = enable_client_stream_send_time_histogram
        self._legacy = legacy
        self._metrics = init_metrics(registry)

    async def intercept_stream_unary(self, continuation, client_call_details, request_generator):
        grpc_service_name, grpc_method_name, _ = grpc_utils.split_method_call(client_call_details)
        grpc_type = grpc_utils.CLIENT_STREAMING

        sent_messages_counter = self._metrics["grpc_client_stream_msg_sent"]

        request_generator = grpc_utils.wrap_iterator_inc_counter(
            request_generator, sent_messages_counter, grpc_type, grpc_service_name, grpc_method_name
        )

        start = default_timer()
        handler = await continuation(client_call_details, request_generator)
        await handler.code()

        if self._legacy:
            self._metrics["grpc_client_started_counter"].labels(
                grpc_type=grpc_type, grpc_service=grpc_service_name, grpc_method=grpc_method_name
            ).inc()
            self._metrics["legacy_grpc_client_completed_latency_seconds_histogram"].labels(
                grpc_type=grpc_type, grpc_service=grpc_service_name, grpc_method=grpc_method_name
            ).observe(max(default_timer() - start, 0))
        else:
            self._metrics["grpc_client_started_counter"].labels(
                grpc_type=grpc_type,
                grpc_service=grpc_service_name,
                grpc_method=grpc_method_name
            ).inc()
            if self._enable_client_handling_time_histogram:
                self._metrics["grpc_client_handled_histogram"].labels(
                    grpc_type=grpc_type,
                    grpc_service=grpc_service_name,
                    grpc_method=grpc_method_name,
                ).observe(max(default_timer() - start, 0))

        if self._enable_client_stream_send_time_histogram and not self._legacy:
            self._metrics["grpc_client_stream_send_histogram"].labels(
                grpc_type=grpc_type,
                grpc_service=grpc_service_name,
                grpc_method=grpc_method_name
            ).observe(max(default_timer() - start, 0))

        return handler


class PromAioStreamStreamClientInterceptor(grpc.aio.StreamStreamClientInterceptor):
    def __init__(
        self,
        enable_client_handling_time_histogram=False,
        enable_client_stream_receive_time_histogram=False,
        enable_client_stream_send_time_histogram=False,
        legacy=False,
        registry=REGISTRY,
    ):
        self._enable_client_handling_time_histogram = enable_client_handling_time_histogram
        self._enable_client_stream_receive_time_histogram = (
            enable_client_stream_receive_time_histogram
        )
        self._enable_client_stream_send_time_histogram = enable_client_stream_send_time_histogram
        self._legacy = legacy
        self._metrics = init_metrics(registry)

    async def intercept_stream_stream(self, continuation, client_call_details, request_generator):
        grpc_service_name, grpc_method_name, _ = grpc_utils.split_method_call(client_call_details)
        grpc_type = grpc_utils.BIDI_STREAMING
        start = default_timer()

        sent_messages_counter = self._metrics["grpc_client_stream_msg_sent"]
        received_messages_counter = self._metrics["grpc_client_stream_msg_received"]

        request_generator = grpc_utils.wrap_iterator_inc_counter(
            request_generator,
            sent_messages_counter,
            grpc_type,
            grpc_service_name,
            grpc_method_name,
        )
        handler = await continuation(client_call_details, request_generator)
        all_responses = []
        async for response in handler:
            received_messages_counter.labels(
                grpc_type=grpc_type,
                grpc_service=grpc_service_name,
                grpc_method=grpc_method_name
            ).inc()
            all_responses.append(response)

        if self._enable_client_stream_send_time_histogram and not self._legacy:
            self._metrics["grpc_client_stream_send_histogram"].labels(
                grpc_type=grpc_type, grpc_service=grpc_service_name, grpc_method=grpc_method_name
            ).observe(max(default_timer() - start, 0))

        if self._enable_client_stream_receive_time_histogram and not self._legacy:
            self._metrics["grpc_client_stream_recv_histogram"].labels(
                grpc_type=grpc_type, grpc_service=grpc_service_name, grpc_method=grpc_method_name
            ).observe(max(default_timer() - start, 0))

        return build_generator(all_responses)
