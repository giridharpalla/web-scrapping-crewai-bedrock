from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
import contextlib
from scraper import scraper

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize the Playwright browser when the app starts
    await scraper.initialize()
    yield
    # Clean up the browser when the app shuts down
    await scraper.close()

app = FastAPI(
    title="Real-Time Dynamic Web Scraper API",
    description="API to scrape JavaScript-rendered content using Playwright",
    version="1.0.0",
    lifespan=lifespan
)

class ScrapeRequest(BaseModel):
    url: str

@app.get("/")
def read_root():
    return {"message": "Welcome to the Real-Time Dynamic Web Scraper API"}

@app.post("/scrape")
async def perform_scrape(request: ScrapeRequest):
    data = await scraper.scrape(request.url)
    
    if data["status"] == "error":
        raise HTTPException(status_code=500, detail=data["error"])
        
    return {"data": data}

@app.get("/scrape/discoverflow")
async def scrape_discoverflow():
    # Dedicated endpoint for the specific requested site
    target_url = "https://discoverflow.co/"
    data = await scraper.scrape(target_url)
    
    if data["status"] == "error":
        raise HTTPException(status_code=500, detail=data["error"])
        
    return {"data": data}

if __name__ == "__main__":
    import uvicorn
    import sys
    import asyncio
    
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
