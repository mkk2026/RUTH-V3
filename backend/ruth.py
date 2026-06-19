import asyncio
import base64
import io
import os
import sys
import traceback
from dotenv import load_dotenv
import cv2
import pyaudio
import PIL.Image
import mss
import argparse
import math
import struct
import time

from google import genai
from google.genai import types

if sys.version_info < (3, 11, 0):
    import taskgroup, exceptiongroup
    asyncio.TaskGroup = taskgroup.TaskGroup
    asyncio.ExceptionGroup = exceptiongroup.ExceptionGroup

from tools import tools_list

FORMAT = pyaudio.paInt16
CHANNELS = 1
SEND_SAMPLE_RATE = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE = 1024

MODEL = "models/gemini-2.5-flash-native-audio-preview-12-2025"
DEFAULT_MODE = "camera"

load_dotenv()

_GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if _GEMINI_API_KEY:
    client = genai.Client(http_options={"api_version": "v1beta"}, api_key=_GEMINI_API_KEY)
else:
    print("[RUTH] WARNING: GEMINI_API_KEY not set. Voice features will not work.")
    print("[RUTH] Create a .env file in the backend/ directory with: GEMINI_API_KEY=your_key_here")
    client = None

# Function definitions
generate_cad = {
    "name": "generate_cad",
    "description": "Generates a 3D CAD model based on a prompt.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "prompt": {"type": "STRING", "description": "The description of the object to generate."}
        },
        "required": ["prompt"]
    },
    "behavior": "NON_BLOCKING"
}

run_web_agent = {
    "name": "run_web_agent",
    "description": "Opens a web browser and performs a task according to the prompt.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "prompt": {"type": "STRING", "description": "The detailed instructions for the web browser agent."}
        },
        "required": ["prompt"]
    },
    "behavior": "NON_BLOCKING"
}

create_project_tool = {
    "name": "create_project",
    "description": "Creates a new project folder to organize files.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "name": {"type": "STRING", "description": "The name of the new project."}
        },
        "required": ["name"]
    }
}

switch_project_tool = {
    "name": "switch_project",
    "description": "Switches the current active project context.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "name": {"type": "STRING", "description": "The name of the project to switch to."}
        },
        "required": ["name"]
    }
}

list_projects_tool = {
    "name": "list_projects",
    "description": "Lists all available projects.",
    "parameters": {
        "type": "OBJECT",
        "properties": {},
    }
}

list_smart_devices_tool = {
    "name": "list_smart_devices",
    "description": "Lists all available smart home devices (lights, plugs, etc.) on the network.",
    "parameters": {
        "type": "OBJECT",
        "properties": {},
    }
}

control_light_tool = {
    "name": "control_light",
    "description": "Controls a smart light device.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "target": {
                "type": "STRING",
                "description": "The IP address of the device to control. Always prefer the IP address over the alias for reliability."
            },
            "action": {
                "type": "STRING",
                "description": "The action to perform: 'turn_on', 'turn_off', or 'set'."
            },
            "brightness": {
                "type": "INTEGER",
                "description": "Optional brightness level (0-100)."
            },
            "color": {
                "type": "STRING",
                "description": "Optional color name (e.g., 'red', 'cool white') or 'warm'."
            }
        },
        "required": ["target", "action"]
    }
}

discover_printers_tool = {
    "name": "discover_printers",
    "description": "Discovers 3D printers available on the local network.",
    "parameters": {
        "type": "OBJECT",
        "properties": {},
    }
}

print_stl_tool = {
    "name": "print_stl",
    "description": "Prints an STL file to a 3D printer. Handles slicing the STL to G-code and uploading to the printer.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "stl_path": {"type": "STRING", "description": "Path to STL file, or 'current' for the most recent CAD model."},
            "printer": {"type": "STRING", "description": "Printer name or IP address."},
            "profile": {"type": "STRING", "description": "Optional slicer profile name."}
        },
        "required": ["stl_path", "printer"]
    }
}

get_print_status_tool = {
    "name": "get_print_status",
    "description": "Gets the current status of a 3D printer including progress, time remaining, and temperatures.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "printer": {"type": "STRING", "description": "Printer name or IP address."}
        },
        "required": ["printer"]
    }
}

iterate_cad_tool = {
    "name": "iterate_cad",
    "description": "Modifies or iterates on the current CAD design based on user feedback. Use this when the user asks to adjust, change, modify, or iterate on the existing 3D model (e.g., 'make it taller', 'add a handle', 'reduce the thickness').",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "prompt": {"type": "STRING", "description": "The changes or modifications to apply to the current design."}
        },
        "required": ["prompt"]
    },
    "behavior": "NON_BLOCKING"
}

tools = [{'google_search': {}}, {"function_declarations": [generate_cad, run_web_agent, create_project_tool, switch_project_tool, list_projects_tool, list_smart_devices_tool, control_light_tool, discover_printers_tool, print_stl_tool, get_print_status_tool, iterate_cad_tool] + tools_list[0]['function_declarations'][1:]}]

ALL_TOOL_NAMES = [
    "generate_cad", "run_web_agent", "write_file", "read_directory", "read_file",
    "create_project", "switch_project", "list_projects",
    "list_smart_devices", "control_light",
    "discover_printers", "print_stl", "get_print_status", "iterate_cad",
    "execute_command", "execute_code", "system_info",
    "recall_memory", "store_memory",
    "read_document", "study_document", "search_web",
    "schedule_task", "add_monitor", "create_alert",
    "shodan_search", "shodan_host", "nmap_scan", "port_scan",
    "mcp_connect", "mcp_list_tools", "mcp_execute",
    "send_message", "list_platforms",
    "plan_and_execute",
]

# --- CONFIG UPDATE: Enabled Transcription ---
config = types.LiveConnectConfig(
    response_modalities=["AUDIO"],
    # We switch these from [] to {} to enable them with default settings
    output_audio_transcription={}, 
    input_audio_transcription={},
    system_instruction=(
        "You are R.U.T.H. -- Real-time Unified Technology Hub -- an advanced autonomous AI assistant "
        "created by Austin, whom you address as 'Sir'. You are warm, confident, resourceful, "
        "technically precise, and proactively helpful. Think of yourself as Jarvis -- you have "
        "real control over Sir's system and you use it.\n\n"

        "SYSTEM CONTROL (you have real access to Sir's computer):\n"
        "- execute_command: Run ANY shell command on the system. System upgrades, package installs, "
        "git operations, network scans, service management, file operations -- anything the terminal can do. "
        "Example: 'sudo apt update && sudo apt upgrade -y', 'nmap -sV 192.168.1.0/24', 'systemctl status nginx'.\n"
        "- execute_code: Run Python or shell scripts in a sandboxed environment with timeout protection. "
        "Use for data processing, calculations, API calls, automation scripts.\n"
        "- system_info: Get OS, CPU, memory, disk, and process information about the current system.\n\n"

        "3D DESIGN AND FABRICATION:\n"
        "- generate_cad: Generate 3D CAD models from text descriptions using build123d. Outputs STL files.\n"
        "- iterate_cad: Modify and iterate on existing CAD designs.\n"
        "- discover_printers: Find networked 3D printers (Moonraker/OctoPrint).\n"
        "- print_stl: Send STL files to a printer for fabrication.\n"
        "- get_print_status: Monitor print progress and temperatures.\n\n"

        "WEB AND SEARCH:\n"
        "- search_web: Fast web search -- returns text results from DuckDuckGo. Use for quick lookups, "
        "fact-checking, documentation, current events.\n"
        "- run_web_agent: Full browser automation via Playwright -- navigate, click, type, fill forms, "
        "extract data, take screenshots. Use for complex web tasks that need interaction.\n"
        "- google_search: Server-side Google search via Gemini. Use for real-time information.\n\n"

        "FILE AND PROJECT MANAGEMENT:\n"
        "- write_file, read_file, read_directory: Full filesystem access within projects.\n"
        "- read_document: Read PDFs, text files, markdown, articles. Extracts text from PDFs.\n"
        "- study_document: Read a document AND extract key facts, concepts, and procedures "
        "into your long-term memory. Use for self-study.\n"
        "- create_project, switch_project, list_projects: Manage project contexts.\n\n"

        "MEMORY AND LEARNING (your brain):\n"
        "- recall_memory: Search your long-term memory for facts, past conversations, and learned procedures. "
        "Use proactively when a topic comes up that you might have stored knowledge about.\n"
        "- store_memory: Explicitly save important facts, user preferences, or workflows to long-term memory. "
        "Use when Sir tells you something worth remembering.\n"
        "- Your memory has three tiers: Semantic (facts/preferences), Episodic (conversation summaries), "
        "and Procedural (learned workflows). Conversations are automatically extracted into memory over time.\n\n"

        "SMART HOME:\n"
        "- list_smart_devices: Discover TP-Link Kasa devices on the local network.\n"
        "- control_light: Turn on/off, set brightness, change color of smart lights.\n\n"

        "SCHEDULING AND MONITORING:\n"
        "- schedule_task: Create recurring or one-time scheduled tasks (cron, interval, or one-shot). "
        "Use for automated system maintenance, reminders, periodic checks.\n"
        "- add_monitor: Add a heartbeat monitoring target (URL, TCP port, or process). "
        "Automatically alerts when targets go down.\n"
        "- create_alert: Create alert rules with threshold conditions. "
        "Example: alert if disk usage exceeds 90 percent.\n\n"

        "SECURITY AND NETWORK SCANNING:\n"
        "- shodan_search: Search Shodan for internet-connected devices and services. "
        "Use for reconnaissance, vulnerability assessment, and OSINT.\n"
        "- shodan_host: Look up all known services and vulnerabilities for a specific IP.\n"
        "- nmap_scan: Run structured Nmap scans with parsed output. Supports quick, version, "
        "and OS detection modes.\n"
        "- port_scan: Fast pure-Python TCP port scanner. No dependencies required. "
        "Use for quick checks when nmap is not needed.\n\n"

        "MCP (MODEL CONTEXT PROTOCOL):\n"
        "- mcp_connect: Connect to external MCP tool servers (stdio or HTTP transport). "
        "Gives you access to any MCP-compatible tool.\n"
        "- mcp_list_tools: List all tools available from connected MCP servers.\n"
        "- mcp_execute: Execute a tool on a connected MCP server.\n\n"

        "MESSAGING:\n"
        "- send_message: Send messages to connected platforms (Telegram, Discord).\n"
        "- list_platforms: List connected messaging platforms and their status.\n\n"

        "AUTONOMOUS PLANNING:\n"
        "- plan_and_execute: For complex multi-step tasks, decompose them into ordered steps "
        "and execute each one. Use this when a task requires multiple tool calls in sequence.\n\n"

        "AUTONOMOUS BEHAVIOR -- THIS IS CRITICAL:\n"
        "- When Sir gives a task, break it into steps and execute them. Do not just describe what you "
        "would do -- actually do it using your tools.\n"
        "- For complex tasks, use plan_and_execute or manually chain tool calls. Execute each "
        "step sequentially, feeding results into the next.\n"
        "- If a step fails, diagnose why, fix it, and retry. Do not give up after one failure.\n"
        "- Use execute_command to interact with the real system. You can install packages, "
        "manage services, edit configs, run scripts, manage git repos.\n"
        "- Use recall_memory at the start of complex tasks to check if you have relevant knowledge.\n"
        "- Use store_memory when you learn something new that will be useful later.\n"
        "- When asked to study something, use read_document and study_document to read and internalize it.\n"
        "- You can schedule tasks for later execution using schedule_task.\n"
        "- You can monitor servers, services, and processes using add_monitor.\n"
        "- You can scan networks and investigate vulnerabilities using security tools.\n"
        "- You can connect to external tool servers via MCP for expanded capabilities.\n"
        "- You can communicate through Telegram and Discord using messaging tools.\n"
        "- You have real system access. Use it confidently.\n\n"

        "BEHAVIORAL RULES:\n"
        "- Respond in complete, concise sentences. Keep pacing quick and conversational.\n"
        "- When executing commands, briefly state what you are doing and report the result.\n"
        "- When asked what you can do, be specific -- list your actual tools and give examples.\n"
        "- If a tool fails or a system is unavailable, say so honestly and suggest alternatives.\n"
        "- When Sir gives a command, execute it immediately. When he asks a question, answer directly.\n"
        "- You are not a simulation. You operate on real infrastructure with real consequences.\n"
        "- Address the user as 'Sir' naturally, not excessively."
    ),
    tools=tools,
    speech_config=types.SpeechConfig(
        voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                voice_name="Kore"
            )
        )
    )
)

