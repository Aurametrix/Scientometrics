import requests
import csv
import os
import time

def fetch_batch_abstracts(dois_chunk):
    """
    Fetches abstracts for a batch of up to 500 DOIs using 
    Semantic Scholar's batch endpoint.
    """
    url = "https://api.semanticscholar.org/graph/v1/paper/batch"
    params = {"fields": "title,abstract,year"}
    
    # Format IDs with 'DOI:' prefix as required by the batch API
    formatted_ids = [f"DOI:{doi.replace('https://doi.org/', '').strip()}" for doi in dois_chunk]
    body = {"ids": formatted_ids}
    
    headers = {
        "User-Agent": "DOIAbstractFetcher/1.0 (mailto:researcher@example.com)",
        "Content-Type": "application/json"
    }
    
    # Retry loop with exponential backoff for rate limits (429)
    max_retries = 4
    backoff = 3
    
    for attempt in range(max_retries):
        try:
            response = requests.post(url, params=params, json=body, headers=headers, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                print(f"    [!] Rate limited (429). Retrying in {backoff} seconds...")
                time.sleep(backoff)
                backoff *= 2  # Double the wait time for the next retry
            else:
                print(f"    [!] API error status {response.status_code}: {response.text}")
                break
        except requests.exceptions.RequestException as e:
            print(f"    [!] Request exception: {e}")
            time.sleep(backoff)
            backoff *= 2
            
    return None

def process_dois_from_file(input_file="dois.txt", output_file="downloaded_abstracts.csv"):
    if not os.path.exists(input_file):
        print(f"Error: Could not find '{input_file}'. Please create it and add your DOIs.")
        return

    # Read all lines from the text file
    with open(input_file, "r", encoding="utf-8") as f:
        dois = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    if not dois:
        print(f"'{input_file}' is empty or contains no valid DOIs.")
        return

    print(f"Found {len(dois)} DOI(s) in '{input_file}'. Processing in batches...")

    results = []
    chunk_size = 500  # Semantic Scholar batch limit is 500 IDs per request
    
    for i in range(0, len(dois), chunk_size):
        chunk = dois[i:i + chunk_size]
        batch_num = (i // chunk_size) + 1
        total_batches = (len(dois) + chunk_size - 1) // chunk_size
        
        print(f"Processing batch {batch_num}/{total_batches} ({len(chunk)} DOIs)...")
        
        data = fetch_batch_abstracts(chunk)
        
        if data and isinstance(data, list):
            # Map returned items back to their respective DOIs
            for original_doi, paper_data in zip(chunk, data):
                clean_doi = original_doi.replace("https://doi.org/", "").strip()
                if paper_data and isinstance(paper_data, dict):
                    results.append({
                        "doi": clean_doi,
                        "title": paper_data.get("title", "Title not found"),
                        "year": paper_data.get("year", "Year not found"),
                        "abstract": paper_data.get("abstract") or "Abstract not available via API."
                    })
                else:
                    results.append({
                        "doi": clean_doi,
                        "title": "N/A",
                        "year": "N/A",
                        "abstract": "DOI not found in database or returned null."
                    })
        else:
            print(f"    [!] Batch {batch_num} failed completely. Marking items as failed.")
            for original_doi in chunk:
                clean_doi = original_doi.replace("https://doi.org/", "").strip()
                results.append({
                    "doi": clean_doi,
                    "title": "N/A",
                    "year": "N/A",
                    "abstract": "Failed to fetch batch chunk."
                })
        
        # Brief pause between large batches to be a good API citizen
        time.sleep(1.5)

    # Write all results to CSV
    fieldnames = ["doi", "title", "year", "abstract"]
    with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in results:
            writer.writerow(row)
            
    print(f"\nDone! Processed {len(results)} items. Saved to '{output_file}'.")

if __name__ == "__main__":
    process_dois_from_file()
