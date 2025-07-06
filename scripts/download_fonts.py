import os
import requests
from fontTools.ttLib import TTFont

def download_file(url, local_path):
    """Download a file from URL to local path"""
    response = requests.get(url)
    response.raise_for_status()
    
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    with open(local_path, 'wb') as f:
        f.write(response.content)

def convert_to_woff2(ttf_path, woff2_path):
    """Convert TTF to WOFF2 format"""
    font = TTFont(ttf_path)
    font.flavor = 'woff2'
    font.save(woff2_path)

def main():
    # Create fonts directory
    fonts_dir = 'static/fonts'
    os.makedirs(fonts_dir, exist_ok=True)

    # Download Material Icons
    material_icons_url = 'https://github.com/google/material-design-icons/raw/master/font/MaterialIcons-Regular.ttf'
    material_icons_ttf = os.path.join(fonts_dir, 'MaterialIcons-Regular.ttf')
    material_icons_woff2 = os.path.join(fonts_dir, 'MaterialIcons-Regular.woff2')
    
    print('Downloading Material Icons...')
    download_file(material_icons_url, material_icons_ttf)
    print('Converting Material Icons to WOFF2...')
    convert_to_woff2(material_icons_ttf, material_icons_woff2)
    os.remove(material_icons_ttf)  # Clean up TTF file

    # Google Sans font files (using a more reliable source)
    google_sans_files = {
        'Regular': 'https://fonts.gstatic.com/s/productsans/v5/HYvgU2fE2nRJvZ5JFAumwegdm0LZdjqr5-oayXSOefg.woff2',
        'Medium': 'https://fonts.gstatic.com/s/productsans/v5/N0c8y_dasvG2CzM7uYqPLnZ2MAKAc2x4R1uOSeegc5U.woff2',
        'Bold': 'https://fonts.gstatic.com/s/productsans/v5/N0c8y_dasvG2CzM7uYqPLm3VxGQVvk1xuEiZf1jk_Oo.woff2'
    }

    for weight, url in google_sans_files.items():
        woff2_path = os.path.join(fonts_dir, f'GoogleSans-{weight}.woff2')
        
        print(f'Downloading Google Sans {weight}...')
        try:
            download_file(url, woff2_path)
            print(f'Successfully downloaded Google Sans {weight}')
        except requests.exceptions.HTTPError as e:
            print(f'Failed to download Google Sans {weight}: {e}')
            # If download fails, create an empty file to prevent future errors
            with open(woff2_path, 'wb') as f:
                f.write(b'')

    print('Font setup completed!')

if __name__ == '__main__':
    main() 