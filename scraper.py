import requests
from bs4 import BeautifulSoup
import re
import os
from urllib.parse import urljoin

URL = "https://www.fancode.com/cricket/tour/bangladesh-premier-league-2025-26-19256675/video-highlights"

headers = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 9; Termux) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
}

def download_image(image_url, filename, folder="images"):
    """Download and save an image from URL"""
    try:
        # Create folder if it doesn't exist
        if not os.path.exists(folder):
            os.makedirs(folder)
        
        # Get image content
        img_response = requests.get(image_url, headers=headers, stream=True)
        if img_response.status_code == 200:
            # Extract filename from URL if not provided
            if not filename:
                filename = image_url.split("/")[-1].split("?")[0]
            
            # Add extension if missing
            if not filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                # Try to get content type
                content_type = img_response.headers.get('content-type', '')
                if 'image/jpeg' in content_type:
                    filename += '.jpg'
                elif 'image/png' in content_type:
                    filename += '.png'
                elif 'image/webp' in content_type:
                    filename += '.webp'
                else:
                    filename += '.jpg'
            
            filepath = os.path.join(folder, filename)
            
            # Save image
            with open(filepath, 'wb') as f:
                for chunk in img_response.iter_content(1024):
                    f.write(chunk)
            
            print(f"✓ Image saved: {filepath}")
            return filepath
        else:
            print(f"✗ Failed to download image: {image_url} (Status: {img_response.status_code})")
            return None
    except Exception as e:
        print(f"✗ Error downloading image {image_url}: {e}")
        return None

def scrape_images(soup, base_url):
    """Scrape all images from the page"""
    images = []
    
    # Find all image tags
    for img_tag in soup.find_all("img"):
        img_data = {}
        
        # Get image URL
        if img_tag.get("src"):
            img_url = img_tag["src"]
        elif img_tag.get("data-src"):  # For lazy-loaded images
            img_url = img_tag["data-src"]
        else:
            continue
        
        # Convert relative URL to absolute
        img_url = urljoin(base_url, img_url)
        
        # Get alt text
        alt_text = img_tag.get("alt", "").strip()
        
        # Get title or caption
        title = img_tag.get("title", "").strip()
        
        # Get image dimensions if available
        width = img_tag.get("width", "")
        height = img_tag.get("height", "")
        
        img_data = {
            "url": img_url,
            "alt": alt_text,
            "title": title,
            "width": width,
            "height": height,
            "filename": ""
        }
        
        images.append(img_data)
        print(f"Found image: {alt_text or 'No alt text'} | URL: {img_url}")
    
    return images

