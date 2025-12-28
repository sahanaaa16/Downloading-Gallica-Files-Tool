"""
Gallica Stealth Downloader - Uses undetected-chromedriver to bypass anti-bot protection
"""

import csv
import os
import time
import random
import ssl
from pathlib import Path

# Fix SSL certificate issues
ssl._create_default_https_context = ssl._create_unverified_context

try:
    import undetected_chromedriver as uc
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
except ImportError:
    print("ERROR: Required packages not installed!")
    print("Please run: pip3 install undetected-chromedriver")
    exit(1)


def extract_ark_id(url):
    """Extract ARK ID from Gallica URL."""
    parts = url.rstrip('/').split('/')
    if 'ark:' in url:
        try:
            idx = parts.index('12148')
            return parts[idx + 1] if idx + 1 < len(parts) else None
        except ValueError:
            return None
    return None


def wait_random(min_sec=2, max_sec=5):
    """Random wait to mimic human behavior."""
    time.sleep(random.uniform(min_sec, max_sec))


def wait_for_downloads(download_folder, timeout=60):
    """Wait for all downloads to complete (no .crdownload files)."""
    print("  Waiting for all downloads to complete...")
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        crdownload_files = list(Path(download_folder).glob("*.crdownload"))
        if not crdownload_files:
            print("  ✓ All downloads completed!")
            return True
        time.sleep(2)
    
    print(f"  ⚠ Timeout waiting for downloads")
    return False



def download_gallica_pdf(driver, url, ark_id, download_folder):
    """
    Navigate to Gallica and download PDF.
    """
    try:
        # Check if file already exists
        existing_files = list(Path(download_folder).glob(f"*{ark_id}.pdf"))
        if existing_files:
            print(f"  ⊙ Already downloaded: {ark_id}")
            return True, "Already exists"
        
        print(f"  Opening: {url}")
        driver.get(url)
        
        # Wait for page to load
        wait_random(3, 5)
        
        # Try direct PDF download URL
        pdf_url = f"https://gallica.bnf.fr/ark:/12148/{ark_id}.pdf"
        print(f"  Trying PDF URL: {pdf_url}")
        
        driver.get(pdf_url)
        
        # Wait a moment for the page to load
        time.sleep(3)
        
        # Check if we got an error page or authentication requirement
        try:
            page_title = driver.title.lower()
            page_source = driver.page_source.lower()
            
            # Check for common error indicators
            error_indicators = [
                'erreur', 'error', 'not found', '404', 'access denied',
                'authentification', 'authentication', 'login', 'connexion',
                'restricted', 'restreint', 'indisponible', 'unavailable',
                'payant', 'payment', 'abonnement', 'subscription'
            ]
            
            for indicator in error_indicators:
                if indicator in page_title or indicator in page_source[:2000]:  # Check first 2000 chars
                    print(f"  ⚠ Link requires authentication or is restricted")
                    print(f"  ⚠ SKIPPED: {url}")
                    return False, "Link not directly downloadable (authentication/payment required)"
        except:
            # If we can't check the page, continue anyway
            pass
        
        # Wait for download to actually start
        print(f"  Waiting for download to start...")
        download_started = False
        initial_wait = 15  # Wait up to 15 seconds for download to start
        start_time = time.time()
        
        while time.time() - start_time < initial_wait:
            # Check if download has started (.crdownload or .pdf file)
            crdownload_files = list(Path(download_folder).glob(f"*{ark_id}*.crdownload"))
            pdf_files = list(Path(download_folder).glob(f"*{ark_id}.pdf"))
            
            if crdownload_files or pdf_files:
                download_started = True
                print(f"  ✓ Download started")
                break
            
            time.sleep(1)
        
        if not download_started:
            print(f"  ⚠ Download did not start - link may not be directly downloadable")
            print(f"  ⚠ SKIPPED: {url}")
            return False, "Download did not start (link not directly downloadable)"
        
        # Wait for download to actually complete
        print(f"  Waiting for download to complete...")
        download_complete = False
        max_wait = 600  # 10 minutes max per file (for large PDFs)
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            # Check if PDF file exists (not .crdownload)
            existing_files = list(Path(download_folder).glob(f"*{ark_id}.pdf"))
            if existing_files:
                # File exists, check if it's still growing
                file_size = existing_files[0].stat().st_size
                time.sleep(5)  # Wait longer for large files
                new_size = existing_files[0].stat().st_size
                
                # Double-check that file has stopped growing
                if new_size == file_size and file_size > 1000:
                    time.sleep(5)  # Wait again to be sure
                    final_size = existing_files[0].stat().st_size
                    
                    if final_size == new_size:  # File truly stopped growing
                        download_complete = True
                        file_size_mb = file_size / (1024 * 1024)
                        print(f"  ✓ Download complete ({file_size_mb:.1f} MB)")
                        break
            
            time.sleep(3)
        
        if not download_complete:
            return False, "Download timeout or failed"
        
        return True, "Download complete"
        
    except Exception as e:
        return False, f"Error: {str(e)}"


