#!/usr/bin/env python3
'''Web fuzzer'''
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from bs4 import BeautifulSoup
from fire import Fire
from requests import Session
from requests_cache import install_cache
from urllib3 import disable_warnings
from urllib3.exceptions import InsecureRequestWarning

from lib.progress import Progress

install_cache()
disable_warnings(InsecureRequestWarning)


class Fuzzy(Session):
    DD = Path(__file__).resolve().parent / 'dicts'

    def __init__(self, url):
        super().__init__()
        self.headers['User-Agent'] = 'Mozilla/5.0'
        self.start_url = url

    def fuzz(self, dicts, max_workers=None):
        dict_paths: list[Path] = [self.DD / f'{d}.txt' for d in dicts]
        for dp in dict_paths:
            print('[*] Using', dp.stem)
            with dp.open() as df:
                self._fuzz(df, max_workers)

    def _fuzz(self, file, max_workers):
        def read_chunk():
            return list(map(str.strip, file.readlines(1024)))

        progress = Progress(sum(1 for _ in file))
        file.seek(0)

        with ThreadPoolExecutor(max_workers) as ex:
            lines = read_chunk()

            def shutdown():
                ex.shutdown(wait=False, cancel_futures=True)
                exit()

            while lines:
                f = ex.map(self._check_path, lines)
                try:
                    for ok, path, code, cnt, title in f:
                        if ok:
                            print(f'\r[+] [{code}] {path} ({cnt} B)', title)
                        progress(path)
                except KeyboardInterrupt:
                    print('\rInterrupted')
                    shutdown()
                except Exception as e:
                    print(f'\r{repr(e)}')
                    # shutdown()
                lines = read_chunk()

    def _check_path(self, path):
        r = self.get(
            f'{self.start_url}{path}',
            verify=False,
            stream=True,
            timeout=5
        )
        code = r.status_code
        status = 200 <= code < 300 or code >= 500
        title = ''
        if status:
            s = BeautifulSoup(r.text, 'html.parser')
            if s.title:
                title = s.title.text
            elif s.h1:
                title = s.h1.text
            title = title.replace('\n', ' ').replace('\r', '')
        return status, path, code, len(r.content) if status else 0, title


def main(url, dicts=None):
    if isinstance(dicts, str):
        dicts = [dicts]
    Fuzzy(url).fuzz(dicts)


if __name__ == '__main__':
    Fire(main)
