import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import sqlite3 as sql
from IPython.display import display
import requests
import h5py
import os

from PIL import Image
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from scipy.sparse import csr_matrix



class book_predictor:
    def __init__(self): 
        #Load up the data. #Don't want to drop user ratings that might be NaN. Replace with 0
        self.main = pd.read_csv('./Data/100k_books.csv').dropna()
        self.books = pd.read_csv('./Data/Books.csv', header= 0).dropna()
        self.ratings = pd.read_csv('./Data/Ratings.csv', header = 0).fillna(0)

        #Holdings for matrices that will be used
        self.similarity_descriptions = None
        self.cleaned_ratings = None

        
        self.data_clean()
        self.initial_similarity_data()
        self.show_books()
        return
    
    ############## Data Cleaning and Management Functions ##############
    
    def data_clean(self, rate_threshold = 50):
        if self.table_exists('books') == True:
            return print("The books database already exists")
        else:
            print("Creating database for books...")
            #Unifying the book list, primarily using the main dataframe. 
            df = pd.merge(self.main, self.books, left_on='isbn', right_on='ISBN', how='left')

            #Cleaning up merged dataframes
            ##Getting Rid of redundant columns 
            to_keep = ['isbn', 'title', 'author', 'desc', 'pages',
                    'Year-Of-Publication', 'Publisher',  'genre', 
                        'img', 'rating', 'totalratings']
            df = df[to_keep].fillna('Unknown')

            ##From initial dataset, want books that have been rated by at least several people, use 50 for now. Could change it.
            df = df[df['totalratings'] >= rate_threshold]

            ##Some books appear to have many authors and very long titles, lets truncate that ******POSSIBLY USE REGEX IN THE FUTURE******
            ##We do want to maintain full authors and titles for display purposes.
            df['author_short'] = df['author'].apply(lambda x: x[:20] + '...' if len(x) > 20 else x)
            df['title_short'] = df['title'].apply(lambda x: x[:20] + '...' if len(x) > 20 else x)

            df.reset_index(inplace=True, drop=True)

            #Saving dataframe as a sqldatabase so that it can be easily accessed
            conn = sql.connect('./Data/database.db')
            df.to_sql(name = 'books', con = conn)
            conn.close()

            self.books = df
            return print("Book database created!")
    
    def show_books(self):
        display(self.books.columns)
        return
    

    #############Need Function to Add a Book#############
    def add_book(self, book_info):
        conn = sql.connect('./Data/database.db')
        df = pd.read_sql('SELECT * FROM books', conn)
        

    #Interaction with the webscraper goes here




        conn.close()
        return



    ############## Exploratory Data Analysis Functions ##############
    
    #Function to generate a barplot. Label is author or title, metric is some generated metric
    def top_n_barplot(data, labels, metric, top_n, horizontal = True, title = None):
        sorted = data.sort_values(by = metric, ascending = False)
        metric_order = sorted[labels].iloc[:top_n]
        plt.figure()
        
        #give option for horizontal or vertical barplots
        if horizontal == False:
            sns.barplot(data = sorted, x = labels, y = metric, hue = labels, legend = None, order = metric_order)
        else:
            sns.barplot(data = sorted, y = labels, x = metric, hue = labels, legend = None, order = metric_order)

        if title != None:
            plt.title(title)

        plt.tight_layout()
        plt.show()
        plt.close()
        return
    
    #Function to look at some common metrics: Most prolific authors, highest rated authors, highest rated books, and most read books
    def exploratory_data_analysis(self, top_n = 5):

        #Getting data
        conn = sql.connect('./Data/database.db')
        df = pd.read_sql('SELECT * FROM books', conn)

        #Getting authors by rating and num of books for analysis
        authors = df.groupby(['author_short'], as_index = False).agg({'title':'size', 'rating':'mean'}).rename(columns = {'title':'Count', 'rating': 'Average_Rating'})
        
        try:
            authors.to_sql(name = 'authors', con = conn)
        except:
            print("Authors table already in database")

        conn.close()

        #Getting some common metrics
        data = [authors, authors, df, df]
        labels = ['author_short', 'author_short', 'title_short', 'title_short']
        metrics = ['Count', 'Average_Rating', 'rating', 'totalratings']
        titles = ['The Most Prolific Authors', 'The Highest Rated Authors', 'The Highest Rated Books', 'The Most Read Books (By # of Ratings)']
        for i in range(len(labels)):
            self.top_n_barplot(data = data[i], labels = labels[i], metric = metrics[i], top_n = top_n, title = titles[i])
        
        return



    ############## Book Description Similarity Functions ##############

    #Using TFID to turn book descriptions to vectors for similiarity calculations.
    def initial_similarity_data(self):

    
        print("Computing similarities based on book descriptions...")
        #Getting data
        conn = sql.connect('./Data/database.db')
        df = pd.read_sql('SELECT * FROM books', conn)
        conn.close()
        
        print("Processing (this might take a moment)...")
        #Using batches for ease of processing
        n = len(df)
        vectorizer = TfidfVectorizer()
        batch_size = 5000
        num_of_batches = (n // batch_size) +1
        similarity = np.zeros((n, n), dtype=np.int32)

        for i in range(num_of_batches):
            start = batch_size * i
            end = min(n, (i +1) * batch_size)

            batch = df['desc'][start:end]
            transformed_tfid_batch = vectorizer.fit_transform(batch)
            batch_similarity = cosine_similarity(transformed_tfid_batch, transformed_tfid_batch)
            similarity[start:end, start:end] = batch_similarity

        print("Batch processing completed!")
        print("Saving so this isn't needed again (unless a new book is added)...")
        
        self.similarity_descriptions = pd.DataFrame(similarity)
        return print("Book similartiies computed!")
        
    #Updating the similiariy table to be called when books are added
    def update_similarity_data(self):
        return

    #Functions for taking a desired book and getting similar titles based on description
    def get_similar(self, similarity, target_index, n):
        similar = similarity.iloc[:, target_index]
        results = similar.sort_values(ascending=False)
        results = results[1:n+1]
        results = results.index
        return results

    #Convert found books to readable titles.
    def title_lookup(self, df, indicies):
        titles = []
        for index in indicies:
            title = df['title'].iloc[index]
            titles.append(title)
        return titles

    #Take target book and get similiar based on descriptions
    def description_similarity(self, target, n = 5):
        #Getting needed data
        conn = sql.connect('./Data/database.db')
        df = pd.read_sql('SELECT * FROM books', conn)
        conn.close()
        
        print(f"Finding books similar to {df.loc[target, 'title']}")

        results = self.get_similar(self.similarity_descriptions, target, n)
        results = self.title_lookup(df, results)
        return results



   
    
    

pred = book_predictor()
pred.description_similarity(2)






