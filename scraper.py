import asyncio
from playwright.async_api import async_playwright, Page
from typing import Dict, Any

class DiscoverFlowScraper:
    def __init__(self):
        self._playwright = None
        self._browser = None

    async def initialize(self):
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=True)

    async def close(self):
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    async def scrape(self, url: str) -> Dict[str, Any]:
        if not self._browser:
            await self.initialize()

        context = await self._browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        try:
            # Navigate to the URL and wait until network is mostly idle
            await page.goto(url, wait_until="networkidle", timeout=30000)

            # Wait to ensure dynamic JS components render
            await page.wait_for_timeout(5000)
            
            # Take a screenshot to debug if the page loaded correctly or if we got blocked
            await page.screenshot(path="debug_screenshot.png")

            # Extract basic metadata
            title = await page.title()
            
            # Extract main text content
            # This evaluates a script in the browser to grab all text from body
            body_text = await page.evaluate("() => document.body.innerText")
            
            # Extract links on the page
            links = await page.evaluate('''() => {
                const anchors = Array.from(document.querySelectorAll('a'));
                return anchors.map(a => ({ text: a.innerText, href: a.href })).filter(a => a.href);
            }''')

            # Extract some specific dynamic structured items if they exist
            # For a generic scraping approach of a dynamic site, pulling heading structures is useful
            headings = await page.evaluate('''() => {
                const h1s = Array.from(document.querySelectorAll('h1')).map(h => h.innerText);
                const h2s = Array.from(document.querySelectorAll('h2')).map(h => h.innerText);
                return { h1: h1s, h2: h2s };
            }''')

            return {
                "url": url,
                "title": title,
                "headings": headings,
                "links": links[:20], # limit to 20 for brevity
                "text_snippet": body_text[:500] + "..." if len(body_text) > 500 else body_text,
                "status": "success"
            }

        except Exception as e:
            return {
                "url": url,
                "status": "error",
                "error": str(e)
            }
        finally:
            await context.close()

# Singleton instance for the app to use
scraper = DiscoverFlowScraper()
