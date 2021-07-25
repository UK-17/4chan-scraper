import logging
import logging.config
import time
import os
from typing import List
import requests
from os import listdir
from PIL import Image
from bs4 import BeautifulSoup
import pandas as pd
from requests.models import Response
import json
logging.config.fileConfig('logging.conf')
logger = logging.getLogger(__name__)



class Metadata:
    
    """

    Extracting metadata about all the boards on 4chan using its API:
    1. Display List of boards on 4chan. Select a board from the list.
    2. Display all threads of the board.Select a thread from the list.

    """

    TIMEOUT = 10 # global timeout for request function
    BOARD_DATA = 'https://a.4cdn.org/boards.json' # to get list of boards
    CATALOG_DATA = 'https://a.4cdn.org/<board_code>/catalog.json' # to get threads list
    
    def __init__(self) -> None:
        
        """ Initialize all the metadata. Select board code. """

        print('\nGathering metadata on the threads...')
        self.boards_list = self.get_boards_list()
        self.board_code = self.select_board()
        self.threads = self.get_board_threads()
        self.thread_id = self.select_thread()
    
    def get_boards_list(self) -> dict:
        
        """ Get a list of image boards and codes. """

        print('\nFetching all the imageboards available...')
        try:
            response = requests.get(Metadata.BOARD_DATA,timeout=Metadata.TIMEOUT) # make request to API
        except Exception as e:
            logger.error(e) # error in making request
            logger.critical(f'Error in request. | URL : {Metadata.BOARD_DATA}')
            return None
        
        raw_data = json.loads(response.content)['boards'] # extract json from response
        boards_list = dict()
        
        for index,each in enumerate(raw_data):
            boards_list[str(index)] = {"board_name":each['title'], "board_code":each['board']} # make custom dictionary

        return boards_list
    
    def display_board_list(self) -> None:
        
        """ Display List of boards to select from """
        
        for index,details in self.boards_list.items():
            print(f"{index}.{details['board_name']}")
    
    def select_board(self) -> str:

        """ Driver function to select board. """
        
        print('\nSelect a board from the following:')
        self.display_board_list()
        selected_board_index = input('\nEnter Board Number:')
        selected_board_code = self.boards_list[selected_board_index]['board_code']
        return selected_board_code
    
    def get_board_threads(self) -> list:
        
        """ Get a list of threads available for the board """
        
        print(f'Getting list of threads currently on /{self.board_code} board...')
        threads_list = list()
        url = self.CATALOG_DATA.replace('<board_code>',self.board_code) # getting threads for selected board
        
        try:
            response = requests.get(url,timeout=self.TIMEOUT)
        except Exception as e:
            logger.error(e) # timeout error
            logger.critical(f'Error in request | URL:{url}')
            return None
        
        raw_data = json.loads(response.content)
        for each in raw_data:
            threads = each['threads']
            for thread in threads:
                thread_id = thread['no']
                thread_info = thread['semantic_url']
                no_of_images = int(thread['images'])
                if no_of_images>0: threads_list.append((thread_id,thread_info,no_of_images)) # Thread-ID|Label|Images
        
        return threads_list
    
    def display_threads_list(self) -> None:

        """ Display all threads on the selected board to select from. """
    
        display_view = pd.DataFrame(self.threads,columns=['Thread-ID','Label','Images'])
        display_view = display_view.sort_values(by='Images')
        print(f'\nThreads currently on /{self.board_code} board :')
        print(display_view.to_string(index=False))
    
    def select_thread(self) -> str:
       
        """ Select a thread from the list of threads displayed"""
       
        self.display_threads_list()
        thread_id = input('\nEnter Thread-ID : ')
        return thread_id

        

    

