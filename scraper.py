import json
import logging.config
import os
import shutil
import time
from io import BytesIO
from os import listdir
from pathlib import Path
from zipfile import ZipFile

import pandas as pd
import requests
from PIL import Image
from bs4 import BeautifulSoup

logging.config.fileConfig('logging.conf')
logger = logging.getLogger(__name__)

TIMEOUT = 10  # global timeout for request function


class Website:
    """
    The main 4chan page.

    """

    BOARD_DATA = 'https://a.4cdn.org/boards.json'  # to get list of boards

    def __init__(self) -> None:

        """ Initialize all the metadata. Select board code. """

        print('\nGathering metadata on the threads...')
        self.boards = []

    def fetch_boards(self) -> None:

        """ Get a list of image boards and codes. """

        print('\nFetching all the image boards available...')
        try:
            __response = requests.get(Website.BOARD_DATA, timeout=TIMEOUT)  # make request to API
            __board_data = json.loads(__response.content)['boards']
            self.boards = [Board(index=i + 1, b_data=board) for i, board in enumerate(__board_data)]
        except Exception as e:
            logger.error(e)  # error in making request
            logger.critical(f'Error in request. | URL : {Website.BOARD_DATA}')

    def display_boards(self) -> None:

        """ Display List of boards to select from """

        ch = int(input(
            '\n1.NSFW Boards\n2.General Boards\n3.All Boards\nEnter your choice:'))  # take choice on NSFW/SFW board.
        print('\nSelect a board from the following:')
        for board in self.boards:
            if (ch == 1 and not board.work_safe) or (ch == 2 and board.work_safe) or (ch == 3):
                print(f"{board.index}. {board.name}")


class Board:
    """
    Represents a board in 4chan.

    """

    def __init__(self, b_data: dict, index: int):
        self.index = index
        self.name = b_data['title']
        self.code = b_data['board']
        self.work_safe = b_data['ws_board']
        self.url = f'https://a.4cdn.org/{self.code}/catalog.json'
        self.threads = []

    def fetch_threads(self):

        """ Get a list of threads available for the board """

        print(f'Getting list of threads currently on /{self.name} board...')

        try:
            response = requests.get(self.url, timeout=TIMEOUT)
            threads_data = json.loads(response.content)
            self.threads = [Thread(t_data=thread_detail, b_code=self.code) for page in threads_data for thread_detail in
                            page['threads']]
        except Exception as e:
            logger.error(e)  # timeout error
            logger.critical(f'Error in request | URL:{self.url}')
            return

    def display_board_threads(self) -> None:

        """ Display all threads on the selected board to select from. """
        __threads = [{'Thread-ID': thread.id,
                      'Label': thread.info,
                      'Images': thread.images_count} for thread in self.threads]
        display_view = pd.DataFrame(__threads, columns=['Thread-ID', 'Label', 'Images'])
        display_view = display_view.sort_values(by='Images')
        print(f'\nThreads currently on /{self.name} board :')
        print(display_view.to_string(index=False))


