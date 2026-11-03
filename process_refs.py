import time
import pandas as pd
import requests

# 1. Load your CSV file
# Make sure 'Refs.csv' is in the same folder as this script
df = pd.read_csv("Refs.csv")

# CHANGE THIS to match the exact header name of the column containing your references in the CSV
REFERENCE_COLUMN_NAME = "Reference"


def get_pub_date_from_reference(reference_text):
  """Queries the free Crossref API to retrieve publication metadata."""
  if pd.isna(reference_text) or not str(reference_text).strip():
    return {
        "matched_title": None,
        "doi": None,
        "year": None,
        "month": None,
        "day": None,
    }

  url = "https://api.crossref.org/works"
  params = {
      "query.bibliographic": reference_text,
      "rows": 1,
      "mailto": "irene@aurametrix.com",  # Replace with your actual email for Crossref's polite pool
  }

  try:
    response = requests.get(url, params=params, timeout=10)
    if response.status_code == 200:
      data = response.json()
      items = data.get("message", {}).get("items", [])

      if items:
        item = items[0]
        title = item.get("title", ["Unknown Title"])[0]
        doi = item.get("DOI", "No DOI")

        # Check for publication dates in order of preference
        date_parts = None
        for field in ["published-print", "published-online", "issued"]:
          if field in item:
            date_parts = item[field].get("date-parts", [[]])[0]
            break

        year = date_parts[0] if len(date_parts) > 0 else None
        month = date_parts[1] if len(date_parts) > 1 else None
        day = date_parts[2] if len(date_parts) > 2 else None

        return {
            "matched_title": title,
            "doi": doi,
            "year": year,
            "month": month,
            "day": day,
        }
  except Exception as e:
    print(f"Error querying reference: {e}")

  return {
      "matched_title": None,
      "doi": None,
      "year": None,
      "month": None,
      "day": None,
  }


# Lists to store the fetched data
years, months, days, dois, matched_titles = [], [], [], [], []

print(f"Processing references from '{REFERENCE_COLUMN_NAME}'...")

# Loop through each row one by one
for index, ref in enumerate(df[REFERENCE_COLUMN_NAME]):
  print(f"Processing row {index + 1}...")
  result = get_pub_date_from_reference(ref)

  years.append(result["year"])
  months.append(result["month"])
  days.append(result["day"])
  dois.append(result["doi"])
  matched_titles.append(result["matched_title"])

  # Be polite to the API: pause for 0.5 seconds between requests
  time.sleep(0.5)

# Append new columns to your dataframe
df["Crossref_Year"] = years
df["Crossref_Month"] = months
df["Crossref_Day"] = days
df["Crossref_DOI"] = dois
df["Crossref_Matched_Title"] = matched_titles

# Save the updated data to a new CSV file
output_file = "refs_with_dates.csv"
df.to_csv(output_file, index=False)
print(f"Done! Results successfully saved to '{output_file}'.")
