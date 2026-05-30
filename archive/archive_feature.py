import json
import shutil
import os
import sys

def archive_active_feature():
    source_file = 'planning/trackers/active_feature.json'
    archive_dir = 'archive/feature-trackers'
    
    if not os.path.exists(source_file):
        print(f"Error: {source_file} not found.")
        sys.exit(1)
        
    os.makedirs(archive_dir, exist_ok=True)
    
    with open(source_file, 'r') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            print(f"Error: {source_file} contains invalid JSON.")
            sys.exit(1)
            
    epic_id = data.get('epicId', 'UNKNOWN_EPIC')
    feature_id = data.get('featureId', 'UNKNOWN_FEATURE')
    feature_name = data.get('featureName', 'Unnamed_Feature').replace(' ', '_')
    
    dest_filename = f"{epic_id}-{feature_id}-{feature_name}.json"
    dest_path = os.path.join(archive_dir, dest_filename)
    
    shutil.move(source_file, dest_path)
    print(f"Successfully archived active feature to {dest_path}")

if __name__ == '__main__':
    archive_active_feature()
