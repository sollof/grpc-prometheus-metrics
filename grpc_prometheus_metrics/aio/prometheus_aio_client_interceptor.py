"""Interceptor a client call with prometheus"""

from timeit import default_timer

import grpc
from prometheus_client.registry import REGISTRY

from grpc_prometheus_metrics import grpc_utils
from grpc_prometheus_metrics.client_metrics import init_metrics


class PromAioUnaryUnaryClientInterceptor(grpc.aio.UnaryUnaryClientInterceptor):
    """
    Intercept gRPC client requests.
    """

    def __init__(
        self,
        enable_client_handling_time_histogram=False,
        legacy=False,
        registry=REGISTRY,
    ):
        self._enable_client_handling_time_histogram = enable_client_handling_time_histogram
        self._legacy = legacy
        self._metrics = init_metrics(registry)

    async def intercept_unary_unary(self, continuation, client_call_details, request):
        grpc_service_name, grpc_method_name, _ = grpc_utils.split_method_call(client_call_details)
        grpc_type = grpc_utils.UNARY

        self._metrics["grpc_client_started_counter"].labels(
            grpc_type=grpc_type, grpc_service=grpc_service_name, grpc_method=grpc_method_name
        ).inc()

        start = default_timer()
        try:
            handler = await continuation(client_call_details, request)
            code = await handler.code()
        except grpc.aio.AioRpcError as exc:
            code = exc.code()
            raise exc
        finally:
            if self._legacy:
                self._metrics["legacy_grpc_client_completed_latency_seconds_histogram"].labels(
                    grpc_type=grpc_type,
                    grpc_service=grpc_service_name,
                    grpc_method=grpc_method_name,
                ).observe(max(default_timer() - start, 0))
            elif self._enable_client_handling_time_histogram:
                self._metrics["grpc_client_handled_histogram"].labels(
                    grpc_type=grpc_type,
                    grpc_service=grpc_service_name,
                    grpc_method=grpc_method_name,
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
