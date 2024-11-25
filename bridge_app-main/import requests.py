import requests
import os

# IQAir API endpoint for device data
BASE_URL = 'https://api.iqair.com/v2/devices/{device_id}/data'

API_KEY = ''
DEVICE_ID = '63315fdfc962d9f338d7e42f'

url = BASE_URL.format(device_id=DEVICE_ID)

def get_device_data(api_key, url):
    params = {
        'key': api_key
    }
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        data = response.json()
        return data
    else:
        print(f"Failed to retrieve data: {response.status_code}, {response.text}")
        return None

device_data = get_device_data(API_KEY, url)

if device_data:
    print("Device Data:", device_data)
