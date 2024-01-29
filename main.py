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


def display_data():
    cred = get_credentials()
    data = parser.request_data(cred)
    parser.parse_data(data)
    # Print a full width dataframe
    parser.pd.set_option("display.max_colwidth", 30)
    print(parser.df)
    mean = parser.compute_mean()
    print("Overall mean:", mean)


def main():
    try:
        opt_parser = argparse.ArgumentParser(description="Fetch grades from the GAPS system.")
        opt_parser.add_argument("-l", "--login", action="store_true", help="input or replace the login credentials")
        opt_parser.add_argument("-d", "--daemon", action="store_true", help="run in daemon mode")
        args = opt_parser.parse_args()

        if args.login:
            save_credentials()
        else:
            display_data()

    except KeyboardInterrupt:
        print("\nProgram interrupted by user. Exiting...")
        sys.exit(0)


if __name__ == "__main__":
    main()
