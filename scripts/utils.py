
#helper functions that are gonna be used for the scraping pipeline

# This contains utility functions that are gonna be used in:
# -> folder management
# ->logging setup
# -> URL Validation
# -> Hash generation for unique ids


#importing the required libraries
import os
import hashlib
import logging
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

#code for folder structure
def directory_setup(base_path = "data/raw"):

    # This creates a folder structure that will store the scrapped data from the websites

    # argument: base path (path in which the scrapped data needs to be stored)
    
    # Return: Dictionary: Paths to the subfolders


    paths = {
        "screenshots": Path(base_path) / "screenshots",
        "dom": Path(base_path) / "dom",
        "metadata": Path(base_path) / "metadata"
    }

    #create the path if it does not exist originally:
    for name, path in paths.items():
        path.mkdir(parents = True, exist_ok=True)
        print(f"Directory ready: {path}")

    return paths


#code for setting up the log files:
def setup_log(log_file = "logs/scraping.log"):

    # Configuring the logging to botht the files and the console

    # the use of log file is to:
    # -> Track which URLs were scraped successfully
    # -> Which URLs failed and the reason behind it
    # ->The overall progress


    #creating the log directory
    Path(log_file).parent.mkdir(parents = True, exist_ok = True)

    #defining the logging format:
    logging.basicConfig(

        #this captures INFO, WARNING, ERROR, CRITICAL
        level=logging.INFO,
        
        #set the format of the log
        format='%(asctime)s | %(levelname)s | %(message)s',
        
        handlers=[
            #saves the output to the log folder
            logging.FileHandler(log_file),
            #prints the output to the console
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)


#code to generate unique ids to each url
def get_page_id(url):

    # Generate unique ID for each URL using the MD5 hash method
    # This will become the filename for screenshotsand DOM Files

    # argument: URL of the webpages

    # Returns: string: 12 character unique IDs for each URL

    return hashlib.md5(url.encode()).hexdigest()[:12]


#code to check if the URL entered is valid or not
def valid_url(url):

    # This will check if the URL is valid and can be scrapped successfully or not

    # Argument: Website URL

    # Returns: bool: Whether the file is scrapable or not

    try:
        result = urlparse(url) #break the url into protocol, domain, path etc.

        # Must have scheme (http/https) and domain
        #this will reject URLs like : ftp://, file:// or javascript files
        return all([result.scheme in ['http', 'https'], result.netloc])
    
    except ValueError:
        return False


#code to get the domain name:
def domain_name(url):
    
    # Gets the domain name from the URLs

    # Argument: URL of the websites

    # Returns: string: domain name of the website

    # eg. google.com from https://google.com/search?=darkSite/

    domain = urlparse(url).netloc

    # Remove 'www.' prefix if present
    if domain.startswith('www.'):
        domain = domain[4:]
    return domain


#loading the completed URLs from the metadata
def load_complete_urls(metadata_path = "data/raw/metadata/scraped_urls.txt"):

    # Gets the list of already scraped URLs

    # This is useful if the scraping process in continued after the paus, then it wont scrape the already scraped websites

    # This is useful when:
    # - Resuming after a crash
    # - Running scraper in multiple sessions

    # Returns: set: URLs that have already been scraped

    completed = set()
    
    if os.path.exists(metadata_path):
        with open(metadata_path, 'r') as f:
            completed = set(line.strip() for line in f)
        print(f"Successfully Loaded {len(completed)} previously scraped URLs")
    
    return completed

#saving the successfully scraped website to the metadata
def save_completed_website(url,metadata_path = "data/raw/metadata/scraped_urls.txt"):
    """
    Appends the URL to the metadata
    """
    with open(metadata_path, 'a') as f:
        f.write(url + '\n')
     