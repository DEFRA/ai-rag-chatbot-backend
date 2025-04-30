import json
import time

import httpx

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
        print(f" First item in search data: {search_response.json()}")
        results = search_data.get("results", [])
        print(
            f"Search successful. Found {len(results)} potential items (limit {SEARCH_PARAMS['count']})."
        )
        print(
            f"total number of results from search api is: {search_data['total']}"
        )  # Print total number of results found
        # You might want to check search_data['total'] to see if pagination is needed

    except httpx.exceptions.RequestException as e:
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
    print(f"results: {results}")
    return results


def fetch_content_for_items(results):
    """
    Fetches content for each item in the results list.
    Each item is expected to be a dictionary with a 'link' key.
    Returns a list of dictionaries with the original link and the fetched content.
    """
    all_grant_data = []
    print("\n--- Fetching content for each item ---")
    print(f"\nFetching content for {len(results)} items...")
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
            )
            # Optional: Print a snippet for progress indication
            print(f"  -> Fetched title: {content_data.get('title', 'N/A')}")

        except httpx.exceptions.HTTPError as e:
            # Handle specific content fetch errors (e.g., 404 Not Found) gracefully
            print(
                f"  -> Error fetching content for {link}: {e.response.status_code} {e.response.reason}"
            )
            # Optionally store error information
            all_grant_data.append(
                {
                    "link": link,
                    "content_url": content_url,
                    "error": f"HTTP Error: {e.response.status_code} {e.response.reason}",
                }
            )
        except httpx.exceptions.RequestException as e:
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


# --- Execution ---
if __name__ == "__main__":
    fetched_data = fetch_content_for_items(results=fetch_farming_grant_content())

    if fetched_data is not None:
        print(f"\nSuccessfully processed {len(fetched_data)} items.")

        # Example: Print titles of successfully fetched items and count errors
        print("\n--- Summary ---")
        successful_fetches = 0
        failed_fetches = 0
        for item in fetched_data:
            if "content_data" in item and "error" not in item:
                title = item["content_data"].get("title", "N/A")
                print(f"- [SUCCESS] Link: {item['link']}, Title: {title}")
                successful_fetches += 1
            elif "error" in item:
                print(f"- [ FAILED] Link: {item['link']}, Error: {item['error']}")
                failed_fetches += 1
            else:
                print(
                    f"- [UNKNOWN] Link: {item['link']}, No content or error recorded."
                )
                failed_fetches += (
                    1  # Count as failed if no content and no specific error
                )

        print(f"\nTotal items processed: {len(fetched_data)}")
        print(f"Successfully fetched content for: {successful_fetches} items.")
        print(f"Failed/Errored items: {failed_fetches} items.")

        # You can now work with the 'fetched_data' list.
        # Each element in the list is a dictionary.
        # If successful, it has keys 'link', 'content_url', 'content_data'.
        # If failed, it has keys 'link', 'content_url', 'error'.
        # The 'content_data' value is the full JSON response from the Content API.

        # Example: Save the full results to a JSON file
        try:
            output_filename = "farming_grants_content.json"
            with open(output_filename, "w", encoding="utf-8") as f:
                json.dump(fetched_data, f, indent=4, ensure_ascii=False)
            print(f"\nSaved detailed results to {output_filename}")
        except OSError as e:
            print(f"\nError saving results to file: {e}")
        except TypeError as e:
            print(f"\nError preparing data for JSON saving: {e}")
