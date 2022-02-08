#!/usr/bin/python3

import argparse
import csv
import os.path
import sqlite3
from contextlib import closing

def parse_args():
    parser = argparse.ArgumentParser(description="Import questions from a CSV into a trivia SQLite database.")
    parser.add_argument("-i", "--input", dest="input_file", metavar="FILE", required=True,
                    help="The input CSV file to import questions from.")
    parser.add_argument("-o", "-output", dest="output_file", metavar="FILE", required=True,
                    help="The output SQLite file to save questions to. If this file does not exist a new trivia SQLite database is created.")

    args = parser.parse_args()
    return args.input_file, args.output_file

def create_schema(conn):
    with open("init.sql") as file:
        query = file.read()
        conn.executescript(query)

def import_questions(input_file, output_file):
    output_file_exists = os.path.exists(output_file)

    with closing(sqlite3.connect(output_file)) as conn:
        if not output_file_exists:
            create_schema(conn)

        with open(input_file, newline="") as csv_file:
            reader = csv.reader(csv_file)
            query = """
                INSERT INTO Questions ( Question, Answer ) VALUES ( ?, ? )
            """

            with closing(conn.cursor()) as cursor:
                for row in reader:
                    cursor.execute(query, [row[0], row[1]])

        conn.commit()

if __name__ == "__main__":
    input_file, output_file = parse_args()
    import_questions(input_file, output_file)
