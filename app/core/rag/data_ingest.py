from langchain_community.document_loaders import WebBaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

urls = [
    "https://www.gov.uk/how-to-have-your-benefits-paid",
    "https://www.gov.uk/how-to-claim-universal-credit",
    "https://www.gov.uk/government/publications/universal-credit-and-rented-housing--2/universal-credit-and-rented-housing-guide-for-landlords",
    "https://www.gov.uk/guidance/understanding-artificial-intelligence-ethics-and-safety",
]

docs = [WebBaseLoader(url).load() for url in urls]
docs_list = [item for sublist in docs for item in sublist]

text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
    chunk_size=100,
    chunk_overlap=50,
)

doc_splits = text_splitter.split_documents(docs_list)

print("Document loading and splitting complete.")
