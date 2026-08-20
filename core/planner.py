"""
[V12.0] J.A.R.V.I.S. Runtime Adaptive Planner
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Not static plan-at-start. Real adaptive planner:
- Runtime replanning when steps fail
- Dynamic node injection based on intermediate results
- Opportunistic execution (skip unnecessary steps)
- Plan repair without full replan
"""
import logging, json, re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from core.execution_graph import ExecutionGraph, NodeType, NodeStatus

logger = logging.getLogger("JARVIS.Planner")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  LEGACY PLAN STRUCTURES (PlanExecutor compatibility)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class PlanNode:
    step_number: int; protocol_tag: str; argument: str = ""
    sub_nodes: List["PlanNode"] = field(default_factory=list); label: str = ""

@dataclass
class ExecutionPlan:
    steps: List[PlanNode] = field(default_factory=list); original_request: str = ""
    @property
    def total_steps(self) -> int: return len(self.steps)
    def get_context_summary(self) -> str:
        if not self.steps: return "Empty plan."
        return f"Plan: {' → '.join(s.protocol_tag for s in self.steps)} ({self.total_steps} step)"

ALIAS_MAP = {
    "SEARCH": "WEB_SEARCH", "GOOGLE": "GOOGLE_SEARCH", "YOUTUBE": "YT_SEARCH",
    "YOUTUBE_SEARCH": "YT_SEARCH", "YOUTUBE_PLAY": "YT_PLAY", "OPEN": "WEB_OPEN",
    "KILL": "APP_KILL", "WHATSAPP": "WHATSAPP_MESSAGE", "WA_MESSAGE": "WHATSAPP_MESSAGE",
    "SHUTDOWN": "SYSTEM_SHUTDOWN", "POWER": "SYSTEM_POWER",
    "REMEMBER_THIS": "REMEMBER", "SAVE_MEMORY": "REMEMBER",
    "MAP": "MAP_SHOW", "CHART": "CHART_SHOW", "GRAPH": "CHART_SHOW",
    # LLM sometimes names the plan step after the post-tool signal.
    # VISION_INTERPRET is a next_action, not a protocol — fold it into VISION.
    "VISION_INTERPRET": "VISION",
}

def _apply_filters(tag: str, arg: str) -> tuple:
    tag = tag.strip().upper(); arg = arg.strip()
    tag = ALIAS_MAP.get(tag, tag)
    return tag, arg

PLAN_BLOCK_RE = re.compile(r'\[PLAN\](.*?)\[/PLAN\]', re.DOTALL | re.IGNORECASE)
PLAN_MARKER_RE = re.compile(r'\[/?PLAN\]', re.IGNORECASE)

def contains_plan_block(response: str) -> bool:
    """True if the text carries plan markup, whether or not it parses.

    Used to keep plan syntax out of speech: an unclosed or unknown-tag
    [PLAN] block is machine output, not an answer for the user."""
    if not response: return False
    return PLAN_MARKER_RE.search(response) is not None

def parse_plan(response: str) -> Optional[ExecutionPlan]:
    """Parses [PLAN]...[/PLAN] block from LLM response."""
    match = PLAN_BLOCK_RE.search(response)
    if not match: return None
    body = match.group(1).strip()
    if not body: return None
    steps = []; num = 0
    
    # Known protocol tags — tags not in this list are NOT considered steps
    KNOWN_TAGS = {
        "SPEAK", "FILE_WRITE", "FILE_READ", "FILE_CREATE", "FILE_DELETE", "FILE_LATEST",
        "APP_OPEN", "APP_KILL", "FOLDER_OPEN", "WEB_SEARCH", "WEB_OPEN",
        "GOOGLE_SEARCH", "YT_SEARCH", "YT_PLAY", "WHATSAPP_MESSAGE",
        "PYTHON_EXEC", "VISION", "REMEMBER", "CHART_SHOW", "MAP_SHOW",
        "GOOGLE_TRENDS", "SYSTEM_SHUTDOWN", "SYSTEM_POWER", "YOUTUBE_STRATEGY",
        "ANALIZ_PRO", "LLM_EVAL",
        # Alias'lar
        "SEARCH", "GOOGLE", "YOUTUBE", "YOUTUBE_SEARCH", "YOUTUBE_PLAY",
        "OPEN", "KILL", "WHATSAPP", "WA_MESSAGE", "SHUTDOWN", "POWER",
        "REMEMBER_THIS", "SAVE_MEMORY", "MAP", "CHART", "GRAPH",
        "VISION_INTERPRET",
    }

    for line in body.split('\n'):
        line = line.strip()
        if not line: continue
        line = re.sub(r'^[\d]+[\.\)\-:]\s*', '', line).strip()
        if not line: continue
        proto = re.match(r'\[PROTOCOL:\s*(\w+)\]\s*(.*)', line, re.IGNORECASE)
        if proto:
            tag, arg = proto.group(1), proto.group(2).strip()
        else:
            parts = line.split(None, 1)
            if not parts: continue
            tag = parts[0]; arg = parts[1] if len(parts) > 1 else ""
        
        tag_upper = tag.strip().upper()
        tag_upper = ALIAS_MAP.get(tag_upper, tag_upper)
        
        # If it is not a known tag → add it as an argument to the previous step (line of code etc.)
        if tag_upper not in KNOWN_TAGS:
            if steps:
                # Add the line to the argument of the previous step (FILE_WRITE multi-line code case)
                steps[-1].argument += "\n" + line
            # ADD unknown tag as a step
            continue
        
        tag, arg = _apply_filters(tag, arg)
        num += 1; steps.append(PlanNode(step_number=num, protocol_tag=tag, argument=arg))
    if not steps: return None
    _prefer_web_search_when_eval_follows(steps)
    plan = ExecutionPlan(steps=steps)
    logger.info(f"Plan parsed: {plan.get_context_summary()}")
    return plan


