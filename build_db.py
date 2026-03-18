import csv
import sys
from openai import OpenAI
import os

# A fix for working with ChromaDB on Streamlit Community Cloud
__import__('pysqlite3')
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
import chromadb


# Create OpenAI client using environment variable
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

# A function that adds a single article to the ChromaDB collection
def add_to_collection(collection, text, doc_id, company, date, url):
    response = client.embeddings.create(
        input=text,
        model='text-embedding-3-small'
    )
    embedding = response.data[0].embedding

    collection.add(
        documents=[text],
        ids=[doc_id],
        embeddings=[embedding],
        metadatas=[{"company": company, "date": date, "url": url}]
    )

# Read the CSV and load all articles into ChromaDB
def load_csv_to_collection(csv_path, collection):
    rows = []
    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    print(f"Loaded {len(rows)} articles from CSV")

    for i, row in enumerate(rows):
        text = row['Document'].strip()
        if not text:
            continue

        add_to_collection(
            collection=collection,
            text=text,
            doc_id=str(i),
            company=row['company_name'].strip(),
            date=row['Date'].strip(),
            url=row['URL'].strip()
        )

        if (i + 1) % 100 == 0:
            print(f"  Inserted {i + 1}/{len(rows)}")

    print(f"Done! {collection.count()} articles in the database")

# Set up ChromaDB and run
chroma_client = chromadb.PersistentClient(path='./news_chroma_db')

try:
    chroma_client.delete_collection('news_articles')
    print("Deleted old collection")
except:
    pass

collection = chroma_client.create_collection(
    name='news_articles',
    metadata={'hnsw:space': 'cosine'}
)

load_csv_to_collection('news.csv', collection)