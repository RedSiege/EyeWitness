# Get Names from cert.sh and do a reverse DNS lookup.
# This is a totally janky script, but it does what I need it to do for now.


# import libraries.
import requests
import pandas as pd
import os


# Get Initial results and build a list.
def runQuery():
    # Build the query and format it.
    query = input("Enter entity to search: ")
    query = query.replace(" ", "+")

    # Craft a request.
    request = requests.get(f"https://crt.sh/?q={query}")

    # Check if the request's status code is a 200 OK.
    # If so, proceed to get the common names.
    if request.status_code == 200:
        print(f"[+] Succeeded with status code: {request.status_code}.")
        dfs = pd.read_html(request.text)
        df = dfs[2]
        common_name = df["Common Name"]
        common_name = common_name.drop_duplicates()
        common_name = common_name.str.replace(r"\*.", "", regex=True)
        common_name.to_csv("common_names", header=False, index=False)

    # If we don't get a 200 response code. Print error code and exit.
    else:
        print(f"Failed with status code: {request.status_code}.")
        exit()


# Define the function, runScan. I will probably start using the Python nmap library later, but this works for now.
def runScan():
    # This is just a regular nmap scan looking for common web ports against the hosts we pulled from the runQuery function.
    # It will export to an xml file for our next step.
    os.system("nmap -T4 -p 80,443,8080 --open -iL common_names -oX list.xml")


# This just runs eyewitness. There is probably a better way to do this.
def getScreens():
    # Runs EyeWitness against our target list.
    os.system("/usr/bin/python3 EyeWitness.py -x list.xml --web")


# Run the script as its three individual functions.
runQuery()
runScan()
getScreens()
