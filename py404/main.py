import typer
from typing_extensions import Annotated
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from urllib3.exceptions import InsecureRequestWarning
import asyncio
import aiohttp
from tabulate import tabulate
import csv

app = typer.Typer()

requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

def find_pages(root_url):
    visited_urls = set()
    urls_to_visit = [root_url]

    while urls_to_visit:
        url = urls_to_visit.pop(0)

        # Skip if already visited
        if url in visited_urls:
            continue

        print("Page found:", url)

        try:
            response = requests.get(url, verify=False)
        except requests.exceptions.RequestException as e:
            print("Failed to crawl:", url, "Error:", e)
            continue

        # Add current URL to visited set
        visited_urls.add(url)

        # Parse HTML content
        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract all links from the page
        links = soup.find_all('a', href=True)
        for link in links:
            href = link['href']
            # Construct absolute URL if relative
            absolute_url = urljoin(url, href)
            # Add to list if it's from the same domain and not already visited
            if absolute_url.startswith(root_url) and absolute_url not in visited_urls:
                urls_to_visit.append(absolute_url)

    return visited_urls

def find_links(page):
    print("Finding links on:", page)
    links_to_check = set()
    try:
        response = requests.get(page, verify=False)
        soup = BeautifulSoup(response.content, 'html.parser')

        for tag in soup.find_all('a', href=True):
            link = tag['href']
            if link.startswith('#'):
                links_to_check.add(urljoin(page, link))
            elif urlparse(link).netloc == '':
                links_to_check.add(urljoin(page, link))
            else:
                links_to_check.add(link)

        for tag in soup.find_all(['img', 'video', 'audio', 'source']):
            src = tag.get('src')
            if src:
                links_to_check.add(urljoin(page, src))

        for tag in soup.find_all('link', rel=True):
            rel_values = tag.get('rel', [])
            href = tag.get('href')
            if 'stylesheet' in rel_values:
                links_to_check.add(urljoin(page, href))
            elif 'font' in rel_values:
                links_to_check.add(urljoin(page, href))
            elif 'icon' in rel_values:
                links_to_check.add(urljoin(page, href))

        for tag in soup.find_all('script', src=True):
            src = tag.get('src')
            if src:
                links_to_check.add(urljoin(page, src))

        for tag in soup.find_all(['a', 'link', 'script'], href=True):
            href = tag.get('href')
            if href.endswith('.xml'):
                links_to_check.add(urljoin(page, href))
            elif href.endswith(('.csv', '.json', '.xml')):
                links_to_check.add(urljoin(page, href))
            elif any(href.endswith(ext) for ext in ('.pdf', '.doc', '.docx', '.zip')):
                links_to_check.add(urljoin(page, href))
            elif href.startswith('http') or href.startswith('//'):
                links_to_check.add(urljoin(page, href))

        for tag in soup.find_all(['form'], action=True):
            action = tag.get('action')
            if action.startswith('http'):
                links_to_check.append(urljoin(page, action))

    except Exception as e:
        print("Error:", e)

    return links_to_check

async def check_link(session, link):
    print("Checking link:", link)
    try:
        async with session.get(link, verify_ssl=False) as response:
            if response.status == 404:
                return False
            else:
                return True
    except Exception as e:
        print(f"Exception occurred for {link}: {e}")
        return True
    
async def find_deadlinks(links_to_check):
    deadlinks = set()
    async with aiohttp.ClientSession() as session:
        tasks = []
        for link in links_to_check:
            task = check_link(session, link)
            tasks.append(task)
        results = await asyncio.gather(*tasks)
        for link, result in zip(links_to_check, results):
            if not result:
                deadlinks.add(link)

    return deadlinks

@app.command()
def main(url: str,
         save: Annotated[bool, typer.Option(help="Save output to csv file.")] = False):
    """
    Find deadlinks for any given URL.

    If --save is used as an option, saves results to csv in cwd.  
    """
    previously_discovered_links = set()
    links_and_pages = {}
    for page in find_pages(url):
        newly_discovered_links = find_links(page) - previously_discovered_links
        for link in newly_discovered_links:
            links_and_pages[link] = page
        previously_discovered_links.update(newly_discovered_links)

    links_to_check = list(links_and_pages.keys())
    discovered_deadlinks = asyncio.run(find_deadlinks(links_to_check))
    deadlinks_with_pages = {key: links_and_pages[key] for key in discovered_deadlinks if key in links_and_pages}

    table_data = []
    for link, page in deadlinks_with_pages.items():
        link_path = urlparse(link).path
        page_path = urlparse(page).path
        table_data.append((link_path[:80], page_path[:80]))
    print(tabulate(table_data, headers=["Deadlink", "Found on Page"]))

    if save:
        csv_filename = "py404.csv"
        with open(csv_filename, "w", newline="") as csvfile:
            csv_writer = csv.writer(csvfile)
            csv_writer.writerow(["Deadlink", "Found on Page"])  # Write headers
            csv_writer.writerows(table_data)  # Write data rows

        print(f"\nTable data saved to '{csv_filename}'")