import typer
from typing_extensions import Annotated
import aiohttp
import asyncio
from bs4 import BeautifulSoup
import csv
from urllib.parse import urljoin, urlparse

app = typer.Typer()

async def fetch(url, session):
    try:
        async with session.get(url) as response:
            return await response.text(), response.status
    except Exception as e:
        return str(e), 404

async def parse(url, session, base_domain, crawled, results):
    text, status = await fetch(url, session)
    if status == 200:
        soup = BeautifulSoup(text, 'html.parser')
        for link in soup.find_all('a', href=True):
            link_url = urljoin(url, link['href'])
            # Check if the link is within the same domain and not already crawled
            if urlparse(link_url).netloc == base_domain and link_url not in crawled:
                crawled.add(link_url)
                # Recursively parse the new link
                await parse(link_url, session, base_domain, crawled, results)
            elif link_url not in crawled:
                # If it's an external link, just check if it's broken without further crawling
                _, status = await fetch(link_url, session)
                if status == 404:
                    if link_url not in results:
                        results[link_url] = set()
                    results[link_url].add(url)
    elif status == 404:
        if url not in results:
            results[url] = set()
        results[url].add(url)

async def crawl(base_url):
    crawled = set([base_url])
    results = {}
    async with aiohttp.ClientSession() as session:
        await parse(base_url, session, urlparse(base_url).netloc, crawled, results)
    return results

def dump_to_csv(bad_links, file_name="py404.csv"):
    with open(file_name, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Bad Link', 'Found On'])
        for link, pages in bad_links.items():
            writer.writerow([link, '; '.join(pages)])

async def py404(url):
    bad_links = await crawl(url)
    dump_to_csv(bad_links)

@app.command()
def main(url: str):
    """
    Find deadlinks for any given website URL  
    """
    asyncio.run(py404(url))
    print("Deadlinks saved in CSV file 'py404.csv'")
