import pandas as pd
import time
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup


test = "43739.The_Invincible_Iron_Man?ref=nav_sb_ss_3_10"


class book_getter:

    def __init__(self):
        self.url = "https://www.goodreads.com/book/show/"
        try:
            self.driver = webdriver.Firefox()
        except:
            self.driver = webdriver.Chrome()
        self.genre_status = False
        self.details_status = False
        return
    
    #Function to go through and expand all sections of page
    def page_clicker(self, target):
        #Getting desired book target
        url = self.url + target
        self.driver.get(url)
        time.sleep(10)
        
        #Desired publication and ISBN is under a button. Target button and click to reveal for scraping.
        try:
            button_path = '/html/body/div[1]/div[2]/main/div[1]/div[2]/div[2]/div[2]/div[6]/div/div/button'
            button = self.driver.find_element(By.XPATH, button_path)
            button.click()
            time.sleep(2)
            self.details_status = True
        except Exception:
            pass
        

        #Also want to expand to get full list of genres for each book
        try:
            genre_path = "/html/body/div[1]/div[2]/main/div[1]/div[2]/div[2]/div[2]/div[5]/ul/div/button/span"
            genre_button = self.driver.find_element(By.XPATH, genre_path)
            genre_button.click()
            time.sleep(2)
            self.genre_status = True
        except Exception:
            pass

        page_clicked = self.driver.page_source
        self.driver.quit()
        return page_clicked
    
    #Need to clean some fields of the book up.
    def book_cleaner(self, book):
        #Separating the date and Publisher
        publication = book["publisher"]
        publication_pattern = r'\b\d{4}(?= by\b)'
        publication_match = re.search(publication_pattern, publication)

        if publication_match:
            date = publication_match.group(0)

            publisher = publication_match.end() +len(" by ")
            publisher = publication[publisher:].strip()
            book["publisher"] = publisher
            book["date"] = date
        else:
            book["publisher"] = "Unknown"
            book["date"] = "Unknown"

        #Separating the ISBN
        isbn = book["ISBN"]
        isbn_pattern = r'\b\d+\b'
        isbn_match = re.search(isbn_pattern, isbn)

        if isbn_match:
            book["ISBN"] = isbn_match.group(0)
        else:
            book["ISBN"] = 'Unknown'

        #Getting page numbers
        pages = book["pages"]
        page_template = r'(\d{1,3}(,\d{3})*)(?= pages)'
        page_match = re.search(page_template, pages)

        if page_match:
            page_number = page_match.group(0)
            book["pages"] = int(page_number.replace(',', ''))
        else:
            book["pages"] = "Unknown"

        #Getting ratings count
        ratings = book["totalratings"]
        ratings = ratings.replace(u'\xa0', u' ')
        ratings_pattern = r'^[^ ]+'
        ratings_match = re.search(ratings_pattern, ratings)
        
        if ratings_match:
            ratings = ratings_match.group(0)
            book["totalratings"] = int(ratings.replace(',', ''))
        else:
            book["totalratings"] = "Unknown"
        return book

    def get_book(self, target):
        try:
            page = self.page_clicker(target)
            soup = BeautifulSoup(page, "html.parser")
        except:
            problem = "There appears to be an issue with loading the page. Try again"
            return problem
            #Actually scrape desired information about book
        try:
            book = self.soup_strainer(soup)
            book = self.book_cleaner(book)
            return book
        except:
            problem = "There appears to be an issue with getting book details. Try again"
            return problem
    
    #Getting relevant book details
    def soup_strainer(self, soup):
        book = {
            "title" : soup.find("h1", {"class": "Text Text__title1", "data-testid":"bookTitle"}).text,
            "author" : soup.find("span", {"class": "ContributorLink__name", "data-testid": "name"}).text,
            "desciption": soup.find("span", {"class": "Formatted"}).text,
            "pages" : soup.find("p", {"data-testid" : "pagesFormat"}).text,
            "publisher" : self.get_publication_info(soup, self.details_status),
            "image" : soup.select("img[class=ResponsiveImage]")[0]['src'],
            "ISBN" : self.get_ISBN(soup, self.details_status),
            "genre" : self.genre_getter(soup, self.genre_status),
            "rating" : soup.find("div", {"class": "RatingStatistics__rating"}).text,
            "totalratings" : soup.find("span", {"data-testid": "ratingsCount"}).text, 
            }
        print(book)
        return book
        

    #Helper functions to get less straightforward info
    def genre_getter(self, soup, status):
        genres = []
        all_genres = soup.find_all("span", {"class": "BookPageMetadataSection__genreButton"})
        for genre in all_genres:
            genres.append(genre.text)

        if status == False:
            genres.append("Possibly Some Genres Not Included")

        return genres
    
    def get_publication_info(self, soup, status):
        if status == True:
            try:
                marker = soup.find(string = re.compile('Published')).parent
                pub_info = marker.next_sibling.text
                return pub_info
            except:
                return "0000 by Unknown"
        else:
            return "0000 by Unknown"
    
    def get_ISBN(self, soup, status):
        if status == True:
            try:
                marker = soup.find(string = re.compile('ISBN')).parent
                ISBN = marker.next_sibling.text
                return ISBN
            except:
                return "Unknown (could not find)"
        else:
            return 'Unknown (could not find)'


gettem = book_getter()
gettem.get_book(test)



#Should generally be good. Might need some tweaking to ensure unknowns are entered correctly.








