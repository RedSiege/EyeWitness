# Get Names from cert.sh and do a reverse DNS lookup.

# import libraries.
import requests
import pandas as pd
import os


# Get Initial results and build a list.
def runQuery():
    # Build the query and format it.
    query = input("Enter entity to search: ")
    query = query.replace(" ", "+")

    # Make the request to the webserver.
    request = requests.get(f"https://crt.sh/?q={query}")

    # Check for a 200 OK. If good, we proceed.
    if response.status_code == 200:
        print(f"[+] Succeeded with status code: {request.status_code}.")
        dfs = pd.read_html(request.text)
        df = dfs[2]
        common_name = df["Common Name"]
        common_name = common_name.drop_duplicates()
        common_name = common_name.str.replace(r"\*.", "", regex=True)
        common_name.to_csv("common_names", header=False, index=False)

    # If we get anything other than a 200 OK, we print the error code.
    else:
        print(f"Failed with status code: {request.status_code}.")
        exit()


# Create a function that will run the Python command. Looks for common web ports.
# I should probably implement the Python Nmap library in the future.
# This works for now.
def runScan():
    os.system("nmap -T4 -p 80,443,8080 --open -iL common_names -oX list.xml")


# This runs eyewitness.
def getScreens():
    os.system("/usr/bin/python3 EyeWitness.py -x list.xml --web")


# Run the script, function-by-function.
runQuery()
runScan()
getScreens()
