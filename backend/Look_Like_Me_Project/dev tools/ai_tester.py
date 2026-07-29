
import os
import sys
import django
import pandas as pd

# ==========================================
# 1. DJANGO SETUP (Crucial for standalone scripts)
# ==========================================
# Add the current directory (project root) to the Python path
sys.path.append(os.getcwd())

# Tell Python where your Django settings are. 
# REPLACE 'core.settings' with your actual project settings path if different!
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings') 

# Initialize Django
django.setup()

# Now it is safe to import Django models and DRF tools
from auths.models import User
from rest_framework.test import APIClient

# ==========================================
# 2. SCRIPT LOGIC
# ==========================================
def walk_queries(output_file='./dev tools/results.csv'):
    # Initialize the DRF test client (simulates requests without a running server)
    client = APIClient()
    
    # Fetch all users whose username starts with 'query'
    query_users = User.objects.filter(name__startswith='query')
    
    print(f"Found {query_users.count()} query users. Processing...")
    
    results = []

    for user in query_users:
        # Authenticate as the user (bypass token login)
        client.force_authenticate(user=user)
        
        # Call the endpoint directly. 
        response = client.get(f'/api/matches/feed/{user.id}/')
        
        if response.status_code == 200:
            data = response.data
            
            # Extract basic data
            search_time_str = data.get('Search_time', '0 seconds')
            
            # Clean the string to just get the float number, or keep it as is. 
            # We'll keep the raw string based on your prompt.
            search_time = float(search_time_str.split()[0])
            
            # The data key might be None if no matches were found, so we default to []
            matches = data.get('data') or []
            num_results = len(matches)
            
            # Base dictionary for this row
            row = {
                'query_name': user.name,
                'search_time': search_time,
                'num_results': num_results,
            }
            
            # Dynamically add the 5 match columns
            for i in range(5):
                match_prefix = f'match_{i+1}'
                
                if i < num_results:
                    # We found a match for this slot
                    match_data = matches[i]
                    # Assuming the nested user structure from previous setup
                    matched_user = match_data.get('user', {})
                    
                    row[f'{match_prefix}_name'] = matched_user.get('name', 'Unknown')
                    row[f'{match_prefix}_score'] = match_data.get('similarity_score', 0.0)
                else:
                    # No match for this slot, pad with None (will become blank in CSV)
                    row[f'{match_prefix}_name'] = None
                    row[f'{match_prefix}_score'] = None
                    
            results.append(row)
        else:
            print(f"Error processing {user.username}: {response.status_code} - {response.data}")

    # ==========================================
    # 3. SAVE TO CSV
    # ==========================================
    if results:
        df = pd.DataFrame(results)
        df.to_csv(output_file, index=False)
        print(f"\nSuccess! Saved {len(results)} rows to {output_file}")
    else:
        print("\nNo results to save.")

# Trigger the function when the script runs
if __name__ == "__main__":
    walk_queries()