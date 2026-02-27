"""
Interactive Chat Agent with AWS Bedrock Llama 4 Maverick + Playwright Scraper.

Type your questions about discoverflow.co (or any website) and the agent
will scrape live data to answer. Type 'quit' or 'exit' to stop.
"""

import json
import asyncio
import sys
import boto3
from scraper import DiscoverFlowScraper

# --- Configuration ---
MODEL_ID = "us.meta.llama4-maverick-17b-instruct-v1:0"
REGION = "us-east-1"

# --- Tool Definition (Bedrock Converse format) ---
TOOL_CONFIG = {
    "tools": [
        {
            "toolSpec": {
                "name": "scrape_website",
                "description": (
                    "Scrapes a dynamic JavaScript-rendered website using a headless browser. "
                    "Returns the page title, links, headings, and text content. "
                    "Use this tool whenever the user asks about a website's content, "
                    "services, links, or any information that requires visiting the site."
                ),
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "description": "The URL to scrape, e.g. https://discoverflow.co/"
                            }
                        },
                        "required": ["url"]
                    }
                }
            }
        }
    ]
}


def execute_scraper(url: str) -> str:
    """Run the Playwright scraper synchronously and return formatted text."""
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    async def _run():
        s = DiscoverFlowScraper()
        await s.initialize()
        try:
            data = await s.scrape(url)
            if data["status"] == "error":
                return f"Error scraping: {data.get('error')}"

            result = f"Title: {data.get('title', 'N/A')}\n\n"

            result += "Headings:\n"
            for h in data.get("headings", {}).get("h1", []):
                result += f"  H1: {h}\n"
            for h in data.get("headings", {}).get("h2", []):
                result += f"  H2: {h}\n"

            result += "\nLinks:\n"
            for link in data.get("links", [])[:15]:
                text = link.get("text", "").strip()
                href = link.get("href", "").strip()
                if text or href:
                    result += f"  - {text}: {href}\n"

            result += "\nText Content:\n"
            result += data.get("text_snippet", "")[:2000]
            return result
        finally:
            await s.close()

    return asyncio.run(_run())


def handle_tool_calls(assistant_content):
    """Process any tool calls in the assistant response and return tool results."""
    tool_results = []
    for block in assistant_content:
        if "toolUse" in block:
            tool_use = block["toolUse"]
            tool_id = tool_use["toolUseId"]
            tool_name = tool_use["name"]
            tool_input = tool_use["input"]

            url = tool_input.get("url", "https://discoverflow.co/")
            print(f"  [Scraping {url}...]")

            try:
                result_text = execute_scraper(url)
                print(f"  [Done - {len(result_text)} chars scraped]")
                tool_results.append({
                    "toolResult": {
                        "toolUseId": tool_id,
                        "content": [{"text": result_text}]
                    }
                })
            except Exception as e:
                print(f"  [Scraper error: {e}]")
                tool_results.append({
                    "toolResult": {
                        "toolUseId": tool_id,
                        "content": [{"text": f"Error: {str(e)}"}],
                        "status": "error"
                    }
                })
    return tool_results


def main():
    client = boto3.client("bedrock-runtime", region_name=REGION)

    system_prompt = [
        {
            "text": (
                "You are a helpful web research assistant. You have access to a scrape_website tool "
                "that can fetch live data from any website using a headless browser.\n\n"
                "When the user asks about a website (especially https://discoverflow.co/), "
                "use the scrape_website tool to get real, current data and answer based on that.\n\n"
                "Be concise and helpful. If the user asks a general question that doesn't need "
                "web scraping, answer directly without using the tool.\n\n"
                "The default website to scrape is https://discoverflow.co/ unless the user specifies another URL."
            )
        }
    ]

    messages = []

    print("=" * 60)
    print("  DiscOverflow Chat - Powered by Llama 4 Maverick")
    print("  Ask me anything about discoverflow.co!")
    print("  Type 'quit' or 'exit' to stop.")
    print("=" * 60)

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break

        # Add user message
        messages.append({
            "role": "user",
            "content": [{"text": user_input}]
        })

        # Agent loop - handle tool calls
        max_turns = 5
        for turn in range(max_turns):
            try:
                response = client.converse(
                    modelId=MODEL_ID,
                    messages=messages,
                    system=system_prompt,
                    toolConfig=TOOL_CONFIG,
                    inferenceConfig={"temperature": 0.1, "maxTokens": 4096}
                )
            except Exception as e:
                print(f"\n[API Error: {e}]")
                # Remove the last user message so conversation stays valid
                messages.pop()
                break

            stop_reason = response["stopReason"]
            output_message = response["output"]["message"]
            assistant_content = output_message["content"]

            # Add assistant response to history
            messages.append(output_message)

            if stop_reason == "tool_use":
                # Execute tools and send results back
                tool_results = handle_tool_calls(assistant_content)
                messages.append({
                    "role": "user",
                    "content": tool_results
                })
                # Continue the loop to get the final answer

            elif stop_reason == "end_turn":
                # Print the final answer
                print("\nAssistant: ", end="")
                for block in assistant_content:
                    if "text" in block:
                        print(block["text"])
                break
            else:
                print(f"\n[Unexpected stop: {stop_reason}]")
                for block in assistant_content:
                    if "text" in block:
                        print(block["text"])
                break
        else:
            print("\n[Max tool-call turns reached]")


if __name__ == "__main__":
    main()