def scrape_highlights(url):
    print(f"Scraping: {url}")
    print("-" * 50)
    
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Failed to fetch page, status code: {response.status_code}")
        return

    soup = BeautifulSoup(response.text, "html.parser")
    
    # ====== IMAGE SCRAPING ======
    print("\n" + "=" * 50)
    print("SCRAPING IMAGES")
    print("=" * 50)
    
    images = scrape_images(soup, url)
    
    if images:
        print(f"\nFound {len(images)} images")
        
        # Download first 5 images as example
        download_count = min(5, len(images))
        print(f"\nDownloading first {download_count} images...")
        
        for i, img in enumerate(images[:download_count]):
            print(f"\n[{i+1}/{download_count}]")
            # Create a safe filename
            if img['alt']:
                filename = re.sub(r'[^\w\s-]', '', img['alt']).strip().replace(' ', '_')
                filename = filename[:50]  # Limit filename length
            else:
                filename = f"image_{i+1}"
            
            img['filename'] = download_image(img['url'], filename)
    else:
        print("No images found on the page")
    
    # ====== HIGHLIGHTS SCRAPING ======
    print("\n" + "=" * 50)
    print("SCRAPING VIDEO HIGHLIGHTS")
    print("=" * 50)
    
    highlights = []
    
    # Try multiple selectors for finding highlights
    # 1. Look for video links in anchor tags
    for a_tag in soup.find_all("a", href=True):
        href = a_tag['href']
        title = a_tag.get_text(strip=True)
        
        # Check for video-related content
        if href and ("video" in href.lower() or "highlight" in href.lower()):
            if title and len(title) > 3:  # Reduced minimum length
                # Get thumbnail if available (look for image within anchor)
                thumbnail = ""
                img_tag = a_tag.find("img")
                if img_tag:
                    if img_tag.get("src"):
                        thumbnail = urljoin(url, img_tag["src"])
                    elif img_tag.get("data-src"):
                        thumbnail = urljoin(url, img_tag["data-src"])
                
                highlight_data = {
                    "title": title,
                    "link": urljoin(url, href),
                    "thumbnail": thumbnail
                }
                highlights.append(highlight_data)
    
    # 2. Look for video elements directly
    video_tags = soup.find_all("video")
    for video in video_tags:
        if video.get("src"):
            title = video.get("title", "Video")
            poster = video.get("poster", "")  # Thumbnail
            
            highlight_data = {
                "title": title,
                "link": urljoin(url, video["src"]),
                "thumbnail": urljoin(url, poster) if poster else ""
            }
            highlights.append(highlight_data)
    
    # 3. Look for meta tags that might contain video info
    meta_tags = soup.find_all("meta")
    for meta in meta_tags:
        if meta.get("property") in ["og:video", "og:video:url"]:
            video_url = meta.get("content", "")
            if video_url and ("highlight" in video_url.lower() or "video" in video_url.lower()):
                # Try to get title from og:title
                title = "Video Highlight"
                title_meta = soup.find("meta", property="og:title")
                if title_meta:
                    title = title_meta.get("content", "Video Highlight")
                
                # Get thumbnail from og:image
                thumbnail = ""
                image_meta = soup.find("meta", property="og:image")
                if image_meta:
                    thumbnail = image_meta.get("content", "")
                
                highlight_data = {
                    "title": title,
                    "link": urljoin(url, video_url),
                    "thumbnail": urljoin(url, thumbnail) if thumbnail else ""
                }
                highlights.append(highlight_data)
    
    # Remove duplicates
    seen_links = set()
    unique_highlights = []
    for h in highlights:
        if h['link'] not in seen_links:
            unique_highlights.append(h)
            seen_links.add(h['link'])
    
    # Display results
    if unique_highlights:
        print(f"\nFound {len(unique_highlights)} video highlights:\n")
        for i, h in enumerate(unique_highlights, 1):
            print(f"{i}. {h['title']}")
            print(f"   Link: {h['link']}")
            if h['thumbnail']:
                print(f"   Thumbnail: {h['thumbnail']}")
            print()
    else:
        print("\nNo video highlights found directly in HTML.")
        print("The site likely uses JavaScript to load content dynamically.")
        print("\nSuggestions:")
        print("1. Check if the site has an API endpoint (look in Network tab of browser DevTools)")
        print("2. Use requests to fetch JSON data if available")
        print("3. Look for iframe or embed tags that might contain video")
        
        # Check for iframes
        iframes = soup.find_all("iframe")
        if iframes:
            print(f"\nFound {len(iframes)} iframe(s) that might contain videos:")
            for iframe in iframes[:3]:  # Show first 3
                src = iframe.get("src", "")
                if src:
                    print(f"  - {src}")
    
    return {
        "images": images[:5],  # Return first 5 images
        "highlights": unique_highlights,
        "total_images": len(images),
        "total_highlights": len(unique_highlights)
    }

def scrape_page_metadata(soup, url):
    """Extract meta information about the page"""
    print("\n" + "=" * 50)
    print("PAGE METADATA")
    print("=" * 50)
    
    metadata = {}
    
    # Page title
    title = soup.find("title")
    if title:
        metadata['title'] = title.text.strip()
        print(f"Page Title: {metadata['title']}")
    
    # Meta description
    desc = soup.find("meta", attrs={"name": "description"})
    if desc:
        metadata['description'] = desc.get("content", "").strip()
        print(f"Description: {metadata['description'][:100]}...")
    
    # Open Graph tags
    og_tags = {}
    for meta in soup.find_all("meta", property=re.compile(r"^og:")):
        property_name = meta.get("property", "")[3:]
        content = meta.get("content", "")
        if property_name and content:
            og_tags[property_name] = content
    
    if og_tags:
        metadata['og_tags'] = og_tags
        print(f"Open Graph tags found: {len(og_tags)}")
    
    return metadata

if __name__ == "__main__":
    print("FanCode Scraper - BPL 2025-26 Highlights")
    print("=" * 50)
    
    results = scrape_highlights(URL)
    
    # Print summary
    print("\n" + "=" * 50)
    print("SCRAPING SUMMARY")
    print("=" * 50)
    print(f"Total images found: {results['total_images']}")
    print(f"Total highlights found: {results['total_highlights']}")
    print(f"Images downloaded: {len([img for img in results['images'] if img.get('filename')])}")
    print("=" * 50)
    
    # Save results to a text file
    try:
        with open("scraping_results.txt", "w") as f:
            f.write("FanCode BPL 2025-26 Scraping Results\n")
            f.write("=" * 50 + "\n")
            f.write(f"URL: {URL}\n")
            f.write(f"Total images found: {results['total_images']}\n")
            f.write(f"Total highlights found: {results['total_highlights']}\n\n")
            
            f.write("VIDEO HIGHLIGHTS:\n")
            f.write("-" * 30 + "\n")
            for i, h in enumerate(results['highlights'], 1):
                f.write(f"{i}. {h['title']}\n")
                f.write(f"   Link: {h['link']}\n")
                if h['thumbnail']:
                    f.write(f"   Thumbnail: {h['thumbnail']}\n")
                f.write("\n")
        
        print("Results saved to: scraping_results.txt")
    except Exception as e:
        print(f"Note: Could not save results to file: {e}")
