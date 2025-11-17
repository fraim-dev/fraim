import os
import re
from pathlib import Path

def process_directory(base_dir):
    """
    Process directories starting with XBEN- and standardize their configuration files
    """
    # Find all XBEN-* directories
    for root, dirs, _ in os.walk(base_dir):
        for dir_name in dirs:
            if dir_name.startswith('XBEN-'):
                process_xben_directory(os.path.join(root, dir_name))

def process_xben_directory(xben_dir):
    """
    Process configuration files within an XBEN directory
    """
    print(f"Processing directory: {xben_dir}")
    
    # Find all configuration files
    config_files = []
    for root, _, files in os.walk(xben_dir):
        for file in files:
            if file.endswith(('.wsgi', '.conf')):
                config_files.append(os.path.join(root, file))
    
    # Get original names before renaming
    original_names = [os.path.splitext(os.path.basename(f))[0] for f in config_files]
    
    # Rename files to app_conf
    for file_path in config_files:
        dir_path = os.path.dirname(file_path)
        extension = os.path.splitext(file_path)[1]
        new_name = f"app_conf{extension}"
        new_path = os.path.join(dir_path, new_name)
        
        print(f"Renaming {file_path} to {new_path}")
        os.rename(file_path, new_path)
    
    # Replace content in all files
    for root, _, files in os.walk(xben_dir):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Replace all original names with app_conf
                modified = False
                for original_name in original_names:
                    if original_name in content:
                        content = content.replace(original_name, 'app_conf')
                        modified = True
                
                if modified:
                    print(f"Updating content in {file_path}")
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                        
            except UnicodeDecodeError:
                print(f"Skipping binary file: {file_path}")
            except Exception as e:
                print(f"Error processing {file_path}: {str(e)}")

def main():
    # Process both directories
    directories = ['benchmarks', 'benchmarks_patched']
    for directory in directories:
        if os.path.exists(directory):
            print(f"\nProcessing {directory} directory...")
            process_directory(directory)
        else:
            print(f"Directory {directory} not found!")

if __name__ == "__main__":
    main()
