import sys
import io
import traceback
import logging
from tools.base_tool import BaseTool, ToolResult

logger = logging.getLogger("JARVIS.PythonTool")

def _blocked_input(prompt=""):
    """input() forbidden: J.A.R.V.I.S. Input cannot be received from the user in the environment."""
    raise NotImplementedError(
        "[SANDBOX RESTRICTION] `input()` cannot be used in this environment."
        "Instead of taking input from the user, it uses tools such as mathematical operations."
        "Write it in a way that directly calculates the result and returns it with `print()`."
        "Example: print(sum(5, 3)) → print(8)"
    )

class PythonExecutionTool(BaseTool):
    name = "python_execution"
    description = "Python runs the code and returns terminal output (print). Use ONLY when math, data analysis, text processing, or complex calculations are required. DO NOT USE for normal chats."
    protocol_tag = "PYTHON_EXEC"
    domain = "system"
    latency_ms = 1000
    reliability_score = 0.95
    parameters = {"code": {"type": "string", "description": "Pure Python code to run (without Markdown or ```). input() CANNOT be used, values ​​must be constants."}}

    async def execute(self, params: dict, engine_context: dict = None) -> ToolResult:
        code = params.get("code", "")
        if not code:
            return ToolResult(success=False, verified=False, error="NoCode", message="Couldn't find code to run.")

        # LLM can sometimes put code between ```python...`` tags, clean them up
        code = code.replace("```python", "").replace("```", "").strip()
        
        # LLM bazen [PROTOCOL: PYTHON_EXEC] veya [: PYTHON_EXEC] etiketlerini
        # embeds inside code block — clear them
        import re
        # Delete leading protocol tags or any line
        code = re.sub(r'\[/?[A-Z_ :]+PYTHON_EXEC[^\]]*\]', '', code)
        # Genel protokol etiketlerini temizle: [PROTOCOL: ...] veya [/PROTOCOL: ...]
        code = re.sub(r'\[/?PROTOCOL[^\]]*\]', '', code)
        # Discard empty lines and recombine
        code = "\n".join(line for line in code.splitlines() if line.strip()).strip()

        step_data = engine_context.get("step_results", {}) if engine_context else {}

        def _run_code_in_thread():
            """[V16.7] exec() ayrı thread'de çalışır — event loop kilidi önlenir.
            Böylece executor.py'deki asyncio.wait_for(60s) timeout devreye girebilir."""
            old_stdout = sys.stdout
            redirected_output = io.StringIO()
            sys.stdout = redirected_output
            try:
                exec_globals = {
                    "step_results": step_data,
                    "input": _blocked_input,
                    "__builtins__": __builtins__,
                }
                exec(code, exec_globals)
                return ("ok", redirected_output.getvalue().strip())
            except NotImplementedError as e:
                return ("sandbox", str(e))
            except Exception as e:
                return ("error", str(e), traceback.format_exc())
            finally:
                # stdout'u her halükarda geri yükle
                sys.stdout = old_stdout

        try:
            import asyncio
            loop = asyncio.get_running_loop()
            result_tuple = await loop.run_in_executor(None, _run_code_in_thread)
        except Exception as e:
            logger.error(f"[PythonExec] Thread execution error: {e}")
            return ToolResult(
                success=False, verified=False, error="ThreadError",
                message=f"Code execution thread failed: {str(e)}",
                speak="Sir, there was an error running the code."
            )

        # Thread sonuçlarını işle
        status = result_tuple[0]

        if status == "ok":
            output = result_tuple[1]
            if not output:
                output = "The code ran successfully but did not print anything to the screen."
            return ToolResult(
                success=True, verified=True,
                message=f"Code Output:\n{output}",
                speak="The code has been run, I am interpreting the result, Sir...",
                data={"output": output},
                next_action="PYTHON_INTERPRET"
            )
        elif status == "sandbox":
            error_msg = result_tuple[1]
            logger.warning(f"[PythonExec] Sandbox violation (input() call): {error_msg}")
            return ToolResult(
                success=False, verified=False, error="SandboxError",
                message=f"ERROR: {error_msg}\n\nSolution: Regenerate the code without input(), by writing the values directly.",
                speak="Sir, I used input() in the code I wrote. It is prohibited in this environment. I'm fixing the code."
            )
        else:  # "error"
            error_str = result_tuple[1]
            error_tb = result_tuple[2]
            logger.error(f"[PythonExec] Code Error:\n{error_tb}")
            return ToolResult(
                success=False, verified=False, error="ExecError",
                message=f"There was an error in the code you wrote:\n{error_str}\n\nExact error:\n{error_tb}",
                speak="Sir, there was an error in the code I wrote."
            )