class Thread:
    """
    Represents the webpage for a particular 4chan thread.

    """

    BASE_URL = 'https://boards.4chan.org/{board_code}/thread/'  # root URL for every thread on random board
    THREAD_METADATA = 'https://a.4cdn.org/{board_code}/thread/{thread_id}.json'  # gathering info about the thread
    SAVE_DIR = str(os.curdir)  # root folder for saving images

    def __init__(self, t_data: dict, b_code: int) -> None:

        """ Initializing class and getting the page information. """

        self.id = t_data['no']
        self.info = t_data['semantic_url']
        self.images_count = int(t_data['images'])
        self.images = []
        self.url = self.BASE_URL.format(board_code=b_code) + str(self.id)  # url of the thread
        self.save_path = None
        self.page = None
        self.soup = None
        self.is_completed = False
        self.corrupt_files = None

    def make_dir(self) -> None:

        """ Name of the directory is same as the thread. """

        print(f'\nMaking a new directory to save images...')
        path = os.path.join(self.SAVE_DIR, str(self.id))
        os.makedirs(path)  # new directory made
        logger.info(f'Image save directory: {path}')
        print(f'New directory : {str(path)}')

        self.save_path = str(path)

    def get_page(self) -> None:

        """ Fetching HTML page using Requests library. """

        logger.info(f'Fetching page | URL:{self.url}')

        print('\nGetting contents of the thread page...')
        try:
            page = requests.get(self.url, timeout=TIMEOUT)  # page fetched
        except Exception as e:
            logger.error(e)  # timeout error
            logger.critical(f'URL:{self.url} | Timeout {TIMEOUT}s reached')
            page = None

        self.page = page

    def make_soup(self) -> None:

        """ Parsing the page using BeautifulSoup and HTML5LIB. """

        print('Scanning and parsing the HTML page...')
        logger.info(f'Parsing HTML content | BeautifulSoup+html5lib')
        soup = BeautifulSoup(self.page.content, 'html5lib')  # making a soup-object

        self.soup = soup

    def get_images(self, tag: str) -> None:

        """ Extract all the links in the page with a given tag. """

        print('Extracting image links from the HTML page...')
        images = list()
        image_list = self.soup.select(tag)  # select all elements with the specified tag

        logger.info(f'tag:{tag} | items:{image_list}')

        for image in image_list:

            image_link = 'https:' + image['src']  # extract the source link from the tag

            if '.jpg' in image_link:  # avoid all other formats
                item = image_link.replace('i.4cdn.org', 'is2.4chan.org').replace('s.jpg',
                                                                                 '.jpg')
                # replace thumbnail links with original image
                images.append(item)
            if '.png' in image_link:
                item = image_link.replace('i.4cdn.org', 'is2.4chan.org').replace('s.png',
                                                                                 '.png')
                # replace thumbnail links with original image
                images.append(item)

        logger.info(f'No of images : {len(images)}')
        print(f'A total of {str(len(images))} image links found on the page.')

        self.images = images

    @staticmethod
    def get_image_file(image_link) -> bytes:

        """ Fetching an image in raw bytes. """

        logger.info(f'Fetching image | URL:{image_link}')

        try:
            image_file = requests.get(image_link, timeout=TIMEOUT)  # get request for the image
        except Exception as e:
            logger.error(e)  # timeout error
            logger.critical(f'Timeout of {TIMEOUT}s|URL:{image_link}')
            return bytearray()
        image_bytes = image_file.content  # storing as bytes

        return image_bytes

    @staticmethod
    def save_image_file(image_bytes, image_path) -> str:

        """ Save each image to the directory. """

        logger.info(f'Writing image.')

        try:
            img_file = Image.open(BytesIO(image_bytes))  # convert bytes to Image object
            img_file.save(fp=image_path, format=img_file.format)  # saving Image object
        except Exception as e:
            logger.error(e)
            logger.critical(f'Image:{image_path} could not be handled by PIL.Image')
            pass

        return f'File : {image_path}'

    def get_and_save_all_images(self) -> None:

        """ Driver function to fetch and save each image in the list. """

        count = 0
        for image in self.images:
            extension = 'jpg' if '.jpg' in image else 'png'
            count += 1
            print(f'Processing Image #{count}')
            image_bytes = self.get_image_file(image)  # fetch the image
            if image_bytes is None:
                continue
            image_path = self.save_path + f'/image_{count}.{extension}'  # path to save image
            msg = self.save_image_file(image_bytes, image_path)  # save image to path
            logger.info(f'Image saved as : {msg}')

    def check_for_corrupt_files(self) -> None:

        """ Verify the images and catch the corrupt ones."""

        print('Waiting for images to get downloaded... ')
        time.sleep(3)
        print('Checking for corrupt files...')
        self.corrupt_files = list()

        for filename in listdir(self.save_path):
            if filename.endswith('.jpg') or filename.endswith('.png'):
                image_path = f'{self.save_path}/{filename}'  # relative path of the image
                try:
                    img = Image.open(image_path)  # open the image file
                    img.verify()  # verify if image is corrupt
                except (IOError, SyntaxError) as e:
                    logger.error(e)  # file is corrupt
                    logger.critical(f'Corrupt File : {filename}')
                    self.corrupt_files.append(image_path)  # add file to list of corrupt images

        logger.critical(f'List of corrupt files:{self.corrupt_files}')

    def delete_corrupt_files(self) -> None:

        """ Delete the files which were categorized as corrupt. """

        logger.info('Removing corrupt images.')

        for file in self.corrupt_files:
            if os.path.exists(file):  # check if file exists
                os.remove(file)  # removing file from disk
                logger.info(f'{file} deleted.')
                print(f'Deleting {file} due to corruption...')
            else:
                logger.critical(f'{file} does not exist')

        logger.info(f'Removed {len(self.corrupt_files)} files.')

    def get_all_file_paths(self):
        """ Recursively getting all file paths of the save directory. """

        # initializing empty file paths list
        file_paths = []

        # crawling through directory and subdirectories
        for root, directories, files in os.walk(self.save_path):
            for filename in files:
                # join the two strings in order to form the full filepath.
                filepath = os.path.join(root, filename)
                file_paths.append(filepath)

        logger.debug(f'Files to archive : {file_paths}')
        # returning all file paths
        return file_paths

    def remove_dir(self):

        """ Removing temp folder and files. """

        try:
            shutil.rmtree(self.save_path)
        except Exception as e:
            logger.error(e)
            logger.critical(f'Could not remove {self.save_path}')

    def archive_dir(self) -> None:

        """ Archiving the thread images directory. """

        home_path = Path.home()
        logger.info(f'Archiving images to {home_path}')
        files_to_archive = self.get_all_file_paths()
        with ZipFile(f'{self.id}_{self.info}.zip', 'w') as zipper:
            # writing each file one by one
            for file in files_to_archive:
                zipper.write(file)

        shutil.move(f'{self.id}_{self.info}.zip', home_path)
        self.remove_dir()

    def extract_images(self) -> None:

        """ Driver function to extract the images and save them. """

        try:
            self.get_and_save_all_images()
            self.check_for_corrupt_files()
            self.delete_corrupt_files()
            self.archive_dir()
            flag = True

        except Exception as e:
            logger.error(e)
            logger.critical(f'Error in the driver function to extract images.')
            flag = False

        self.is_completed = flag


