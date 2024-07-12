import os
from datetime import datetime
from pathlib import Path

import pandas as pd
from SPARQLWrapper import JSON, SPARQLWrapper
from taxonomical_utils.merger import merge_files
from taxonomical_utils.resolver import resolve_taxa

# Change directory to the parent directory of the script
p = Path(__file__).parents[1]
os.chdir(p)


# Function to query Wikidata
def query_wikidata():
    sparql = SPARQLWrapper("https://query.wikidata.org/sparql")
    sparql.setQuery(
        """
        PREFIX wikibase: <http://wikiba.se/ontology#>
        PREFIX wdt: <http://www.wikidata.org/prop/direct/>
        SELECT DISTINCT ?taxon ?taxon_name WHERE {
          ?taxon wdt:P31 wd:Q16521 .
          ?taxon wdt:P225 ?taxon_name .
          MINUS { ?taxon wdt:P9157 ?ott_id. }
        }
        LIMIT 100
    """
    )
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()
    return results


# Fetch data from Wikidata
wikidata_results = query_wikidata()

# Process Wikidata results
wikidata_data = []
for result in wikidata_results["results"]["bindings"]:
    taxon = result["taxon"]["value"].split("/")[-1]
    taxon_name = result["taxon_name"]["value"]
    wikidata_data.append({"?taxon": taxon, "?taxon_name": taxon_name})

# Convert to DataFrame
wikidata_df = pd.DataFrame(wikidata_data)

# Save Wikidata results to a file
input_data_path = "./data/wikidata_input.tsv"
wikidata_df.to_csv(input_data_path, index=False, sep="\t")

print("Wikidata query results saved.")

# Resolve taxa
resolved_taxa = resolve_taxa(
    input_file=input_data_path, output_file="./data/resolved_taxa.csv", org_column_header="?taxon_name"
)

# Merge files
merged_files = merge_files(
    input_file=input_data_path,
    output_file="./data/merged_files.csv",
    resolved_taxa_file="./data/resolved_taxa.csv",
    org_column_header="?taxon_name",
)

# Load the merged file into a DataFrame
df = pd.read_csv("./data/merged_files.csv")

# Ensure boolean values are properly handled
df["otl_is_synonym"] = df["otl_is_synonym"].astype(bool)
df["otl_is_approximate_match"] = df["otl_is_approximate_match"].astype(bool)

# Filter rows where otl_is_synonym and otl_is_approximate_match are both False
filtered_df = df[(df["otl_is_synonym"].eq(False)) & (df["otl_is_approximate_match"].eq(False))]


# Get today's date in the required format
today_date = datetime.today().strftime("+%Y-%m-%dT00:00:00Z/11")

# Create Quick Statements file
quick_statements = []

for _, row in filtered_df.iterrows():
    taxon_qid = row["?taxon"]
    ott_id = int(row["otl_taxon.ott_id"])
    quick_statements.append(f'{taxon_qid}|P9157|"{ott_id}"|S248|Q124708476|S813|{today_date}')

# Write Quick Statements to a file
output_file = "./data/quick_statements.txt"
with open(output_file, "w") as f:
    for statement in quick_statements:
        f.write(statement + "\n")

print(f"Quick Statements file created: {output_file}")
