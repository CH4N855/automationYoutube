"""Download through a real Chrome session when a site rejects yt-dlp."""
import os
from pathlib import Path


def browser_download(url, output, progress=None):
    import requests
    from selenium import webdriver
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.common.exceptions import SessionNotCreatedException, TimeoutException

    options = webdriver.ChromeOptions()
    options.add_argument('--user-data-dir=' + str(
        Path(os.environ['LOCALAPPDATA']) / 'Google/Chrome/User Data'))
    options.add_argument('--profile-directory=Profile 1')
    if progress:
        progress(None, 'Opening Chrome Profile 1. Close other Chrome windows if startup fails.')
    try:
        driver = webdriver.Chrome(options=options)
    except SessionNotCreatedException as exc:
        raise RuntimeError('Chrome Profile 1 could not start. Close all Chrome windows '
                           'and retry so the bot can use that profile.') from exc
    try:
        driver.set_page_load_timeout(45)
        driver.get(url)
        if progress:
            progress(None, 'Waiting for video in Chrome. Complete login or verification if shown.')
        try:
            source = WebDriverWait(driver, 90).until(lambda d: d.execute_script(
                "const v=document.querySelector('video'); "
                "if(v && v.currentSrc.startsWith('https://')) return v.currentSrc; "
                "const media=performance.getEntriesByType('resource').find(e => "
                "e.name.startsWith('https://') && e.name.includes('/video/tos/')); "
                "return media ? media.name : null;"))
        except TimeoutException as exc:
            raise RuntimeError('Chrome did not expose a downloadable video within 90 seconds. '
                               'The page may require verification or use an unsupported stream.') from exc
        with requests.Session() as session:
            session.headers.update({'User-Agent': driver.execute_script('return navigator.userAgent'),
                                    'Referer': driver.current_url})
            for cookie in driver.get_cookies():
                session.cookies.set(cookie['name'], cookie['value'],
                                    domain=cookie['domain'], path=cookie.get('path', '/'))
            if progress:
                progress(None, 'Downloading video from the browser stream...')
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
        driver.quit()
