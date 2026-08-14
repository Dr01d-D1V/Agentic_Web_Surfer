import requests
from playwright.sync_api import sync_playwright

def test_steel_browser():
    base_url = "http://localhost:9223"
    
    # 1. Manually fetch the correct JSON metadata from Steel
    try:
        response = requests.get(f"{base_url}/json/version")
        data = response.json()
        
        # 2. Extract the internal websocket debugger URL
        raw_ws_url = data.get("webSocketDebuggerUrl")
        
        # 3. Force Playwright to talk directly to your port 9223 mapping
        # This fixes Steel's bug of omitting ':9223' in the returned metadata
        cdp_url = raw_ws_url.replace("localhost/", "localhost:9223/")
        print(f"Corrected CDP Endpoint: {cdp_url}")
        
    except Exception as e:
        print(f"Failed to fetch CDP metadata: {e}")
        return

    with sync_playwright() as p:
        print("Connecting to local Steel Browser...")
        browser = p.chromium.connect_over_cdp(cdp_url)
        context = browser.contexts[0]

        page = context.pages[0]
        # page = browser.new_page()
        # page.goto("https://example.com")
        # page.goto("https://youtube.com", wait_until="domcontentloaded")
        page.goto("https://linkedin.com", wait_until="domcontentloaded")
        
        title = page.title()
        print(f"Successfully loaded page! Title is: '{title}'")
        
        browser.close()

if __name__ == "__main__":
    test_steel_browser()
