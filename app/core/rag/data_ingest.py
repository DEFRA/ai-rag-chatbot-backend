from langchain_community.document_loaders import WebBaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

urls = [
    "https://www.gov.uk/how-to-have-your-benefits-paid",
    "https://www.gov.uk/how-to-claim-universal-credit",
    "https://www.gov.uk/government/publications/universal-credit-and-rented-housing--2/universal-credit-and-rented-housing-guide-for-landlords",
    "https://www.gov.uk/guidance/understanding-artificial-intelligence-ethics-and-safety",
]

titles = {
    urls[0]: "How to Have Your Benefits Paid",
    urls[1]: "How to Claim Universal Credit",
    urls[2]: "Universal Credit and Rented Housing: Guide for Landlords",
    urls[3]: "Understanding Artificial Intelligence Ethics and Safety",
}

docs = [WebBaseLoader(url).load() for url in urls]
docs_list = [item for sublist in docs for item in sublist]

# add metadata to each document
for doc in docs_list:
    source_url = doc.metadata.get("source", "")
    doc.metadata["url"] = source_url
    doc.metadata["title"] = titles.get(source_url, "GOV.UK")


text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
    chunk_size=100,
    chunk_overlap=50,
)

doc_splits = text_splitter.split_documents(docs_list)

print("Document loading and splitting complete.")
