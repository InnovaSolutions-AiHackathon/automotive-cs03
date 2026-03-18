import anthropic

class ClaudeClient:
    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    async def generate(self, messages, system_prompt, tools):
        return self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system_prompt,
            tools=tools,
            messages=messages
        )