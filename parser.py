"""
This script is used to parse data from the GAPS system. It includes functions to request data, parse the HTML content,
extract tables from the HTML, convert these tables to pandas DataFrames, and convert these DataFrames to objects.

The main functions in this script are:
- request_data: Requests the data from GAPS and returns it as a string.
- parse: Parses the HTML content and returns a list of objects.
- extract_tables: Extracts tables from the HTML content.
- table_to_df: Converts the extracted tables to pandas DataFrames.
- df_to_object: Converts the DataFrames to objects.

This script uses the following libraries:
- requests: To send HTTP requests.
- BeautifulSoup: To parse the HTML content.
- pandas: To work with the data in a tabular format.
- re: To use regular expressions.
- io: To handle the StringIO object.
"""

import config
import requests
import re
from bs4 import BeautifulSoup
import pandas as pd
from io import StringIO


def request_data(cred):
    """
    Request the data from GAPS and return it as a string. Exits upon failure.

    :param cred: A keyring.Credential object containing the username and password
    :return: The HTML content of the GAPS page as a string
    """

    with requests.session() as request:
        print("Connection to GAPS...")
        login_data = {
            "login": cred.username,
            "password": cred.password,
            "submit": "enter",
        }
        grade_data = {
            "rs": "smartReplacePart",
            "rsargs": '["result","result",null,null,null,null]',
        }

        res = request.post(config.URL, data=login_data, headers=config.HEADER_DATA)

        # Check for our successful login indicator
        if res.text.find("Etat des contrôles continus") < 0:
            print("An error occured while fetching the data from GAPS")
            exit(1)
        else:
            res = request.post(config.URL, data=grade_data, headers=config.HEADER_DATA)
            if res.status_code != 200:
                print(
                    "An error occured while fetching the data. Http status: ",
                    res.status_code,
                )
                return None
            print("Successfully retrieved GAPS data")
            return re.sub(r"\\", "", res.content.decode("utf-8"))


def parse(content):
    """

    :param content: The HTML content of the page, unescaped and containing a valid HTML document tree
    :return: An array of objects containing the course name, grade, assessments grade plus data and practical work grade
             and data
    """

    soup = BeautifulSoup(content, "html.parser")
    tables = extract_tables(soup)
    dfs = table_to_df(tables)
    objects = []

    for df in dfs:
        objects.append(df_to_object(df))

    return objects


def extract_tables(soup):
    """
    Extracts the (sub)tables from the HTML content.

    :param soup: The BeautifulSoup object containing the HTML content
    :return: A list of tables per course containing the parsed data
    """

    groups = []
    current_group = []

    trs = list(soup.find_all('tr'))
    for i, tr in enumerate(trs):
        if i + 1 < len(trs):
            next_tr = trs[i + 1]
            if next_tr.find('td', {'class': 'bigheader'}):
                current_group.append(tr)
                groups.append(current_group)
                current_group = []
            else:
                current_group.append(tr)
        else:
            current_group.append(tr)
            groups.append(current_group)

    return groups


def table_to_df(tables):
    """
    Converts the tables to pandas DataFrames.

    :param tables: The list of tables to convert
    :return: A array of pandas DataFrames containing the GAPS grade data
    """

    dfs = []
    for table in tables:
        soup = BeautifulSoup('<table></table>', 'html.parser')
        table_tag = soup.table

        for tr in table:
            table_tag.append(tr)

        html_table = str(table_tag)
        html_io = StringIO(html_table)

        df = pd.read_html(html_io)[0]
        df.columns = ["Header", "Date", "Description", "Mean", "Weight", "Grade"]
        dfs.append(df)
    return dfs


def df_to_object(df):
    """
    Converts the DataFrames to a key-value dictionary containing the GAPS grade data with the following schema:
        course: The name of the course
        grade: The grade of the course
        course_grade: The grade of the assessments
        course_data: The DataFrame containing the assessments data
        lab_grade: The grade of the practical work
        lab_data: The DataFrame containing the practical work data

    :param df: The DataFrame to convert
    :return: A key-value dictionary containing the GAPS grade data
    """

    re_float = r"\d\.\d{1,2}"
    data = {}

    header = df.iloc[0].to_dict()["Header"]

    data["course"] = header.split(" ")[0] if header else None

    grade = re.findall(re_float, header)
    data["grade"] = grade[0] if grade else None

    # Extract the course grades
    subheaders = df.loc[df['Grade'] == 'note']["Header"]
    course_grade = re.findall(re_float, subheaders.values[0])
    data["course_grade"] = course_grade[0] if course_grade else None

    # Extract the lab grade if present
    lab_header = re.findall(re_float, subheaders.values[1]) if len(subheaders.values) > 1 else None
    data["lab_grade"] = lab_header[0] if lab_header else None

    # Drop the first column of the dataframe since it's not needed anymore
    df = df.drop(columns=["Header"])

    # Extract the course and lab dataframes
    if lab_header:
        data["course_data"] = df.iloc[subheaders.index[0] + 1: subheaders.index[1]].reset_index(drop=True)
        data["lab_data"] = df.iloc[subheaders.index[1] + 1:].reset_index(drop=True)
    else:
        data["course_data"] = df.iloc[subheaders.index[0] + 1:].reset_index(drop=True)

    return data
