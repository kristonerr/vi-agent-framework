import json
import logging
import subprocess
import threading
from pathlib import Path

MCP_SERVERS_KEY = "mcp_servers"


def _read_json():
    config_path = Path(__file__).parent.parent / "config.json"
    try:
        return json.loads(config_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_json(data: dict):
    config_path = Path(__file__).parent.parent / "config.json"
    config_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


class MCPServer:
    def __init__(self, name: str, command: str, args: list[str] | None = None, env: dict | None = None):
        self.name = name
        self.command = command
        self.args = args or []
        self.env = {**{k: v for k, v in (env or {}).items()}, "MCP_ENABLED": "1"}
        self._process: subprocess.Popen | None = None
        self._tools: list[dict] = []
        self._lock = threading.Lock()

    def start(self) -> bool:
        try:
            self._process = subprocess.Popen(
                [self.command, *self.args],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=None,
            )
            resp = self._rpc_call("initialize", {"protocolVersion": "2024-11-05"})
            if resp and resp.get("result"):
                tool_resp = self._rpc_call("tools/list", {})
                if tool_resp and "result" in tool_resp:
                    self._tools = tool_resp["result"].get("tools", [])
                    logging.info(f"MCP [{self.name}]: {len(self._tools)} tools loaded")
                    return True
            return False
        except Exception as e:
            logging.warning(f"MCP [{self.name}] failed: {e}")
            self._cleanup()
            return False

    def call_tool(self, tool_name: str, arguments: dict) -> dict:
        resp = self._rpc_call("tools/call", {"name": tool_name, "arguments": arguments})
        if resp and "result" in resp:
            return resp["result"]
        return {"error": resp}

    def list_tools(self) -> list[dict]:
        return self._tools

    def _rpc_call(self, method: str, params: dict) -> dict | None:
        if not self._process or not self._process.stdin:
            return None
        req = {"jsonrpc": "2.0", "id": id(method), "method": method, "params": params}
        with self._lock:
            try:
                self._process.stdin.write(json.dumps(req) + "\n")
                self._process.stdin.flush()
                line = self._process.stdout.readline() if self._process.stdout else ""
                if line:
                    return json.loads(line.strip())
            except Exception as e:
                logging.warning(f"MCP RPC error [{self.name}]: {e}")
        return None

    def _cleanup(self):
        if self._process:
            try:
                self._process.terminate()
            except Exception:
                pass
        self._process = None
        self._tools = []

    def stop(self):
        self._cleanup()


class MCPClient:
    def __init__(self):
        self.servers: dict[str, MCPServer] = {}

    def start_all(self):
        config = _read_json()
        servers_cfg = config.get(MCP_SERVERS_KEY, [])
        for cfg in servers_cfg:
            name = cfg.get("name", "mcp")
            server = MCPServer(
                name=name,
                command=cfg["command"],
                args=cfg.get("args", []),
                env=cfg.get("env", {}),
            )
            if server.start():
                self.servers[name] = server

    def load_tools_into_registry(self):
        from .tools import registry

        for name, server in self.servers.items():
            for tool in server.list_tools():
                tool_name = tool["name"]
                description = tool.get("description", "")

                def make_handler(server=server, tname=tool_name):
                    def handler(args: dict) -> dict:
                        return server.call_tool(tname, args)

                    handler.__name__ = f"mcp_{name}_{tool_name}"
                    handler.__doc__ = description
                    return handler

                registry.register(f"mcp_{tool_name}", make_handler())

    def stop_all(self):
        for server in self.servers.values():
            server.stop()
        self.servers.clear()

    def list_enabled(self) -> list[str]:
        return list(self.servers.keys())


def register_mcp_servers():
    client = MCPClient()
    client.start_all()
    client.load_tools_into_registry()
    return client
