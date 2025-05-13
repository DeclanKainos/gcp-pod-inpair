import requests
import folium
import boto3
from datetime import datetime 
import os

def lambda_handler(event, context):
    # Read API token from environment variable
    env_variable_name = 'INPOST_API_TOKEN'
    token = os.environ.get(env_variable_name)

    if not token:
        return {
            'statusCode': 500,
            'body': f'Error: {env_variable_name} environment variable not set.'
        }

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

    # Get number of pages with points
    page_count = requests.get(url, headers=headers)
    if page_count.status_code == 200:
        total_pages=page_count.json()["total_pages"]
    else:
        print(page_count.status_code)
    
    # Go through all the pages to get all the points that report air_index_level (not None)
    # add them to the map with appropriate colour
    for i in range(1,total_pages+1):
        params = {'page': i,}
        print(i)
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            #points = response.json()
            points=response.json()["items"]
            
            for point in points:
                if point["air_index_level"] is not None:
                    color_code = air_quality_index_to_color_code[point["air_index_level"]]
                    air_quality_index = point["air_index_level"]
                    folium.Circle(location=[point['location']['latitude'], 
                                            point['location']['longitude']],
                                            radius=750,
                                            fill_opacity=0.6,
                                            fill_color=color_code,
                                            stroke=False,
                                            tooltip=air_quality_index
                                            ).add_to(my_map)
    
        else:
            print(response.status_code)

    # Add the current date as a text label as the title
    current_date = datetime.now().strftime("%H:%M %d.%m.%Y")
    title_html = f'<h1 style="position:absolute;z-index:100000;left:35vw" >Dane pobrano o godzinie {current_date}</h1>'
    my_map.get_root().html.add_child(folium.Element(title_html))
    
    # Save the map as a (/tmp required by Lambda) HTML file
    my_map.save("/tmp/index.html")
    
    # Upload file to S3
    bucket_name = "www.inpair.pl"
    s3_object_key = "index.html"
    content_type = "text/html"

    with open("/tmp/index.html", 'rb') as file:
        file_content = file.read()

    try:
        s3 = boto3.client('s3')
        s3.put_object(Body=file_content, Bucket=bucket_name, Key=s3_object_key, ContentType=content_type)
        print(f"HTML file uploaded to S3: s3://{bucket_name}/{s3_object_key}")
    except FileNotFoundError:
        return {
            'statusCode': 500,
            'body': f'The file {s3_object_key} was not found.'
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': f'An error occurred: {e}'
        }
    return {
        'statusCode': 200,
        'body': 'HTML file uploaded to S3 successfully.'
    }
