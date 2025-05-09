import json
import time

import httpx
from markitdown.converters._html_converter import HtmlConverter

# --- Configuration ---
SEARCH_API_URL = "https://www.gov.uk/api/search.json"
CONTENT_API_BASE_URL = "https://www.gov.uk/api/content"  # Base URL for content API
SEARCH_PARAMS = {
    "filter_format": "farming_grant",
    "fields": "link",  # Only fetch the link field from search results
    "count": 500,  # Number of results to fetch (adjust as needed)
}

# It's good practice to identify your script with a User-Agent
HEADERS = {"User-Agent": "MyFarmingGrantFetcherScript/1.0 (stewart.jumbe@defra.gov.uk)"}
# Add a small delay between content API calls to be polite to the server
DELAY_BETWEEN_REQUESTS = 0.2  # seconds

# Instantiate HtmlConverter
html_converter = HtmlConverter()


# --- Main Logic ---
def fetch_farming_grant_content():
    """
    Searches for farming grants on GOV.UK and fetches content for each.
    Returns a list of dictionaries, each containing the link and its content data.
    """
    print("--- Starting GOV.UK Farming Grant Fetcher ---")

    # 1. Search for farming grants
    print(f"Searching for farming grants using: {SEARCH_API_URL}")
    print(f"Parameters: {SEARCH_PARAMS}")
    search_response = None  # Initialize to None for error handling avoid unbound local error, if get request fails
    try:
        search_response = httpx.get(
            SEARCH_API_URL, params=SEARCH_PARAMS, headers=HEADERS, timeout=30
        )
        search_response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        search_data = search_response.json()  # Parse the JSON response
        print(
            f" First item in search data: {search_response.json().get('results', [])[0]}"
        )
        results = search_data.get("results", [])
        print(
            f"Search successful. Found {len(results)} potential items (limit {SEARCH_PARAMS['count']})."
        )
        print(f"total number of results from search api is: {search_data['total']}")

    except httpx.RequestError as e:
        print(f"Error during search API request: {e}")
        return None  # Indicate failure
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from search API: {e}")
        print(
            f"Response text: {search_response.text[:500]}..."
        )  # Print beginning of response
        return None

    # 2. Extract links and fetch content for each
    if not results:
        print("No results found matching the criteria.")
        return []
    # print(f"results: {results}")
    return results


def convert_grant_data_to_metadata_and_markdown(grant_item):
    """
    Converts the content_data of a single grant item into a Markdown string.

    Args:
        grant_item (dict): A dictionary containing the fetched grant data,
                           expected to have 'link' and 'content_data' keys.

    Returns:
        dict: A dictionary containing 'markdown_content' and 'metadata'
              (title, url, description), or None if conversion fails.
    """
    if "error" in grant_item or "content_data" not in grant_item:
        return None  # Cannot convert if there was an error or no data

    content_data = grant_item.get("content_data", {})
    link = grant_item.get("link", "N/A")

    # --- Extract and Convert relevant content to Markdown ---
    title = content_data.get("title", "No Title")
    description = content_data.get("description", "No Description")
    details = content_data.get("details", {})
    body_html = details.get("body", "")
    change_history_list = details.get("change_history", [])

    # Convert HTML body to Markdown
    body_md = ""
    if body_html:
        try:
            # Use the HtmlConverter directly with the HTML string
            body_md_result = html_converter.convert_string(body_html)
            body_md = (
                body_md_result.text_content.strip()
            )  # Strip leading/trailing whitespace
        except Exception as md_err:
            print(f"  -> Error converting body HTML to Markdown for {link}: {md_err}")
            body_md = (
                "Error during Markdown conversion."  # Or keep original HTML: body_html
            )

    # Format change history
    change_history_md_parts = []
    if change_history_list:
        change_history_md_parts.append("\n## Change History")
        for entry in change_history_list:
            timestamp = entry.get("public_timestamp", "N/A")
            note = entry.get("note", "N/A")
            change_history_md_parts.append(f"*   **{timestamp}:** {note.strip()}")
    change_history_md = "\n".join(change_history_md_parts)

    # Assemble final markdown string
    markdown_content = f"# {title}\n\n**URL:** https://www.gov.uk{link}\n\n## Description\n\n{description}\n\n## Details\n\n{body_md}"
    if change_history_md:
        markdown_content += f"\n{change_history_md}\n"
    else:
        markdown_content += (
            "\n"  # Ensure a newline at the end even if no change history
        )

    # Construct metadata dictionary
    metadata = {
        "title": title,
        "url": f"https://www.gov.uk{link}",  # Full URL
        "description": description,
    }

    return {"markdown_content": markdown_content, "metadata": metadata}


