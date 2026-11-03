import difflib
import pandas as pd
import re



def clean_title_extraction(ref_text):
  if pd.isna(ref_text):
    return ""
  text = str(ref_text).strip()

  # Strategy: Look for text that follows an author block ending (either 'et al.' or a name-ending pattern like 'Name, Initial.')
  # and stops right before the journal/year metadata sequence (e.g., '. Journal Name. 2023' or '. Cureus. 2023').

  # Regex breakdown:
  # 1. Finds the last occurrence of an author-like termination (e.g., "et al." or a capitalized surname followed by initials and a period).
  # 2. Captures everything non-greedy until it hits a period followed by a known publisher/journal cue or a 4-digit year.
  pattern = (
      r"(?:et al\.|[A-Z][a-zà-ÿ]+,\s+[A-Z]\.[\w\s,;\.\(\)]*?\.)\s+(?P<title>.+?)"
      r"(?=\.\s+(?:arXiv|Cureus|Medical teacher|Journal|Scientific reports|Academic medicine|Healthcare|BMJ|Archives|American journal|Frontiers|Canadian Association|Journal of|[\d]{4}[;\.]))"
  )

  match = re.search(pattern, text)
  if match:
    title = match.group("title").strip()
    # Clean up trailing periods if captured
    if title.endswith("."):
      title = title[:-1].strip()
    return title

  # Fallback heuristic if regex fails: Split by sentences and look for the longest middle fragment
  parts = text.split(". ")
  if len(parts) > 2:
    # Usually the title is the longest string segment between authors and journal
    candidates = sorted(parts[1:-1], key=len, reverse=True)
    if candidates:
      return candidates[0].strip()

  return text
  
  


# Load your file
input_file = "refs_with_dates.csv"
df = pd.read_csv(input_file)

# Extract titles from the first column ('Reference')
REFERENCE_COLUMN_NAME = "Reference"  # Update if your column name is different
df["Extracted_Ref_Title"] = df[REFERENCE_COLUMN_NAME].apply(
    clean_title_extraction
)


# Function to calculate text similarity ratio (0.0 to 1.0)
def get_similarity(a, b):
  if pd.isna(a) or pd.isna(b):
    return 0.0
  return round(
      difflib.SequenceMatcher(
          None, str(a).lower().strip(), str(b).lower().strip()
      ).ratio(),
      2,
  )


# Compare Extracted Reference Title with Crossref Matched Title
df["Title_Similarity_Score"] = df.apply(
    lambda row: get_similarity(
        row.get("Extracted_Ref_Title"), row.get("Crossref_Matched_Title")
    ),
    axis=1,
)

# Flag rows where similarity score is below 0.8
df["Needs_Review"] = df["Title_Similarity_Score"] < 0.8

# Save results
output_file = "refs_title_comparison.csv"
df.to_csv(output_file, index=False)

print(f"Done! Results successfully saved to '{output_file}'.")
print(
    "Rows flagged for review (Similarity < 0.8):"
    f" {df['Needs_Review'].sum()}"
)

  
  

# Load your existing file with dates and Crossref matches
input_file = "refs_with_dates.csv"
df = pd.read_csv(input_file)

# Extract titles from the first column ('Reference')
# Change 'Reference' if your CSV column has a different name
REFERENCE_COLUMN_NAME = "Reference"
df["Extracted_Ref_Title"] = df[REFERENCE_COLUMN_NAME].apply(
    clean_title_extraction
)


# Function to calculate text similarity ratio (0.0 to 1.0)
def get_similarity(a, b):
  if pd.isna(a) or pd.isna(b):
    return 0.0
  return round(
      difflib.SequenceMatcher(
          None, str(a).lower().strip(), str(b).lower().strip()
      ).ratio(),
      2,
  )


# Compare Extracted Reference Title with Crossref Matched Title
df["Title_Similarity_Score"] = df.apply(
    lambda row: get_similarity(
        row.get("Extracted_Ref_Title"), row.get("Crossref_Matched_Title")
    ),
    axis=1,
)

# Flag rows where the match is weak (Similarity score below 0.8)
df["Needs_Review"] = df["Title_Similarity_Score"] < 0.8

# Save the detailed comparison to a new CSV file
output_file = "refs_title_comparison.csv"
df.to_csv(output_file, index=False)

print(f"Done! Results successfully saved to '{output_file}'.")
print(f"Total rows processed: {len(df)}")
print(
    "Rows flagged for review (Similarity < 0.8):"
    f" {df['Needs_Review'].sum()}"
)
