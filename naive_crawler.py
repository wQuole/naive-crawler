import re
import storage
import args
import requests
import concurrent.futures
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin


class NaiveCrawler:
    def __init__(self, initial_url, allowed_domains, depth, database, init=True):
        self.init = init
        self.initial_url = initial_url
        self.current_url = ""
        self.allowed_domains = allowed_domains
        self.depth = depth
        self.links_to_visit = set()
        self.visited_links = set()
        self.db = database
        self.recall_last_crawl()
        self.display_status_on_init()

        
    @staticmethod
    def is_absolute(url):
        return bool(urlparse(url).netloc)

    
    def recall_last_crawl(self):
        try:
            prev_state = self.db.json_load()
            if prev_state:
                self.current_url = prev_state["current_url"]
                self.visited_links = set(prev_state["visited_links"])
                self.links_to_visit = set(prev_state["links_to_visit"])
                self.initial_url = self.current_url
                self.init = False
            else:
                pass
        except Exception as ex:
            return ex


    def display_status_on_init(self):
        print(f"\U0001F7E2\tCrawler starting at:\n{self.current_url}\n")
        print(f"\U0001F645\tRestricted to crawl {len(self.allowed_domains)} domain(s):\n{self.allowed_domains} for depth: {self.depth}")



    def is_valid(self, candidate):
        if candidate in self.visited_links:
            return False   
        
        if  re.search('tel:', candidate)\
            or re.search('mailto:', candidate)\
            or re.search('#', candidate):
            return False

        # Fetch domain name (including potential subdomain)
        current_domain_name = urlparse(candidate).netloc
        # try:
        #     current_subdomain = current_domain_name.split('.')[0]
        # except Exception:
        #     # No subdomain
        #     pass

        # Validate if traversal is restricted
        if current_domain_name not in self.allowed_domains:
            return False
            

        url_ojbect = urlparse(candidate)
        return any([url_ojbect.scheme, url_ojbect.netloc, url_ojbect.path])


    @staticmethod    
    def get_relative_path(href):
        if href.startswith("/"):
            return href[1:len(href)]
        return href

    
    def get_links(self):
        try:
            if self.init:
                self.links_to_visit.add(self.initial_url)
                self.init = False

            # Pop out an arbitrary element from the set
            self.current_link = self.links_to_visit.pop()
            
            current_page = requests.get(self.current_link)
            print(f"\n\U0001F577\U0001F578\tCrawler \U0001F440 at:\n{self.current_link}")

            self.visited_links.add(self.current_link)

            soup = BeautifulSoup(current_page.content, 'html.parser')
            
            return soup.find_all('a')

        except Exception:
            print("\U0001F6AB Invalid URL.")
            return False
        

    def crawl(self):
        links = self.get_links()

        if links:
            for i, link in enumerate(links):
                if link is not None:
                    link_href = link.get('href')
                    
                    if not self.is_absolute(link_href):
                        relative_path = self.get_relative_path(link_href)
                        parsed_linked_href = urlparse(link_href)
                        scheme = parsed_linked_href.scheme

                        current_domain_name = urlparse(self.current_link).netloc
                        if not scheme: scheme = 'http'
                        link_href = f"{scheme}://{current_domain_name}/{relative_path}"

                    if not self.is_valid(link_href):
                        continue
                    self.links_to_visit.add(link_href)

        print(f"Links to visit: {len(self.links_to_visit)}")
            

    
    def initium(self):
        try:
            if self.init:
                threads = 1
            else:
                threads = min(32, len(self.links_to_visit)+1)

            for i in range(self.depth):
                # print(f'\n\U0001F577\U0001F578\tCrawler_{i}')
                with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as dominus:
                    dominus.submit(self.crawl())
            
            print(f"\U0001F534\tCrawler stopped after crawling {len(self.visited_links)} link(s).")
            print(f"\U0001F481\tFound {len(self.links_to_visit)} page(s) to crawl.\n")

            # Save the state
            self.salvare()
            
        except Exception as ex:
            print(f"The following error occured:\n{ex}")
            return


    def salvare(self):
        state = {
        "current_url": self.current_link,
        "visited_links": list(self.visited_links),
        "links_to_visit": list(self.links_to_visit)
        }
        
        self.db.json_save(state)

