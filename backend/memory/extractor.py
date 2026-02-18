"""AI-powered memory extraction from conversations.

Analyzes conversation turns to identify facts, preferences, and procedures
that should be persisted to long-term memory.
"""

from typing import Optional


EXTRACTION_PROMPT = """Analyze the following conversation segment and extract any important information that should be remembered long-term.

Conversation:
{conversation}

Extract the following types of memories (return JSON):
{{
  "facts": ["list of facts/preferences about the user (e.g., 'User prefers dark mode', 'User's name is Naz')"],
  "procedures": ["list of learned workflows (e.g., 'To deploy: run npm build then scp to server')"],
  "summary": "One-sentence summary of what happened in this conversation segment"
}}

Rules:
- Only extract genuinely useful long-term information
- Skip trivial or transient details
- Facts should be about the USER, not about the conversation
- Procedures should be reusable workflows
- If nothing worth remembering, return empty lists
- Return ONLY valid JSON, no markdown"""


class MemoryExtractor:
    """Extracts persistent memories from conversation turns.

    Uses the configured AI provider to analyze conversations and identify
    facts, preferences, and procedures worth remembering.
    """

    def __init__(self, router=None):
        self.router = router

    async def extract(self, conversation_text: str) -> dict:
        """Analyze a conversation segment and extract memories.

        Args:
            conversation_text: Recent conversation to analyze

        Returns:
            Dict with 'facts', 'procedures', and 'summary' keys
        """
        if not self.router:
            return {"facts": [], "procedures": [], "summary": ""}

        if not conversation_text.strip():
            return {"facts": [], "procedures": [], "summary": ""}

        try:
            provider = self.router.get_provider("memory_extraction")
            model = self.router.get_model("memory_extraction")

            prompt = EXTRACTION_PROMPT.format(conversation=conversation_text)

            response = await provider.generate(
                prompt,
                model=model,
                temperature=0.3,
                max_tokens=1000,
            )

            return self._parse_response(response.text)

        except Exception as e:
            print(f"[MemoryExtractor] Extraction failed: {e}")
            return {"facts": [], "procedures": [], "summary": ""}

    def _parse_response(self, text: str) -> dict:
        """Parse the AI response into structured memory data."""
        import json

        # Try to extract JSON from the response
        text = text.strip()

        # Handle markdown code blocks
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()

        try:
            data = json.loads(text)
            return {
                "facts": data.get("facts", []),
                "procedures": data.get("procedures", []),
                "summary": data.get("summary", ""),
            }
        except json.JSONDecodeError:
            return {"facts": [], "procedures": [], "summary": ""}