def exec_main() -> None:
    """ Main driver function to run the code. """

    # welcome message
    print(f''' *** Welcome to 4chan-scraper.***
                   Author : (UK!7)
            
            Step 1 : Choose a board of your interest
            Step 2 : Choose a thread from that board
            
            All the images from the board will be saved in a zip file.  ''')

    # menu driven execution
    while True:
        ch = input('''
        ----------------------
        1. Continue.
        2. Exit.
        Enter your choice : ''')

        if int(ch) == 2:
            break  # stopping execution

        logger.info(f'Execution started.')

        website = Website()
        website.fetch_boards()
        website.display_boards()

        board_ch = int(input('\nEnter Board Number:'))
        for board in website.boards:
            if board.index == board_ch:
                print(board.index)
                board.fetch_threads()
                board.display_board_threads()
                thread_id = int(input('\nEnter Thread-ID : '))
                for thread in board.threads:
                    if thread_id == thread.id:
                        thread.make_dir()
                        thread.get_page()
                        thread.make_soup()
                        thread.get_images('img')
                        thread.extract_images()
                        logger.info(f'Execution successful: {thread.is_completed}.')
                        print(f'All your downloaded files are available here : ')

    # closing message 
    print('''
    -----------------------------------------------
    Thank you for using 4chan-scraper. Bye-bye !!!
    -----------------------------------------------
    ''')


if __name__ == "__main__":
    exec_main()
