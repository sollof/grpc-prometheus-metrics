from unittest.mock import patch

import pytest
import grpc

from tests.grpc_prometheus_metrics.utils import get_server_metric
from tests.integration.hello_world import hello_world_pb2


@pytest.mark.parametrize("target_count", [1, 10, 100])
def test_grpc_server_handled_with_server_error(
    target_count, grpc_server, grpc_stub
):  # pylint: disable=unused-argument
    for _ in range(target_count):
        with pytest.raises(grpc.RpcError):
            grpc_stub.SayHello(hello_world_pb2.HelloRequest(name="unknownError"))

    target_metric = get_server_metric("grpc_server_handled")
    assert target_metric.samples == []


@pytest.mark.parametrize("target_count", [1, 10, 100])
def test_grpc_server_handled_with_rpc_error(
    target_count, grpc_server, grpc_stub
):  # pylint: disable=unused-argument
    for _ in range(target_count):
        with pytest.raises(grpc.RpcError):
            grpc_stub.SayHello(hello_world_pb2.HelloRequest(name="rpcError"))

    target_metric = get_server_metric("grpc_server_handled")
    assert target_metric.samples[0].value == target_count


@pytest.mark.parametrize("target_count", [1, 10, 100])
def test_grpc_server_handled_with_interceptor_error(
    target_count, grpc_server, grpc_stub
):  # pylint: disable=unused-argument
    for _ in range(target_count):
        with patch(
            'grpc_prometheus_metrics.prometheus_server_interceptor.'
            'PromServerInterceptor._compute_status_code',
            side_effect=Exception('mocked error'),
        ):
            with pytest.raises(grpc.RpcError):
                grpc_stub.SayHello(hello_world_pb2.HelloRequest(name="unary"))


@pytest.mark.parametrize("target_count", [1, 10, 100])
def test_grpc_server_handled_with_server_error_and_skip_exceptions(
    target_count, grpc_server_with_exception_handling, grpc_stub
):  # pylint: disable=unused-argument
    for _ in range(target_count):
        with pytest.raises(grpc.RpcError):
            grpc_stub.SayHello(hello_world_pb2.HelloRequest(name="unknownError"))

    target_metric = get_server_metric("grpc_server_handled")
    assert target_metric.samples == []


@pytest.mark.parametrize("target_count", [1, 10, 100])
def test_grpc_server_handled_with_interceptor_error_and_skip_exceptions(
    target_count, grpc_server_with_exception_handling, grpc_stub
):  # pylint: disable=unused-argument
    for _ in range(target_count):
        with patch(
            'grpc_prometheus_metrics.prometheus_server_interceptor.'
            'PromServerInterceptor._compute_status_code',
            side_effect=Exception('mocked error'),
        ):
            assert (
                grpc_stub.SayHello(hello_world_pb2.HelloRequest(name="unary")).message
                == "Hello, unary!"
            )

    target_metric = get_server_metric("grpc_server_handled")
    assert target_metric.samples == []


@pytest.mark.parametrize("target_count", [1, 10, 100])
def test_grpc_server_handled_before_request_error(
    target_count, grpc_server, grpc_stub
):  # pylint: disable=unused-argument
    for _ in range(target_count):
        with patch(
            'grpc_prometheus_metrics.grpc_utils.wrap_iterator_inc_counter',
            side_effect=Exception('mocked error'),
        ):
            assert (
                grpc_stub.SayHello(hello_world_pb2.HelloRequest(name="unary")).message
                == "Hello, unary!"
            )