def save_markdown_in_json_file(processed_docs):
    average_document_length = []

    # Save the processed documents (metadata + markdown) to a JSON file
    if processed_docs:
        for item in processed_docs:
            # Calculate length of the actual markdown content
            content_length = len(item.get("markdown_content", ""))
            average_document_length.append(content_length)
            print(
                f"******Document content length: {content_length} characters for link: {item.get('metadata', {}).get('url', 'N/A')}"
            )
        try:
            output_filename = "farming_grants_processed.json"  # Save as JSON
            with open(output_filename, "w", encoding="utf-8") as f:
                json.dump(processed_docs, f, indent=4, ensure_ascii=False)
            print(f"\nSaved processed documents to {output_filename}")
            if average_document_length:  # Ensure list is not empty
                avg_len = sum(average_document_length) / len(average_document_length)
                print(
                    f"\nAverage Markdown content length is: {avg_len:.2f} characters."
                )
        except OSError as e:
            print(f"\nError saving processed documents to file: {e}")
        except TypeError as e:
            print(f"\nError preparing data for JSON saving: {e}")
    else:
        print("\nNo documents were successfully processed to save.")


def fetch_content_for_items(results):
    """
    Fetches content for each item in the results list.
    Each item is expected to be a dictionary with a 'link' key.
    Returns a list of dictionaries with the original link and the fetched content.
    """
    all_grant_data = []
    # Iterate over each result and fetch its content
    for i, item in enumerate(results):
        link = item.get("link")
        if not link or not link.startswith("/"):
            print(
                f"Item {i + 1}/{len(results)}: Skipping - Invalid or missing link: {link}"
            )
            continue

        # Construct the full content API URL (e.g., https://www.gov.uk/api/content/path/to/page)
        # The link from search results already starts with '/', so just append it.
        content_url = f"{CONTENT_API_BASE_URL}{link}"
        print(f"Item {i + 1}/{len(results)}: Fetching content from {content_url}")
        content_response = None  # Initialize to None for error handling avoid unbound local error, if get request fails
        try:
            # Add a small delay
            time.sleep(DELAY_BETWEEN_REQUESTS)

            content_response = httpx.get(content_url, headers=HEADERS, timeout=30)
            content_response.raise_for_status()  # Check for HTTP errors for this specific item
            content_data = content_response.json()

            # Store the original link and the fetched content
            all_grant_data.append(
                {
                    "link": link,
                    "content_url": content_url,
                    "content_data": content_data,  # This is the full JSON content for the item
                }
            )  # Append raw data first
            # Optional: Print a snippet for progress indication
            print(f"  -> Fetched title: {content_data.get('title', 'N/A')}")

        except httpx.HTTPStatusError as e:  # More specific exception for HTTP errors
            # Handle specific content fetch errors (e.g., 404 Not Found) gracefully
            print(
                f"  -> Error fetching content for {link}: {e.response.status_code} {e.response.reason}"
            )
            # Optionally store error information
            all_grant_data.append(
                {
                    "link": link,
                    "content_url": content_url,
                    "error": f"HTTP Error: {e.response.status_code} {e.response.reason_phrase}",
                }
            )
        except httpx.RequestError as e:
            print(f"  -> Network error fetching content for {link}: {e}")
            all_grant_data.append(
                {
                    "link": link,
                    "content_url": content_url,
                    "error": f"Request Error: {e}",
                }
            )
        except json.JSONDecodeError as e:
            print(f"  -> Error decoding JSON content for {link}: {e}")
            print(
                f"     Response text: {content_response.text[:200]}..."
            )  # Print beginning of response
            all_grant_data.append(
                {
                    "link": link,
                    "content_url": content_url,
                    "error": f"JSON Decode Error: {e}",
                }
            )

    print("\n--- Fetching complete ---")
    return all_grant_data


def fetch_and_convert_grant_data():
    """
    Fetches farming grant data from GOV.UK and converts it to Markdown format.
    Returns a list of dictionaries with the original link and the converted Markdown content.
    """
    # 1. Fetch search results
    search_results = fetch_farming_grant_content()

    if search_results:
        # 2. Fetch content for each item
        print("\n--- Fetching content for each item ---")
        print(f"\nFetching content for {len(search_results)} items...")
        fetched_data = fetch_content_for_items(results=search_results)
        processed_docs = []
        successful_processing = 0
        failed_fetches_or_conversions = 0

        # Note: successful_fetches is initialized but not used below.
        # 3. Convert fetched data to Markdown and save individual files
        print("\n--- Converting content to Markdown ---")
        print("\n--- Summary ---")
        for item in fetched_data:
            if "error" in item:
                print(f"- [FAILED] Fetch Error: {item['link']}, Error: {item['error']}")
                failed_fetches_or_conversions += 1
                continue

            processed_result = convert_grant_data_to_metadata_and_markdown(item)
            if processed_result:
                processed_docs.append(processed_result)
                successful_processing += 1
            elif "error" in item:
                print(f"- [ FAILED] Link: {item['link']}, Error: {item['error']}")
                failed_fetches_or_conversions += 1
            else:
                print(f"- [ FAILED] Processing Error: {item['link']}")
                failed_fetches_or_conversions += 1

        print(
            f"\nTotal items processed: {len(fetched_data)}\nSuccessfully saved content for: {successful_processing} items\nFailed/Errored items: {failed_fetches_or_conversions} items."
        )
        return save_markdown_in_json_file(processed_docs)
    return None


# running the file
fetch_and_convert_grant_data()
