# DiscOverflow AI Web Research Agent

An AI-powered web research agent that scrapes dynamic, JavaScript-rendered content from [discoverflow.co](https://discoverflow.co/) in real-time using a headless browser and answers questions using **AWS Bedrock Llama 4 Maverick** (`meta.llama4-maverick-17b-instruct-v1:0`).

---

## Features

- **Real-Time Dynamic Scraping** -- Uses Playwright headless browser to render and extract data from JavaScript-heavy websites
- **AI-Powered Analysis** -- Llama 4 Maverick on AWS Bedrock analyzes scraped content and provides intelligent summaries
- **Interactive Chat Mode** -- Ask follow-up questions in a conversational interface with full context memory
- **One-Shot Agent Mode** -- Automatically scrapes and summarizes a website in a single run
- **FastAPI Server** -- REST API endpoint for programmatic scraping access
- **Native Tool Calling** -- Uses AWS Bedrock Converse API with native tool use for reliable scraper invocation

---

## Architecture

```
User CLI (chat.py / agent.py)
        |
        v
AWS Bedrock Converse API (boto3)
  Model: Llama 4 Maverick 17B
        |
        |--- tool_use: scrape_website(url)
        |         |
        |         v
        |    Playwright Headless Browser (scraper.py)
        |         |
        |         v
        |    Target Website (discoverflow.co)
        |         |
        |         v
        |    Extracted: title, headings, links, text
        |
        v
Final Answer to User
```

**Flow:**

1. User asks a question (via CLI chat or one-shot agent)
2. Llama 4 Maverick decides if it needs to scrape a website
3. If yes, it calls the `scrape_website` tool with the target URL
4. Playwright launches a headless Chromium browser, navigates to the URL, waits for JS to render
5. Scraper extracts title, headings, links, and text content
6. Scraped data is sent back to Llama 4 Maverick
7. The model analyzes the data and responds to the user

---

## Project Structure

```
swp/
  chat.py            # Interactive chat agent (main entry point)
  agent.py           # One-shot scrape and summarize agent
  scraper.py         # Playwright headless browser scraper
  main.py            # FastAPI REST API server for scraping
  requirements.txt   # Python dependencies
  .gitignore         # Git ignore rules
  venv/              # Python virtual environment
```

---

## Local Setup

### Prerequisites

- **Python 3.10+**
- **AWS Account** with Bedrock access enabled for Meta Llama 4 Maverick
- **AWS CLI** configured with valid credentials (`aws configure`)

### Installation

```bash
# 1. Clone the repository
git clone <repo-url>
cd swp

# 2. Create and activate virtual environment
python -m venv venv

# Windows
.\venv\Scripts\Activate.ps1

# macOS/Linux
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install Playwright browsers
playwright install chromium

# 5. Configure AWS credentials (if not already done)
aws configure
# Enter your AWS Access Key ID, Secret Access Key, and Region (us-east-1)
```

### AWS Bedrock Model Access

Make sure you have **Model Access** granted for Meta Llama 4 Maverick 17B Instruct in AWS Bedrock:

1. Go to AWS Console > Amazon Bedrock > Model Access
2. Request access for **Meta Llama 4 Maverick 17B Instruct**
3. Wait for access to be granted (usually immediate)

---

## Local Testing

### 1. Interactive Chat Mode

```bash
python chat.py
```

Starts an interactive chatbot. Ask questions about discoverflow.co and the agent scrapes the website in real-time. Type `quit` to exit.

**Example Session:**

```
============================================================
  DiscOverflow Chat - Powered by Llama 4 Maverick
  Ask me anything about discoverflow.co!
  Type 'quit' or 'exit' to stop.
============================================================

You: what services does discoverflow.co offer?
  [Scraping https://discoverflow.co/...]
  [Done - 1808 chars scraped]
