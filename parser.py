import config
import requests
import re
from bs4 import BeautifulSoup
import pandas as pd
from dateutil import parser as date_parser

RE_FLOAT = r"\d\.\d{1,2}"
RE_BRANCH = r"[A-Z]{3}"
RE_DATE = r"\d{1,2}\.\d{1,2}\.\d{2,4}"
RE_STRING = r"[\sA-Za-z]+"

# Pandas setup
df = pd.DataFrame(
    columns=["Subject", "Subject avg", "Lab", "Course", "Date", "Name", "Grade", "Mean", "Weight"]
)


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


def parse_data(content):
    """
    Parse the GAPS HTML data

    :param content: The GAPS HTML data to parse
    """
    soup = BeautifulSoup(content, "html.parser")

    # Create an dictionary to store the data

    rows = soup.find_all("tr")
    data = {
        "subject": "",
        "subject_avg": None,
        "lab": None,
        "course": None,
        "date": "",
        "name": "",
        "mean": "",
        "weight": "",
        "grade": "",
    }

    for i in range(len(rows)):
        row = rows[i]

        # Iterate on cells
        cells = row.find_all("td")
        for cell in cells:
            # Handle header row
            if cell.text in ["date", "descriptif", "moyenne", "coef.", "note"]:
                pass
            elif "poids" in cell.text:  # Parse subheader
                # Handle "project" case
                if "Labo" in cell.text:
                    data["lab"] = re.findall(RE_FLOAT, cell.text)[0] or None
                elif "Cours" in cell.text:
                    course = re.findall(RE_FLOAT, cell.text)
                    # FIXME: we wrongly find a course for all branches, even if there is none
                    if len(course) > 0:
                        data["course"] = course[0]
                    else:
                        data["course"] = None
            elif "moyenne" in cell.text:  # Parse header
                data["subject"] = re.findall(RE_BRANCH, cell.text)[0]
                grade_avg = re.findall(RE_FLOAT, cell.text)
                # Check if a grade was found, otherwise set it to "-"
                if len(grade_avg) > 0:
                    data["subject_avg"] = grade_avg[0]
                else:
                    data["subject_avg"] = None
            # Handle sub rows
            else:
                if re.match(RE_DATE, cell.text):  # Parse date
                    data["date"] = date_parser.parse(cell.text).strftime("%Y-%m-%d")
                elif re.match(RE_STRING, cell.text):  # Parse name
                    # Check if a subtag div.onclick exists
                    if cell.findAll("div", {"id": re.compile(r"long__lm_")}):
                        data["name"] = cell.find(
                            "div", {"id": re.compile(r"long__lm_")}
                        ).text.strip()
                    else:
                        data["name"] = cell.text
                elif re.match(RE_FLOAT, cell.text):  # Parse mean, weight and grade
                    data["mean"] = cell.text
                    data["weight"] = cells[3].text
                    data["grade"] = cells[4].text
                    write_all(data)
                    break


def write_all(data):
    # Add data to the df dataframe
    df.loc[len(df)] = [
        data["subject"],
        data["subject_avg"],
        data["lab"],
        data["course"],
        data["date"],
        data["name"],
        data["grade"],
        data["mean"],
        data["weight"],
    ]


def compute_mean():
    # Extract the subject and subject_avg columns
    df1 = df[["Subject", "Subject avg"]].drop_duplicates()
    df2 = df1["Subject avg"]
    # Convert the subject_avg column to numeric
    df2 = pd.to_numeric(df2, errors="coerce")
    return round(df2.mean(), 2)
