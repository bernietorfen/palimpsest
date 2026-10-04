"""Loopback-only viewing-room preview with byte-range media responses.

The standard Python preview server does not advertise seekable byte ranges.
Chromium treats some otherwise fully buffered audio files as unseekable there.
"""
import argparse
from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re
import shutil


class Handler(SimpleHTTPRequestHandler):
    protocol_version="HTTP/1.1"

    def send_head(self):
        self.byte_range=None
        requested=self.headers.get("Range","")
        match=re.fullmatch(r"bytes=(\d*)-(\d*)",requested)
        path=Path(self.translate_path(self.path))
        if not match or not path.is_file() or self.headers.get("If-Range"):
            return super().send_head()
        size=path.stat().st_size
        left,right=match.groups()
        if not left and not right:
            return super().send_head()
        start=int(left) if left else max(0,size-int(right))
        end=min(size-1,int(right)) if left and right else size-1
        if start>end or start>=size:
            self.send_response(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE)
            self.send_header("Content-Range",f"bytes */{size}")
            self.send_header("Content-Length","0")
            self.end_headers()
            return None
        source=path.open("rb")
        source.seek(start)
        self.byte_range=(start,end)
        self.send_response(HTTPStatus.PARTIAL_CONTENT)
        self.send_header("Content-Type",self.guess_type(str(path)))
        self.send_header("Content-Range",f"bytes {start}-{end}/{size}")
        self.send_header("Content-Length",str(end-start+1))
        self.send_header("Last-Modified",self.date_time_string(path.stat().st_mtime))
        self.end_headers()
        return source

    def end_headers(self):
        self.send_header("Accept-Ranges","bytes")
        super().end_headers()

    def copyfile(self,source,outputfile):
        if self.byte_range is None:
            return shutil.copyfileobj(source,outputfile)
        remaining=self.byte_range[1]-self.byte_range[0]+1
        while remaining:
            block=source.read(min(remaining,1024*1024))
            if not block:
                break
            outputfile.write(block)
            remaining-=len(block)


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--site",default="site")
    parser.add_argument("--port",type=int,default=8083)
    args=parser.parse_args()
    handler=partial(Handler,directory=Path(args.site).resolve())
    with ThreadingHTTPServer(("127.0.0.1",args.port),handler) as server:
        print(f"Viewing room on RunPod loopback port {args.port}",flush=True)
        server.serve_forever()