def setup_driver(download_folder):
    """Setup undetected Chrome driver."""
    options = uc.ChromeOptions()
    
    # Set download directory
    abs_download_path = os.path.abspath(download_folder)
    prefs = {
        "download.default_directory": abs_download_path,
        "download.prompt_for_download": False,
        "plugins.always_open_pdf_externally": True,
    }
    options.add_experimental_option("prefs", prefs)
    
    # Don't use headless mode - it's easier to detect
    # options.add_argument("--headless")
    
    driver = uc.Chrome(options=options)
    return driver


def download_from_csv(csv_file, download_folder='gallica_downloads'):
    """Download all PDFs from CSV."""
    
    if not os.path.exists(csv_file):
        print(f"ERROR: CSV file '{csv_file}' not found!")
        return None
    
    Path(download_folder).mkdir(parents=True, exist_ok=True)
    
    print("=" * 70)
    print("Gallica Stealth Downloader")
    print("=" * 70)
    print(f"\nCSV file: {csv_file}")
    print(f"Download folder: {os.path.abspath(download_folder)}")
    print("\nStarting undetected Chrome browser...")
    
    driver = None
    successful = 0
    failed = 0
    total = 0
    
    try:
        driver = setup_driver(download_folder)
        print("✓ Browser started\n")
        print("-" * 70)
        
        # Read CSV
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            urls = [row[0].strip() for row in reader if row and row[0].strip()]
        
        total = len(urls)
        print(f"Found {total} URLs to process\n")
        
        for i, url in enumerate(urls, 1):
            ark_id = extract_ark_id(url)
            print(f"[{i}/{total}] {ark_id}")
            
            # Restart browser every 10 downloads to prevent crashes
            if i > 1 and (i - 1) % 10 == 0:
                print("  ⟳ Restarting browser to prevent memory issues...")
                try:
                    driver.quit()
                    time.sleep(3)
                except:
                    pass
                driver = setup_driver(download_folder)
                print("  ✓ Browser restarted\n")
            
            try:
                success, message = download_gallica_pdf(driver, url, ark_id, download_folder)
                
                if success:
                    successful += 1
                    print(f"  ✓ {message}")
                else:
                    failed += 1
                    print(f"  ✗ {message}")
            except Exception as e:
                failed += 1
                print(f"  ✗ Error: {str(e)}")
                # Try to restart browser on error
                try:
                    driver.quit()
                    time.sleep(3)
                except:
                    pass
                driver = setup_driver(download_folder)
                print("  ⟳ Browser restarted after error")
            
            # Random delay between downloads
            if i < total:
                delay = random.uniform(3, 6)
                print(f"  Waiting {delay:.1f}s before next download...\n")
                time.sleep(delay)
        
        print("-" * 70)
        print(f"\nSummary:")
        print(f"  Total: {total}")
        print(f"  Successful: {successful}")
        print(f"  Failed: {failed}")
        print(f"\nDownloads folder: {os.path.abspath(download_folder)}")
        
        # Wait for all downloads to complete before closing browser
        print("\nFinalizing downloads...")
        wait_for_downloads(download_folder, timeout=120)
        
        return {'total': total, 'successful': successful, 'failed': failed}
        
    except Exception as e:
        print(f"\nERROR: {str(e)}")
        return None
        
    finally:
        if driver:
            print("\nClosing browser in 5 seconds...")
            time.sleep(5)
            driver.quit()


if __name__ == "__main__":
    import sys
    
    csv_file = "test.csv"
    download_folder = "gallica_downloads"
    
    if len(sys.argv) > 1:
        csv_file = sys.argv[1]
    if len(sys.argv) > 2:
        download_folder = sys.argv[2]
    
    result = download_from_csv(csv_file, download_folder)
    
    if result:
        print("\n✓ Done!")
    else:
        print("\n✗ Failed!")
        sys.exit(1)
