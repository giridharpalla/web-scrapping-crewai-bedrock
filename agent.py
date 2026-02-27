"""
CrewAI-style Agent using AWS Bedrock Converse API directly.
Uses meta.llama4-maverick-17b-instruct-v1:0 with tool calling
and the Playwright scraper as a tool.

We bypass CrewAI's LLM wrapper because it has a known bug with
Bedrock's message formatting for tool results.
"""

import json
import asyncio
import sys
import boto3
from scraper import scraper

# ─── Configuration ───────────────────────────────────────────────
MODEL_ID = "us.meta.llama4-maverick-17b-instruct-v1:0"
REGION = "us-east-1"

# ─── Tool Definition (Bedrock Converse format) ──────────────────
TOOL_CONFIG = {
    "tools": [
        {
            "toolSpec": {
                "name": "scrape_website",
                "description": (
                    "Scrapes a dynamic JavaScript-rendered website using a headless browser. "
                    "Returns the page title, links, headings, and text content. "
                    "Use this to gather real-time information from any website."
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

# ─── Tool Execution ─────────────────────────────────────────────
def execute_scraper_tool(url: str) -> str:
    """Run the Playwright scraper synchronously."""
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    async def _run():
        await scraper.initialize()
        try:
            data = await scraper.scrape(url)
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
            await scraper.close()

    return asyncio.run(_run())


# ─── Agent Loop ──────────────────────────────────────────────────
def run_agent():
    client = boto3.client("bedrock-runtime", region_name=REGION)

    system_prompt = [
        {
            "text": (
                "You are an expert web researcher. Your job is to use the scrape_website tool "
                "to fetch real data from websites and provide accurate summaries based ONLY on "
                "the actual scraped content. Never make up information. Always use the tool first, "
                "then analyze the results."
            )
        }
    ]

    user_message = (
        "Use the scrape_website tool to fetch data from https://discoverflow.co/ and then "
        "provide a detailed bulleted summary of the website's main offerings, services, and key links."
    )

    messages = [
        {"role": "user", "content": [{"text": user_message}]}
    ]

    print("=" * 60)
    print("[Agent] Senior Web Researcher")
    print(f"[Task] Scrape & summarize discoverflow.co")
    print(f"[Model] {MODEL_ID}")
    print("=" * 60)

    max_turns = 5
    for turn in range(max_turns):
        print(f"\n--- Turn {turn + 1} ---")

        response = client.converse(
            modelId=MODEL_ID,
            messages=messages,
            system=system_prompt,
            toolConfig=TOOL_CONFIG,
            inferenceConfig={"temperature": 0.1, "maxTokens": 4096}
        )

        stop_reason = response["stopReason"]
        output_message = response["output"]["message"]
        assistant_content = output_message["content"]

        # Add assistant response to history
        messages.append(output_message)

        # Check if the model wants to use a tool
        if stop_reason == "tool_use":
            tool_results = []
            for block in assistant_content:
                if "toolUse" in block:
                    tool_use = block["toolUse"]
                    tool_id = tool_use["toolUseId"]
                    tool_name = tool_use["name"]
                    tool_input = tool_use["input"]

                    print(f"[Tool Called] {tool_name}")
                    print(f"   Input: {json.dumps(tool_input)}")

                    # Execute the tool
                    url = tool_input.get("url", "https://discoverflow.co/")
                    print(f"   Scraping {url}...")

                    try:
                        result_text = execute_scraper_tool(url)
                        print(f"   [OK] Scraper returned {len(result_text)} chars")
                        tool_results.append({
                            "toolResult": {
                                "toolUseId": tool_id,
                                "content": [{"text": result_text}]
                            }
                        })
                    except Exception as e:
                        print(f"   [ERROR] Tool error: {e}")
                        tool_results.append({
                            "toolResult": {
                                "toolUseId": tool_id,
                                "content": [{"text": f"Error: {str(e)}"}],
                                "status": "error"
                            }
                        })

            # Send tool results back — in its OWN user turn (no text blocks mixed)
            messages.append({
                "role": "user",
                "content": tool_results
            })

        elif stop_reason == "end_turn":
            # Model finished, extract the final text
            print("\n" + "=" * 60)
            print("FINAL RESULT")
            print("=" * 60 + "\n")
            for block in assistant_content:
                if "text" in block:
                    print(block["text"])
            break
        else:
            print(f"[WARNING] Unexpected stop reason: {stop_reason}")
            for block in assistant_content:
                if "text" in block:
                    print(block["text"])
            break
    else:
        print("[WARNING] Max turns reached without final answer.")


if __name__ == "__main__":
    print("Starting agent execution...\n")
    try:
        run_agent()
    except Exception as e:
        print(f"\nError during execution: {e}")
        import traceback
        traceback.print_exc()
