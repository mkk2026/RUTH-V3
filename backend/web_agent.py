"""Web Agent -- browser automation using Playwright with configurable AI providers."""

import os
import asyncio
import base64
from typing import Optional

from dotenv import load_dotenv
try:
    from playwright.async_api import async_playwright
    _PLAYWRIGHT_AVAILABLE = True
except ImportError:
    async_playwright = None
    _PLAYWRIGHT_AVAILABLE = False
    print("[WebAgent] playwright not installed. Web automation disabled.")

from providers.router import ModelRouter

load_dotenv()

SCREEN_WIDTH = 1440
SCREEN_HEIGHT = 900


class WebAgent:
    """Browser automation agent powered by AI computer-use models.

    Currently only Gemini supports computer-use natively. When other providers
    are selected for the web_agent task, falls back to Gemini's computer-use model.
    """

    def __init__(self, router: Optional[ModelRouter] = None):
        self.router = router
        self.browser = None
        self.context = None
        self.page = None

        # For computer-use, we need the direct Gemini client since the
        # computer_use tool type is Gemini-specific
        self._init_gemini_client()

    def _init_gemini_client(self):
        """Initialize Gemini client for computer-use (provider-specific feature)."""
        from google import genai
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key and self.router:
            api_key = self.router._resolve_api_key("gemini")
        self.client = genai.Client(api_key=api_key) if api_key else None
        self.model_id = "gemini-2.5-computer-use-preview-10-2025"
        if self.router:
            self.model_id = self.router.get_model("web_agent")

    def denormalize_x(self, x: int, width: int) -> int:
        return int((x / 1000) * width)

    def denormalize_y(self, y: int, height: int) -> int:
        return int((y / 1000) * height)

    async def execute_function_calls(self, function_calls):
        """Execute browser actions from model function calls."""
        results = []

        for call in function_calls:
            call_id = getattr(call, 'id', None)
            fn_name = call.name
            args = call.args
            print(f"[ACTION] Action: {fn_name} {args}")

            requires_acknowledgement = False
            if "safety_decision" in args:
                decision = args["safety_decision"]
                if decision.get("decision") == "require_confirmation":
                    print(f"   [SAFETY] Safety Alert: {decision.get('explanation')}")
                    requires_acknowledgement = True

            result_data = {}

            try:
                if fn_name == "open_web_browser":
                    pass
                elif fn_name == "navigate":
                    await self.page.goto(args["url"])
                elif fn_name == "go_back":
                    await self.page.go_back()
                elif fn_name == "go_forward":
                    await self.page.go_forward()
                elif fn_name == "search":
                    query = args.get("query", "")
                    await self.page.goto("https://www.google.com")
                    if query:
                        await asyncio.sleep(1)
                        search_input = self.page.locator('textarea[name="q"], input[name="q"]').first
                        await search_input.fill(query)
                        await search_input.press("Enter")
                        await asyncio.sleep(2)
                elif fn_name == "wait_5_seconds":
                    await asyncio.sleep(5)
                elif fn_name == "click_at":
                    x = self.denormalize_x(args["x"], SCREEN_WIDTH)
                    y = self.denormalize_y(args["y"], SCREEN_HEIGHT)
                    await self.page.mouse.click(x, y)
                elif fn_name == "type_text_at":
                    x = self.denormalize_x(args["x"], SCREEN_WIDTH)
                    y = self.denormalize_y(args["y"], SCREEN_HEIGHT)
                    text = args["text"]
                    press_enter = args.get("press_enter", False)
                    clear_before = args.get("clear_before_typing", True)
                    await self.page.mouse.click(x, y)
                    if clear_before:
                        await self.page.keyboard.press("Control+A")
                        await self.page.keyboard.press("Backspace")
                    await self.page.keyboard.type(text)
                    if press_enter:
                        await self.page.keyboard.press("Enter")
                elif fn_name == "hover_at":
                    x = self.denormalize_x(args["x"], SCREEN_WIDTH)
                    y = self.denormalize_y(args["y"], SCREEN_HEIGHT)
                    await self.page.mouse.move(x, y)
                elif fn_name == "drag_and_drop":
                    start_x = self.denormalize_x(args["x"], SCREEN_WIDTH)
                    start_y = self.denormalize_y(args["y"], SCREEN_HEIGHT)
                    end_x = self.denormalize_x(args["destination_x"], SCREEN_WIDTH)
                    end_y = self.denormalize_y(args["destination_y"], SCREEN_HEIGHT)
                    await self.page.mouse.move(start_x, start_y)
                    await self.page.mouse.down()
                    await self.page.mouse.move(end_x, end_y)
                    await self.page.mouse.up()
                elif fn_name == "key_combination":
                    key_comb = args.get("keys")
                    await self.page.keyboard.press(key_comb)
                elif fn_name in ("scroll_document", "scroll_at"):
                    magnitude = args.get("magnitude", 800)
                    direction = args.get("direction", "down")
                    if fn_name == "scroll_at":
                        x = self.denormalize_x(args["x"], SCREEN_WIDTH)
                        y = self.denormalize_y(args["y"], SCREEN_HEIGHT)
                        await self.page.mouse.move(x, y)
                    dx, dy = 0, 0
                    if direction == "down": dy = magnitude
                    elif direction == "up": dy = -magnitude
                    elif direction == "right": dx = magnitude
                    elif direction == "left": dx = -magnitude
                    await self.page.mouse.wheel(dx, dy)
                else:
                    print(f"[WARN] Unimplemented function: {fn_name}")

                await asyncio.sleep(1)

            except Exception as e:
                print(f"[ERR] Error executing {fn_name}: {e}")
                result_data = {"error": str(e)}

            if requires_acknowledgement:
                result_data["safety_acknowledgement"] = True

            results.append((call_id, fn_name, result_data))

        return results

    async def get_function_responses(self, results):
        """Capture screenshot and build function responses."""
        from google.genai import types

        screenshot_bytes = await self.page.screenshot(type="png")
        current_url = self.page.url

        function_responses = []
        for call_id, name, result in results:
            response_data = {"url": current_url}
            response_data.update(result)
            function_responses.append(
                types.FunctionResponse(
                    name=name,
                    id=call_id,
                    response=response_data,
                    parts=[types.FunctionResponsePart(
                        inline_data=types.FunctionResponseBlob(
                            mime_type="image/png",
                            data=screenshot_bytes,
                        )
                    )],
                )
            )
        return function_responses, screenshot_bytes

    async def run_task(self, prompt, update_callback=None):
        """Run the web agent with the given prompt.

        Args:
            prompt: Task description for the agent.
            update_callback: async function(screenshot_b64, log_text)

        Returns:
            Final response text from the agent.
        """
        if not self.client:
            return "Web Agent Error: No Gemini API key configured"

        from google.genai import types

        print(f"[WebAgent] Started. Goal: {prompt}")
        final_response = "Agent finished without a final summary."

        async with async_playwright() as p:
            self.browser = await p.chromium.launch(headless=True)
            self.context = await self.browser.new_context(
                viewport={"width": SCREEN_WIDTH, "height": SCREEN_HEIGHT},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                ),
            )
            self.page = await self.context.new_page()
            await self.page.goto("https://www.google.com")

            config = types.GenerateContentConfig(
                tools=[types.Tool(
                    computer_use=types.ComputerUse(
                        environment=types.Environment.ENVIRONMENT_BROWSER
                    )
                )],
                thinking_config=types.ThinkingConfig(include_thoughts=True),
            )

            initial_screenshot = await self.page.screenshot(type="png")

            if update_callback:
                encoded_image = base64.b64encode(initial_screenshot).decode("utf-8")
                await update_callback(encoded_image, "Web Agent Initialized")

            chat_history = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part(text=prompt),
                        types.Part.from_bytes(data=initial_screenshot, mime_type="image/png"),
                    ],
                )
            ]

            MAX_TURNS = 20

            for turn in range(MAX_TURNS):
                print(f"\n--- Turn {turn + 1} ---")

                try:
                    response = await self.client.aio.models.generate_content(
                        model=self.model_id,
                        contents=chat_history,
                        config=config,
                    )
                except Exception as e:
                    print(f"[CRITICAL] API Error: {e}")
                    if update_callback:
                        await update_callback(None, f"Error: {e}")
                    break

                if not response.candidates:
                    print("[WARN] Model returned no content.")
                    break

                candidate = response.candidates[0]
                model_content = candidate.content
                chat_history.append(model_content)

                has_tool_use = False
                agent_text = ""

                for part in model_content.parts:
                    if part.thought:
                        pass
                    elif part.text:
                        agent_text = part.text
                    if part.function_call:
                        has_tool_use = True

                if agent_text:
                    final_response = agent_text

                function_calls = [part.function_call for part in model_content.parts if part.function_call]

                if not function_calls:
                    if not has_tool_use:
                        if update_callback:
                            await update_callback(None, "Task Finished")
                        break
                    continue

                results = await self.execute_function_calls(function_calls)
                function_responses, screenshot_bytes = await self.get_function_responses(results)

                if update_callback:
                    encoded_image = base64.b64encode(screenshot_bytes).decode("utf-8")
                    actions_log = ", ".join([r[1] for r in results])
                    await update_callback(encoded_image, f"Executed: {actions_log}")

                response_parts = [types.Part(function_response=fr) for fr in function_responses]
                chat_history.append(types.Content(role="user", parts=response_parts))

            await self.browser.close()
            return final_response


if __name__ == "__main__":
    agent = WebAgent()
    asyncio.run(agent.run_task("Go to google.com and search for 'Gemini API' pricing."))
