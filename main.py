import math
import requests
import pandas as pd
from dateutil import parser
import re
import keyring as kr
import getpass
from bs4 import BeautifulSoup

# Constants
APP_NAME = "autogaps"
URL_BASE = "https://gaps.heig-vd.ch/consultation.php"  # GAPS login url
URL = "https://gaps.heig-vd.ch/consultation/controlescontinus/consultation.php"
HEADER_DATA = {
    # "Accept-Encoding": "gzip, deflate, br"
    # "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0"
    # "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    # "Accept-Language": "fr,fr-FR;q=0.8,en-US;q=0.5,en;q=0.3",
}

RE_FLOAT = r"\d\.\d{1,2}"
RE_BRANCH = r"[A-Z]{3}"
RE_DATE = r"\d{1,2}\.\d{1,2}\.\d{2,4}"
RE_STRING = r"[\sA-Za-z]+"

df = pd.DataFrame(
    columns=["Subject", "Subject avg", "Lab", "Course", "Date", "Name", "Grade", "Mean", "Weight"]
)


# Save the credentials to system keyring
def save_credentials():
    # TODO check that no credentials exist, otherwise override
    print("Your AAI credentials will be stored in the system keyring.")
    username = input("Input your username (first.last): ")
    password = getpass.getpass("Enter your password: ")
    kr.set_password(APP_NAME, username, password)  # TODO add try/except


# Could use some error handling
def get_credentials():
    cred = kr.get_credential(APP_NAME, None)
    if cred is None:
        save_credentials()
        cred = kr.get_credential(APP_NAME, "")
    assert cred is not None
    return cred


def request_data(cred):
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

        res = request.post(URL, data=login_data, headers=HEADER_DATA)

        # Check for our successful login indicator
        if res.text.find("Etat des contrôles continus") < 0:
            print("An error occured while fetching the data from GAPS")
            exit(1)
        else:
            res = request.post(URL, data=grade_data, headers=HEADER_DATA)
            if res.status_code != 200:
                print(
                    "An error occured while fetching the data. Http status: ",
                    res.status_code,
                )
                return None
            print("Successfully retrieved GAPS data")
            return res.content.decode("unicode-escape").replace('\\', "")


def parse_data(content):
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
                    data["date"] = parser.parse(cell.text).strftime("%Y-%m-%d")
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


def main():
    cred = get_credentials()
    data = request_data(cred)
    parse_data(data)
    # Print a full width dataframe
    pd.set_option("display.max_colwidth", 30)
    print(df)
    mean = compute_mean()
    print("Overall mean:", mean)


if __name__ == "__main__":
    main()
