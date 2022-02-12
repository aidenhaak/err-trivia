#!/usr/bin/python3

import argparse
import csv
import os.path
import sqlite3
from contextlib import closing

def parse_args():
    parser = argparse.ArgumentParser(description="Import questions from a CSV into a trivia SQLite database.")
    parser.add_argument("-q", "--questions", dest="questions_file", metavar="FILE", required=False,
                    help="The input CSV file to import questions from.")
    parser.add_argument("-w", "--words", dest="words_file", metavar="FILE", required=False,
                    help="The file to import words for scrambled word questions from.")
    parser.add_argument("-o", "-output", dest="output_file", metavar="FILE", required=True,
                    help="The output SQLite file to save questions to. If this file does not exist a new trivia SQLite database is created.")

    args = parser.parse_args()
    return args.questions_file, args.words_file, args.output_file

def create_schema(conn):
    with open("init.sql") as file:
        query = file.read()
        conn.executescript(query)

def import_questions(conn, questions_file):
    with open(questions_file, newline="") as file:
        reader = csv.reader(file)
        query = """
            INSERT INTO Questions ( Question, Answer ) VALUES ( ?, ? )
        """

        with closing(conn.cursor()) as cursor:
            for row in reader:
                cursor.execute(query, [row[0], row[1]])

def import_scrambled_words(conn, words_file):
    with open(words_file, newline="") as file:
        query = """
            INSERT INTO ScrambledWords ( Word ) VALUES ( ? )
        """

        with closing(conn.cursor()) as cursor:
            for line in file:
                cursor.execute(query, [line.strip()])

if __name__ == "__main__":
    questions_file, words_file, output_file = parse_args()

    output_file_exists = os.path.exists(output_file)

    with closing(sqlite3.connect(output_file)) as conn:
        if not output_file_exists:
            create_schema(conn)

        if questions_file:
            import_questions(conn, questions_file)

        if words_file:    
            import_scrambled_words(conn, words_file)

        conn.commit()
