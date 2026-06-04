import requests
from bs4 import BeautifulSoup

target_url = "https://www.cftech.co.in/iqf-multijet-freezer.htm"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

print(f"Attempting to connect to: {target_url}...")
response = requests.get(target_url, headers=headers)

print(f"Server Response Code: {response.status_code}")

# If the connection is successful, let's read the data
if response.status_code == 200:
    print("Connection successful! Extracting the specification table...\n")
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 1. Target the exact box you found in Screenshot 2
    # Note: We use 'fo rowflex' without the dots here!
    details_box = soup.find('div', class_='fo rowflex')
    
    if details_box:
        print("--- SUCCESSFULLY FOUND THE TABLE ---\n")
        
        # 1. Get the text with our pipe separator
        clean_text = details_box.get_text(separator=' | ', strip=True)
        
        # 2. Split the text into a list of items
        data_list = clean_text.split(' | ')
        
        # 3. Pair them up into a Python Dictionary!
        machine_specs = {}
        
        # Loop through the list, jumping 2 steps at a time (Key, then Value)
        # We use a try-except just in case the website has an odd number of items
        try:
            for i in range(0, len(data_list), 2):
                key = data_list[i].strip()
                value = data_list[i+1].strip()
                machine_specs[key] = value
                
            print("--- FINAL STRUCTURED DATA (JSON/DICT FORMAT) ---\n")
            # Print it out beautifully
            import json
            print(json.dumps(machine_specs, indent=4))
            print("\n------------------------------------")
            
        except IndexError:
            print("Warning: The table had an odd number of items, formatting might be slightly off.")
            print(clean_text)
            
    else:
        print("Could not find the 'fo rowflex' box.")
else:
    print("Failed to connect.")