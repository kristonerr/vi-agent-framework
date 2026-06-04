import shlex
import subprocess
from .registry import register, is_command_allowed


def run_command_tool(args: dict) -> dict:
    command = args.get("command", "")
    if not command:
        return {"success": False, "error": "command is required"}
    if not is_command_allowed(command):
        return {"success": False, "error": f"command '{command.split()[0]}' not in allowlist"}
    try:
        cmd_list = shlex.split(command)
        result = subprocess.run(
            cmd_list,
            shell=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return {
            "success": True,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "command timed out"}
    except Exception as e:
        return {"success": False, "error": str(e)}


register("run_command", run_command_tool)
