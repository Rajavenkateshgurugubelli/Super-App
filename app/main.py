import logging
import grpc
from concurrent import futures
import sys
import os

# Add app directory AND parent directory to sys.path
# Parent dir: needed for 'from app import ...'
# Current dir: needed for 'import user_pb2' inside generated code
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
sys.path.append(os.path.dirname(current_dir))

# Generated code imports
from app import user_pb2_grpc, wallet_pb2_grpc, policy_pb2_grpc

# Service implementations
from app.services import user_service, wallet_service, policy_service
from app.middleware import interceptors

# OpenTelemetry Imports
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.grpc import GrpcInstrumentorServer
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

def serve():
    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)

    # Setup Tracing
    try:
        resource = Resource.create(attributes={"service.name": os.environ.get("OTEL_SERVICE_NAME", "superapp-backend")})
        trace.set_tracer_provider(TracerProvider(resource=resource))
        otlp_exporter = OTLPSpanExporter(endpoint=os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://jaeger:4317"), insecure=True)
        trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(otlp_exporter))

        # Instrument gRPC Server
        GrpcInstrumentorServer().instrument()
        
        # Instrument SQLAlchemy (for DB query tracing)
        SQLAlchemyInstrumentor().instrument()
    except Exception as e:
        logger.error(f"Failed to initialize OpenTelemetry: {e}")

    # Initialize gRPC server with interceptors
    # We will enable interceptors later after verifying basic connectivity
    # interceptors_list = [interceptors.GeoFencingInterceptor()]
    # server = grpc.server(futures.ThreadPoolExecutor(max_workers=10), interceptors=interceptors_list)
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    # Register services
    user_pb2_grpc.add_UserServiceServicer_to_server(user_service.UserService(), server)
    wallet_pb2_grpc.add_WalletServiceServicer_to_server(wallet_service.WalletService(), server)
    policy_pb2_grpc.add_PolicyServiceServicer_to_server(policy_service.PolicyService(), server)

    # Enable Reflection (optional, for debugging with grpcurl)
    # from grpc_reflection.v1alpha import reflection
    # SERVICE_NAMES = (
    #     user_pb2.DESCRIPTOR.services_by_name['UserService'].full_name,
    #     wallet_pb2.DESCRIPTOR.services_by_name['WalletService'].full_name,
    #     policy_pb2.DESCRIPTOR.services_by_name['PolicyService'].full_name,
    #     reflection.SERVICE_NAME,
    # )
    # reflection.enable_server_reflection(SERVICE_NAMES, server)

    # Bind to port
    port = '[::]:50051'
    server.add_insecure_port(port)
    logger.info(f"Server starting on {port}")
    server.start()
    server.wait_for_termination()

if __name__ == '__main__':
    serve()
