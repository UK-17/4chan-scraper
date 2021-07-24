import logging
import logging.config
import os
from typing import List
import requests
from os import listdir
from PIL import Image
from bs4 import BeautifulSoup
from requests.models import Response
logging.config.fileConfig('logging.conf')
logger = logging.getLogger(__name__)

class Page:

    """ 
    4chan.org Random Board Image Extractor. Takes thread-id as input. Extracts all images from the thread,
    saves them in a folder then checks for corrupt images and deletes them.

    """
    
    BASE_URL = 'https://boards.4chan.org/b/thread/' # root URL for every thread on random board
    SAVE_DIR = str(os.curdir) # root folder for saving images 
    TIMEOUT = 10 # global timeout for requests made
    
    def __init__(self,thread:str) -> None:
        
        """ Inititalizing class and getting the page information. """
        
        logger.info(f'initializing Thread : {thread}')
        
        self.thread_id = thread # thread-ID from the board
        self.save_path = self.make_dir() # making a directory to save all images
        self.url = self.BASE_URL + thread # url of the thread
        self.page = self.get_page() # fetching the page
        self.soup = self.make_soup() # parsing the page
        self.images = self.get_images('img') # collection of all images in the page

    
    def make_dir(self) -> str:

        """ Name of the directory is same as the thread. """
        
        logger.info(f'Making directory to save all images')
        
        path = os.path.join(self.SAVE_DIR,self.thread_id)
        os.makedirs(path) # new directory made
        logger.info(f'New directory made: {path}')
        
        return str(path)

    
    def get_page(self) -> Response:
        
        """ Fetching HTML page using Requests library. """
        
        logger.info(f'Fetching page | URL:{self.url}')
        
        try:
            page = requests.get(self.url,timeout=Page.TIMEOUT) # page fetched
        except Exception as e:
            logger.error(e) # timeout error
            logger.critical(f'URL:{self.url} | Timeout {Page.TIMEOUT}s reached')
            page = None
        
        return page
    
    def make_soup(self) -> BeautifulSoup:

        """ Parsing the page using BeautifulSoup and HTML5LIB. """

        logger.info(f'Parsing HTML content | BeautifulSoup+html5lib')
        soup = BeautifulSoup(self.page.content,'html5lib') # making a soup-object
        
        return soup
    
    def get_images(self,tag:str) -> list:

        """ Extract all the links in the page with a given tag. """

        images = list()
        image_list = self.soup.select(tag) # select all elements with the specified tag
        
        logger.info(f'tag:{tag} | items:{image_list}')
        
        for image in image_list:
            image_link = 'https:'+image['src'] # extract the source link from the tag
            if '.jpg' in image_link: # avoid all other formats
                item = image_link.replace('i.4cdn.org','is2.4chan.org').replace('s.jpg','.jpg') # replace thumbnail links with original image 
                images.append(item)
        
        logger.info(f'No of images : {len(images)}')
        
        return images
    
    def get_image_file(self,image_link) -> bytes:
        
        """ Fetching an image in raw bytes. """
        
        logger.info(f'Fetching image | URL:{image_link}')
        
        try:
            image_file = requests.get(image_link,timeout=Page.TIMEOUT) # get request for the image
        except Exception as e:
            logger.error(e) # timeout error
            logger.critical(f'Timeout of {Page.TIMEOUT}s|URL:{image_link}')
            return None
        image_bytes = image_file.content # storing as bytes
        
        return image_bytes
    
    def save_image_file(self,image_bytes,image_path):
        
        """ Save each image to the directory. """
        
        logger.info(f'Writing image.')
        
        with open(image_path,'wb') as f: 
            f.write(image_bytes)
        
        return f'File : {image_path}'
    
    def get_and_save_all_images(self):
        
        """ Driver function to fetch and save each image in the list. """
        
        count =0 
        for image in self.images:
            count+=1
            image_bytes = self.get_image_file(image) #fetch the image
            if image_bytes is None:continue
            image_path = self.save_path+ f'/image_{count}.jpg' # path to save image 
            msg = self.save_image_file(image_bytes,image_path) # save image to path
            logger.info(f'Image saved as : {msg}')

    def check_for_corrupt_files(self):
        
        """ Verify the images and catch the corrupt ones."""
        
        self.corrupt_files = list()
        
        for filename in listdir(self.save_path):
            if filename.endswith('.jpg'):
                image_path = f'{self.save_path}/{filename}' # relative path of the image
                try:
                    img = Image.open(image_path) # open the image file
                    img.verify() # verify if image is corrupt
                except (IOError, SyntaxError) as e:
                    logger.error(e) # file is corrupt
                    logger.critical(f'Corrupt File : {filename}')
                    self.corrupt_files.append(image_path) # add file to list of corrupt images
        
        logger.critical(f'List of corrupt files:{self.corrupt_files}')
    
    def delete_corrupt_files(self):
        """ Delete the files which were categorized as corrupt. """

        logger.info('Removing corrupt images.')
        
        for file in self.corrupt_files:
            if os.path.exists(file): # check if file exists
                os.remove(file) # removing file from disk
                logger.info(f'{file} deleted.')
            else:
                logger.critical(f'{file} does not exist')

        

if __name__=="__main__":
    page = Page(input('Enter thread ID :'))
    page.get_and_save_all_images()
    page.check_for_corrupt_files()
    page.delete_corrupt_files()