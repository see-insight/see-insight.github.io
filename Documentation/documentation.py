from pyzotero import zotero
import re
from html import escape

# Addresses for the script to use
GROUP_ID = "2465069"
COLLECTION_KEY = "C5JFAYLL"
OUTPUT_FILE = "publications.html"

# Connect to Zotero
zot = zotero.Zotero(GROUP_ID, "group")

# Get all items in the collection
items = zot.everything(
    zot.collection_items(COLLECTION_KEY)
)

publications = []

# Loop through items and extract relevant information
for item in items:
    data = item["data"]

    # Ignore attachments
    if data["itemType"] == "attachment":
        continue

    # Extract year from Zotero date
    match = re.search(r"\d{4}", data.get("date", ""))
    year = match.group() if match else "Unknown"

    # Get authors
    authors = []

    for creator in data.get("creators", []):
        if creator.get("creatorType") != "author":
            continue

        if "name" in creator:
            authors.append(creator["name"])
        else:
            first = creator.get("firstName", "")
            last = creator.get("lastName", "")
            authors.append(f"{first} {last}".strip())

    # Use DOI if available, otherwise URL
    link = data.get("url", "")

    if data.get("DOI"):
        link = f"https://doi.org/{data['DOI']}"

    publications.append({
        "year": year,
        "title": data.get("title", ""),
        "authors": ", ".join(authors),
        "link": link,
        "type": data["itemType"],
    })


# Sort newest first
publications.sort(
    key=lambda x: int(x["year"]) if x["year"].isdigit() else 0,
    reverse=True
)


# Generate HTML
html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Publications</title>
</head>
<body>

<h1>Publications</h1>

"""

for pub in publications:
    title = escape(pub["title"])
    authors = escape(pub["authors"])
    year = escape(pub["year"])

    if pub["link"]:
        link = escape(pub["link"], quote=True)
        title_html = f'<a href="{link}">{title}</a>'
    else:
        title_html = title

    html += f"""<div class="publication">
    <p>
        <strong>{year}</strong><br>
        {authors}<br>
        {title_html}
    </p>
</div>

"""

html += """</body>
</html>
"""


# Write the file
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write(html)

print(f"Generated {OUTPUT_FILE} with {len(publications)} entries.")