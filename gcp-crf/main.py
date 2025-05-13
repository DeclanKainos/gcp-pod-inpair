import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import folium
import functions_framework
import requests
from google.cloud import storage


@functions_framework.http
def generate_map(request):
    # Read API token from environment variable
    token = os.environ.get('INPOST_API_TOKEN')
    if not token:
        return 'Error: INPOST_API_TOKEN environment variable not set.', 500

    # API location and auth
    url = "https://api.inpost.pl/v1/points"
    headers = {"Authorization": f"Bearer {token}"}

    # Create a folium map centered on Poland
    map_center = [52, 19]
    my_map = folium.Map(location=map_center, zoom_start=7)

    # Color coding for different air quality indexes from points
    air_quality_index_to_color_code = {
        "VERY_GOOD": "green",
        "GOOD": "lightgreen",
        "SATISFACTORY": "orange",
        "MODERATE": "red",
        "BAD": "darkred",
        "VERY_BAD": "black"
    }

    try:
        # Get number of pages with points
        initial_response = requests.get(url, headers=headers)
        if initial_response.status_code != 200:
            return f'Error fetching data: {initial_response.status_code}', 500

        response_data = initial_response.json()
        if "total_pages" not in response_data:
            return 'Error: API response format unexpected. "total_pages" not found.', 500

        total_pages = response_data["total_pages"]
        print(f"Total pages to process: {total_pages}")

        # Track execution time
        start_time = time.time()

        # OPTIMIZATION: Use thread pool to fetch pages in parallel
        all_points = []
        MAX_WORKERS = min(32, total_pages)  # Cap the number of workers

        def fetch_page(page_num):
            """Helper function to fetch a single page"""
            params = {'page': page_num}
            try:
                response = requests.get(url, headers=headers, params=params)
                if response.status_code == 200:
                    data = response.json()
                    if "items" in data:
                        return data["items"]
                    else:
                        print(f"Missing 'items' key in response on page {page_num}")
                else:
                    print(f"Error on page {page_num}: {response.status_code}")
            except Exception as e:
                print(f"Exception fetching page {page_num}: {e}")
            return []

        # Use ThreadPoolExecutor for parallel fetching
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # Submit all page fetch tasks
            future_to_page = {executor.submit(fetch_page, i): i for i in range(1, total_pages + 1)}

            # Process completed tasks as they finish
            completed = 0
            for future in as_completed(future_to_page):
                page_num = future_to_page[future]
                try:
                    page_points = future.result()
                    all_points.extend(page_points)
                    completed += 1
                    if completed % 10 == 0 or completed == total_pages:
                        print(f"Completed {completed}/{total_pages} pages ({(completed/total_pages*100):.1f}%)")
                except Exception as e:
                    print(f"Error processing page {page_num}: {e}")

        # Process the collected points
        points_added = 0
        for point in all_points:
            # Check if the required fields exist
            if (point.get("air_index_level") is not None and
                    "location" in point and
                    "latitude" in point["location"] and
                    "longitude" in point["location"]):

                air_quality_index = point["air_index_level"]
                # Check if the air quality index is in our color mapping
                if air_quality_index in air_quality_index_to_color_code:
                    color_code = air_quality_index_to_color_code[air_quality_index]

                    folium.Circle(
                        location=[point['location']['latitude'],
                                  point['location']['longitude']],
                        radius=750,
                        fill_opacity=0.6,
                        fill_color=color_code,
                        stroke=False,
                        tooltip=air_quality_index
                    ).add_to(my_map)

                    points_added += 1

        # Calculate and log processing time
        execution_time = time.time() - start_time
        print(f"Processed {len(all_points)} points in {execution_time:.2f} seconds")
        print(f"Added {points_added} points to the map")

        # Add the current date as a text label as the title
        current_date = datetime.now().strftime("%H:%M %d.%m.%Y")
        title_html = f'''
        <div style="position: fixed; top: 10px; left: 50%; transform: translateX(-50%); 
                   background-color: white; padding: 10px; border-radius: 5px; 
                   z-index: 1000; text-align: center;">
            <h3>Dane pobrano o godzinie {current_date}</h3>
        </div>
        '''

        # Add a simple completion popup message
        popup_script = f'''
        <script>
        window.onload = function() {{
            alert("Processing complete! Added {points_added} points to the map in {execution_time:.2f} seconds.");
        }};
        </script>
        '''

        # Add both elements to the map
        my_map.get_root().html.add_child(folium.Element(title_html))
        my_map.get_root().html.add_child(folium.Element(popup_script))

        # Save the map as a (/tmp required by Lambda) HTML file
        output_path = "/tmp/index.html"
        my_map.save(output_path)

        # Upload to Google Cloud Storage
        bucket_name = 'gcp-lab-kainos-1'
        destination_blob_name = 'index.html'

        try:
            # For GCP functions, Application Default Credentials should work
            # If running locally, ensure you've run 'gcloud auth application-default login' or comment out code block to bypass
            client = storage.Client()
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(destination_blob_name)
            blob.upload_from_filename(output_path, content_type='text/html')

            # Read the HTML file content to return it in the response
            with open(output_path, 'r', encoding='utf-8') as html_file:
                html_content = html_file.read()

            # Return the actual HTML content with performance metrics in the header
            performance_header = f"Processed {total_pages} pages with {len(all_points)} points in {execution_time:.2f} seconds."
            return html_content, 200, {'Content-Type': 'text/html', 'X-Processing-Info': performance_header}
        except Exception as e:
            return f"An error occurred during GCS upload: {e}", 500

    except Exception as e:
        return f"An unexpected error occurred: {e}", 500