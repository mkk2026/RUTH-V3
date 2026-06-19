import sys
import asyncio

# Fix for asyncio subprocess support on Windows
# MUST BE SET BEFORE OTHER IMPORTS
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import socketio
import uvicorn
from fastapi import FastAPI
import asyncio
import threading
import sys
import os
import json
from datetime import datetime
from pathlib import Path



# Ensure we can import ruth
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    import ruth
except ImportError as e:
    print(f"[SERVER] ruth module unavailable (missing dep: {e}). Voice features disabled.")
    ruth = None

try:
    from authenticator import FaceAuthenticator
except ImportError as e:
    print(f"[SERVER] FaceAuthenticator unavailable (missing dep: {e}). Face auth disabled.")
    FaceAuthenticator = None

try:
    from kasa_agent import KasaAgent
except ImportError as e:
    print(f"[SERVER] KasaAgent unavailable (missing dep: {e}). Smart home disabled.")
    KasaAgent = None

from config import AppConfig
from providers.router import ModelRouter
from terminal_manager import TerminalManager
from scheduler import TaskScheduler
from heartbeat import HeartbeatMonitor
from alerts import AlertManager
from integrations.registry import IntegrationRegistry
from messaging.broker import MessageBroker
from plugins.registry import PluginRegistry
from plugins.loader import PluginLoader
from memory.manager import MemoryManager
from sandbox import CodeSandbox

# Create a Socket.IO server
# CORS origins are configurable via RUTH_CORS_ORIGINS (comma-separated).
# Defaults to '*' for local development; set explicit origins if ever exposed.
_cors_env = os.environ.get("RUTH_CORS_ORIGINS", "*").strip()
_cors_origins = "*" if _cors_env in ("", "*") else [o.strip() for o in _cors_env.split(",") if o.strip()]
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins=_cors_origins)
app = FastAPI()
app_socketio = socketio.ASGIApp(sio, app)

import signal

# --- SHUTDOWN HANDLER ---
def signal_handler(sig, frame):
    print(f"\n[SERVER] Caught signal {sig}. Exiting gracefully...")
    if audio_loop:
        try:
            print("[SERVER] Stopping Audio Loop...")
            audio_loop.stop() 
        except:
            pass
    print("[SERVER] Force exiting...")
    os._exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# --- Configuration ---
app_config = AppConfig("settings.json")
SETTINGS = app_config.get_all()

# --- Model Router ---
model_router = ModelRouter(
    model_config=app_config.model_config,
    api_keys=app_config.get_api_keys(),
)

# --- Global State ---
audio_loop = None
loop_task = None
authenticator = None
kasa_agent = KasaAgent(known_devices=SETTINGS.get("kasa_devices")) if KasaAgent else None

# --- New Module Instances (graceful degradation if deps missing) ---
try:
    terminal_manager = TerminalManager()
except Exception as e:
    print(f"[SERVER] TerminalManager unavailable: {e}")
    terminal_manager = None

