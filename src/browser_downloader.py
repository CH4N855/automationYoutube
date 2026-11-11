"""Download through a real Chrome session when a site rejects direct scraping."""
import os
import shutil
import tempfile
from pathlib import Path


def browser_download(url, output, progress=None):
    import requests
    from selenium import webdriver
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.common.exceptions import SessionNotCreatedException, TimeoutException

    driver = None
    temp_user_data = None
    try:
        # Step 1: Attempt using the user's Chrome Profile 1 (if available and Chrome is closed)
        try:
            options = webdriver.ChromeOptions()
            chrome_user_data = Path(os.environ.get('LOCALAPPDATA', '')) / 'Google/Chrome/User Data'
            if chrome_user_data.exists():
                options.add_argument(f'--user-data-dir={chrome_user_data}')
                options.add_argument('--profile-directory=Profile 1')
            options.add_argument('--no-first-run')
            options.add_argument('--no-default-browser-check')
            if progress:
                progress(None, 'Opening Chrome browser session...')
            driver = webdriver.Chrome(options=options)
        except (SessionNotCreatedException, Exception):
            # Step 2: If user's Chrome is already running (profile locked), use isolated clean session
            if progress:
                progress(None, 'Chrome profile in use. Launching isolated background session...')
            temp_user_data = tempfile.mkdtemp(prefix='chrome-isolated-')
            fallback_opts = webdriver.ChromeOptions()
            fallback_opts.add_argument(f'--user-data-dir={temp_user_data}')
            fallback_opts.add_argument('--headless=new')
            fallback_opts.add_argument('--disable-gpu')
            fallback_opts.add_argument('--no-sandbox')
            fallback_opts.add_argument('--disable-dev-shm-usage')
            fallback_opts.add_argument('--window-size=1920,1080')
            fallback_opts.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36')
            driver = webdriver.Chrome(options=fallback_opts)

        driver.set_page_load_timeout(45)
        driver.get(url)
        if progress:
            progress(None, 'Resolving video media stream in browser...')

        try:
            source = WebDriverWait(driver, 90).until(lambda d: d.execute_script(
                "const v = document.querySelector('video'); "
                "if (v && v.currentSrc && v.currentSrc.startsWith('http')) return v.currentSrc; "
                "if (v && v.src && v.src.startsWith('http')) return v.src; "
                "const sources = Array.from(document.querySelectorAll('video source')).map(s => s.src).filter(s => s && s.startsWith('http')); "
                "if (sources.length > 0) return sources[0]; "
                "const media = performance.getEntriesByType('resource').find(e => "
                "  e.name.startsWith('https://') && (e.name.includes('/video/tos/') || e.name.includes('.mp4') || e.name.includes('mime_type=video_mp4'))"
                "); "
                "return media ? media.name : null;"
            ))
        except TimeoutException as exc:
            raise RuntimeError(
                'Browser did not expose a downloadable video within 90 seconds. '
                'The link may require login, verification, or is private/deleted.'
            ) from exc

        with requests.Session() as session:
            session.headers.update({
                'User-Agent': driver.execute_script('return navigator.userAgent') or 'Mozilla/5.0',
                'Referer': driver.current_url or 'https://www.tiktok.com/'
            })
            for cookie in driver.get_cookies():
                session.cookies.set(
                    cookie['name'], cookie['value'],
                    domain=cookie.get('domain', ''), path=cookie.get('path', '/')
                )
            if progress:
                progress(None, 'Downloading video from browser stream...')
            with session.get(source, stream=True, timeout=(15, 60)) as response:
                response.raise_for_status()
                if 'text/html' in response.headers.get('Content-Type', ''):
                    raise RuntimeError('The video server returned a web page instead of video.')
                with Path(output).open('wb') as target:
                    for chunk in response.iter_content(1024 * 256):
                        target.write(chunk)

        if Path(output).stat().st_size == 0:
            raise RuntimeError('The browser download was empty.')
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
        if temp_user_data and os.path.exists(temp_user_data):
            shutil.rmtree(temp_user_data, ignore_errors=True)
