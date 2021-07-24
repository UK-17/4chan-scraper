import logging
import logging.config
import os
import requests
from os import listdir
from PIL import Image
from bs4 import BeautifulSoup
logging.config.fileConfig('logging.conf')
logger = logging.getLogger(__name__)

class Page:
    
    BASE_URL = 'https://boards.4chan.org/b/thread/'
    SAVE_DIR = str(os.curdir)
    TIMEOUT = 10
    
    def __init__(self,thread:str) -> None:
        logger.info(f'initializing Thread : {thread}')
        self.thread_id = thread
        self.save_path = self.make_dir()
        self.url = self.BASE_URL + thread
        self.page = self.get_page()
        self.soup = self.make_soup()
        self.images = self.get_images('img')
    
    def make_dir(self):
        logger.info(f'Making directory to save all images')
        path = os.path.join(self.SAVE_DIR,self.thread_id)
        os.makedirs(path)
        logger.info(f'New directory made: {path}')
        return str(path)

    
    def get_page(self):
        logger.info(f'Fetching page | URL:{self.url}')
        try:
            page = requests.get(self.url,timeout=Page.TIMEOUT)
        except Exception as e:
            logger.error(e)
            logger.critical(f'URL:{self.url} | Timeout {Page.TIMEOUT}s reached')
            page = None
        return page
    
    def make_soup(self):
        logger.info(f'Parsing HTML content | BeautifulSoup+html5lib')
        soup = BeautifulSoup(self.page.content,'html5lib')
        return soup
    
    def get_images(self,tag:str):
        images = list()
        image_list = self.soup.select(tag)
        logger.info(f'tag:{tag} | items:{image_list}')
        for image in image_list:
            image_link = 'https:'+image['src']
            if '.jpg' in image_link:
                item = image_link.replace('i.4cdn.org','is2.4chan.org').replace('s.jpg','.jpg') 
                images.append(item)
        logger.info(f'No of images : {len(images)}')
        return images
    
    def get_image_file(self,image_link):
        logger.info(f'Fetching image | URL:{image_link}')
        try:
            image_file = requests.get(image_link,timeout=Page.TIMEOUT)
        except Exception as e:
            logger.error(e)
            logger.critical(f'Timeout of {Page.TIMEOUT}s|URL:{image_link}')
            return None
        image_bytes = image_file.content
        return image_bytes
    
    def save_image_file(self,image_bytes,image_path):
        logger.info(f'Writing image.')
        with open(image_path,'wb') as f: f.write(image_bytes)
        return f'File : {image_path}'
    
    def get_and_save_all_images(self):
        count =0 
        for image in self.images:
            count+=1
            image_bytes = self.get_image_file(image)
            if image_bytes is None:continue
            image_path = self.save_path+ f'/image_{count}.jpg'
            msg = self.save_image_file(image_bytes,image_path)
            logger.info(f'Image saved as : {msg}')

    def check_for_corrupt_files(self):
        self.corrupt_files = list()
        for filename in listdir(self.save_path):
            if filename.endswith('.jpg'):
                image_path = f'{self.save_path}/{filename}'
                try:
                    img = Image.open(image_path) # open the image file
                    img.verify() # verify that it is, in fact an image
                except (IOError, SyntaxError) as e:
                    logger.error(e)
                    logger.critical(f'Corrupt File : {filename}')
                    self.corrupt_files.append(image_path)
        logger.critical(f'List of corrupt files:{self.corrupt_files}')
    
    def delete_corrupt_files(self):
        logger.info('Removing corrupt images.')
        for file in self.corrupt_files:
            if os.path.exists(file):
                os.remove(file)
                logger.info(f'{file} deleted.')
            else:
                logger.critical(f'{file} does not exist')

        

if __name__=="__main__":
    page = Page(input('Enter thread ID :'))
    page.get_and_save_all_images()
    page.check_for_corrupt_files()
    page.delete_corrupt_files()