class Page:

    """ 
    Extract all images from a given 4chan thread.

    """
    
    BASE_URL = 'https://boards.4chan.org/<board_code>/thread/' # root URL for every thread on random board
    SAVE_DIR = str(os.curdir)+'/data'# root folder for saving images 
    TIMEOUT = 10 # global timeout for requests made
    
    def __init__(self,board_code,thread:str) -> None:
        
        """ Inititalizing class and getting the page information. """
        
        logger.info(f'initializing Thread : {thread}')
        self.BASE_URL = self.BASE_URL.replace('<board_code>',board_code)
        
        self.thread_id = thread # thread-ID from the board
        self.save_path = self.make_dir() # making a directory to save all images
        self.url = self.BASE_URL + thread # url of the thread
        self.page = self.get_page() # fetching the page
        self.soup = self.make_soup() # parsing the page
        self.images = self.get_images('img') # collection of all images in the page
        self.extract_images() # running the driver function

    
    def make_dir(self) -> str:

        """ Name of the directory is same as the thread. """
        
        print(f'\nMaking a new directory to save images...')
        path = os.path.join(self.SAVE_DIR,self.thread_id)
        os.makedirs(path) # new directory made
        logger.info(f'Image save directory: {path}')
        print(f'New directory : {str(path)}')
        
        return str(path)

    
    def get_page(self) -> Response:
        
        """ Fetching HTML page using Requests library. """
        
        logger.info(f'Fetching page | URL:{self.url}')
        
        print('\nGetting contents of the thread page...')
        try:
            page = requests.get(self.url,timeout=Page.TIMEOUT) # page fetched
        except Exception as e:
            logger.error(e) # timeout error
            logger.critical(f'URL:{self.url} | Timeout {Page.TIMEOUT}s reached')
            page = None
        
        return page
    
    def make_soup(self) -> BeautifulSoup:

        """ Parsing the page using BeautifulSoup and HTML5LIB. """

        print('Scanning and parsing the HTML page...')
        logger.info(f'Parsing HTML content | BeautifulSoup+html5lib')
        soup = BeautifulSoup(self.page.content,'html5lib') # making a soup-object
        
        return soup
    
    def get_images(self,tag:str) -> list:

        """ Extract all the links in the page with a given tag. """

        print('Extracting image links from the HTML page...')
        images = list()
        image_list = self.soup.select(tag) # select all elements with the specified tag
        
        logger.info(f'tag:{tag} | items:{image_list}')
        
        for image in image_list:
            
            image_link = 'https:'+image['src'] # extract the source link from the tag
            
            if '.jpg' in image_link: # avoid all other formats
                item = image_link.replace('i.4cdn.org','is2.4chan.org').replace('s.jpg','.jpg') # replace thumbnail links with original image 
                images.append(item)
            if '.png' in image_link:
                item = image_link.replace('i.4cdn.org','is2.4chan.org').replace('s.png','.png') # replace thumbnail links with original image 
                images.append(item)

        
        logger.info(f'No of images : {len(images)}')
        print(f'A total of {str(len(images))} image links found on the page.')
        
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
    
    def save_image_file(self,image_bytes,image_path) -> str:
        
        """ Save each image to the directory. """
        
        logger.info(f'Writing image.')
        
        with open(image_path,'wb') as f: 
            f.write(image_bytes)
        
        return f'File : {image_path}'
    
    def get_and_save_all_images(self) -> None:
        
        """ Driver function to fetch and save each image in the list. """
        
        count =0 
        for image in self.images:
            extension = 'jpg' if '.jpg' in image else 'png'
            count+=1
            print(f'Processing Image #{count}')
            image_bytes = self.get_image_file(image) #fetch the image
            if image_bytes is None:continue
            image_path = self.save_path+ f'/image_{count}.{extension}' # path to save image 
            msg = self.save_image_file(image_bytes,image_path) # save image to path
            logger.info(f'Image saved as : {msg}')

    def check_for_corrupt_files(self) -> None:
        
        """ Verify the images and catch the corrupt ones."""
        
        print('Waiting for images to get downloaded... ')
        time.sleep(10)
        print('Checking for corrupt files...')
        self.corrupt_files = list()
        
        for filename in listdir(self.save_path):
            if filename.endswith('.jpg') or filename.endswith('.png'):
                image_path = f'{self.save_path}/{filename}' # relative path of the image
                try:
                    img = Image.open(image_path) # open the image file
                    img.verify() # verify if image is corrupt
                except (IOError, SyntaxError) as e:
                    logger.error(e) # file is corrupt
                    logger.critical(f'Corrupt File : {filename}')
                    self.corrupt_files.append(image_path) # add file to list of corrupt images
        
        logger.critical(f'List of corrupt files:{self.corrupt_files}')
    
    def delete_corrupt_files(self) -> None:
        
        """ Delete the files which were categorized as corrupt. """

        logger.info('Removing corrupt images.')
        
        for file in self.corrupt_files:
            if os.path.exists(file): # check if file exists
                os.remove(file) # removing file from disk
                logger.info(f'{file} deleted.')
                print(f'Deleting {file} due to corruption...')
            else:
                logger.critical(f'{file} does not exist')
        
        logger.info(f'Removed {len(self.corrupt_files)} files.')
    
    def extract_images(self) -> None:

        """ Driver function to extract the images and save them. """

        self.get_and_save_all_images()
        self.check_for_corrupt_files()
        self.delete_corrupt_files()




def exec_main() -> None:
    
    """ Main driver function to run the code. """
    
    # welcome message
    print(f''' *** Welcome to 4chan-scraper.***
                   Author : Utkarsh-kushagra (UK!7)
            
            Step 1 : Choose a board of your interest
            Step 2 : Choose a thread from that board
            
            All the images from the board will be saved in the data folder.  ''')
    
    # pause introduced to read the message
    time.sleep(8)
    
    logger.info(f'Execution started.')
    metadata = Metadata()
    page = Page(metadata.board_code,metadata.thread_id)
    logger.info('Execution completed.')
    print(f'All your downloaded files are available here : {page.save_path}')
    
    # closing message 
    print('\nThanks for using 4chan-scraper.\n')



        

if __name__=="__main__":
    exec_main()