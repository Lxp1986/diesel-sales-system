# setup.py
from setuptools import setup # type: ignore
import os

# --- Configuration ---
APP_NAME = "柴油库存管理系统"
APP_SCRIPT = 'main.py'
VERSION = '1.0.0' # You can change this version number

# --- Data Files ---
# Include the database file and the template file
# These will be placed in the Resources directory of the .app bundle
# Format: [ (destination_directory, [source_files]) ]
# '' represents the top-level Resources directory
DATA_FILES = [
    ('', ['diesel_sales.db', '模版.xlsx'])
]

# --- py2app Options ---
OPTIONS = {
    'argv_emulation': True, # Allows dropping files onto the app icon (if needed later)
    'packages': ['pandas', 'openpyxl', 'tkinter'], # Explicitly include packages
    'includes': [], # Add specific modules here if needed later
    'iconfile': None, # No icon specified for now
    'plist': {
        'CFBundleName': APP_NAME,
        'CFBundleDisplayName': APP_NAME,
        'CFBundleGetInfoString': f"{APP_NAME} {VERSION}",
        'CFBundleIdentifier': f"com.yourcompany.{APP_NAME.replace(' ', '')}", # Replace with your identifier if you have one
        'CFBundleVersion': VERSION,
        'CFBundleShortVersionString': VERSION,
        'NSHumanReadableCopyright': 'Copyright © 2025 Your Name/Company. All rights reserved.' # Customize this
    }
}

# --- Setup ---
setup(
    app=[APP_SCRIPT],
    name=APP_NAME,
    version=VERSION,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)

print("\n--- Setup Complete ---")
print(f"To build the application, run: python setup.py py2app -A")
print("The application bundle will be created in the 'dist' directory.")
print("Note: The '-A' flag (alias mode) is faster for testing.")
print("For a self-contained distributable app, run: python setup.py py2app")
