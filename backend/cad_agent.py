"""CAD Agent -- generates 3D models via build123d using configurable AI providers."""

import os
import re
import sys
import asyncio
import subprocess
import base64
from datetime import datetime
from typing import Optional

from providers.router import ModelRouter


class CadAgent:
    def __init__(
        self,
        on_thought=None,
        on_status=None,
        router: Optional[ModelRouter] = None,
    ):
        self.router = router
        self.on_thought = on_thought
        self.on_status = on_status

        self.system_instruction = """
You are a Python-based 3D CAD Engineer using the `build123d` library.
Your goal is to write a Python script that generates a 3D model based on the user's request.

Requirements:
1. Start with `from build123d import *`.
2. Include `import numpy as np` if you use any numpy functions (like `np.sign`, `np.pi`).
3. You MUST assign the final object to a variable named `result_part`.
4. If you create a sketch or line, extrude it to make it a solid `Part`.
5. The model should be centered at (0,0,0) and have reasonable dimensions (mm).
6. **IMPORTANT**: Do NOT use old or PascalCase function names for core operations.
   - Use `make_face()` instead of `MakeFace()`.
   - Use `extrude()` instead of `Extrude()`.
   - Use `fillet()` instead of `Fillet()`.
   - Use `chamfer()` instead of `Chamfer()`.
   - Use `revolve()` instead of `Revolve()`.
   - Use `loft()` instead of `Loft()`.
   - Use `sweep()` instead of `Sweep()`.
   - Use `offset()` instead of `Offset()`.
   - generally prefer lowercase builder methods inside contexts.

7. **Vector Access**: Do NOT access vector components like `v.X`, `v.Y`, `v.Z` unless you are sure they exist (use `v.X` etc on Vector objects, but ensure they are Vectors).
8. **Final Output**: The script MUST end by exporting the final part to an STL file named 'output.stl'.
   - `export_stl(result_part, 'output.stl')`

9. **Robustness**: Operations like `fillet()` and `chamfer()` will crash if the radius is too large for the geometry.
   - Use conservative values (e.g., 0.5mm to 2mm) unless you are certain of the dimensions.
   - If a fillet is purely aesthetic, keep it small to ensure success.

Example Script:
```python
from build123d import *

with BuildPart() as p:
    Box(10, 10, 10)
    Fillet(p.edges(), radius=1)

result_part = p.part
export_stl(result_part, 'output.stl')
```
"""

    def _get_provider_and_model(self):
        """Get the configured provider and model for CAD tasks."""
        if self.router:
            provider = self.router.get_provider("cad")
            model = self.router.get_model("cad")
            return provider, model

        # Fallback to direct Gemini client for backward compatibility
        from google import genai
        from dotenv import load_dotenv
        load_dotenv()
        client = genai.Client(
            http_options={"api_version": "v1beta"},
            api_key=os.getenv("GEMINI_API_KEY"),
        )
        return client, "gemini-3-pro-preview"

    async def _generate_code_streaming(self, prompt: str) -> str:
        """Generate code using the configured provider with streaming."""
        provider, model = self._get_provider_and_model()

        # If we have a router-based provider, use the streaming abstraction
        if self.router:
            raw_content = ""
            async for chunk in provider.stream(
                prompt,
                model=model,
                system_instruction=self.system_instruction,
                temperature=1.0,
                thinking=True,
            ):
                if chunk.is_done:
                    break
                if chunk.is_thinking and chunk.thinking:
                    if self.on_thought:
                        self.on_thought(chunk.thinking)
                elif chunk.text:
                    raw_content += chunk.text
            return raw_content

        # Fallback: direct Gemini client (legacy path)
        from google.genai import types
        client = provider
        raw_content = ""
        stream = await client.aio.models.generate_content_stream(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=self.system_instruction,
                temperature=1.0,
                thinking_config=types.ThinkingConfig(include_thoughts=True),
            ),
        )
        async for chunk in stream:
            if chunk.candidates and chunk.candidates[0].content and chunk.candidates[0].content.parts:
                for part in chunk.candidates[0].content.parts:
                    if not part.text:
                        continue
                    elif part.thought:
                        if self.on_thought:
                            self.on_thought(part.text)
                    else:
                        raw_content += part.text
        return raw_content

    @staticmethod
    def _extract_code(raw_content: str) -> Optional[str]:
        """Extract Python code from model response."""
        code_match = re.search(r'```python(.*?)```', raw_content, re.DOTALL)
        if code_match:
            return code_match.group(1).strip()

        if "import build123d" in raw_content or "from build123d" in raw_content:
            return raw_content
        return None

    async def _execute_script(self, script_path: str) -> tuple:
        """Execute a Python script and return (returncode, stdout, stderr)."""
        try:
            proc = await asyncio.to_thread(
                subprocess.run,
                [sys.executable, script_path],
                capture_output=True,
                text=True,
            )
            return proc.returncode, proc.stdout, proc.stderr
        except Exception as e:
            return 1, "", str(e)

    async def generate_prototype(self, prompt: str, output_dir: Optional[str] = None):
        """Generates 3D geometry by asking AI for a build123d script, then running it locally."""
        print(f"[CadAgent] Generation started for: '{prompt}'")

        try:
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
                work_dir = output_dir
            else:
                import tempfile
                work_dir = tempfile.gettempdir()

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_stl = os.path.join(work_dir, f"output_{timestamp}.stl")
            script_path = os.path.join(work_dir, "current_design.py")

            max_retries = 3
            current_prompt = (
                f"You are a build123d expert. Write a generic python script to create "
                f"a 3D model of: {prompt}. Ensure you export to 'output.stl'. Unscaled."
            )

            for attempt in range(max_retries):
                print(f"[CadAgent] Attempt {attempt + 1}/{max_retries}")

                if self.on_status:
                    self.on_status({
                        "status": "generating" if attempt == 0 else "retrying",
                        "attempt": attempt + 1,
                        "max_attempts": max_retries,
                        "error": None,
                    })

                raw_content = await self._generate_code_streaming(current_prompt)

                if not raw_content:
                    print("[CadAgent] Empty response from model.")
                    return None

                code = self._extract_code(raw_content)
                if not code:
                    print("[CadAgent] Could not extract python code.")
                    return None

                safe_output_path = output_stl.replace("\\", "\\\\")
                with open(script_path, "w") as f:
                    f.write(code.replace("output.stl", safe_output_path))

                returncode, stdout, stderr = await self._execute_script(script_path)

                if returncode != 0:
                    error_lines = stderr.strip().split('\n')
                    short_error = error_lines[-1][:100] if error_lines else "Unknown error"
                    print(f"[CadAgent] Script failed: {short_error}")

                    if self.on_status:
                        self.on_status({
                            "status": "retrying",
                            "attempt": attempt + 1,
                            "max_attempts": max_retries,
                            "error": short_error,
                        })

                    current_prompt = (
                        f"The Python script you generated failed with error:\n{stderr}\n\n"
                        f"Fix the code. Return the full corrected script. "
                        f"Export to 'output.stl'.\nOriginal request: {prompt}"
                    )
                    continue

                if os.path.exists(output_stl):
                    with open(output_stl, "rb") as f:
                        stl_data = f.read()
                    return {
                        "format": "stl",
                        "data": base64.b64encode(stl_data).decode("utf-8"),
                        "file_path": output_stl,
                    }

                current_prompt = (
                    "The script executed but 'output.stl' was not found. "
                    "Ensure you call `export_stl(result_part, 'output.stl')` at the end."
                )
                continue

            print("[CadAgent] All attempts failed.")
            if self.on_status:
                self.on_status({
                    "status": "failed",
                    "attempt": max_retries,
                    "max_attempts": max_retries,
                    "error": "All generation attempts failed",
                })
            return None

        except Exception as e:
            print(f"CadAgent Error: {e}")
            import traceback
            traceback.print_exc()
            return None

    async def iterate_prototype(self, prompt: str, output_dir: Optional[str] = None):
        """Iterates on the existing design by reading current_design.py and applying changes."""
        print(f"[CadAgent] Iteration started for: '{prompt}'")

        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            work_dir = output_dir
        else:
            import tempfile
            work_dir = tempfile.gettempdir()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        script_path = os.path.join(work_dir, "current_design.py")
        output_stl = os.path.join(work_dir, f"output_{timestamp}.stl")

        existing_code = ""
        if os.path.exists(script_path):
            with open(script_path, "r") as f:
                existing_code = f.read()
            # Sanitize embedded paths
            existing_code = re.sub(
                r"['\"]C:\\\\?Users\\\\?[^'\"]+\\\\?output[^'\"]*\.stl['\"]",
                "'output.stl'", existing_code,
            )
            existing_code = re.sub(
                r"['\"]C:/Users/[^'\"]+/output[^'\"]*\.stl['\"]",
                "'output.stl'", existing_code,
            )
        else:
            print("[CadAgent] No existing script found. Falling back to fresh generation.")
            return await self.generate_prototype(prompt, output_dir)

        try:
            max_retries = 3
            current_prompt = (
                f"You are iterating on an existing 3D model script.\n\n"
                f"Current Python Code:\n```python\n{existing_code}\n```\n\n"
                f"User Request: {prompt}\n\n"
                f"Task: Rewrite the code to satisfy the user's request while maintaining "
                f"the rest of the model structure. Ensure you still export to 'output.stl'."
            )

            for attempt in range(max_retries):
                print(f"[CadAgent] Iteration Attempt {attempt + 1}/{max_retries}")

                if self.on_status:
                    self.on_status({
                        "status": "generating" if attempt == 0 else "retrying",
                        "attempt": attempt + 1,
                        "max_attempts": max_retries,
                        "error": None,
                    })

                raw_content = await self._generate_code_streaming(current_prompt)

                if not raw_content:
                    print("[CadAgent] Empty response from model.")
                    return None

                code = self._extract_code(raw_content)
                if not code:
                    print("[CadAgent] Could not extract python code.")
                    return None

                safe_output_path = output_stl.replace("\\", "\\\\")
                with open(script_path, "w") as f:
                    f.write(code.replace("output.stl", safe_output_path))

                returncode, stdout, stderr = await self._execute_script(script_path)

                if returncode != 0:
                    print(f"[CadAgent] Script failed:\n{stderr}")
                    current_prompt = (
                        f"The updated script failed with error:\n{stderr}\n\n"
                        f"Fix the code. Return the full corrected script. "
                        f"Export to 'output.stl'."
                    )
                    continue

                if os.path.exists(output_stl):
                    with open(output_stl, "rb") as f:
                        stl_data = f.read()
                    return {
                        "format": "stl",
                        "data": base64.b64encode(stl_data).decode("utf-8"),
                        "file_path": output_stl,
                    }

                current_prompt = (
                    f"The script executed but '{output_stl}' was not found. "
                    f"Ensure you call `export_stl(result_part, 'output.stl')` at the end."
                )
                continue

            print("[CadAgent] All iteration attempts failed.")
            if self.on_status:
                self.on_status({
                    "status": "failed",
                    "attempt": max_retries,
                    "max_attempts": max_retries,
                    "error": "All iteration attempts failed",
                })
            return None

        except Exception as e:
            print(f"CadAgent Error: {e}")
            import traceback
            traceback.print_exc()
            return None
