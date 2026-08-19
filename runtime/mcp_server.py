"""Identity-bound MCP Surface Runtime for local Free installs."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from ie.status_cmd import collect_status

from .apply import apply_from_dict
from .mass import build_public_card, compute_mass_readout
from .models import RequestStatus
from .request import list_inbound_requests
from .sqlite_store import SQLiteStore


class MCPBindingError(ValueError):
    """Raised when an MCP session cannot be bound to the local Identity."""


@dataclass(frozen=True)
class MCPIdentityBinding:
    """The one Identity and optional membrane context for an MCP process."""

    install_root: Path
    identity_id: str
    local_handle: str
    preferred_name: Optional[str]
    substrate: str
    space_id: Optional[str] = None

    @classmethod
    def from_install(
        cls,
        install_root: str | Path,
        *,
        identity_id: Optional[str] = None,
        space_id: Optional[str] = None,
    ) -> "MCPIdentityBinding":
        store = SQLiteStore(install_root)
        identity = store.identity()
        bound_identity_id = str(identity["identity_id"])
        if identity_id is not None and identity_id != bound_identity_id:
            raise MCPBindingError(
                f"identity binding mismatch: requested {identity_id!r}, "
                f"install is bound to {bound_identity_id!r}"
            )
        if space_id is not None:
            raise MCPBindingError(
                "space_id is not supported by local Free V1; refusing an "
                "unenforced membrane context"
            )
        return cls(
            install_root=store.root,
            identity_id=bound_identity_id,
            local_handle=str(identity["local_handle"]),
            preferred_name=identity["preferred_name"],
            substrate=str(identity["substrate"]),
        )

    def result(self, operation: str, value: Any) -> dict[str, Any]:
        return {
            "schema_version": "mcp-result-v0",
            "operation": operation,
            "actor_identity_id": self.identity_id,
            "identity_id": self.identity_id,
            "space_id": self.space_id,
            "result": value,
        }


def create_mcp_server(binding: MCPIdentityBinding):
    """Create an MCP server whose tools close over one validated Identity."""
    try:
        from mcp.server.mcpserver import MCPServer
    except ImportError as exc:
        raise MCPBindingError(
            "MCP support is optional; install ie-os[mcp] to run the MCP surface"
        ) from exc

    server = MCPServer(
        "ie-os-local-v0",
        version="0",
        description="Identity-bound local IE Surface Runtime",
        instructions=(
            "This server is bound to one local Identity. Tool results include "
            "actor_identity_id. Cross-Identity and Space writes are not implied."
        ),
    )

    @server.tool(
        name="get_status",
        description="Read status for the bound local Identity installation.",
        structured_output=True,
    )
    def get_status() -> dict[str, Any]:
        return binding.result("get_status", collect_status(binding.install_root))

    @server.tool(
        name="get_public_card",
        description="Read the public card for the bound Identity.",
        structured_output=True,
    )
    def get_public_card() -> dict[str, Any]:
        card = build_public_card(
            local_handle=binding.local_handle,
            registry_root=binding.install_root,
            preferred_name=binding.preferred_name,
            substrate=binding.substrate,
        )
        return binding.result("get_public_card", card)

    @server.tool(
        name="get_mass",
        description="Read the derived emergent self-Mass for the bound Identity.",
        structured_output=True,
    )
    def get_mass() -> dict[str, Any]:
        return binding.result("get_mass", compute_mass_readout(binding.install_root).to_dict())

    @server.tool(
        name="list_inbound_requests",
        description="List estimate requests addressed to the bound Identity.",
        structured_output=True,
    )
    def list_requests(status: Optional[str] = None) -> dict[str, Any]:
        request_status = RequestStatus(status) if status else None
        requests = list_inbound_requests(
            binding.install_root,
            status=request_status,
        )
        return binding.result(
            "list_inbound_requests",
            {"requests": [request.to_dict() for request in requests]},
        )

    @server.tool(
        name="receive_interaction_signal",
        description="Apply an Interaction Signal to the bound Identity.",
        structured_output=True,
    )
    def receive_interaction_signal(payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise MCPBindingError("payload must be an object")
        signal_payload = dict(payload)
        signal_payload["transport"] = "mcp"
        receipt = apply_from_dict(
            signal_payload,
            registry_root=binding.install_root,
            expected_to_handle=binding.local_handle,
            observer_handle=binding.local_handle,
        )
        return binding.result("receive_interaction_signal", receipt.to_dict())

    return server


def serve(
    install_root: str | Path,
    *,
    identity_id: Optional[str] = None,
    space_id: Optional[str] = None,
    transport: str = "stdio",
    host: str = "127.0.0.1",
    port: int = 8788,
    path: str = "/mcp",
) -> None:
    binding = MCPIdentityBinding.from_install(
        install_root,
        identity_id=identity_id,
        space_id=space_id,
    )
    server = create_mcp_server(binding)
    if transport == "stdio":
        server.run("stdio")
        return
    if transport == "streamable-http":
        server.run(
            "streamable-http",
            host=host,
            port=port,
            streamable_http_path=path,
        )
        return
    raise MCPBindingError(f"unsupported MCP transport: {transport}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="IE OS local MCP surface")
    parser.add_argument("--install", required=True, help="Path to the IE install root")
    parser.add_argument("--identity-id", help="Expected bound identity_id")
    parser.add_argument(
        "--space-id",
        help="Reserved membrane context; rejected by local Free V1",
    )
    parser.add_argument(
        "--transport",
        choices=("stdio", "streamable-http"),
        default="stdio",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8788)
    parser.add_argument("--path", default="/mcp")
    args = parser.parse_args(argv)
    serve(
        args.install,
        identity_id=args.identity_id,
        space_id=args.space_id,
        transport=args.transport,
        host=args.host,
        port=args.port,
        path=args.path,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())