##########################################################################
# Author: America779
# Date: August 16, 2024
# Version: 1.1
# Email: rares.mihai1@yahoo.com
# Project: Web Crawler and Tree Viewer
#
# Description:
# This script is designed to crawl web pages starting from a given URL 
# and visualize the crawled URLs in a tree structure.
#
# Time Spent:
# Approximately ~1h45
#
# Requirements:
# - Python 3.8+
# - aiohttp
# - BeautifulSoup4
# - NetworkX
# - Quart
# - Uvicorn
#
# Usage:
# $ python -m uvicorn main:app --reload
# Open a web browser and navigate to http://localhost:8000
# to start using the web crawler and view the results.
##########################################################################

import asyncio
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import chardet
import networkx as nx
from quart import Quart, jsonify, render_template, request

app = Quart(__name__)

should_stop = False

class AsyncWebCrawler:
    def __init__(self, base_url, max_depth=0, max_concurrent_requests=10, rate_limit=10.0):
        if not isinstance(base_url, str):
            raise TypeError("base_url should be a string")
        self.base_url = base_url
        self.max_depth = max_depth
        self.visited = set()
        self.to_visit = asyncio.Queue()
        self.to_visit.put_nowait((base_url, 0))
        self.max_concurrent_requests = max_concurrent_requests
        self.rate_limit = rate_limit 
        self.allowed_extensions = {".html", ".htm", ".php", ".asp", ".aspx", ".jsp", "/"}
        self.graph = nx.DiGraph()

    async def fetch_page(self, session, url):
        try:
            await asyncio.sleep(1 / self.rate_limit)
            async with session.get(url) as response:
                response.raise_for_status()
                raw_content = await response.read()
                detected_encoding = chardet.detect(raw_content)['encoding']
                if detected_encoding:
                    return raw_content.decode(detected_encoding, errors='ignore')
                else:
                    return raw_content.decode('utf-8', errors='ignore')
        except aiohttp.ClientResponseError as e:
            print(f"HTTP error while fetching {url}: {e.status}")
        except aiohttp.ClientConnectionError as e:
            print(f"Connection error while fetching {url}: {str(e)}")
        except UnicodeDecodeError as e:
            print(f"Encoding error while decoding {url}: {str(e)}")
        except Exception as e:
            print(f"Unexpected error while fetching {url}: {str(e)}")
        return None

    def parse_links(self, html, base_url):
        soup = BeautifulSoup(html, 'html.parser')
        links = set()
        for link in soup.find_all('a', href=True):
            href = link['href']
            full_url = urljoin(base_url, href)
            normalized_url = full_url.split('#')[0]
            parsed_url = urlparse(normalized_url)
            if parsed_url.scheme in ['http', 'https'] and self.is_html_link(parsed_url.path):
                links.add(normalized_url)
        return links

    def is_html_link(self, path):
        extension = path.split('.')[-1].lower()
        return any(path.endswith(ext) for ext in self.allowed_extensions) or not '.' in path.split('/')[-1]

    async def crawl(self):
        global should_stop
        async with aiohttp.ClientSession() as session:
            while not self.to_visit.empty() and not should_stop:
                tasks = []
                for _ in range(min(self.max_concurrent_requests, self.to_visit.qsize())):
                    url, depth = await self.to_visit.get()
                    if depth <= self.max_depth and url not in self.visited:
                        tasks.append(self.handle_request(session, url, depth))
                
                if tasks:
                    await asyncio.gather(*tasks)

    async def handle_request(self, session, url, depth):
        global should_stop
        if should_stop:
            return
        print(f"Crawling: {url} (depth: {depth})")
        html = await self.fetch_page(session, url)
        if html:
            self.visited.add(url)
            links = self.parse_links(html, url)
            for link in links:
                if link not in self.visited:
                    await self.to_visit.put((link, depth + 1))
                    self.graph.add_edge(url, link)

    def get_tree_data(self):
        def build_tree(node):
            children = list(self.graph.successors(node))
            return {
                "name": node,
                "children": [build_tree(child) for child in children]
            }

        return build_tree(self.base_url)

@app.route('/crawl', methods=['POST'])
async def crawl():
    global should_stop
    should_stop = False

    try:
        if request.content_type == 'application/json':
            data = await request.get_json()
        else:
            data = await request.form
        
        if data is None:
            return jsonify({"error": "Request body must be JSON or form data"}), 400
        
        start_url = data.get('url')
        if not isinstance(start_url, str):
            return jsonify({"error": "Invalid URL format. URL should be a string."}), 400

        max_depth = int(data.get('max_depth', 2))
        rate_limit = float(data.get('rate_limit', 10.0))

        crawler = AsyncWebCrawler(start_url, max_depth=max_depth, max_concurrent_requests=10, rate_limit=rate_limit)
        await crawler.crawl()
        tree_data = crawler.get_tree_data()
        return jsonify(tree_data), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/stop', methods=['POST'])
async def stop_crawl():
    global should_stop
    should_stop = True
    return jsonify({"status": "stopping"})

@app.route('/')
async def index():
    return await render_template('index.html')

if __name__ == "__main__":
    app.run(debug=True)