def _prefer_web_search_when_eval_follows(steps: list) -> None:
    """GOOGLE_SEARCH opens a tab and returns no page text.

    A later LLM_EVAL / WHATSAPP_MESSAGE needs that text. Rewrite the
    gather step to WEB_SEARCH so the eval tool is not fed {}."""
    tags = {s.protocol_tag.upper() for s in steps}
    if "LLM_EVAL" not in tags and "WHATSAPP_MESSAGE" not in tags:
        return
    for s in steps:
        if s.protocol_tag.upper() == "GOOGLE_SEARCH":
            s.protocol_tag = "WEB_SEARCH"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  COGNITIVE PLANNER ENGINE (V12 Adaptive)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class PlannerEngine:
    """
    [V12.0] Adaptive Cognitive Planner
    Creates DAG plans and repairs them at runtime.
    """
    def __init__(self, brain):
        self.brain = brain
        self._replan_count = 0
        self._max_replans = 3

    async def create_plan(self, user_input: str, world_state: Dict[str, Any]) -> ExecutionGraph:
        """Decomposes goal into ExecutionGraph via LLM."""
        logger.info(f"Planning: {user_input[:60]}")
        prompt = self._build_prompt(user_input, world_state)
        try:
            response = await self.brain.think(prompt)
            match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
            if not match: match = re.search(r'(\{.*\})', response, re.DOTALL)
            if match:
                data = json.loads(match.group(1))
                return self._build_graph(user_input, data)
        except Exception as e:
            logger.error(f"Planning failed: {e}")
        return self._fallback_graph(user_input)

    async def repair_plan(self, graph: ExecutionGraph, failed_node_id: str,
                          error: str, world_state: Dict[str, Any]) -> bool:
        """
        Runtime plan repair — tries to fix a failed node without full replan.
        Returns True if repair succeeded (new nodes injected).
        """
        if self._replan_count >= self._max_replans:
            logger.warning("Max replans reached, cannot repair further.")
            return False

        self._replan_count += 1
        failed = graph.nodes.get(failed_node_id)
        if not failed: return False

        logger.info(f"PLAN REPAIR: {failed_node_id} failed with: {error[:80]}")

        # Strategy 1: Simple retry with modified params
        if failed.retry_count < failed.max_retries:
            return False  # Let normal retry handle it

        # Strategy 2: Try alternate tool
        alternates = self._get_alternate_tools(failed.action)
        if alternates:
            alt_tool = alternates[0]
            new_id = await graph.inject_node(
                NodeType.TOOL_CALL, alt_tool,
                params=failed.params.copy(), after_node_id=None)
            # Rewire dependents of failed node to new node
            for n in graph.nodes.values():
                if failed_node_id in n.dependencies and n.status == NodeStatus.PENDING:
                    await graph.rewire_dependency(n.id, failed_node_id, new_id)
            logger.info(f"REPAIR: Replaced {failed.action} with {alt_tool}")
            return True

        # [DEMO MODE] APP_OPEN Reflection
        if failed.action == "APP_OPEN":
            app_name = failed.params.get("app_name", "").lower()
            aliases = []
            if "hesap" in app_name or "calc" in app_name:
                aliases = ["calculator", "calc.exe", "Windows Calculator"]
            elif "not defteri" in app_name or "notepad" in app_name:
                aliases = ["notepad", "notepad.exe", "Windows Notepad"]
            elif "whatsapp" in app_name:
                aliases = ["whatsapp", "WhatsApp Desktop"]

            aliases = [a for a in aliases if a.lower() != app_name]
            
            # Use the attempt count based on replan_count to pick an alias
            # Ensure we try at least 3 alternatives before giving up
            idx = self._replan_count - 1
            if idx < len(aliases):
                alt_app = aliases[idx]
                new_params = failed.params.copy()
                new_params["app_name"] = alt_app
                
                # Highlight in DEMO MODE
                if getattr(self.brain.config, "demo_mode", False):
                    print(f"\n[🚀 DEMO MODE: REFLECTION] APP_OPEN başarısız oldu: '{app_name}'. Alternatif deneniyor: '{alt_app}'...")
                    
                new_id = await graph.inject_node(
                    NodeType.TOOL_CALL, "APP_OPEN",
                    params=new_params, after_node_id=None)
                for n in graph.nodes.values():
                    if failed_node_id in n.dependencies and n.status == NodeStatus.PENDING:
                        await graph.rewire_dependency(n.id, failed_node_id, new_id)
                logger.info(f"REPAIR: Retrying APP_OPEN with alias '{alt_app}'")
                return True

        # Strategy 3: Skip and inject reasoning node to explain
        await graph.skip_node(failed_node_id, f"Repair failed: {error[:50]}")
        await graph.inject_node(
            NodeType.REASONING, "EXPLAIN_FAILURE",
            params={"original_action": failed.action, "error": error[:200]})
        return True

    async def replan_from_scratch(self, original_goal: str,
                                   completed_nodes: List[Dict],
                                   world_state: Dict[str, Any]) -> ExecutionGraph:
        """Full replan using context of what already succeeded."""
        logger.info(f"FULL REPLAN for: {original_goal[:60]}")
        self._replan_count += 1

        context = {"completed_steps": [n["action"] for n in completed_nodes],
                    "world_state": world_state}
        prompt = f"""[ORIGINAL GOAL]: {original_goal}
[ALREADY COMPLETED]: {json.dumps(context['completed_steps'])}
[CURRENT STATE]: {json.dumps(world_state)}

Create NEW plan for remaining steps (DO NOT REPEAT completed steps).
Return JSON ONLY: {{"nodes": [{{"id": "s1", "type": "tool_call", "action": "TOOL_TAG", "params": {{}}, "deps": []}}]}}"""

        try:
            response = await self.brain.think(prompt)
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                data = json.loads(match.group(1))
                return self._build_graph(original_goal, data)
        except Exception as e:
            logger.error(f"Replan failed: {e}")
        return self._fallback_graph(original_goal)

    def _get_alternate_tools(self, tool_tag: str) -> List[str]:
        alts = {
            "GOOGLE_SEARCH": ["WEB_SEARCH", "WEB_OPEN"],
            "WEB_SEARCH": ["GOOGLE_SEARCH"],
            "APP_OPEN": ["WEB_OPEN"],
            "YT_PLAY": ["YT_SEARCH", "WEB_OPEN"],
        }
        return alts.get(tool_tag, [])

    def _build_prompt(self, goal: str, state: Dict[str, Any]) -> str:
        return f"""[GOAL]: {goal}
[STATE]: {json.dumps(state)}
Create DAG plan for the task. Let each step be small and verifiable.
CRITICAL RULE: If the goal contains multiple distinct actions separated by commas, 've', 'ardından', or 'sonra' (e.g. 'Hesap makinesini aç, 2026 ile 15'i çarp, sonucu söyle' or 'Google'dan dolar kurunu öğren, masaüstüne kaydet, not defterinde aç'), YOU MUST break it down into multiple separate, sequential 'tool_call' nodes (e.g. APP_OPEN -> CALCULATE -> SPEAK_RESULT). DO NOT combine multiple actions into a single node.
Node types: tool_call, reasoning, memory_retrieval, validation, reflection
JSON ONLY: {{"reasoning_trace": "...", "nodes": [{{"id": "s1", "type": "tool_call", "action": "TOOL", "params": {{}}, "deps": [], "max_retries": 3}}]}}"""

    def _build_graph(self, goal: str, data: Dict[str, Any]) -> ExecutionGraph:
        graph = ExecutionGraph(task_id=f"plan_{goal[:8]}")
        id_map = {}
        for nd in data.get("nodes", []):
            try:
                nt = NodeType(nd.get("type", "tool_call"))
            except ValueError:
                nt = NodeType.TOOL_CALL
            nid = graph.add_node(nt, nd.get("action", "AUTO"),
                                  nd.get("params", {}),
                                  [id_map[d] for d in nd.get("deps", []) if d in id_map])
            id_map[nd.get("id", nid)] = nid
            graph.nodes[nid].max_retries = nd.get("max_retries", 3)
        logger.info(f"Graph built: {len(graph.nodes)} nodes. Trace: {data.get('reasoning_trace','')[:80]}")
        return graph

    def _fallback_graph(self, goal: str) -> ExecutionGraph:
        graph = ExecutionGraph(task_id=f"fb_{goal[:8]}")
        graph.add_node(NodeType.TOOL_CALL, "AUTO_DETECT", {"input": goal})
        return graph
