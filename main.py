import config
import argparse
import logging
import sys
import parser
import re
import keyring as kr
import getpass

# Logger setup
logging.basicConfig(format='%(levelname)s: %(message)s')


def save_credentials():
    """
    Save the user's credentials to the system keyring. Exits upon failure
    """

    logging.info("Your AAI credentials will be stored in the system keyring.")
    username = input("Enter your username (first.last): ")
    password = getpass.getpass("Enter your password: ")

    # Validate the input
    if not username or not password:
        logging.error("You must enter a username and a password")
        exit(1)
    elif not re.match(r"^[a-z]+\.[a-z]+$", username):
        logging.error("The username must be in the format first.last")
        exit(1)

    # Save the credentials to the system keyring
    try:
        kr.set_password(config.APP_NAME, username, password)
    except kr.errors.KeyringError as e:
        logging.error("Failed to store credentials in keychain: %s", e)
        exit(1)
    except kr.errors.PasswordSetError:
        logging.error("An error occured while saving the credentials")
        exit(1)
    except Exception as e:
        logging.error("An unknown error occured while saving the credentials: %s", e)
        exit(1)
    else:
        logging.info("Credentials successfully saved to system keyring")


def get_credentials():
    """
    Retrieve the user's credentials from the system keyring. Exits upon failure.

    :return: A keyring.Credential object containing the username and password
    :rtype: keyring.Credential
    """
    cred = None

    # Try to retrieve the credentials from the system keyring
    try:
        cred = kr.get_credential(config.APP_NAME, None)
    except kr.errors.KeyringError as e:
        logging.error("Failed to retrieve credentials from keychain: %s", e)
    except Exception as e:
        logging.error("An unexpected error occurred: %s", e)

    # If the credentials are not found, display a message and exit.
    if cred is None:
        logging.error("Failed to retrieve credentials. Please use `./autogaps.py --login` to save your login details "
                      "to the system keyring.")
        exit(1)

    return cred


def compute_mean(data):
    """
    Compute the mean of the grades in the subject key

    :param data: The object containing the parsed GAPS data
    :return: The mean of the grades
    :rtype: float
    """

    grades = [float(course["grade"]) for course in data if course["grade"] is not None]
    return sum(grades) / len(grades) if grades else 0


def display_data(data):
    for row in data:
        print("{}: {}".format(row["course"], row["grade"]))

        assessment_data = row["assessment_data"].drop(columns=["Mean", "Weight"]).to_string(header=False, index=False, justify='left')
        print("Assessments: {}\n{}".format(row["course_grade"], assessment_data))

        if "practical_work_data" in row and row["practical_work_data"] is not None:
            practical_work_data = row["practical_work_data"].drop(columns=["Mean", "Weight"]).to_string(header=False, index=False, justify='left')
            print("Practical work: {}\n{}".format(row["lab_grade"], practical_work_data))

        print("")

    print("Overall mean: {}".format(compute_mean(data)))


def main():
    try:
        opt_parser = argparse.ArgumentParser(description="Fetch grades from the GAPS system.")
        opt_parser.add_argument("-l", "--login", action="store_true", help="input or replace the login credentials")
        opt_parser.add_argument("-d", "--daemon", action="store_true", help="run in daemon mode")
        args = opt_parser.parse_args()

        if args.login:
            save_credentials()
        else:
            cred = get_credentials()
            data = parser.request_data(cred)
            data = parser.parse(data)
            display_data(data)

    except KeyboardInterrupt:
        print("\nProgram interrupted by user. Exiting...")
        sys.exit(0)


if __name__ == "__main__":
    main()