async def _handle_scheduled_task(task):
    """Execute a scheduled task via Ruth's session or direct subprocess."""
    tool_name = task.get("tool_name", "")
    tool_args = task.get("tool_args", {})
    task_name = task.get("name", "unnamed")
    print(f"[SERVER] [SCHEDULER] Executing task '{task_name}': {tool_name}")

    # Route through Ruth's active session if available
    if audio_loop and audio_loop.session:
        try:
            msg = f"System: Scheduled task '{task_name}' triggered. Execute tool '{tool_name}' with arguments: {tool_args}"
            await audio_loop.session.send(input=msg, end_of_turn=True)
            print(f"[SERVER] [SCHEDULER] Task '{task_name}' sent to Ruth.")
            return
        except Exception as e:
            print(f"[SERVER] [SCHEDULER] Failed to route through Ruth: {e}")

    # Fallback: execute command directly
    if tool_name == "execute_command" and tool_args.get("command"):
        try:
            proc = await asyncio.create_subprocess_shell(
                tool_args["command"],
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
            print(f"[SERVER] [SCHEDULER] Direct exec result: exit={proc.returncode}")
        except Exception as e:
            print(f"[SERVER] [SCHEDULER] Direct exec failed: {e}")
    else:
        print(f"[SERVER] [SCHEDULER] No active Ruth session and no direct handler for '{tool_name}'")

    # Notify frontend
    try:
        await sio.emit('notifications', [{
            'message': f"Scheduled task '{task_name}' executed ({tool_name})",
            'severity': 'info',
        }])
    except Exception:
        pass

try:
    task_scheduler = TaskScheduler(
        storage_path="~/.ruth/scheduler",
        on_task_execute=_handle_scheduled_task,
    )
except Exception as e:
    print(f"[SERVER] TaskScheduler unavailable: {e}")
    task_scheduler = None

try:
    heartbeat_monitor = HeartbeatMonitor(storage_path="~/.ruth/heartbeat")
except Exception as e:
    print(f"[SERVER] HeartbeatMonitor unavailable: {e}")
    heartbeat_monitor = None

try:
    alert_manager = AlertManager(storage_path="~/.ruth/alerts")
except Exception as e:
    print(f"[SERVER] AlertManager unavailable: {e}")
    alert_manager = None

try:
    integration_registry = IntegrationRegistry()
except Exception as e:
    print(f"[SERVER] IntegrationRegistry unavailable: {e}")
    integration_registry = None

try:
    message_broker = MessageBroker()
except Exception as e:
    print(f"[SERVER] MessageBroker unavailable: {e}")
    message_broker = None

try:
    plugin_registry = PluginRegistry()
except Exception as e:
    print(f"[SERVER] PluginRegistry unavailable: {e}")
    plugin_registry = None

try:
    from mcp_client import MCPClientManager
    mcp_manager = MCPClientManager()
except Exception as e:
    print(f"[SERVER] MCPClientManager unavailable: {e}")
    mcp_manager = None

try:
    memory_manager = MemoryManager(storage_path="~/.ruth/memory", router=model_router)
except Exception as e:
    print(f"[SERVER] MemoryManager unavailable: {e}")
    memory_manager = None

try:
    code_sandbox = CodeSandbox()
except Exception as e:
    print(f"[SERVER] CodeSandbox unavailable: {e}")
    code_sandbox = None

def save_settings():
    app_config.update(SETTINGS)

def load_settings():
    global SETTINGS
    app_config.load()
    SETTINGS = app_config.get_all()
# tool_permissions is now SETTINGS["tool_permissions"]

@app.on_event("startup")
async def startup_event():
    import sys
    print(f"[SERVER DEBUG] Startup Event Triggered")
    print(f"[SERVER DEBUG] Python Version: {sys.version}")
    try:
        loop = asyncio.get_running_loop()
        print(f"[SERVER DEBUG] Running Loop: {type(loop)}")
        policy = asyncio.get_event_loop_policy()
        print(f"[SERVER DEBUG] Current Policy: {type(policy)}")
    except Exception as e:
        print(f"[SERVER DEBUG] Error checking loop: {e}")

    if kasa_agent:
        print("[SERVER] Startup: Initializing Kasa Agent...")
        await kasa_agent.initialize()
    else:
        print("[SERVER] Startup: KasaAgent not available, skipping.")

    # --- Load Plugins ---
    if plugin_registry:
        try:
            from plugins.base import PluginContext
            loader = PluginLoader(plugin_registry)
            plugin_context = PluginContext(
                router=model_router,
                config=app_config,
                emit=lambda event, data: asyncio.create_task(sio.emit(event, data)),
            )
            await loader.load_all(context=plugin_context)
            print(f"[SERVER] Loaded {len(plugin_registry.list_plugins())} plugins")
        except Exception as e:
            print(f"[SERVER] Plugin loading failed: {e}")

    # --- Start Scheduler Loop ---
    if task_scheduler:
        try:
            asyncio.create_task(task_scheduler.start())
            print("[SERVER] TaskScheduler loop started")
        except Exception as e:
            print(f"[SERVER] TaskScheduler start failed: {e}")

    # --- Start Heartbeat Monitor ---
    if heartbeat_monitor:
        try:
            async def on_heartbeat_change(target, old_status, new_status):
                target_name = target.get('name', target.get('id', 'unknown'))
                await sio.emit('heartbeat_status', {
                    'target': target,
                    'old_status': old_status,
                    'new_status': new_status,
                })
                if alert_manager and new_status == 'down':
                    alert_manager.add_notification(
                        f"Heartbeat target '{target_name}' is DOWN",
                        severity="error"
                    )
                    await sio.emit('notifications', alert_manager.get_notifications())

            heartbeat_monitor._on_status_change = on_heartbeat_change
            asyncio.create_task(heartbeat_monitor.start())
            print("[SERVER] HeartbeatMonitor loop started")
        except Exception as e:
            print(f"[SERVER] HeartbeatMonitor start failed: {e}")

    # --- Start Alert Evaluation Loop ---
    if alert_manager:
        async def _alert_evaluation_loop():
            """Periodically collect system metrics and evaluate alert rules."""
            import shutil
            while True:
                try:
                    await asyncio.sleep(60)
                    # Collect system metrics
                    disk = shutil.disk_usage("/")
                    context = {
                        "disk": {
                            "used_percent": round((disk.used / disk.total) * 100, 1),
                            "free_gb": round(disk.free / (1024**3), 1),
                        },
                    }
                    try:
                        load = os.getloadavg()
                        context["cpu"] = {"load_1m": load[0], "load_5m": load[1], "load_15m": load[2]}
                    except (OSError, AttributeError):
                        pass
                    try:
                        with open("/proc/meminfo", "r") as f:
                            for line in f:
                                if line.startswith("MemTotal:"):
                                    context.setdefault("memory", {})["total_kb"] = int(line.split()[1])
                                elif line.startswith("MemAvailable:"):
                                    context.setdefault("memory", {})["available_kb"] = int(line.split()[1])
                        mem = context.get("memory", {})
                        if mem.get("total_kb") and mem.get("available_kb"):
                            mem["used_percent"] = round((1 - mem["available_kb"] / mem["total_kb"]) * 100, 1)
                    except FileNotFoundError:
                        pass

                    await alert_manager.check_rules(context)

                    new_notifications = alert_manager.get_notifications(limit=5)
                    if new_notifications:
                        await sio.emit('notifications', new_notifications)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    print(f"[SERVER] Alert evaluation error: {e}")
                    await asyncio.sleep(60)

        asyncio.create_task(_alert_evaluation_loop())
        print("[SERVER] Alert evaluation loop started (60s interval)")

    # --- Wire Messaging Broker ---
    if message_broker:
        async def _handle_incoming_message(msg):
            """Route incoming messages from any platform to Ruth."""
            print(f"[SERVER] [MSG] Incoming from {msg.platform}/{msg.sender}: {msg.text[:80]}")
            response_text = None

            # Try routing through Ruth's active session
            if audio_loop and audio_loop.session:
                try:
                    await audio_loop.session.send(
                        input=f"[Message from {msg.sender} on {msg.platform}]: {msg.text}",
                        end_of_turn=True,
                    )
                    response_text = "(Ruth is processing via voice session)"
                except Exception as e:
                    print(f"[SERVER] [MSG] Failed to route to Ruth session: {e}")
                    response_text = "I'm having trouble processing that right now. Please try again."
            else:
                response_text = "I'm currently offline. I'll respond when I'm back online."

            # Reply on the same platform/channel
            if response_text and msg.thread_id:
                try:
                    await message_broker.send(msg.platform, msg.thread_id, response_text)
                except Exception as e:
                    print(f"[SERVER] [MSG] Reply failed: {e}")

        message_broker.set_handler(_handle_incoming_message)

        # Register Telegram adapter if token is configured
        telegram_token = SETTINGS.get("telegram_bot_token") or os.environ.get("TELEGRAM_BOT_TOKEN")
        if telegram_token:
            try:
                from messaging.telegram_adapter import TelegramAdapter
                telegram_adapter = TelegramAdapter(bot_token=telegram_token)
                message_broker.register_adapter(telegram_adapter)
                print("[SERVER] Telegram adapter registered")
            except Exception as e:
                print(f"[SERVER] Telegram adapter registration failed: {e}")

        # Register Discord adapter if token is configured
        discord_token = SETTINGS.get("discord_bot_token") or os.environ.get("DISCORD_BOT_TOKEN")
        if discord_token:
            try:
                from messaging.discord_adapter import DiscordAdapter
                discord_adapter = DiscordAdapter(bot_token=discord_token)
                message_broker.register_adapter(discord_adapter)
                print("[SERVER] Discord adapter registered")
            except Exception as e:
                print(f"[SERVER] Discord adapter registration failed: {e}")

        # Start all registered adapters
        try:
            results = await message_broker.start_all()
            for platform, success in results.items():
                status = "connected" if success else "failed"
                print(f"[SERVER] Messaging platform '{platform}': {status}")
        except Exception as e:
            print(f"[SERVER] Message broker start failed: {e}")

    # --- Wire Terminal Output Callback ---
    if terminal_manager:
        try:
            async def on_terminal_output(session_id, data):
                await sio.emit('terminal_output', {'session_id': session_id, 'data': data})

            terminal_manager._on_output = on_terminal_output
            print("[SERVER] TerminalManager output callback wired")
        except Exception as e:
            print(f"[SERVER] TerminalManager callback wiring failed: {e}")

@app.get("/status")
async def status():
    return {"status": "running", "service": "R.U.T.H. Backend"}

@sio.event
async def connect(sid, environ):
    print(f"Client connected: {sid}")
    await sio.emit('status', {'msg': 'Connected to R.U.T.H. Backend'}, room=sid)

    global authenticator
    
    # Callback for Auth Status
    async def on_auth_status(is_auth):
        print(f"[SERVER] Auth status change: {is_auth}")
        await sio.emit('auth_status', {'authenticated': is_auth})

    # Callback for Auth Camera Frames
    async def on_auth_frame(frame_b64):
        await sio.emit('auth_frame', {'image': frame_b64})

    # Initialize Authenticator if not already done
    if authenticator is None and FaceAuthenticator is not None:
        authenticator = FaceAuthenticator(
            reference_image_path="reference.jpg",
            on_status_change=on_auth_status,
            on_frame=on_auth_frame
        )
    
    # Check if already authenticated or needs to start
    if authenticator is None:
        print("[SERVER] FaceAuthenticator not available -- auto-authenticating.")
        await sio.emit('auth_status', {'authenticated': True})
    elif authenticator.authenticated:
        await sio.emit('auth_status', {'authenticated': True})
    else:
        # Check Settings for Auth
        if SETTINGS.get("face_auth_enabled", False):
            await sio.emit('auth_status', {'authenticated': False})
            # Start the auth loop in background
            asyncio.create_task(authenticator.start_authentication_loop())
        else:
            # Bypass Auth
            print("Face Auth Disabled. Auto-authenticating.")
            # We don't change authenticator state to true to avoid confusion if re-enabled? 
            # Or we should just tell client it's auth'd.
            await sio.emit('auth_status', {'authenticated': True})

@sio.event
async def disconnect(sid):
    print(f"Client disconnected: {sid}")

@sio.event
async def start_audio(sid, data=None):
    global audio_loop, loop_task
    
    # Optional: Block if not authenticated
    # Only block if auth is ENABLED and not authenticated
    if SETTINGS.get("face_auth_enabled", False):
        if authenticator and not authenticator.authenticated:
            print("Blocked start_audio: Not authenticated.")
            await sio.emit('error', {'msg': 'Authentication Required'})
            return

    print("Starting Audio Loop...")
    
    device_index = None
    device_name = None
    if data:
        device_name = data.get('device_name') or None
        # Only trust the frontend device_index if a real device name was provided
        if device_name:
            device_index = data.get('device_index')
            
    print(f"Using input device: Name='{device_name}', Index={device_index}")
    
    if audio_loop:
        if loop_task and (loop_task.done() or loop_task.cancelled()):
             print("Audio loop task appeared finished/cancelled. Clearing and restarting...")
             audio_loop = None
             loop_task = None
        else:
             print("Audio loop already running. Re-connecting client to session.")
             await sio.emit('status', {'msg': 'R.U.T.H. Already Running'})
             return


    # Callback to send audio data to frontend
    def on_audio_data(data_bytes):
        # We need to schedule this on the event loop
        # This is high frequency, so we might want to downsample or batch if it's too much
        asyncio.create_task(sio.emit('audio_data', {'data': list(data_bytes)}))

    # Callback to send CAL data to frontend
    def on_cad_data(data):
        info = f"{len(data.get('vertices', []))} vertices" if 'vertices' in data else f"{len(data.get('data', ''))} bytes (STL)"
        print(f"Sending CAD data to frontend: {info}")
        asyncio.create_task(sio.emit('cad_data', data))

    # Callback to send Browser data to frontend
    def on_web_data(data):
        print(f"Sending Browser data to frontend: {len(data.get('log', ''))} chars logs")
        asyncio.create_task(sio.emit('browser_frame', data))
        
    # Callback to send Transcription data to frontend
    def on_transcription(data):
        # data = {"sender": "User"|"RUTH", "text": "..."}
        asyncio.create_task(sio.emit('transcription', data))

    # Callback to send Confirmation Request to frontend
    def on_tool_confirmation(data):
        # data = {"id": "uuid", "tool": "tool_name", "args": {...}}
        print(f"Requesting confirmation for tool: {data.get('tool')}")
        asyncio.create_task(sio.emit('tool_confirmation_request', data))

    # Callback to send CAD status to frontend
    def on_cad_status(status):
        # status can be: 
        # - a string like "generating" (from ruth.py handle_cad_request)
        # - a dict with {status, attempt, max_attempts, error} (from CadAgent)
        if isinstance(status, dict):
            print(f"Sending CAD Status: {status.get('status')} (attempt {status.get('attempt')}/{status.get('max_attempts')})")
            asyncio.create_task(sio.emit('cad_status', status))
        else:
            # Legacy: simple string
            print(f"Sending CAD Status: {status}")
            asyncio.create_task(sio.emit('cad_status', {'status': status}))

    # Callback to send CAD thoughts to frontend (streaming)
    def on_cad_thought(thought_text):
        asyncio.create_task(sio.emit('cad_thought', {'text': thought_text}))

    # Callback to send Project Update to frontend
    def on_project_update(project_name):
        print(f"Sending Project Update: {project_name}")
        asyncio.create_task(sio.emit('project_update', {'project': project_name}))

    # Callback to send Device Update to frontend
    def on_device_update(devices):
        # devices is a list of dicts
        print(f"Sending Kasa Device Update: {len(devices)} devices")
        asyncio.create_task(sio.emit('kasa_devices', devices))

    # Callback to send Error to frontend
    def on_error(msg):
        print(f"Sending Error to frontend: {msg}")
        asyncio.create_task(sio.emit('error', {'msg': msg}))

    # Callback for Neural Avatar: a tool is being executed by the model
    def on_tool_call(tool_name, params=None):
        asyncio.create_task(sio.emit('ruth_tool_call', {
            'tool_name': tool_name,
            'description': f'Executing {tool_name}...',
            'params': params or {},
        }))

    # Initialize AudioLoop
    if ruth is None:
        print("[SERVER] ruth module not available -- voice features disabled.")
        await sio.emit('error', {'msg': 'Voice module unavailable (missing dependencies).'})
        return

    try:
        print(f"Initializing AudioLoop with device_index={device_index}")
        audio_loop = ruth.AudioLoop(
            video_mode="none", 
            on_audio_data=on_audio_data,
            on_cad_data=on_cad_data,
            on_web_data=on_web_data,
            on_transcription=on_transcription,
            on_tool_confirmation=on_tool_confirmation,
            on_cad_status=on_cad_status,
            on_cad_thought=on_cad_thought,
            on_project_update=on_project_update,
            on_device_update=on_device_update,
            on_error=on_error,
            on_tool_call=on_tool_call,
            input_device_index=device_index,
            input_device_name=device_name,
            kasa_agent=kasa_agent,
            router=model_router,
            memory_manager=memory_manager,
            sandbox=code_sandbox,
            task_scheduler=task_scheduler,
            heartbeat_monitor=heartbeat_monitor,
            alert_manager=alert_manager,
            message_broker=message_broker,
            mcp_manager=mcp_manager,
        )
        print("AudioLoop initialized successfully.")

        # Apply current permissions
        audio_loop.update_permissions(SETTINGS["tool_permissions"])
        
        # Check initial mute state
        if data and data.get('muted', False):
            print("Starting with Audio Paused")
            audio_loop.set_paused(True)

        print("Creating asyncio task for AudioLoop.run()")
        loop_task = asyncio.create_task(audio_loop.run())
        
        # Add a done callback to catch silent failures in the loop
        def handle_loop_exit(task):
            try:
                task.result()
            except asyncio.CancelledError:
                print("Audio Loop Cancelled")
            except Exception as e:
                print(f"Audio Loop Crashed: {e}")
                # You could emit 'error' here if you have context
        
        loop_task.add_done_callback(handle_loop_exit)
        
        print("Emitting 'R.U.T.H. Started'")
        await sio.emit('status', {'msg': 'R.U.T.H. Started'})

        # Load saved printers
        saved_printers = SETTINGS.get("printers", [])
        if saved_printers and audio_loop.printer_agent:
            print(f"[SERVER] Loading {len(saved_printers)} saved printers...")
            for p in saved_printers:
                audio_loop.printer_agent.add_printer_manually(
                    name=p.get("name", p["host"]),
                    host=p["host"],
                    port=p.get("port", 80),
                    printer_type=p.get("type", "moonraker"),
                    camera_url=p.get("camera_url")
                )
        
        # Start Printer Monitor
        asyncio.create_task(monitor_printers_loop())
        
    except Exception as e:
        print(f"CRITICAL ERROR STARTING RUTH: {e}")
        import traceback
        traceback.print_exc()
        await sio.emit('error', {'msg': f"Failed to start: {str(e)}"})
        audio_loop = None # Ensure we can try again


async def monitor_printers_loop():
    """Background task to query printer status periodically."""
    print("[SERVER] Starting Printer Monitor Loop")
    while audio_loop and audio_loop.printer_agent:
        try:
            agent = audio_loop.printer_agent
            if not agent.printers:
                await asyncio.sleep(5)
                continue
                
            tasks = []
            for host, printer in agent.printers.items():
                if printer.printer_type.value != "unknown":
                    tasks.append(agent.get_print_status(host))
            
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for res in results:
                    if isinstance(res, Exception):
                        pass # Ignore errors for now
                    elif res:
                        # res is PrintStatus object
                        await sio.emit('print_status_update', res.to_dict())
                        
        except asyncio.CancelledError:
            print("[SERVER] Printer Monitor Cancelled")
            break
        except Exception as e:
            print(f"[SERVER] Monitor Loop Error: {e}")
            
        await asyncio.sleep(2) # Update every 2 seconds for responsiveness

@sio.event
async def stop_audio(sid):
    global audio_loop
    if audio_loop:
        audio_loop.stop() 
        print("Stopping Audio Loop")
        audio_loop = None
        await sio.emit('status', {'msg': 'R.U.T.H. Stopped'})

@sio.event
async def pause_audio(sid):
    global audio_loop
    if audio_loop:
        audio_loop.set_paused(True)
        print("Pausing Audio")
        await sio.emit('status', {'msg': 'Audio Paused'})

@sio.event
async def resume_audio(sid):
    global audio_loop
    if audio_loop:
        audio_loop.set_paused(False)
        print("Resuming Audio")
        await sio.emit('status', {'msg': 'Audio Resumed'})

@sio.event
async def confirm_tool(sid, data):
    # data: { "id": "...", "confirmed": True/False }
    request_id = data.get('id')
    confirmed = data.get('confirmed', False)
    
    print(f"[SERVER DEBUG] Received confirmation response for {request_id}: {confirmed}")
    
    if audio_loop:
        audio_loop.resolve_tool_confirmation(request_id, confirmed)
    else:
        print("Audio loop not active, cannot resolve confirmation.")

@sio.event
async def shutdown(sid, data=None):
    """Gracefully shutdown the server when the application closes."""
    global audio_loop, loop_task, authenticator
    
    print("[SERVER] ========================================")
    print("[SERVER] SHUTDOWN SIGNAL RECEIVED FROM FRONTEND")
    print("[SERVER] ========================================")
    
    # Stop audio loop
    if audio_loop:
        print("[SERVER] Stopping Audio Loop...")
        audio_loop.stop()
        audio_loop = None
    
    # Cancel the loop task if running
    if loop_task and not loop_task.done():
        print("[SERVER] Cancelling loop task...")
        loop_task.cancel()
        loop_task = None
    
    # Stop authenticator if running
    if authenticator:
        print("[SERVER] Stopping Authenticator...")
        authenticator.stop()
    
    print("[SERVER] Graceful shutdown complete. Terminating process...")
    
    # Force exit immediately - os._exit bypasses cleanup but ensures termination
    os._exit(0)

@sio.event
async def user_input(sid, data):
    text = data.get('text')
    print(f"[SERVER DEBUG] User input received: '{text}'")
    
    if not audio_loop:
        print("[SERVER DEBUG] [Error] Audio loop is None. Cannot send text.")
        return

    if not audio_loop.session:
        print("[SERVER DEBUG] [Error] Session is None. Cannot send text.")
        return

    if text:
        print(f"[SERVER DEBUG] Sending message to model: '{text}'")
        
        # Log User Input to Project History
        if audio_loop and audio_loop.project_manager:
            audio_loop.project_manager.log_chat("User", text)
            
        # Use the same 'send' method that worked for audio, as 'send_realtime_input' and 'send_client_content' seem unstable in this env
        # INJECT VIDEO FRAME IF AVAILABLE (VAD-style logic for Text Input)
        if audio_loop and audio_loop._latest_image_payload:
            print(f"[SERVER DEBUG] Piggybacking video frame with text input.")
            try:
                # Send frame first
                await audio_loop.session.send(input=audio_loop._latest_image_payload, end_of_turn=False)
            except Exception as e:
                print(f"[SERVER DEBUG] Failed to send piggyback frame: {e}")
                
        # Neural Avatar: signal that RUTH is now processing the query
        await sio.emit('ruth_thinking', {'thought': 'Analyzing query...', 'query': text[:100]})

        try:
            await audio_loop.session.send(input=text, end_of_turn=True)
            print(f"[SERVER DEBUG] Message sent to model successfully.")
        except Exception as e:
            print(f"[SERVER DEBUG] Failed to send text to model: {e}")
            await sio.emit('ruth_response', {"text": "I'm reconnecting to the server. Please try again in a moment.", "sender": "RUTH"})

import json
from datetime import datetime
from pathlib import Path

# ... (imports)

@sio.event
async def video_frame(sid, data):
    # data should contain 'image' which is binary (blob) or base64 encoded
    image_data = data.get('image')
    if image_data and audio_loop:
        # We don't await this because we don't want to block the socket handler
        # But send_frame is async, so we create a task
        asyncio.create_task(audio_loop.send_frame(image_data))

@sio.event
async def save_memory(sid, data):
    try:
        messages = data.get('messages', [])
        if not messages:
            print("No messages to save.")
            return

        # Ensure directory exists
        memory_dir = Path("long_term_memory")
        memory_dir.mkdir(exist_ok=True)

        # Generate filename
        # Use provided filename if available, else timestamp
        provided_name = data.get('filename')
        
        if provided_name:
            # Simple sanitization
            if not provided_name.endswith('.txt'):
                provided_name += '.txt'
            # Prevent directory traversal
            filename = memory_dir / Path(provided_name).name 
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = memory_dir / f"memory_{timestamp}.txt"

        # Write to file
        with open(filename, 'w', encoding='utf-8') as f:
            for msg in messages:
                sender = msg.get('sender', 'Unknown')
                text = msg.get('text', '')
        print(f"Conversation saved to {filename}")
        await sio.emit('status', {'msg': 'Memory Saved Successfully'})

    except Exception as e:
        print(f"Error saving memory: {e}")
        await sio.emit('error', {'msg': f"Failed to save memory: {str(e)}"})

@sio.event
async def upload_memory(sid, data):
    print(f"Received memory upload request")
    try:
        memory_text = data.get('memory', '')
        if not memory_text:
            print("No memory data provided.")
            return

        if not audio_loop:
             print("[SERVER DEBUG] [Error] Audio loop is None. Cannot load memory.")
             await sio.emit('error', {'msg': "System not ready (Audio Loop inactive)"})
             return
        
        if not audio_loop.session:
             print("[SERVER DEBUG] [Error] Session is None. Cannot load memory.")
             await sio.emit('error', {'msg': "System not ready (No active session)"})
             return

        # Send to model
        print("Sending memory context to model...")
        context_msg = f"System Notification: The user has uploaded a long-term memory file. Please load the following context into your understanding. The format is a text log of previous conversations:\n\n{memory_text}"
        
        await audio_loop.session.send(input=context_msg, end_of_turn=True)
        print("Memory context sent successfully.")
        await sio.emit('status', {'msg': 'Memory Loaded into Context'})

    except Exception as e:
        print(f"Error uploading memory: {e}")
        await sio.emit('error', {'msg': f"Failed to upload memory: {str(e)}"})

@sio.event
async def discover_kasa(sid):
    print(f"Received discover_kasa request")
    if not kasa_agent:
        await sio.emit('error', {'msg': 'Smart home module not available'}, room=sid)
        return
    try:
        devices = await kasa_agent.discover_devices()
        await sio.emit('kasa_devices', devices)
        await sio.emit('status', {'msg': f"Found {len(devices)} Kasa devices"})
        
        # Save to settings
        # devices is a list of full device info dicts. minimizing for storage.
        saved_devices = []
        for d in devices:
            saved_devices.append({
                "ip": d["ip"],
                "alias": d["alias"],
                "model": d["model"]
            })
        
        # Merge with existing to preserve any manual overrides? 
        # For now, just overwrite with latest scan result + previously known if we want to be fancy,
        # but user asked for "Any new devices that are scanned are added there".
        # A simple full persistence of current state is safest.
        SETTINGS["kasa_devices"] = saved_devices
        save_settings()
        print(f"[SERVER] Saved {len(saved_devices)} Kasa devices to settings.")
        
    except Exception as e:
        print(f"Error discovering kasa: {e}")
        await sio.emit('error', {'msg': f"Kasa Discovery Failed: {str(e)}"})

@sio.event
async def iterate_cad(sid, data):
    # data: { prompt: "make it bigger" }
    prompt = data.get('prompt')
    print(f"Received iterate_cad request: '{prompt}'")
    
    if not audio_loop or not audio_loop.cad_agent:
        await sio.emit('error', {'msg': "CAD Agent not available"})
        return

    try:
        # Notify user work has started
        await sio.emit('status', {'msg': 'Iterating design...'})
        await sio.emit('cad_status', {'status': 'generating'})
        
        # Call the agent with project path
        cad_output_dir = str(audio_loop.project_manager.get_current_project_path() / "cad")
        result = await audio_loop.cad_agent.iterate_prototype(prompt, output_dir=cad_output_dir)
        
        if result:
            info = f"{len(result.get('data', ''))} bytes (STL)"
            print(f"Sending updated CAD data: {info}")
            await sio.emit('cad_data', result)
            # Save to Project
            if 'file_path' in result:
                saved_path = audio_loop.project_manager.save_cad_artifact(result['file_path'], prompt)
                if saved_path:
                    print(f"[SERVER] Saved iterated CAD to {saved_path}")

            await sio.emit('status', {'msg': 'Design updated'})
        else:
            await sio.emit('error', {'msg': 'Failed to update design'})
            
    except Exception as e:
        print(f"Error iterating CAD: {e}")
        await sio.emit('error', {'msg': f"Iteration Error: {str(e)}"})

@sio.event
async def generate_cad(sid, data):
    # data: { prompt: "make a cube" }
    prompt = data.get('prompt')
    print(f"Received generate_cad request: '{prompt}'")
    
    if not audio_loop or not audio_loop.cad_agent:
        await sio.emit('error', {'msg': "CAD Agent not available"})
        return

    try:
        await sio.emit('status', {'msg': 'Generating new design...'})
        await sio.emit('cad_status', {'status': 'generating'})
        
        # Use generate_prototype based on prompt with project path
        cad_output_dir = str(audio_loop.project_manager.get_current_project_path() / "cad")
        result = await audio_loop.cad_agent.generate_prototype(prompt, output_dir=cad_output_dir)
        
        if result:
            info = f"{len(result.get('data', ''))} bytes (STL)"
            print(f"Sending newly generated CAD data: {info}")
            await sio.emit('cad_data', result)


            # Save to Project
            if 'file_path' in result:
                saved_path = audio_loop.project_manager.save_cad_artifact(result['file_path'], prompt)
                if saved_path:
                    print(f"[SERVER] Saved generated CAD to {saved_path}")

            await sio.emit('status', {'msg': 'Design generated'})
        else:
            await sio.emit('error', {'msg': 'Failed to generate design'})
            
    except Exception as e:
        print(f"Error generating CAD: {e}")
        await sio.emit('error', {'msg': f"Generation Error: {str(e)}"})

@sio.event
async def prompt_web_agent(sid, data):
    # data: { prompt: "find xyz" }
    prompt = data.get('prompt')
    print(f"Received web agent prompt: '{prompt}'")
    
    if not audio_loop or not audio_loop.web_agent:
        await sio.emit('error', {'msg': "Web Agent not available"})
        return

    try:
        await sio.emit('status', {'msg': 'Web Agent running...'})
        
        # We assume web_agent has a run method or similar.
        # This might block the loop if not strictly async or offloaded.
        # Ideally web_agent.run is async.
        # And it should emit 'browser_snap' and logs automatically via hooks if setup.
        
        # We might need to launch this as a task if it's long running?
        # asyncio.create_task(audio_loop.web_agent.run(prompt))
        # But we want to catch errors here.
        
        # Based on typical agent design, run() is the entry point.
        await audio_loop.web_agent.run(prompt)
        
        await sio.emit('status', {'msg': 'Web Agent finished'})
        
    except Exception as e:
        print(f"Error running Web Agent: {e}")
        await sio.emit('error', {'msg': f"Web Agent Error: {str(e)}"})

@sio.event
async def discover_printers(sid):
    print("Received discover_printers request")
    
    # If audio_loop isn't ready yet, return saved printers from settings
    if not audio_loop or not audio_loop.printer_agent:
        saved_printers = SETTINGS.get("printers", [])
        if saved_printers:
            # Convert saved printers to the expected format
            printer_list = []
            for p in saved_printers:
                printer_list.append({
                    "name": p.get("name", p["host"]),
                    "host": p["host"],
                    "port": p.get("port", 80),
                    "printer_type": p.get("type", "unknown"),
                    "camera_url": p.get("camera_url")
                })
            print(f"[SERVER] Returning {len(printer_list)} saved printers (audio_loop not ready)")
            await sio.emit('printer_list', printer_list)
            return
        else:
            await sio.emit('printer_list', [])
            await sio.emit('status', {'msg': "Connect to R.U.T.H. to enable printer discovery"})
            return
        
    try:
        printers = await audio_loop.printer_agent.discover_printers()
        await sio.emit('printer_list', printers)
        await sio.emit('status', {'msg': f"Found {len(printers)} printers"})
    except Exception as e:
        print(f"Error discovering printers: {e}")
        await sio.emit('error', {'msg': f"Printer Discovery Failed: {str(e)}"})

@sio.event
async def add_printer(sid, data):
    # data: { host: "192.168.1.50", name: "My Printer", type: "moonraker" }
    raw_host = data.get('host')
    name = data.get('name') or raw_host
    ptype = data.get('type', "moonraker")
    
    # Parse port if present
    if ":" in raw_host:
        host, port_str = raw_host.split(":")
        port = int(port_str)
    else:
        host = raw_host
        port = 80
    
    print(f"Received add_printer request: {host}:{port} ({ptype})")
    
    if not audio_loop or not audio_loop.printer_agent:
        await sio.emit('error', {'msg': "Printer Agent not available"})
        return
        
    try:
        # Add manually
        camera_url = data.get('camera_url')
        printer = audio_loop.printer_agent.add_printer_manually(name, host, port=port, printer_type=ptype, camera_url=camera_url)
        
        # Save to settings
        new_printer_config = {
            "name": name,
            "host": host,
            "port": port,
            "type": ptype,
            "camera_url": camera_url
        }
        
        # Check if already exists to avoid duplicates
        exists = False
        for p in SETTINGS.get("printers", []):
            if p["host"] == host and p["port"] == port:
                exists = True
                break
        
        if not exists:
            if "printers" not in SETTINGS:
                SETTINGS["printers"] = []
            SETTINGS["printers"].append(new_printer_config)
            save_settings()
            print(f"[SERVER] Saved printer {name} to settings.")
        
        # Probe to confirm/correct type
        print(f"Probing {host} to confirm type...")
        # Try port 7125 (Moonraker) and 4408 (Fluidd/K1) 
        ports_to_try = [80, 7125, 4408]
        
        actual_type = "unknown"
        for port in ports_to_try:
             found_type = await audio_loop.printer_agent._probe_printer_type(host, port)
             if found_type.value != "unknown":
                 actual_type = found_type
                 # Update port if different
                 if port != 80:
                     printer.port = port
                 break
        
        if actual_type != "unknown" and actual_type != printer.printer_type:
             printer.printer_type = actual_type
             print(f"Corrected type to {actual_type.value} on port {printer.port}")
             
        # Refresh list for everyone
        printers = [p.to_dict() for p in audio_loop.printer_agent.printers.values()]
        await sio.emit('printer_list', printers)
        await sio.emit('status', {'msg': f"Added printer: {name}"})
        
    except Exception as e:
        print(f"Error adding printer: {e}")
        await sio.emit('error', {'msg': f"Failed to add printer: {str(e)}"})

@sio.event
async def print_stl(sid, data):
    print(f"Received print_stl request: {data}")
    # data: { stl_path: "path/to.stl" | "current", printer: "name_or_ip", profile: "optional" }
    
    if not audio_loop or not audio_loop.printer_agent:
        await sio.emit('error', {'msg': "Printer Agent not available"})
        return
        
    try:
        stl_path = data.get('stl_path', 'current')
        printer_name = data.get('printer')
        profile = data.get('profile')
        
        if not printer_name:
             await sio.emit('error', {'msg': "No printer specified"})
             return
             
        await sio.emit('status', {'msg': f"Preparing print for {printer_name}..."})
        
        # Get current project path for resolution
        current_project_path = None
        if audio_loop and audio_loop.project_manager:
            current_project_path = str(audio_loop.project_manager.get_current_project_path())
            print(f"[SERVER DEBUG] Using project path: {current_project_path}")

        # Resolve STL path before slicing so we can preview it
        resolved_stl = audio_loop.printer_agent._resolve_file_path(stl_path, current_project_path)
        
        if resolved_stl and os.path.exists(resolved_stl):
            # Open the STL in the CAD module for preview
            try:
                import base64
                with open(resolved_stl, 'rb') as f:
                    stl_data = f.read()
                stl_b64 = base64.b64encode(stl_data).decode('utf-8')
                stl_filename = os.path.basename(resolved_stl)
                
                print(f"[SERVER] Opening STL in CAD module: {stl_filename}")
                await sio.emit('cad_data', {
                    'format': 'stl',
                    'data': stl_b64,
                    'filename': stl_filename
                })
            except Exception as e:
                print(f"[SERVER] Warning: Could not preview STL: {e}")
        
        # Progress Callback
        async def on_slicing_progress(percent, message):
            await sio.emit('slicing_progress', {
                'printer': printer_name,
                'percent': percent,
                'message': message
            })
            if percent < 100:
                 await sio.emit('status', {'msg': f"Slicing: {percent}%"})

        result = await audio_loop.printer_agent.print_stl(
            stl_path, 
            printer_name, 
            profile,
            progress_callback=on_slicing_progress,
            root_path=current_project_path
        )
        
        await sio.emit('print_result', result)
        await sio.emit('status', {'msg': f"Print Job: {result.get('status', 'unknown')}"})
        
    except Exception as e:
        print(f"Error printing STL: {e}")
        await sio.emit('error', {'msg': f"Print Failed: {str(e)}"})

@sio.event
async def get_slicer_profiles(sid):
    """Get available OrcaSlicer profiles for manual selection."""
    print("Received get_slicer_profiles request")
    if not audio_loop or not audio_loop.printer_agent:
        await sio.emit('error', {'msg': "Printer Agent not available"})
        return
    
    try:
        profiles = audio_loop.printer_agent.get_available_profiles()
        await sio.emit('slicer_profiles', profiles)
    except Exception as e:
        print(f"Error getting slicer profiles: {e}")
        await sio.emit('error', {'msg': f"Failed to get profiles: {str(e)}"})

@sio.event
async def control_kasa(sid, data):
    # data: { ip, action: "on"|"off"|"brightness"|"color", value: ... }
    if not kasa_agent:
        await sio.emit('error', {'msg': 'Smart home module not available'}, room=sid)
        return
    ip = data.get('ip')
    action = data.get('action')
    print(f"Kasa Control: {ip} -> {action}")
    
    try:
        success = False
        if action == "on":
            success = await kasa_agent.turn_on(ip)
        elif action == "off":
            success = await kasa_agent.turn_off(ip)
        elif action == "brightness":
            val = data.get('value')
            success = await kasa_agent.set_brightness(ip, val)
        elif action == "color":
            # value is {h, s, v} - convert to tuple for set_color
            h = data.get('value', {}).get('h', 0)
            s = data.get('value', {}).get('s', 100)
            v = data.get('value', {}).get('v', 100)
            success = await kasa_agent.set_color(ip, (h, s, v))
        
        if success:
            await sio.emit('kasa_update', {
                'ip': ip,
                'is_on': True if action == "on" else (False if action == "off" else None),
                'brightness': data.get('value') if action == "brightness" else None,
            })
 
        else:
             await sio.emit('error', {'msg': f"Failed to control device {ip}"})

    except Exception as e:
         print(f"Error controlling kasa: {e}")
         await sio.emit('error', {'msg': f"Kasa Control Error: {str(e)}"})

@sio.event
async def get_settings(sid):
    await sio.emit('settings', SETTINGS)

@sio.event
async def update_settings(sid, data):
    # Generic update
    print(f"Updating settings: {data}")
    
    # Handle specific keys if needed
    if "tool_permissions" in data:
        SETTINGS["tool_permissions"].update(data["tool_permissions"])
        if audio_loop:
            audio_loop.update_permissions(SETTINGS["tool_permissions"])
            
    if "face_auth_enabled" in data:
        SETTINGS["face_auth_enabled"] = data["face_auth_enabled"]
        # If turned OFF, maybe emit auth status true?
        if not data["face_auth_enabled"]:
             await sio.emit('auth_status', {'authenticated': True})
             # Stop auth loop if running?
             if authenticator:
                 authenticator.stop() 

    if "camera_flipped" in data:
        SETTINGS["camera_flipped"] = data["camera_flipped"]
        print(f"[SERVER] Camera flip set to: {data['camera_flipped']}")

    save_settings()
    # Broadcast new full settings
    await sio.emit('settings', SETTINGS)


# Deprecated/Mapped for compatibility if frontend still uses specific events
@sio.event
async def get_tool_permissions(sid):
    await sio.emit('tool_permissions', SETTINGS["tool_permissions"])

@sio.event
async def update_tool_permissions(sid, data):
    print(f"Updating permissions (legacy event): {data}")
    SETTINGS["tool_permissions"].update(data)
    save_settings()
    
    if audio_loop:
        audio_loop.update_permissions(SETTINGS["tool_permissions"])
    # Broadcast update to all
    await sio.emit('tool_permissions', SETTINGS["tool_permissions"])

# ============================================================
# NEW MODULE EVENT HANDLERS
# ============================================================

# --- Terminal Events ---

@sio.event
async def terminal_create(sid, data=None):
    if not terminal_manager:
        await sio.emit('error', {'msg': 'Terminal not available'}, room=sid)
        return
    try:
        session_id = (data or {}).get('session_id', sid)
        shell = (data or {}).get('shell')
        rows = (data or {}).get('rows', 24)
        cols = (data or {}).get('cols', 80)
        result = terminal_manager.create_session(session_id, shell=shell, rows=rows, cols=cols)
        await sio.emit('terminal_created', result, room=sid)
    except Exception as e:
        print(f"[SERVER] terminal_create error: {e}")
        await sio.emit('terminal_error', {'error': str(e)}, room=sid)

@sio.event
async def terminal_input(sid, data):
    if not terminal_manager:
        return
    try:
        session_id = data.get('session_id', sid)
        text = data.get('data', '')
        terminal_manager.write_input(session_id, text)
    except Exception as e:
        print(f"[SERVER] terminal_input error: {e}")
        await sio.emit('terminal_error', {'error': str(e)}, room=sid)

@sio.event
async def terminal_resize(sid, data):
    if not terminal_manager:
        return
    try:
        session_id = data.get('session_id', sid)
        rows = data.get('rows', 24)
        cols = data.get('cols', 80)
        terminal_manager.resize_session(session_id, rows, cols)
    except Exception as e:
        print(f"[SERVER] terminal_resize error: {e}")

@sio.event
async def terminal_close(sid, data=None):
    if not terminal_manager:
        return
    try:
        session_id = (data or {}).get('session_id', sid)
        terminal_manager.close_session(session_id)
        await sio.emit('terminal_closed', {'session_id': session_id}, room=sid)
    except Exception as e:
        print(f"[SERVER] terminal_close error: {e}")

# --- Scheduler Events ---

@sio.event
async def list_tasks(sid):
    if not task_scheduler:
        await sio.emit('task_list', [], room=sid)
        return
    try:
        tasks = task_scheduler.list_tasks()
        await sio.emit('task_list', tasks, room=sid)
    except Exception as e:
        print(f"[SERVER] list_tasks error: {e}")
        await sio.emit('error', {'msg': f'Scheduler error: {str(e)}'}, room=sid)

@sio.event
async def create_task(sid, data):
    if not task_scheduler:
        await sio.emit('error', {'msg': 'Scheduler not available'}, room=sid)
        return
    try:
        task = task_scheduler.add_task(
            name=data.get('name', 'Untitled Task'),
            description=data.get('description', ''),
            schedule_type=data.get('schedule_type', 'once'),
            schedule_value=data.get('schedule_value', ''),
            tool_name=data.get('tool_name', ''),
            tool_args=data.get('tool_args'),
            enabled=data.get('enabled', True),
        )
        await sio.emit('task_update', {'action': 'created', 'task': task}, room=sid)
        await sio.emit('task_list', task_scheduler.list_tasks(), room=sid)
    except Exception as e:
        print(f"[SERVER] create_task error: {e}")
        await sio.emit('error', {'msg': f'Failed to create task: {str(e)}'}, room=sid)

@sio.event
async def toggle_task(sid, data):
    if not task_scheduler:
        return
    try:
        task_id = data.get('task_id')
        enabled = data.get('enabled', True)
        if enabled:
            task_scheduler.enable_task(task_id)
        else:
            task_scheduler.disable_task(task_id)
        await sio.emit('task_update', {'action': 'toggled', 'task_id': task_id, 'enabled': enabled}, room=sid)
        await sio.emit('task_list', task_scheduler.list_tasks(), room=sid)
    except Exception as e:
        print(f"[SERVER] toggle_task error: {e}")
        await sio.emit('error', {'msg': f'Failed to toggle task: {str(e)}'}, room=sid)

@sio.event
async def delete_task(sid, data):
    if not task_scheduler:
        return
    try:
        task_id = data.get('task_id')
        task_scheduler.remove_task(task_id)
        await sio.emit('task_update', {'action': 'deleted', 'task_id': task_id}, room=sid)
        await sio.emit('task_list', task_scheduler.list_tasks(), room=sid)
    except Exception as e:
        print(f"[SERVER] delete_task error: {e}")
        await sio.emit('error', {'msg': f'Failed to delete task: {str(e)}'}, room=sid)

# --- Heartbeat Target Management Events ---

@sio.event
async def list_heartbeat_targets(sid):
    if not heartbeat_monitor:
        await sio.emit('heartbeat_targets', [], room=sid)
        return
    try:
        targets = heartbeat_monitor.list_targets()
        await sio.emit('heartbeat_targets', targets, room=sid)
    except Exception as e:
        print(f"[SERVER] list_heartbeat_targets error: {e}")
        await sio.emit('error', {'msg': f'Heartbeat error: {str(e)}'}, room=sid)

@sio.event
async def add_heartbeat_target(sid, data):
    if not heartbeat_monitor:
        await sio.emit('error', {'msg': 'Heartbeat monitor not available'}, room=sid)
        return
    try:
        target = heartbeat_monitor.add_target(
            name=data.get('name', 'Untitled Target'),
            target_type=data.get('target_type', 'url'),
            address=data.get('address', ''),
            interval=data.get('interval', 60),
        )
        await sio.emit('heartbeat_targets', heartbeat_monitor.list_targets(), room=sid)
    except Exception as e:
        print(f"[SERVER] add_heartbeat_target error: {e}")
        await sio.emit('error', {'msg': f'Failed to add target: {str(e)}'}, room=sid)

@sio.event
async def remove_heartbeat_target(sid, data):
    if not heartbeat_monitor:
        return
    try:
        target_id = data.get('target_id')
        heartbeat_monitor.remove_target(target_id)
        await sio.emit('heartbeat_targets', heartbeat_monitor.list_targets(), room=sid)
    except Exception as e:
        print(f"[SERVER] remove_heartbeat_target error: {e}")
        await sio.emit('error', {'msg': f'Failed to remove target: {str(e)}'}, room=sid)

# --- Alerts Events ---

@sio.event
async def get_notifications(sid, data=None):
    if not alert_manager:
        await sio.emit('notifications', [], room=sid)
        return
    try:
        limit = (data or {}).get('limit', 50)
        notifications = alert_manager.get_notifications(limit=limit)
        await sio.emit('notifications', notifications, room=sid)
    except Exception as e:
        print(f"[SERVER] get_notifications error: {e}")
        await sio.emit('error', {'msg': f'Alerts error: {str(e)}'}, room=sid)

@sio.event
async def get_alert_rules(sid):
    if not alert_manager:
        await sio.emit('alert_rules', [], room=sid)
        return
    try:
        rules = alert_manager.list_rules()
        await sio.emit('alert_rules', rules, room=sid)
    except Exception as e:
        print(f"[SERVER] get_alert_rules error: {e}")
        await sio.emit('error', {'msg': f'Alerts error: {str(e)}'}, room=sid)

@sio.event
async def add_alert_rule(sid, data):
    if not alert_manager:
        await sio.emit('error', {'msg': 'Alert manager not available'}, room=sid)
        return
    try:
        rule = alert_manager.add_rule(
            name=data.get('name', 'Untitled Rule'),
            condition_type=data.get('condition_type', 'threshold'),
            condition_config=data.get('condition_config', {}),
            action=data.get('action', 'notify'),
            action_config=data.get('action_config'),
            enabled=data.get('enabled', True),
        )
        await sio.emit('alert_rules', alert_manager.list_rules(), room=sid)
    except Exception as e:
        print(f"[SERVER] add_alert_rule error: {e}")
        await sio.emit('error', {'msg': f'Failed to add rule: {str(e)}'}, room=sid)

@sio.event
async def toggle_alert_rule(sid, data):
    if not alert_manager:
        return
    try:
        rule_id = data.get('rule_id')
        enabled = data.get('enabled', True)
        if enabled:
            alert_manager.enable_rule(rule_id)
        else:
            alert_manager.disable_rule(rule_id)
        await sio.emit('alert_rules', alert_manager.list_rules(), room=sid)
    except Exception as e:
        print(f"[SERVER] toggle_alert_rule error: {e}")
        await sio.emit('error', {'msg': f'Failed to toggle rule: {str(e)}'}, room=sid)

@sio.event
async def clear_notifications(sid, data=None):
    if not alert_manager:
        return
    try:
        alert_manager.clear_notifications()
        await sio.emit('notifications', [], room=sid)
    except Exception as e:
        print(f"[SERVER] clear_notifications error: {e}")

# --- Integration Events ---

@sio.event
async def list_integrations(sid):
    if not integration_registry:
        await sio.emit('integration_list', [], room=sid)
        return
    try:
        integrations = integration_registry.list_all()
        await sio.emit('integration_list', integrations, room=sid)
    except Exception as e:
        print(f"[SERVER] list_integrations error: {e}")
        await sio.emit('error', {'msg': f'Integration error: {str(e)}'}, room=sid)

@sio.event
async def connect_integration(sid, data):
    if not integration_registry:
        await sio.emit('error', {'msg': 'Integrations not available'}, room=sid)
        return
    try:
        name = data.get('name')
        integration = integration_registry.get(name)
        if integration:
            await integration.setup()
            await sio.emit('integration_update', {'name': name, 'connected': integration.is_connected}, room=sid)
        else:
            await sio.emit('error', {'msg': f'Integration "{name}" not found'}, room=sid)
    except Exception as e:
        print(f"[SERVER] connect_integration error: {e}")
        await sio.emit('error', {'msg': f'Failed to connect: {str(e)}'}, room=sid)

@sio.event
async def disconnect_integration(sid, data):
    if not integration_registry:
        return
    try:
        name = data.get('name')
        integration = integration_registry.get(name)
        if integration:
            await integration.teardown()
            await sio.emit('integration_update', {'name': name, 'connected': False}, room=sid)
    except Exception as e:
        print(f"[SERVER] disconnect_integration error: {e}")
        await sio.emit('error', {'msg': f'Failed to disconnect: {str(e)}'}, room=sid)

# --- Messaging Events ---

@sio.event
async def list_messaging_platforms(sid):
    if not message_broker:
        await sio.emit('messaging_platform_list', [], room=sid)
        return
    try:
        platforms = message_broker.list_adapters()
        await sio.emit('messaging_platform_list', platforms, room=sid)
    except Exception as e:
        print(f"[SERVER] list_messaging_platforms error: {e}")
        await sio.emit('error', {'msg': f'Messaging error: {str(e)}'}, room=sid)

@sio.event
async def connect_platform(sid, data):
    if not message_broker:
        await sio.emit('error', {'msg': 'Messaging not available'}, room=sid)
        return
    try:
        platform = data.get('platform')
        config = data.get('config', {})
        adapter = message_broker.get_adapter(platform)
        if adapter:
            await adapter.connect()
            await sio.emit('messaging_platform_update', {
                'platform': platform, 'connected': adapter.is_connected
            }, room=sid)
        else:
            await sio.emit('error', {'msg': f'Platform "{platform}" not registered'}, room=sid)
    except Exception as e:
        print(f"[SERVER] connect_platform error: {e}")
        await sio.emit('error', {'msg': f'Failed to connect platform: {str(e)}'}, room=sid)

@sio.event
async def disconnect_platform(sid, data):
    if not message_broker:
        return
    try:
        platform = data.get('platform')
        adapter = message_broker.get_adapter(platform)
        if adapter:
            await adapter.disconnect()
            await sio.emit('messaging_platform_update', {
                'platform': platform, 'connected': False
            }, room=sid)
    except Exception as e:
        print(f"[SERVER] disconnect_platform error: {e}")
        await sio.emit('error', {'msg': f'Failed to disconnect platform: {str(e)}'}, room=sid)

@sio.event
async def update_platform_config(sid, data):
    if not message_broker:
        return
    try:
        platform = data.get('platform')
        config = data.get('config', {})
        # Store config in settings for persistence
        messaging_config = SETTINGS.get('messaging', {})
        messaging_config[platform] = config
        SETTINGS['messaging'] = messaging_config
        save_settings()
        await sio.emit('messaging_platform_update', {
            'platform': platform, 'config_updated': True
        }, room=sid)
    except Exception as e:
        print(f"[SERVER] update_platform_config error: {e}")
        await sio.emit('error', {'msg': f'Failed to update config: {str(e)}'}, room=sid)

# --- Plugin Events ---

@sio.event
async def list_plugins(sid):
    if not plugin_registry:
        await sio.emit('plugin_list', [], room=sid)
        return
    try:
        plugins = plugin_registry.list_plugins()
        await sio.emit('plugin_list', plugins, room=sid)
    except Exception as e:
        print(f"[SERVER] list_plugins error: {e}")
        await sio.emit('error', {'msg': f'Plugin error: {str(e)}'}, room=sid)

@sio.event
async def update_plugin_status(sid, data):
    if not plugin_registry:
        return
    try:
        plugin_name = data.get('name')
        enabled = data.get('enabled', True)
        plugin = plugin_registry.get_plugin(plugin_name)
        if plugin:
            plugin.enabled = enabled
            await sio.emit('plugin_list', plugin_registry.list_plugins(), room=sid)
        else:
            await sio.emit('error', {'msg': f'Plugin "{plugin_name}" not found'}, room=sid)
    except Exception as e:
        print(f"[SERVER] update_plugin_status error: {e}")
        await sio.emit('error', {'msg': f'Failed to update plugin: {str(e)}'}, room=sid)

# --- Memory Events ---

@sio.event
async def search_memory(sid, data):
    if not memory_manager:
        await sio.emit('memory_search_results', {'results': [], 'query': data.get('query', '')}, room=sid)
        return
    try:
        query = data.get('query', '')
        top_k = data.get('top_k', 5)
        context = await memory_manager.get_relevant_context(query, top_k=top_k)
        await sio.emit('memory_search_results', {'results': context, 'query': query}, room=sid)
    except Exception as e:
        print(f"[SERVER] search_memory error: {e}")
        await sio.emit('error', {'msg': f'Memory search error: {str(e)}'}, room=sid)

@sio.event
async def get_memory_stats(sid):
    if not memory_manager:
        await sio.emit('memory_stats', {'episodic': 0, 'semantic': 0, 'procedural': 0}, room=sid)
        return
    try:
        stats = memory_manager.get_stats()
        await sio.emit('memory_stats', stats, room=sid)
    except Exception as e:
        print(f"[SERVER] get_memory_stats error: {e}")
        await sio.emit('error', {'msg': f'Memory stats error: {str(e)}'}, room=sid)

# --- Config / API Key Status ---

@sio.event
async def get_api_key_status(sid):
    try:
        keys = AppConfig.get_api_keys()
        status = {}
        for provider, key in keys.items():
            status[provider] = bool(key and len(key) > 0)
        await sio.emit('api_key_status', status, room=sid)
    except Exception as e:
        print(f"[SERVER] get_api_key_status error: {e}")
        await sio.emit('error', {'msg': f'Config error: {str(e)}'}, room=sid)

# --- Sandbox / Code Execution ---

@sio.event
async def execute_code(sid, data):
    if not code_sandbox:
        await sio.emit('error', {'msg': 'Code sandbox not available'}, room=sid)
        return
    try:
        code = data.get('code', '')
        language = data.get('language', 'python')
        timeout = data.get('timeout', 30)
        result = await code_sandbox.execute(code, language=language, timeout=timeout)
        await sio.emit('code_result', result, room=sid)
    except Exception as e:
        print(f"[SERVER] execute_code error: {e}")
        await sio.emit('error', {'msg': f'Execution error: {str(e)}'}, room=sid)

# ============================================================

if __name__ == "__main__":
    uvicorn.run(
        "server:app_socketio", 
        host="127.0.0.1", 
        port=8000, 
        reload=False, # Reload enabled causes spawn of worker which might miss the event loop policy patch
        loop="asyncio",
        reload_excludes=["temp_cad_gen.py", "output.stl", "*.stl"]
    )