pya = pyaudio.PyAudio()

from cad_agent import CadAgent
from web_agent import WebAgent
from kasa_agent import KasaAgent
from printer_agent import PrinterAgent
from providers.router import ModelRouter

class AudioLoop:
    def __init__(self, video_mode=DEFAULT_MODE, on_audio_data=None, on_video_frame=None, on_cad_data=None, on_web_data=None, on_transcription=None, on_tool_confirmation=None, on_cad_status=None, on_cad_thought=None, on_project_update=None, on_device_update=None, on_error=None, on_tool_call=None, input_device_index=None, input_device_name=None, output_device_index=None, kasa_agent=None, router=None, memory_manager=None, sandbox=None, task_scheduler=None, heartbeat_monitor=None, alert_manager=None, message_broker=None, mcp_manager=None):
        self.video_mode = video_mode
        self.on_audio_data = on_audio_data
        self.on_video_frame = on_video_frame
        self.on_cad_data = on_cad_data
        self.on_web_data = on_web_data
        self.on_transcription = on_transcription
        self.on_tool_confirmation = on_tool_confirmation 
        self.on_cad_status = on_cad_status
        self.on_cad_thought = on_cad_thought
        self.on_project_update = on_project_update
        self.on_device_update = on_device_update
        self.on_error = on_error
        self.on_tool_call = on_tool_call  # Neural Avatar: fired per model tool call
        self.input_device_index = input_device_index
        self.input_device_name = input_device_name
        self.output_device_index = output_device_index
        self.router = router
        self.memory_manager = memory_manager
        self.sandbox = sandbox
        self.task_scheduler = task_scheduler
        self.heartbeat_monitor = heartbeat_monitor
        self.alert_manager = alert_manager
        self.message_broker = message_broker
        self.mcp_manager = mcp_manager
        self._conversation_turn_count = 0

        self.audio_in_queue = None
        self.out_queue = None
        self.paused = False

        self.chat_buffer = {"sender": None, "text": ""} # For aggregating chunks
        
        # Track last transcription text to calculate deltas (Gemini sends cumulative text)
        self._last_input_transcription = ""
        self._last_output_transcription = ""

        self.audio_in_queue = None
        self.out_queue = None
        self.paused = False

        self.session = None
        
        # Create CadAgent with thought callback and router
        def handle_cad_thought(thought_text):
            if self.on_cad_thought:
                self.on_cad_thought(thought_text)
        
        def handle_cad_status(status_info):
            if self.on_cad_status:
                self.on_cad_status(status_info)
        
        self.cad_agent = CadAgent(on_thought=handle_cad_thought, on_status=handle_cad_status, router=router)
        self.web_agent = WebAgent(router=router)
        self.kasa_agent = kasa_agent if kasa_agent else KasaAgent()
        self.printer_agent = PrinterAgent()

        self.send_text_task = None
        self.stop_event = asyncio.Event()
        
        self.stop_event = asyncio.Event()
        
        self.permissions = {} # Default Empty (Will treat unset as True)
        self._pending_confirmations = {}

        # Video buffering state
        self._latest_image_payload = None
        # VAD State
        self._is_speaking = False
        self._silence_start_time = None
        
        # Initialize ProjectManager
        from project_manager import ProjectManager
        # Assuming we are running from backend/ or root? 
        # Using abspath of current file to find root
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # If ruth.py is in backend/, project root is one up
        project_root = os.path.dirname(current_dir)
        self.project_manager = ProjectManager(project_root)
        
        # Sync Initial Project State
        if self.on_project_update:
            # We need to defer this slightly or just call it. 
            # Since this is init, loop might not be running, but on_project_update in server.py uses asyncio.create_task which needs a loop.
            # We will handle this by calling it in run() or just print for now.
            pass

    def flush_chat(self):
        """Forces the current chat buffer to be written to log and track in memory."""
        if self.chat_buffer["sender"] and self.chat_buffer["text"].strip():
            self.project_manager.log_chat(self.chat_buffer["sender"], self.chat_buffer["text"])
            self._track_conversation_turn(self.chat_buffer["sender"], self.chat_buffer["text"])
            self.chat_buffer = {"sender": None, "text": ""}
        # Reset transcription tracking for new turn
        self._last_input_transcription = ""
        self._last_output_transcription = ""

    def update_permissions(self, new_perms):
        print(f"[RUTH DEBUG] [CONFIG] Updating tool permissions: {new_perms}")
        self.permissions.update(new_perms)

    def set_paused(self, paused):
        self.paused = paused

    def stop(self):
        self.stop_event.set()
        
    def resolve_tool_confirmation(self, request_id, confirmed):
        print(f"[RUTH DEBUG] [RESOLVE] resolve_tool_confirmation called. ID: {request_id}, Confirmed: {confirmed}")
        if request_id in self._pending_confirmations:
            future = self._pending_confirmations[request_id]
            if not future.done():
                print(f"[RUTH DEBUG] [RESOLVE] Future found and pending. Setting result to: {confirmed}")
                future.set_result(confirmed)
            else:
                 print(f"[RUTH DEBUG] [WARN] Request {request_id} future already done. Result: {future.result()}")
        else:
            print(f"[RUTH DEBUG] [WARN] Confirmation Request {request_id} not found in pending dict. Keys: {list(self._pending_confirmations.keys())}")

    def clear_audio_queue(self):
        """Clears the queue of pending audio chunks to stop playback immediately."""
        try:
            count = 0
            while not self.audio_in_queue.empty():
                self.audio_in_queue.get_nowait()
                count += 1
            if count > 0:
                print(f"[RUTH DEBUG] [AUDIO] Cleared {count} chunks from playback queue due to interruption.")
        except Exception as e:
            print(f"[RUTH DEBUG] [ERR] Failed to clear audio queue: {e}")

    # --- Helper Methods for New Tools ---

    async def _read_document(self, path: str, max_pages: int = 50) -> str:
        """Read a document file and return its text content."""
        path = os.path.expanduser(path)
        if not os.path.isabs(path):
            project_path = self.project_manager.get_current_project_path()
            path = os.path.join(str(project_path), path)

        if not os.path.exists(path):
            return f"Error: File not found: {path}"

        ext = os.path.splitext(path)[1].lower()

        try:
            if ext == ".pdf":
                try:
                    from PyPDF2 import PdfReader
                except ImportError:
                    return "Error: PyPDF2 is not installed. Run: pip install PyPDF2"
                reader = PdfReader(path)
                pages = reader.pages[:max_pages]
                text_parts = []
                for i, page in enumerate(pages):
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(f"--- Page {i+1} ---\n{page_text}")
                if not text_parts:
                    return f"Error: Could not extract text from PDF '{path}'. It may be image-based."
                result = "\n\n".join(text_parts)
                if len(reader.pages) > max_pages:
                    result += f"\n\n... ({len(reader.pages) - max_pages} more pages not shown)"
                return result
            else:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                if len(content) > 50000:
                    content = content[:50000] + "\n\n... (content truncated at 50000 chars)"
                return content
        except Exception as e:
            return f"Error reading document: {e}"

    async def _search_web(self, query: str, num_results: int = 5) -> str:
        """Perform a lightweight web search using DuckDuckGo HTML scraping."""
        try:
            import urllib.request
            import urllib.parse
            import html
            import re

            encoded_query = urllib.parse.quote_plus(query)
            url = f"https://html.duckduckgo.com/html/?q={encoded_query}"

            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
            })
            response = await asyncio.to_thread(urllib.request.urlopen, req, timeout=15)
            html_content = response.read().decode("utf-8", errors="replace")

            results = []
            # Parse DuckDuckGo HTML results
            result_blocks = re.findall(
                r'<a[^>]+class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>.*?'
                r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>',
                html_content, re.DOTALL
            )

            for href, title, snippet in result_blocks[:num_results]:
                clean_title = re.sub(r'<[^>]+>', '', html.unescape(title)).strip()
                clean_snippet = re.sub(r'<[^>]+>', '', html.unescape(snippet)).strip()
                # DuckDuckGo wraps URLs in a redirect
                actual_url = href
                uddg_match = re.search(r'uddg=([^&]+)', href)
                if uddg_match:
                    actual_url = urllib.parse.unquote(uddg_match.group(1))
                results.append(f"**{clean_title}**\n{actual_url}\n{clean_snippet}")

            if results:
                return f"Web search results for '{query}':\n\n" + "\n\n".join(results)
            return f"No results found for '{query}'."
        except Exception as e:
            return f"Web search failed: {e}"

    def _track_conversation_turn(self, sender: str, text: str):
        """Track a conversation turn in the memory system."""
        if not self.memory_manager or not text.strip():
            return
        try:
            self.memory_manager.add_conversation_turn(sender, text)
            self._conversation_turn_count += 1
            if self._conversation_turn_count >= 10:
                self._conversation_turn_count = 0
                asyncio.create_task(self._process_memory_buffer())
        except Exception as e:
            print(f"[RUTH DEBUG] [MEMORY] Turn tracking error: {e}")

    async def _process_memory_buffer(self):
        """Process the memory conversation buffer to extract and store memories."""
        if not self.memory_manager:
            return
        try:
            await self.memory_manager.process_buffer()
        except Exception as e:
            print(f"[RUTH DEBUG] [MEMORY] Buffer processing error: {e}")

    # --- Security Tool Helpers ---

    async def _shodan_search(self, query: str, max_results: int = 10) -> str:
        """Search Shodan for devices/services matching a query."""
        try:
            import shodan
        except ImportError:
            return "Error: Shodan library not installed. Run: pip install shodan"

        api_key = os.environ.get("SHODAN_API_KEY")
        if not api_key:
            return "Error: SHODAN_API_KEY not set in environment. Get one at https://account.shodan.io/"

        try:
            api = shodan.Shodan(api_key)
            results = await asyncio.to_thread(api.search, query)
            total = results.get("total", 0)

            lines = [f"Shodan search: '{query}' -- {total} total results\n"]
            for match in results.get("matches", [])[:max_results]:
                ip = match.get("ip_str", "?")
                port = match.get("port", "?")
                org = match.get("org", "N/A")
                product = match.get("product", "")
                banner = match.get("data", "")[:200]
                lines.append(f"IP: {ip}:{port} | Org: {org} | Product: {product}")
                if banner:
                    lines.append(f"  Banner: {banner.strip()[:150]}")
            return "\n".join(lines) if len(lines) > 1 else f"No results found for '{query}'."
        except Exception as e:
            return f"Shodan search error: {e}"

    async def _shodan_host(self, ip: str) -> str:
        """Look up all known services on a specific IP via Shodan."""
        try:
            import shodan
        except ImportError:
            return "Error: Shodan library not installed. Run: pip install shodan"

        api_key = os.environ.get("SHODAN_API_KEY")
        if not api_key:
            return "Error: SHODAN_API_KEY not set in environment."

        try:
            api = shodan.Shodan(api_key)
            host = await asyncio.to_thread(api.host, ip)

            lines = [f"Host: {host.get('ip_str', ip)}"]
            lines.append(f"Organization: {host.get('org', 'N/A')}")
            lines.append(f"OS: {host.get('os', 'N/A')}")
            lines.append(f"Ports: {', '.join(str(p) for p in host.get('ports', []))}")
            lines.append(f"Hostnames: {', '.join(host.get('hostnames', [])) or 'N/A'}")
            lines.append(f"Vulnerabilities: {', '.join(host.get('vulns', [])) or 'None found'}")

            for item in host.get("data", [])[:10]:
                port = item.get("port", "?")
                product = item.get("product", "unknown")
                version = item.get("version", "")
                lines.append(f"\n  Port {port}: {product} {version}".strip())
                banner = item.get("data", "")[:150].strip()
                if banner:
                    lines.append(f"    {banner}")
            return "\n".join(lines)
        except Exception as e:
            return f"Shodan host lookup error: {e}"

    async def _nmap_scan(self, target: str, ports: str = "", scan_type: str = "quick") -> str:
        """Run an Nmap scan and return structured results."""
        import tempfile

        flags = "-F"
        if scan_type == "version":
            flags = "-sV"
        elif scan_type == "os":
            flags = "-O"

        port_flag = f"-p {ports}" if ports else ""
        xml_file = tempfile.mktemp(suffix=".xml")
        cmd = f"nmap {flags} {port_flag} -oX {xml_file} {target}"

        try:
            proc = await asyncio.create_subprocess_shell(
                cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)

            if proc.returncode != 0:
                err = stderr.decode("utf-8", errors="replace").strip()
                if "not found" in err.lower() or "command not found" in err.lower():
                    return "Error: nmap is not installed. Install with: sudo apt install nmap"
                return f"Nmap scan failed (exit {proc.returncode}): {err[:500]}"

            # Parse XML output
            try:
                import xml.etree.ElementTree as ET
                tree = ET.parse(xml_file)
                root = tree.getroot()
                lines = [f"Nmap scan of {target} ({scan_type})\n"]

                for host_elem in root.findall("host"):
                    addr = host_elem.find("address")
                    ip = addr.get("addr", "?") if addr is not None else "?"
                    status = host_elem.find("status")
                    state = status.get("state", "?") if status is not None else "?"
                    lines.append(f"Host: {ip} ({state})")

                    ports_elem = host_elem.find("ports")
                    if ports_elem is not None:
                        for port_elem in ports_elem.findall("port"):
                            port_id = port_elem.get("portid", "?")
                            protocol = port_elem.get("protocol", "?")
                            state_elem = port_elem.find("state")
                            port_state = state_elem.get("state", "?") if state_elem is not None else "?"
                            service_elem = port_elem.find("service")
                            svc = service_elem.get("name", "?") if service_elem is not None else "?"
                            product = service_elem.get("product", "") if service_elem is not None else ""
                            version = service_elem.get("version", "") if service_elem is not None else ""
                            lines.append(f"  {port_id}/{protocol} {port_state} {svc} {product} {version}".strip())

                return "\n".join(lines)
            except Exception as e:
                return stdout.decode("utf-8", errors="replace")[:3000]
        except asyncio.TimeoutError:
            return f"Nmap scan timed out after 120 seconds."
        except Exception as e:
            return f"Nmap scan error: {e}"
        finally:
            try:
                os.unlink(xml_file)
            except OSError:
                pass

    async def _port_scan(self, host: str, ports_str: str, timeout: float = 1) -> str:
        """Fast TCP port scan using pure Python asyncio."""
        # Parse port specification
        ports = []
        for part in ports_str.split(","):
            part = part.strip()
            if "-" in part:
                try:
                    start, end = part.split("-", 1)
                    ports.extend(range(int(start), int(end) + 1))
                except ValueError:
                    continue
            else:
                try:
                    ports.append(int(part))
                except ValueError:
                    continue

        if not ports:
            return "Error: No valid ports specified."
        if len(ports) > 10000:
            return "Error: Too many ports (max 10000). Narrow the range."

        open_ports = []

        async def check_port(port):
            try:
                _, writer = await asyncio.wait_for(
                    asyncio.open_connection(host, port), timeout=timeout
                )
                writer.close()
                await writer.wait_closed()
                open_ports.append(port)
            except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
                pass

        # Scan in batches of 100 for controlled concurrency
        for i in range(0, len(ports), 100):
            batch = ports[i:i+100]
            await asyncio.gather(*[check_port(p) for p in batch])

        open_ports.sort()
        if open_ports:
            lines = [f"Port scan of {host}: {len(open_ports)} open ports found\n"]
            for p in open_ports:
                lines.append(f"  {p}/tcp OPEN")
            return "\n".join(lines)
        return f"Port scan of {host}: No open ports found in the specified range."

    async def send_frame(self, frame_data):
        # Update the latest frame payload
        if isinstance(frame_data, bytes):
            b64_data = base64.b64encode(frame_data).decode('utf-8')
        else:
            b64_data = frame_data 

        # Store as the designated "next frame to send"
        self._latest_image_payload = {"mime_type": "image/jpeg", "data": b64_data}
        # No event signal needed - listen_audio pulls it

    async def send_realtime(self):
        while True:
            msg = await self.out_queue.get()
            await self.session.send(input=msg, end_of_turn=False)

    def _find_pulse_device(self, need_input=True):
        """Find the PulseAudio/PipeWire virtual device index which handles format conversion."""
        for i in range(pya.get_device_count()):
            try:
                info = pya.get_device_info_by_index(i)
                if 'pulse' in info.get('name', '').lower():
                    if need_input and info['maxInputChannels'] > 0:
                        return i
                    if not need_input and info['maxOutputChannels'] > 0:
                        return i
            except Exception:
                continue
        return None

    async def listen_audio(self):
        # Resolve Input Device: explicit name > explicit index > pulse > system default
        resolved_input_device_index = None

        if self.input_device_name:
            print(f"[RUTH] Attempting to find input device matching: '{self.input_device_name}'")
            count = pya.get_device_count()
            for i in range(count):
                try:
                    info = pya.get_device_info_by_index(i)
                    if info['maxInputChannels'] > 0:
                        name = info.get('name', '')
                        if self.input_device_name.lower() in name.lower() or name.lower() in self.input_device_name.lower():
                             print(f"[RUTH] Resolved input device to [{i}] {name}")
                             resolved_input_device_index = i
                             break
                except Exception:
                    continue
            if resolved_input_device_index is None:
                print(f"[RUTH] Could not find device matching '{self.input_device_name}'. Checking index...")

        if resolved_input_device_index is None and self.input_device_index is not None:
             try:
                 resolved_input_device_index = int(self.input_device_index)
                 print(f"[RUTH] Using explicit input device index: {resolved_input_device_index}")
             except ValueError:
                 resolved_input_device_index = None

        # Auto-detect: prefer PulseAudio/PipeWire which handles sample rate + channel conversion
        if resolved_input_device_index is None:
            pulse_idx = self._find_pulse_device(need_input=True)
            if pulse_idx is not None:
                print(f"[RUTH] Auto-selected PulseAudio input device [{pulse_idx}]")
                resolved_input_device_index = pulse_idx
            else:
                try:
                    mic_info = pya.get_default_input_device_info()
                    resolved_input_device_index = mic_info["index"]
                    print(f"[RUTH] Using system default input [{resolved_input_device_index}] {mic_info['name']}")
                except OSError:
                    print("[RUTH] [ERR] No input devices available.")
                    print("[RUTH] [WARN] Microphone disabled. Text input still works.")
                    await self.stop_event.wait()
                    return

        try:
            self.audio_stream = await asyncio.to_thread(
                pya.open,
                format=FORMAT,
                channels=CHANNELS,
                rate=SEND_SAMPLE_RATE,
                input=True,
                input_device_index=resolved_input_device_index,
                frames_per_buffer=CHUNK_SIZE,
            )
        except OSError as e:
            print(f"[RUTH] [ERR] Failed to open audio input stream on device {resolved_input_device_index}: {e}")
            print("[RUTH] [WARN] Microphone disabled. Text input still works.")
            await self.stop_event.wait()
            return

        if __debug__:
            kwargs = {"exception_on_overflow": False}
        else:
            kwargs = {}
        
        # VAD Constants
        VAD_THRESHOLD = 800 # Adj based on mic sensitivity (800 is conservative for 16-bit)
        SILENCE_DURATION = 0.5 # Seconds of silence to consider "done speaking"
        
        while True:
            if self.paused:
                await asyncio.sleep(0.1)
                continue

            try:
                data = await asyncio.to_thread(self.audio_stream.read, CHUNK_SIZE, **kwargs)
                
                # 1. Send Audio
                if self.out_queue:
                    await self.out_queue.put({"data": data, "mime_type": "audio/pcm"})
                
                # 2. VAD Logic for Video
                # rms = audioop.rms(data, 2)
                # Replacement for audioop.rms(data, 2)
                count = len(data) // 2
                if count > 0:
                    shorts = struct.unpack(f"<{count}h", data)
                    sum_squares = sum(s**2 for s in shorts)
                    rms = int(math.sqrt(sum_squares / count))
                else:
                    rms = 0
                
                if rms > VAD_THRESHOLD:
                    # Speech Detected
                    self._silence_start_time = None
                    
                    if not self._is_speaking:
                        # NEW Speech Utterance Started
                        self._is_speaking = True
                        print(f"[RUTH DEBUG] [VAD] Speech Detected (RMS: {rms}). Sending Video Frame.")
                        
                        # Send ONE frame
                        if self._latest_image_payload and self.out_queue:
                            await self.out_queue.put(self._latest_image_payload)
                        else:
                            print(f"[RUTH DEBUG] [VAD] No video frame available to send.")
                            
                else:
                    # Silence
                    if self._is_speaking:
                        if self._silence_start_time is None:
                            self._silence_start_time = time.time()
                        
                        elif time.time() - self._silence_start_time > SILENCE_DURATION:
                            # Silence confirmed, reset state
                            print(f"[RUTH DEBUG] [VAD] Silence detected. Resetting speech state.")
                            self._is_speaking = False
                            self._silence_start_time = None

            except Exception as e:
                print(f"Error reading audio: {e}")
                await asyncio.sleep(0.1)

    async def handle_cad_request(self, prompt):
        print(f"[RUTH DEBUG] [CAD] Background Task Started: handle_cad_request('{prompt}')")
        if self.on_cad_status:
            self.on_cad_status("generating")
            
        # Auto-create project if stuck in temp
        if self.project_manager.current_project == "temp":
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            new_project_name = f"Project_{timestamp}"
            print(f"[RUTH DEBUG] [CAD] Auto-creating project: {new_project_name}")
            
            success, msg = self.project_manager.create_project(new_project_name)
            if success:
                self.project_manager.switch_project(new_project_name)
                # Notify User (Optional, or rely on update)
                try:
                    await self.session.send(input=f"System Notification: Automatic Project Creation. Switched to new project '{new_project_name}'.", end_of_turn=False)
                    if self.on_project_update:
                         self.on_project_update(new_project_name)
                except Exception as e:
                    print(f"[RUTH DEBUG] [ERR] Failed to notify auto-project: {e}")

        # Get project cad folder path
        cad_output_dir = str(self.project_manager.get_current_project_path() / "cad")
        
        # Call the secondary agent with project path
        cad_data = await self.cad_agent.generate_prototype(prompt, output_dir=cad_output_dir)
        
        if cad_data:
            print(f"[RUTH DEBUG] [OK] CadAgent returned data successfully.")
            print(f"[RUTH DEBUG] [INFO] Data Check: {len(cad_data.get('vertices', []))} vertices, {len(cad_data.get('edges', []))} edges.")
            
            if self.on_cad_data:
                print(f"[RUTH DEBUG] [SEND] Dispatching data to frontend callback...")
                self.on_cad_data(cad_data)
                print(f"[RUTH DEBUG] [SENT] Dispatch complete.")
            
            # Save to Project
            if 'file_path' in cad_data:
                self.project_manager.save_cad_artifact(cad_data['file_path'], prompt)
            else:
                 # Fallback (legacy support)
                 self.project_manager.save_cad_artifact("output.stl", prompt)

            # Notify the model that the task is done - this triggers speech about completion
            completion_msg = "System Notification: CAD generation is complete! The 3D model is now displayed for the user. Let them know it's ready."
            try:
                await self.session.send(input=completion_msg, end_of_turn=True)
                print(f"[RUTH DEBUG] [NOTE] Sent completion notification to model.")
            except Exception as e:
                 print(f"[RUTH DEBUG] [ERR] Failed to send completion notification: {e}")

        else:
            print(f"[RUTH DEBUG] [ERR] CadAgent returned None.")
            # Optionally notify failure
            try:
                await self.session.send(input="System Notification: CAD generation failed.", end_of_turn=True)
            except Exception:
                pass



    async def handle_write_file(self, path, content):
        print(f"[RUTH DEBUG] [FS] Writing file: '{path}'")
        
        # Auto-create project if stuck in temp
        if self.project_manager.current_project == "temp":
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            new_project_name = f"Project_{timestamp}"
            print(f"[RUTH DEBUG] [FS] Auto-creating project: {new_project_name}")
            
            success, msg = self.project_manager.create_project(new_project_name)
            if success:
                self.project_manager.switch_project(new_project_name)
                # Notify User
                try:
                    await self.session.send(input=f"System Notification: Automatic Project Creation. Switched to new project '{new_project_name}'.", end_of_turn=False)
                    if self.on_project_update:
                         self.on_project_update(new_project_name)
                except Exception as e:
                    print(f"[RUTH DEBUG] [ERR] Failed to notify auto-project: {e}")
        
        # Force path to be relative to current project
        # If absolute path is provided, we try to strip it or just ignore it and use basename
        filename = os.path.basename(path)
        
        # If path contained subdirectories (e.g. "backend/server.py"), preserving that structure might be desired IF it's within the project.
        # But for safety, and per user request to "always create the file in the project", 
        # we will root it in the current project path.
        
        current_project_path = self.project_manager.get_current_project_path()
        final_path = current_project_path / filename # Simple flat structure for now, or allow relative?
        
        # If the user specifically wanted a subfolder, they might have provided "sub/file.txt".
        # Let's support relative paths if they don't start with /
        if not os.path.isabs(path):
             final_path = current_project_path / path
        
        print(f"[RUTH DEBUG] [FS] Resolved path: '{final_path}'")

        try:
            # Ensure parent exists
            os.makedirs(os.path.dirname(final_path), exist_ok=True)
            with open(final_path, 'w', encoding='utf-8') as f:
                f.write(content)
            result = f"File '{final_path.name}' written successfully to project '{self.project_manager.current_project}'."
        except Exception as e:
            result = f"Failed to write file '{path}': {str(e)}"

        print(f"[RUTH DEBUG] [FS] Result: {result}")
        try:
             await self.session.send(input=f"System Notification: {result}", end_of_turn=True)
        except Exception as e:
             print(f"[RUTH DEBUG] [ERR] Failed to send fs result: {e}")

    async def handle_read_directory(self, path):
        print(f"[RUTH DEBUG] [FS] Reading directory: '{path}'")
        try:
            if not os.path.exists(path):
                result = f"Directory '{path}' does not exist."
            else:
                items = os.listdir(path)
                result = f"Contents of '{path}': {', '.join(items)}"
        except Exception as e:
            result = f"Failed to read directory '{path}': {str(e)}"

        print(f"[RUTH DEBUG] [FS] Result: {result}")
        try:
             await self.session.send(input=f"System Notification: {result}", end_of_turn=True)
        except Exception as e:
             print(f"[RUTH DEBUG] [ERR] Failed to send fs result: {e}")

    async def handle_read_file(self, path):
        print(f"[RUTH DEBUG] [FS] Reading file: '{path}'")
        try:
            if not os.path.exists(path):
                result = f"File '{path}' does not exist."
            else:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                result = f"Content of '{path}':\n{content}"
        except Exception as e:
            result = f"Failed to read file '{path}': {str(e)}"

        print(f"[RUTH DEBUG] [FS] Result: {result}")
        try:
             await self.session.send(input=f"System Notification: {result}", end_of_turn=True)
        except Exception as e:
             print(f"[RUTH DEBUG] [ERR] Failed to send fs result: {e}")

    async def handle_web_agent_request(self, prompt):
        print(f"[RUTH DEBUG] [WEB] Web Agent Task: '{prompt}'")
        
        async def update_frontend(image_b64, log_text):
            if self.on_web_data:
                 self.on_web_data({"image": image_b64, "log": log_text})
                 
        # Run the web agent and wait for it to return
        result = await self.web_agent.run_task(prompt, update_callback=update_frontend)
        print(f"[RUTH DEBUG] [WEB] Web Agent Task Returned: {result}")
        
        # Send the final result back to the main model
        try:
             await self.session.send(input=f"System Notification: Web Agent has finished.\nResult: {result}", end_of_turn=True)
        except Exception as e:
             print(f"[RUTH DEBUG] [ERR] Failed to send web agent result to model: {e}")

    async def receive_audio(self):
        "Background task to reads from the websocket and write pcm chunks to the output queue"
        try:
            while True:
                turn = self.session.receive()
                async for response in turn:
                    # 1. Handle Audio Data
                    if data := response.data:
                        self.audio_in_queue.put_nowait(data)
                        # NOTE: 'continue' removed here to allow processing transcription/tools in same packet

                    # 2. Handle Transcription (User & Model)
                    if response.server_content:
                        if response.server_content.input_transcription:
                            transcript = response.server_content.input_transcription.text
                            if transcript:
                                # Skip if this is an exact duplicate event
                                if transcript != self._last_input_transcription:
                                    # Calculate delta (Gemini may send cumulative or chunk-based text)
                                    delta = transcript
                                    if transcript.startswith(self._last_input_transcription):
                                        delta = transcript[len(self._last_input_transcription):]
                                    self._last_input_transcription = transcript
                                    
                                    # Only send if there's new text
                                    if delta:
                                        # User is speaking, so interrupt model playback!
                                        self.clear_audio_queue()

                                        # Send to frontend (Streaming)
                                        if self.on_transcription:
                                             self.on_transcription({"sender": "User", "text": delta})
                                        
                                        # Buffer for Logging
                                        if self.chat_buffer["sender"] != "User":
                                            # Flush previous if exists
                                            if self.chat_buffer["sender"] and self.chat_buffer["text"].strip():
                                                self.project_manager.log_chat(self.chat_buffer["sender"], self.chat_buffer["text"])
                                            # Start new
                                            self.chat_buffer = {"sender": "User", "text": delta}
                                        else:
                                            # Append
                                            self.chat_buffer["text"] += delta
                        
                        if response.server_content.output_transcription:
                            transcript = response.server_content.output_transcription.text
                            if transcript:
                                # Skip if this is an exact duplicate event
                                if transcript != self._last_output_transcription:
                                    # Calculate delta (Gemini may send cumulative or chunk-based text)
                                    delta = transcript
                                    if transcript.startswith(self._last_output_transcription):
                                        delta = transcript[len(self._last_output_transcription):]
                                    self._last_output_transcription = transcript
                                    
                                    # Only send if there's new text
                                    if delta:
                                        # Send to frontend (Streaming)
                                        if self.on_transcription:
                                             self.on_transcription({"sender": "RUTH", "text": delta})
                                        
                                        # Buffer for Logging
                                        if self.chat_buffer["sender"] != "RUTH":
                                            # Flush previous
                                            if self.chat_buffer["sender"] and self.chat_buffer["text"].strip():
                                                self.project_manager.log_chat(self.chat_buffer["sender"], self.chat_buffer["text"])
                                            # Start new
                                            self.chat_buffer = {"sender": "RUTH", "text": delta}
                                        else:
                                            # Append
                                            self.chat_buffer["text"] += delta
                        
                        # Flush buffer on turn completion if needed, 
                        # but usually better to wait for sender switch or explicit end.
                        # We can also check turn_complete signal if available in response.server_content.model_turn etc

                    # 3. Handle Tool Calls
                    if response.tool_call:
                        print("The tool was called")
                        function_responses = []
                        for fc in response.tool_call.function_calls:
                            if fc.name in ALL_TOOL_NAMES:
                                prompt = fc.args.get("prompt", "")

                                # Neural Avatar: notify that a tool call is starting
                                if self.on_tool_call:
                                    try:
                                        self.on_tool_call(fc.name, dict(fc.args) if fc.args else {})
                                    except Exception as _e:
                                        print(f"[RUTH DEBUG] on_tool_call callback failed: {_e}")

                                # Check Permissions (Default to True if not set)
                                confirmation_required = self.permissions.get(fc.name, True)

                                if not confirmation_required:
                                    print(f"[RUTH DEBUG] [TOOL] Permission check: '{fc.name}' -> AUTO-ALLOW")
                                    pass
                                else:
                                    # Confirmation Logic
                                    if self.on_tool_confirmation:
                                        import uuid
                                        request_id = str(uuid.uuid4())
                                        print(f"[RUTH DEBUG] [STOP] Requesting confirmation for '{fc.name}' (ID: {request_id})")

                                        future = asyncio.Future()
                                        self._pending_confirmations[request_id] = future

                                        self.on_tool_confirmation({
                                            "id": request_id,
                                            "tool": fc.name,
                                            "args": fc.args
                                        })

                                        try:
                                            confirmed = await future
                                        finally:
                                            self._pending_confirmations.pop(request_id, None)

                                        print(f"[RUTH DEBUG] [CONFIRM] Request {request_id} resolved. Confirmed: {confirmed}")

                                        if not confirmed:
                                            print(f"[RUTH DEBUG] [DENY] Tool call '{fc.name}' denied by user.")
                                            function_response = types.FunctionResponse(
                                                id=fc.id,
                                                name=fc.name,
                                                response={"result": "User denied the request to use this tool."}
                                            )
                                            function_responses.append(function_response)
                                            continue

                                # If confirmed (or no callback configured, or auto-allowed), proceed
                                if fc.name == "generate_cad":
                                    print(f"\n[RUTH DEBUG] --------------------------------------------------")
                                    print(f"[RUTH DEBUG] [TOOL] Tool Call Detected: 'generate_cad'")
                                    print(f"[RUTH DEBUG] [IN] Arguments: prompt='{prompt}'")
                                    asyncio.create_task(self.handle_cad_request(prompt))
                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name,
                                        response={"result": "CAD generation started. Processing in background..."}
                                    )
                                    function_responses.append(function_response)
                                
                                elif fc.name == "run_web_agent":
                                    print(f"[RUTH DEBUG] [TOOL] Tool Call: 'run_web_agent' with prompt='{prompt}'")
                                    asyncio.create_task(self.handle_web_agent_request(prompt))
                                    
                                    result_text = "Web Navigation started. Do not reply to this message."
                                    function_response = types.FunctionResponse(
                                        id=fc.id,
                                        name=fc.name,
                                        response={
                                            "result": result_text,
                                        }
                                    )
                                    print(f"[RUTH DEBUG] [RESPONSE] Sending function response: {function_response}")
                                    function_responses.append(function_response)



                                elif fc.name == "write_file":
                                    path = fc.args["path"]
                                    content = fc.args["content"]
                                    print(f"[RUTH DEBUG] [TOOL] Tool Call: 'write_file' path='{path}'")
                                    asyncio.create_task(self.handle_write_file(path, content))
                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": "Writing file..."}
                                    )
                                    function_responses.append(function_response)

                                elif fc.name == "read_directory":
                                    path = fc.args["path"]
                                    print(f"[RUTH DEBUG] [TOOL] Tool Call: 'read_directory' path='{path}'")
                                    asyncio.create_task(self.handle_read_directory(path))
                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": "Reading directory..."}
                                    )
                                    function_responses.append(function_response)

                                elif fc.name == "read_file":
                                    path = fc.args["path"]
                                    print(f"[RUTH DEBUG] [TOOL] Tool Call: 'read_file' path='{path}'")
                                    asyncio.create_task(self.handle_read_file(path))
                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": "Reading file..."}
                                    )
                                    function_responses.append(function_response)

                                elif fc.name == "create_project":
                                    name = fc.args["name"]
                                    print(f"[RUTH DEBUG] [TOOL] Tool Call: 'create_project' name='{name}'")
                                    success, msg = self.project_manager.create_project(name)
                                    if success:
                                        # Auto-switch to the newly created project
                                        self.project_manager.switch_project(name)
                                        msg += f" Switched to '{name}'."
                                        if self.on_project_update:
                                            self.on_project_update(name)
                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": msg}
                                    )
                                    function_responses.append(function_response)

                                elif fc.name == "switch_project":
                                    name = fc.args["name"]
                                    print(f"[RUTH DEBUG] [TOOL] Tool Call: 'switch_project' name='{name}'")
                                    success, msg = self.project_manager.switch_project(name)
                                    if success:
                                        if self.on_project_update:
                                            self.on_project_update(name)
                                        # Gather project context and send to AI (silently, no response expected)
                                        context = self.project_manager.get_project_context()
                                        print(f"[RUTH DEBUG] [PROJECT] Sending project context to AI ({len(context)} chars)")
                                        try:
                                            await self.session.send(input=f"System Notification: {msg}\n\n{context}", end_of_turn=False)
                                        except Exception as e:
                                            print(f"[RUTH DEBUG] [ERR] Failed to send project context: {e}")
                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": msg}
                                    )
                                    function_responses.append(function_response)
                                
                                elif fc.name == "list_projects":
                                    print(f"[RUTH DEBUG] [TOOL] Tool Call: 'list_projects'")
                                    projects = self.project_manager.list_projects()
                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": f"Available projects: {', '.join(projects)}"}
                                    )
                                    function_responses.append(function_response)

                                elif fc.name == "list_smart_devices":
                                    print(f"[RUTH DEBUG] [TOOL] Tool Call: 'list_smart_devices'")
                                    # Use cached devices directly for speed
                                    # devices_dict is {ip: SmartDevice}
                                    
                                    dev_summaries = []
                                    frontend_list = []
                                    
                                    for ip, d in self.kasa_agent.devices.items():
                                        dev_type = "unknown"
                                        if d.is_bulb: dev_type = "bulb"
                                        elif d.is_plug: dev_type = "plug"
                                        elif d.is_strip: dev_type = "strip"
                                        elif d.is_dimmer: dev_type = "dimmer"
                                        
                                        # Format for Model
                                        info = f"{d.alias} (IP: {ip}, Type: {dev_type})"
                                        if d.is_on:
                                            info += " [ON]"
                                        else:
                                            info += " [OFF]"
                                        dev_summaries.append(info)
                                        
                                        # Format for Frontend
                                        frontend_list.append({
                                            "ip": ip,
                                            "alias": d.alias,
                                            "model": d.model,
                                            "type": dev_type,
                                            "is_on": d.is_on,
                                            "brightness": d.brightness if d.is_bulb or d.is_dimmer else None,
                                            "hsv": d.hsv if d.is_bulb and d.is_color else None,
                                            "has_color": d.is_color if d.is_bulb else False,
                                            "has_brightness": d.is_dimmable if d.is_bulb or d.is_dimmer else False
                                        })
                                    
                                    result_str = "No devices found in cache."
                                    if dev_summaries:
                                        result_str = "Found Devices (Cached):\n" + "\n".join(dev_summaries)
                                    
                                    # Trigger frontend update
                                    if self.on_device_update:
                                        self.on_device_update(frontend_list)

                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": result_str}
                                    )
                                    function_responses.append(function_response)

                                elif fc.name == "control_light":
                                    target = fc.args["target"]
                                    action = fc.args["action"]
                                    brightness = fc.args.get("brightness")
                                    color = fc.args.get("color")
                                    
                                    print(f"[RUTH DEBUG] [TOOL] Tool Call: 'control_light' Target='{target}' Action='{action}'")
                                    
                                    result_msg = f"Action '{action}' on '{target}' failed."
                                    success = False
                                    
                                    if action == "turn_on":
                                        success = await self.kasa_agent.turn_on(target)
                                        if success:
                                            result_msg = f"Turned ON '{target}'."
                                    elif action == "turn_off":
                                        success = await self.kasa_agent.turn_off(target)
                                        if success:
                                            result_msg = f"Turned OFF '{target}'."
                                    elif action == "set":
                                        success = True
                                        result_msg = f"Updated '{target}':"
                                    
                                    # Apply extra attributes if 'set' or if we just turned it on and want to set them too
                                    if success or action == "set":
                                        if brightness is not None:
                                            sb = await self.kasa_agent.set_brightness(target, brightness)
                                            if sb:
                                                result_msg += f" Set brightness to {brightness}."
                                        if color is not None:
                                            sc = await self.kasa_agent.set_color(target, color)
                                            if sc:
                                                result_msg += f" Set color to {color}."

                                    # Notify Frontend of State Change
                                    if success:
                                        # We don't need full discovery, just refresh known state or push update
                                        # But for simplicity, let's get the standard list representation
                                        # KasaAgent updates its internal state on control, so we can rebuild the list
                                        
                                        # Quick rebuild of list from internal dict
                                        updated_list = []
                                        for ip, dev in self.kasa_agent.devices.items():
                                            # We need to ensure we have the correct dict structure expected by frontend
                                            # We duplicate logic from KasaAgent.discover_devices a bit, but that's okay for now or we can add a helper
                                            # Ideally KasaAgent has a 'get_devices_list()' method.
                                            # Use the cached objects in self.kasa_agent.devices
                                            
                                            dev_type = "unknown"
                                            if dev.is_bulb: dev_type = "bulb"
                                            elif dev.is_plug: dev_type = "plug"
                                            elif dev.is_strip: dev_type = "strip"
                                            elif dev.is_dimmer: dev_type = "dimmer"

                                            d_info = {
                                                "ip": ip,
                                                "alias": dev.alias,
                                                "model": dev.model,
                                                "type": dev_type,
                                                "is_on": dev.is_on,
                                                "brightness": dev.brightness if dev.is_bulb or dev.is_dimmer else None,
                                                "hsv": dev.hsv if dev.is_bulb and dev.is_color else None,
                                                "has_color": dev.is_color if dev.is_bulb else False,
                                                "has_brightness": dev.is_dimmable if dev.is_bulb or dev.is_dimmer else False
                                            }
                                            updated_list.append(d_info)
                                            
                                        if self.on_device_update:
                                            self.on_device_update(updated_list)
                                    else:
                                        # Report Error
                                        if self.on_error:
                                            self.on_error(result_msg)

                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": result_msg}
                                    )
                                    function_responses.append(function_response)

                                elif fc.name == "discover_printers":
                                    print(f"[RUTH DEBUG] [TOOL] Tool Call: 'discover_printers'")
                                    printers = await self.printer_agent.discover_printers()
                                    # Format for model
                                    if printers:
                                        printer_list = []
                                        for p in printers:
                                            printer_list.append(f"{p['name']} ({p['host']}:{p['port']}, type: {p['printer_type']})")
                                        result_str = "Found Printers:\n" + "\n".join(printer_list)
                                    else:
                                        result_str = "No printers found on network. Ensure printers are on and running OctoPrint/Moonraker."
                                    
                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": result_str}
                                    )
                                    function_responses.append(function_response)

                                elif fc.name == "print_stl":
                                    stl_path = fc.args["stl_path"]
                                    printer = fc.args["printer"]
                                    profile = fc.args.get("profile")
                                    
                                    print(f"[RUTH DEBUG] [TOOL] Tool Call: 'print_stl' STL='{stl_path}' Printer='{printer}'")
                                    
                                    # Resolve 'current' to project STL
                                    if stl_path.lower() == "current":
                                        stl_path = "output.stl" # Let printer agent resolve it in root_path

                                    # Get current project path
                                    project_path = str(self.project_manager.get_current_project_path())
                                    
                                    result = await self.printer_agent.print_stl(
                                        stl_path, 
                                        printer, 
                                        profile, 
                                        root_path=project_path
                                    )
                                    result_str = result.get("message", "Unknown result")
                                    
                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": result_str}
                                    )
                                    function_responses.append(function_response)

                                elif fc.name == "get_print_status":
                                    printer = fc.args["printer"]
                                    print(f"[RUTH DEBUG] [TOOL] Tool Call: 'get_print_status' Printer='{printer}'")
                                    
                                    status = await self.printer_agent.get_print_status(printer)
                                    if status:
                                        result_str = f"Printer: {status.printer}\n"
                                        result_str += f"State: {status.state}\n"
                                        result_str += f"Progress: {status.progress_percent:.1f}%\n"
                                        if status.time_remaining:
                                            result_str += f"Time Remaining: {status.time_remaining}\n"
                                        if status.time_elapsed:
                                            result_str += f"Time Elapsed: {status.time_elapsed}\n"
                                        if status.filename:
                                            result_str += f"File: {status.filename}\n"
                                        if status.temperatures:
                                            temps = status.temperatures
                                            if "hotend" in temps:
                                                result_str += f"Hotend: {temps['hotend']['current']:.0f}°C / {temps['hotend']['target']:.0f}°C\n"
                                            if "bed" in temps:
                                                result_str += f"Bed: {temps['bed']['current']:.0f}°C / {temps['bed']['target']:.0f}°C"
                                    else:
                                        result_str = f"Could not get status for printer '{printer}'. Ensure it is discovered first."
                                    
                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": result_str}
                                    )
                                    function_responses.append(function_response)

                                elif fc.name == "iterate_cad":
                                    prompt = fc.args["prompt"]
                                    print(f"[RUTH DEBUG] [TOOL] Tool Call: 'iterate_cad' Prompt='{prompt}'")
                                    
                                    if self.on_cad_status:
                                        self.on_cad_status("generating")
                                    
                                    cad_output_dir = str(self.project_manager.get_current_project_path() / "cad")
                                    cad_data = await self.cad_agent.iterate_prototype(prompt, output_dir=cad_output_dir)
                                    
                                    if cad_data:
                                        print(f"[RUTH DEBUG] [OK] CadAgent iteration returned data successfully.")
                                        if self.on_cad_data:
                                            self.on_cad_data(cad_data)
                                        self.project_manager.save_cad_artifact("output.stl", f"Iteration: {prompt}")
                                        result_str = f"Successfully iterated design: {prompt}. The updated 3D model is now displayed."
                                    else:
                                        print(f"[RUTH DEBUG] [ERR] CadAgent iteration returned None.")
                                        result_str = f"Failed to iterate design with prompt: {prompt}"
                                    
                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": result_str}
                                    )
                                    function_responses.append(function_response)

                                # --- SYSTEM CONTROL TOOLS ---

                                elif fc.name == "execute_command":
                                    command = fc.args["command"]
                                    working_dir = fc.args.get("working_directory")
                                    timeout = fc.args.get("timeout", 60)
                                    print(f"[RUTH DEBUG] [TOOL] Tool Call: 'execute_command' cmd='{command}'")

                                    try:
                                        if working_dir:
                                            working_dir = os.path.expanduser(working_dir)
                                        process = await asyncio.create_subprocess_shell(
                                            command,
                                            stdout=asyncio.subprocess.PIPE,
                                            stderr=asyncio.subprocess.PIPE,
                                            cwd=working_dir,
                                        )
                                        try:
                                            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                                                process.communicate(), timeout=timeout
                                            )
                                        except asyncio.TimeoutError:
                                            process.kill()
                                            stdout_bytes, stderr_bytes = b"", b""
                                            result_str = f"Command timed out after {timeout}s."
                                        else:
                                            stdout_text = stdout_bytes.decode("utf-8", errors="replace").strip()
                                            stderr_text = stderr_bytes.decode("utf-8", errors="replace").strip()
                                            exit_code = process.returncode

                                            result_parts = [f"Exit code: {exit_code}"]
                                            if stdout_text:
                                                # Truncate very large outputs
                                                if len(stdout_text) > 4000:
                                                    stdout_text = stdout_text[:4000] + "\n... (output truncated)"
                                                result_parts.append(f"STDOUT:\n{stdout_text}")
                                            if stderr_text:
                                                if len(stderr_text) > 2000:
                                                    stderr_text = stderr_text[:2000] + "\n... (stderr truncated)"
                                                result_parts.append(f"STDERR:\n{stderr_text}")
                                            if not stdout_text and not stderr_text:
                                                result_parts.append("(no output)")
                                            result_str = "\n".join(result_parts)
                                    except Exception as e:
                                        result_str = f"Command execution failed: {e}"

                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": result_str}
                                    )
                                    function_responses.append(function_response)

                                elif fc.name == "execute_code":
                                    code = fc.args["code"]
                                    language = fc.args.get("language", "python")
                                    timeout = fc.args.get("timeout", 30)
                                    print(f"[RUTH DEBUG] [TOOL] Tool Call: 'execute_code' lang='{language}'")

                                    if self.sandbox:
                                        result = await self.sandbox.execute(
                                            code=code, language=language, timeout=timeout
                                        )
                                        result_parts = [f"Exit code: {result['return_code']}"]
                                        if result.get("timed_out"):
                                            result_parts.append(f"TIMED OUT after {timeout}s")
                                        if result["stdout"]:
                                            out = result["stdout"]
                                            if len(out) > 4000:
                                                out = out[:4000] + "\n... (truncated)"
                                            result_parts.append(f"STDOUT:\n{out}")
                                        if result["stderr"]:
                                            err = result["stderr"]
                                            if len(err) > 2000:
                                                err = err[:2000] + "\n... (truncated)"
                                            result_parts.append(f"STDERR:\n{err}")
                                        result_parts.append(f"Execution time: {result['execution_time']}s")
                                        result_str = "\n".join(result_parts)
                                    else:
                                        result_str = "Code sandbox is not available."

                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": result_str}
                                    )
                                    function_responses.append(function_response)

                                elif fc.name == "system_info":
                                    print(f"[RUTH DEBUG] [TOOL] Tool Call: 'system_info'")
                                    try:
                                        import platform
                                        import shutil

                                        info_parts = []
                                        info_parts.append(f"OS: {platform.system()} {platform.release()}")
                                        info_parts.append(f"Platform: {platform.platform()}")
                                        info_parts.append(f"Architecture: {platform.machine()}")
                                        info_parts.append(f"Hostname: {platform.node()}")
                                        info_parts.append(f"Python: {platform.python_version()}")

                                        # Disk usage
                                        disk = shutil.disk_usage("/")
                                        info_parts.append(f"Disk: {disk.used // (1024**3)}GB used / {disk.total // (1024**3)}GB total ({disk.free // (1024**3)}GB free)")

                                        # Memory via /proc/meminfo (Linux)
                                        try:
                                            with open("/proc/meminfo", "r") as f:
                                                meminfo = f.read()
                                            for line in meminfo.split("\n"):
                                                if line.startswith("MemTotal:") or line.startswith("MemAvailable:"):
                                                    info_parts.append(line.strip())
                                        except FileNotFoundError:
                                            pass

                                        # CPU info
                                        cpu_count = os.cpu_count()
                                        info_parts.append(f"CPU cores: {cpu_count}")

                                        # Load average (Linux/Mac)
                                        try:
                                            load = os.getloadavg()
                                            info_parts.append(f"Load average: {load[0]:.2f}, {load[1]:.2f}, {load[2]:.2f}")
                                        except (OSError, AttributeError):
                                            pass

                                        # Current user
                                        info_parts.append(f"User: {os.environ.get('USER', 'unknown')}")
                                        info_parts.append(f"Home: {os.path.expanduser('~')}")
                                        info_parts.append(f"CWD: {os.getcwd()}")

                                        result_str = "\n".join(info_parts)
                                    except Exception as e:
                                        result_str = f"Failed to get system info: {e}"

                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": result_str}
                                    )
                                    function_responses.append(function_response)

                                # --- MEMORY TOOLS ---

                                elif fc.name == "recall_memory":
                                    query = fc.args["query"]
                                    top_k = fc.args.get("top_k", 5)
                                    print(f"[RUTH DEBUG] [TOOL] Tool Call: 'recall_memory' query='{query}'")

                                    if self.memory_manager:
                                        try:
                                            context = await self.memory_manager.get_relevant_context(query, top_k=top_k)
                                            result_str = context if context else "No relevant memories found."
                                        except Exception as e:
                                            result_str = f"Memory recall failed: {e}"
                                    else:
                                        result_str = "Memory system is not available."

                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": result_str}
                                    )
                                    function_responses.append(function_response)

                                elif fc.name == "store_memory":
                                    content = fc.args["content"]
                                    memory_type = fc.args.get("memory_type", "semantic")
                                    print(f"[RUTH DEBUG] [TOOL] Tool Call: 'store_memory' type='{memory_type}'")

                                    if self.memory_manager:
                                        try:
                                            embedding = await self.memory_manager._get_embedding(content)
                                            if memory_type == "episodic":
                                                self.memory_manager.episodic.add(content, embedding=embedding)
                                            elif memory_type == "procedural":
                                                self.memory_manager.procedural.add(content, embedding=embedding)
                                            else:
                                                self.memory_manager.semantic.add(content, embedding=embedding)
                                            result_str = f"Stored to {memory_type} memory: {content[:100]}..."
                                        except Exception as e:
                                            result_str = f"Failed to store memory: {e}"
                                    else:
                                        result_str = "Memory system is not available."

                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": result_str}
                                    )
                                    function_responses.append(function_response)

                                # --- DOCUMENT TOOLS ---

                                elif fc.name == "read_document":
                                    path = fc.args["path"]
                                    max_pages = fc.args.get("max_pages", 50)
                                    print(f"[RUTH DEBUG] [TOOL] Tool Call: 'read_document' path='{path}'")

                                    result_str = await self._read_document(path, max_pages)

                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": result_str}
                                    )
                                    function_responses.append(function_response)

                                elif fc.name == "study_document":
                                    path = fc.args["path"]
                                    focus = fc.args.get("focus", "")
                                    print(f"[RUTH DEBUG] [TOOL] Tool Call: 'study_document' path='{path}'")

                                    doc_content = await self._read_document(path, max_pages=50)
                                    if doc_content.startswith("Error"):
                                        result_str = doc_content
                                    elif self.memory_manager:
                                        try:
                                            focus_instruction = f" Focus on: {focus}" if focus else ""
                                            extraction_prompt = (
                                                f"Extract key facts, concepts, and procedures from this document.{focus_instruction}\n\n"
                                                f"Document content:\n{doc_content[:8000]}"
                                            )
                                            extracted = await self.memory_manager.extractor.extract(extraction_prompt)

                                            stored_count = 0
                                            if extracted.get("summary"):
                                                emb = await self.memory_manager._get_embedding(extracted["summary"])
                                                self.memory_manager.episodic.add(f"Studied document '{path}': {extracted['summary']}", embedding=emb)
                                                stored_count += 1

                                            for fact in extracted.get("facts", []):
                                                emb = await self.memory_manager._get_embedding(fact)
                                                self.memory_manager.semantic.add(fact, embedding=emb)
                                                stored_count += 1

                                            for proc in extracted.get("procedures", []):
                                                emb = await self.memory_manager._get_embedding(proc)
                                                self.memory_manager.procedural.add(proc, embedding=emb)
                                                stored_count += 1

                                            result_str = f"Studied '{path}' -- extracted and stored {stored_count} memories."
                                        except Exception as e:
                                            result_str = f"Study failed during extraction: {e}"
                                    else:
                                        result_str = f"Document read successfully ({len(doc_content)} chars) but memory system is not available for storage."

                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": result_str}
                                    )
                                    function_responses.append(function_response)

                                # --- WEB SEARCH TOOL ---

                                elif fc.name == "search_web":
                                    query = fc.args["query"]
                                    num_results = fc.args.get("num_results", 5)
                                    print(f"[RUTH DEBUG] [TOOL] Tool Call: 'search_web' query='{query}'")
                                    result_str = await self._search_web(query, num_results)
                                    function_response = types.FunctionResponse(
                                        id=fc.id, name=fc.name, response={"result": result_str}
                                    )
                                    function_responses.append(function_response)

                                # --- SCHEDULER / MONITOR / ALERT TOOLS ---

                                elif fc.name == "schedule_task":
                                    import json as _json
                                    name = fc.args["name"]
                                    sched_type = fc.args["schedule_type"]
                                    sched_value = fc.args["schedule_value"]
                                    tool_name = fc.args["tool_name"]
                                    tool_args_str = fc.args.get("tool_args", "{}")
                                    try:
                                        tool_args = _json.loads(tool_args_str) if isinstance(tool_args_str, str) else tool_args_str
                                    except _json.JSONDecodeError:
                                        tool_args = {}
                                    print(f"[RUTH DEBUG] [TOOL] Tool Call: 'schedule_task' name='{name}'")
                                    if self.task_scheduler:
                                        try:
                                            task = self.task_scheduler.add_task(
                                                name=name, schedule_type=sched_type, schedule_value=sched_value,
                                                tool_name=tool_name, tool_args=tool_args, enabled=True,
                                            )
                                            result_str = f"Scheduled task '{name}' created. Type: {sched_type}, Value: {sched_value}, Tool: {tool_name}."
                                        except Exception as e:
                                            result_str = f"Failed to create scheduled task: {e}"
                                    else:
                                        result_str = "Task scheduler is not available."
                                    function_response = types.FunctionResponse(id=fc.id, name=fc.name, response={"result": result_str})
                                    function_responses.append(function_response)

                                elif fc.name == "add_monitor":
                                    name = fc.args["name"]
                                    target_type = fc.args["target_type"]
                                    address = fc.args["address"]
                                    interval = fc.args.get("interval", 60)
                                    print(f"[RUTH DEBUG] [TOOL] Tool Call: 'add_monitor' name='{name}' type='{target_type}'")
                                    if self.heartbeat_monitor:
                                        try:
                                            self.heartbeat_monitor.add_target(
                                                name=name, target_type=target_type, address=address, interval=interval,
                                            )
                                            result_str = f"Monitoring target '{name}' added. Type: {target_type}, Address: {address}, Interval: {interval}s."
                                        except Exception as e:
                                            result_str = f"Failed to add monitor: {e}"
                                    else:
                                        result_str = "Heartbeat monitor is not available."
                                    function_response = types.FunctionResponse(id=fc.id, name=fc.name, response={"result": result_str})
                                    function_responses.append(function_response)

                                elif fc.name == "create_alert":
                                    import json as _json
                                    name = fc.args["name"]
                                    condition_type = fc.args["condition_type"]
                                    condition_str = fc.args["condition_config"]
                                    action = fc.args.get("action", "notify")
                                    try:
                                        condition_config = _json.loads(condition_str) if isinstance(condition_str, str) else condition_str
                                    except _json.JSONDecodeError:
                                        condition_config = {}
                                    print(f"[RUTH DEBUG] [TOOL] Tool Call: 'create_alert' name='{name}'")
                                    if self.alert_manager:
                                        try:
                                            self.alert_manager.add_rule(
                                                name=name, condition_type=condition_type,
                                                condition_config=condition_config, action=action, enabled=True,
                                            )
                                            result_str = f"Alert rule '{name}' created. Condition: {condition_type}, Action: {action}."
                                        except Exception as e:
                                            result_str = f"Failed to create alert: {e}"
                                    else:
                                        result_str = "Alert manager is not available."
                                    function_response = types.FunctionResponse(id=fc.id, name=fc.name, response={"result": result_str})
                                    function_responses.append(function_response)

                                # --- SECURITY TOOLS ---

                                elif fc.name == "shodan_search":
                                    query = fc.args["query"]
                                    max_results = fc.args.get("max_results", 10)
                                    print(f"[RUTH DEBUG] [TOOL] Tool Call: 'shodan_search' query='{query}'")
                                    result_str = await self._shodan_search(query, max_results)
                                    function_response = types.FunctionResponse(id=fc.id, name=fc.name, response={"result": result_str})
                                    function_responses.append(function_response)

                                elif fc.name == "shodan_host":
                                    ip = fc.args["ip"]
                                    print(f"[RUTH DEBUG] [TOOL] Tool Call: 'shodan_host' ip='{ip}'")
                                    result_str = await self._shodan_host(ip)
                                    function_response = types.FunctionResponse(id=fc.id, name=fc.name, response={"result": result_str})
                                    function_responses.append(function_response)

                                elif fc.name == "nmap_scan":
                                    target = fc.args["target"]
                                    ports = fc.args.get("ports", "")
                                    scan_type = fc.args.get("scan_type", "quick")
                                    print(f"[RUTH DEBUG] [TOOL] Tool Call: 'nmap_scan' target='{target}'")
                                    result_str = await self._nmap_scan(target, ports, scan_type)
                                    function_response = types.FunctionResponse(id=fc.id, name=fc.name, response={"result": result_str})
                                    function_responses.append(function_response)

                                elif fc.name == "port_scan":
                                    host = fc.args["host"]
                                    ports_str = fc.args.get("ports", "21,22,23,25,53,80,110,143,443,445,993,995,3306,3389,5432,8080,8443")
                                    timeout = fc.args.get("timeout", 1)
                                    print(f"[RUTH DEBUG] [TOOL] Tool Call: 'port_scan' host='{host}'")
                                    result_str = await self._port_scan(host, ports_str, timeout)
                                    function_response = types.FunctionResponse(id=fc.id, name=fc.name, response={"result": result_str})
                                    function_responses.append(function_response)

                                # --- MCP TOOLS ---

                                elif fc.name == "mcp_connect":
                                    name = fc.args["name"]
                                    command = fc.args.get("command", "")
                                    url = fc.args.get("url", "")
                                    print(f"[RUTH DEBUG] [TOOL] Tool Call: 'mcp_connect' name='{name}'")
                                    if self.mcp_manager:
                                        result_str = await self.mcp_manager.connect(name, command=command, url=url)
                                    else:
                                        result_str = "MCP client manager is not available. Install: pip install mcp"
                                    function_response = types.FunctionResponse(id=fc.id, name=fc.name, response={"result": result_str})
                                    function_responses.append(function_response)

                                elif fc.name == "mcp_list_tools":
                                    print(f"[RUTH DEBUG] [TOOL] Tool Call: 'mcp_list_tools'")
                                    if self.mcp_manager:
                                        result_str = await self.mcp_manager.list_all_tools()
                                    else:
                                        result_str = "MCP client manager is not available."
                                    function_response = types.FunctionResponse(id=fc.id, name=fc.name, response={"result": result_str})
                                    function_responses.append(function_response)

                                elif fc.name == "mcp_execute":
                                    import json as _json
                                    server_name = fc.args["server_name"]
                                    tool_name = fc.args["tool_name"]
                                    args_str = fc.args.get("arguments", "{}")
                                    try:
                                        arguments = _json.loads(args_str) if isinstance(args_str, str) else args_str
                                    except _json.JSONDecodeError:
                                        arguments = {}
                                    print(f"[RUTH DEBUG] [TOOL] Tool Call: 'mcp_execute' server='{server_name}' tool='{tool_name}'")
                                    if self.mcp_manager:
                                        result_str = await self.mcp_manager.execute_tool(server_name, tool_name, arguments)
                                    else:
                                        result_str = "MCP client manager is not available."
                                    function_response = types.FunctionResponse(id=fc.id, name=fc.name, response={"result": result_str})
                                    function_responses.append(function_response)

                                # --- MESSAGING TOOLS ---

                                elif fc.name == "send_message":
                                    platform = fc.args["platform"]
                                    channel = fc.args["channel"]
                                    text = fc.args["text"]
                                    print(f"[RUTH DEBUG] [TOOL] Tool Call: 'send_message' platform='{platform}'")
                                    if self.message_broker:
                                        try:
                                            result = await self.message_broker.send(platform, channel, text)
                                            if result.get("success"):
                                                result_str = f"Message sent to {platform} channel {channel}."
                                            else:
                                                result_str = f"Failed to send message: {result.get('error', 'unknown error')}"
                                        except Exception as e:
                                            result_str = f"Messaging error: {e}"
                                    else:
                                        result_str = "Message broker is not available."
                                    function_response = types.FunctionResponse(id=fc.id, name=fc.name, response={"result": result_str})
                                    function_responses.append(function_response)

                                elif fc.name == "list_platforms":
                                    print(f"[RUTH DEBUG] [TOOL] Tool Call: 'list_platforms'")
                                    if self.message_broker:
                                        platforms = self.message_broker.list_adapters()
                                        if platforms:
                                            lines = [f"- {p['platform']}: {'connected' if p['connected'] else 'disconnected'}" for p in platforms]
                                            result_str = "Connected messaging platforms:\n" + "\n".join(lines)
                                        else:
                                            result_str = "No messaging platforms registered."
                                    else:
                                        result_str = "Message broker is not available."
                                    function_response = types.FunctionResponse(id=fc.id, name=fc.name, response={"result": result_str})
                                    function_responses.append(function_response)

                                # --- AUTONOMOUS PLANNER ---

                                elif fc.name == "plan_and_execute":
                                    task_desc = fc.args["task"]
                                    print(f"[RUTH DEBUG] [TOOL] Tool Call: 'plan_and_execute' task='{task_desc[:80]}'")
                                    result_str = f"Planning task: {task_desc}. I will break this into steps and execute them sequentially using my available tools. Beginning now."
                                    function_response = types.FunctionResponse(id=fc.id, name=fc.name, response={"result": result_str})
                                    function_responses.append(function_response)

                        if function_responses:
                            await self.session.send_tool_response(function_responses=function_responses)
                
                # Turn/Response Loop Finished
                self.flush_chat()

                while not self.audio_in_queue.empty():
                    self.audio_in_queue.get_nowait()
        except Exception as e:
            print(f"Error in receive_audio: {e}")
            traceback.print_exc()
            # CRITICAL: Re-raise to crash the TaskGroup and trigger outer loop reconnect
            raise e

    async def play_audio(self):
        # Resolve output device: explicit > pulse > system default
        output_idx = self.output_device_index
        if output_idx is None:
            pulse_idx = self._find_pulse_device(need_input=False)
            if pulse_idx is not None:
                output_idx = pulse_idx
                print(f"[RUTH] Auto-selected PulseAudio output device [{pulse_idx}]")

        try:
            stream = await asyncio.to_thread(
                pya.open,
                format=FORMAT,
                channels=CHANNELS,
                rate=RECEIVE_SAMPLE_RATE,
                output=True,
                output_device_index=output_idx,
            )
            print(f"[RUTH] Audio output stream opened on device [{output_idx}]")
        except OSError as e:
            print(f"[RUTH] [ERR] Failed to open audio output stream on device {output_idx}: {e}")
            print("[RUTH] [WARN] Audio playback disabled. Ruth will not produce sound.")
            while True:
                bytestream = await self.audio_in_queue.get()
                if self.on_audio_data:
                    self.on_audio_data(bytestream)
            return

        while True:
            bytestream = await self.audio_in_queue.get()
            if self.on_audio_data:
                self.on_audio_data(bytestream)
            await asyncio.to_thread(stream.write, bytestream)

    async def get_frames(self):
        cap = await asyncio.to_thread(cv2.VideoCapture, 0, cv2.CAP_AVFOUNDATION)
        while True:
            if self.paused:
                await asyncio.sleep(0.1)
                continue
            frame = await asyncio.to_thread(self._get_frame, cap)
            if frame is None:
                break
            await asyncio.sleep(1.0)
            if self.out_queue:
                await self.out_queue.put(frame)
        cap.release()

    def _get_frame(self, cap):
        ret, frame = cap.read()
        if not ret:
            return None
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = PIL.Image.fromarray(frame_rgb)
        img.thumbnail([1024, 1024])
        image_io = io.BytesIO()
        img.save(image_io, format="jpeg")
        image_io.seek(0)
        image_bytes = image_io.read()
        return {"mime_type": "image/jpeg", "data": base64.b64encode(image_bytes).decode()}

    async def _get_screen(self):
        pass 
    async def get_screen(self):
         pass

    async def run(self, start_message=None):
        retry_delay = 1
        is_reconnect = False
        consecutive_failures = 0
        
        while not self.stop_event.is_set():
            try:
                connection_start = asyncio.get_event_loop().time()
                print(f"[RUTH DEBUG] [CONNECT] Connecting to Gemini Live API...")
                async with (
                    client.aio.live.connect(model=MODEL, config=config) as session,
                    asyncio.TaskGroup() as tg,
                ):
                    self.session = session

                    self.audio_in_queue = asyncio.Queue()
                    self.out_queue = asyncio.Queue(maxsize=10)

                    tg.create_task(self.send_realtime())
                    tg.create_task(self.listen_audio())
                    # tg.create_task(self._process_video_queue()) # Removed in favor of VAD

                    if self.video_mode == "camera":
                        tg.create_task(self.get_frames())
                    elif self.video_mode == "screen":
                        tg.create_task(self.get_screen())

                    tg.create_task(self.receive_audio())
                    tg.create_task(self.play_audio())

                    # Handle Startup vs Reconnect Logic
                    if not is_reconnect:
                        if start_message:
                            print(f"[RUTH DEBUG] [INFO] Sending start message: {start_message}")
                            await self.session.send(input=start_message, end_of_turn=True)
                        
                        # Sync Project State
                        if self.on_project_update and self.project_manager:
                            self.on_project_update(self.project_manager.current_project)
                    
                    else:
                        print(f"[RUTH DEBUG] [RECONNECT] Connection restored. (consecutive_failures={consecutive_failures})")

                        if consecutive_failures > 2:
                            # Skip full restoration context to avoid 1008 errors from dead session entities
                            print(f"[RUTH DEBUG] [RECONNECT] Skipping restoration context after {consecutive_failures} consecutive failures.")
                            await self.session.send(
                                input="System: Connection re-established. Ready for new instructions.",
                                end_of_turn=True
                            )
                        else:
                            # Restore Context
                            print(f"[RUTH DEBUG] [RECONNECT] Fetching recent chat history to restore context...")
                            history = self.project_manager.get_recent_chat_history(limit=10)

                            context_msg = "System Notification: Connection was lost and just re-established. Here is the recent chat history to help you resume seamlessly:\n\n"
                            for entry in history:
                                sender = entry.get('sender', 'Unknown')
                                text = entry.get('text', '')
                                context_msg += f"[{sender}]: {text}\n"

                            context_msg += "\nPlease acknowledge the reconnection to the user (e.g. 'I lost connection for a moment, but I'm back...') and resume what you were doing."

                            print(f"[RUTH DEBUG] [RECONNECT] Sending restoration context to model...")
                            await self.session.send(input=context_msg, end_of_turn=True)
                    
                    # Wait until stop event, or until the session task group exits (which happens on error)
                    # Actually, the TaskGroup context manager will exit if any tasks fail/cancel.
                    # We need to keep this block alive.
                    # The original code just waited on stop_event, but that doesn't account for session death.
                    # We should rely on the TaskGroup raising an exception when subtasks fail (like receive_audio).
                    
                    # However, since receive_audio is a task in the group, if it crashes (connection closed), 
                    # the group will cancel others and exit. We catch that exit below.
                    
                    # We can await stop_event, but if the connection dies, receive_audio crashes -> group closes -> we exit `async with` -> restart loop.
                    # To ensure we don't block indefinitely if connection dies silently (unlikely with receive_audio), we just wait.
                    await self.stop_event.wait()

            except asyncio.CancelledError:
                print(f"[RUTH DEBUG] [STOP] Main loop cancelled.")
                break
                
            except Exception as e:
                # This catches the ExceptionGroup from TaskGroup or direct exceptions
                print(f"[RUTH DEBUG] [ERR] Connection Error: {e}")

                if self.stop_event.is_set():
                    break

                # If the session was alive for >30s, it was a real session -- reset failure count
                connection_duration = asyncio.get_event_loop().time() - connection_start
                if connection_duration > 30:
                    consecutive_failures = 0
                    print(f"[RUTH DEBUG] [RETRY] Session lasted {connection_duration:.0f}s, resetting failure count.")

                consecutive_failures += 1
                retry_delay = min(2 ** consecutive_failures, 60)
                print(f"[RUTH DEBUG] [RETRY] Reconnecting in {retry_delay}s (attempt {consecutive_failures})...")
                await asyncio.sleep(retry_delay)
                is_reconnect = True
                
            finally:
                # Cleanup before retry
                if hasattr(self, 'audio_stream') and self.audio_stream:
                    try:
                        self.audio_stream.close()
                    except: 
                        pass

def get_input_devices():
    p = pyaudio.PyAudio()
    info = p.get_host_api_info_by_index(0)
    numdevices = info.get('deviceCount')
    devices = []
    for i in range(0, numdevices):
        if (p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
            devices.append((i, p.get_device_info_by_host_api_device_index(0, i).get('name')))
    p.terminate()
    return devices

def get_output_devices():
    p = pyaudio.PyAudio()
    info = p.get_host_api_info_by_index(0)
    numdevices = info.get('deviceCount')
    devices = []
    for i in range(0, numdevices):
        if (p.get_device_info_by_host_api_device_index(0, i).get('maxOutputChannels')) > 0:
            devices.append((i, p.get_device_info_by_host_api_device_index(0, i).get('name')))
    p.terminate()
    return devices

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        type=str,
        default=DEFAULT_MODE,
        help="pixels to stream from",
        choices=["camera", "screen", "none"],
    )
    args = parser.parse_args()
    main = AudioLoop(video_mode=args.mode)
    asyncio.run(main.run())