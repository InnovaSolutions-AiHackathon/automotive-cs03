import google.genai as genai
import asyncio

class GeminiClient:
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash-lite"):
        self.client = genai.Client(api_key=api_key)
        self.model = model

    async def generate(self, messages, system_prompt, tools=None):
        # Build conversation text from messages
        conversation = "\n".join(
            f"{m['role']}: {c['text']}"
            for m in messages
            for c in m.get("content", []) if c.get("type") == "text"
        )
        prompt = f"{system_prompt}\n\n{conversation}"

        # Wrap sync call in asyncio.to_thread
        response = await asyncio.to_thread(
            self.client.models.generate_content,
            model=self.model,
            contents=prompt
        )
        return response
