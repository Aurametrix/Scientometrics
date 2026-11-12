import requests
import csv
import os
import time

def get_abstract_by_doi(doi):
    """
    Fetches the title, year, and abstract of a paper using its DOI 
    via the Semantic Scholar API.
    """
    clean_doi = doi.replace("https://doi.org/", "").strip()
    
    url = f"https://api.semanticscholar.org/graph/v1/paper/DOI:{clean_doi}"
    params = {"fields": "title,abstract,year"}
    
    headers = {
        "User-Agent": "DOIAbstractFetcher/1.0 (mailto:researcher@example.com)"
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return {
                "doi": clean_doi,
                "title": data.get("title", "Title not found"),
                "year": data.get("year", "Year not found"),
                "abstract": data.get("abstract") or "Abstract not available via API."
            }
        elif response.status_code == 404:
            return {
                "doi": clean_doi, 
                "title": "N/A", 
                "year": "N/A", 
                "abstract": "DOI not found in database."
            }
        else:
            return {
                "doi": clean_doi, 
                "title": "N/A", 
                "year": "N/A", 
                "abstract": f"API returned status code {response.status_code}"
            }
            
    except requests.exceptions.RequestException as e:
        return {
            "doi": clean_doi, 
            "title": "N/A", 
            "year": "N/A", 
            "abstract": f"Error: {str(e)}"
        }

def process_dois_from_file(input_file="dois.txt", output_file="downloaded_abstracts.csv"):
    """
    Reads all DOIs line by line from a text file, fetches their abstracts, 
    and saves the results to a CSV file.
    """
    if not os.path.exists(input_file):
        print(f"Error: Could not find '{input_file}'. Please create it and add your DOIs.")
        return

    # Read all lines from the text file, ignoring empty lines and comments
    with open(input_file, "r", encoding="utf-8") as f:
        dois = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    if not dois:
        print(f"'{input_file}' is empty or contains no valid DOIs.")
        return

    print(f"Found {len(dois)} DOI(s) in '{input_file}'. Processing...")

    results = []
    for i, doi in enumerate(dois, 1):
        print(f"[{i}/{len(dois)}] Fetching: {doi}")
        result = get_abstract_by_doi(doi)
        results.append(result)
        
        # Be a good API citizen: wait half a second between requests
        time.sleep(0.5)

    # Write results to a CSV file
    fieldnames = ["doi", "title", "year", "abstract"]
    with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in results:
            writer.writerow(row)
            
    print(f"\nDone! Results successfully saved to '{output_file}'.")

if __name__ == "__main__":
    process_dois_from_file()
