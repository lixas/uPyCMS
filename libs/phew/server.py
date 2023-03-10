import uasyncio, os, time, sys, io  # type: ignore comment;
from . import logging

_total_bytes_sent = 0
_total_requests = {"Method":{}, "Status":{}}
_routes = []
_default_error_message = """<!DOCTYPE HTML><HTML><HEAD><TITLE>Error</TITLE></HEAD><BODY><h1>Internal Server Error</h1><p>Please check log for detail.</p></BODY></HTML>"""

# convert exception to string
def convert_exc2str(e):
  __ = io.StringIO()
  sys.print_exception(e, __)
  __.seek(0)
  return __.read()


def file_exists(filename):
    try:
        return (os.stat(filename)[0] & 0x4000) == 0
    except OSError:  # type: ignore comment;
        return False


def urldecode(text):
    text = text.replace("+", " ")
    result = ""
    token_caret = 0
    # decode any % encoded characters
    while True:
        start = text.find("%", token_caret)
        if start == -1:
            result += text[token_caret:]
            break
        result += text[token_caret:start]
        code = int(text[start + 1:start + 3], 16)
        result += chr(code)
        token_caret = start + 3
    return result


def _parse_query_string(query_string):
    result = {}
    for parameter in query_string.split("&"):
        key, value = parameter.split("=", 1)
        key = urldecode(key)
        value = urldecode(value)
        result[key] = value
    return result


class Request:
    def __init__(self, method, uri, protocol):
        self.method = method
        self.uri = uri
        self.protocol = protocol
        self.form = {}
        self.data = {}
        self.query = {}
        self.peer = {}
        query_string_start = uri.find("?") if uri.find("?") != -1 else len(uri)
        self.path = uri[:query_string_start]
        self.query_string = uri[query_string_start + 1:]
        if self.query_string:
            self.query = _parse_query_string(self.query_string)

    def __str__(self):
        return f"""\
request: {self.method} {self.path} {self.protocol}
headers: {self.headers}
form: {self.form}
data: {self.data}
peer: {self.peer}"""


class Response:
    def __init__(self, body, status=200, headers={}):
        self.status = status
        self.headers = headers
        self.body = body

    def add_header(self, name, value):
        self.headers[name] = value

    def __str__(self):
        return f"""\
status: {self.status}
headers: {self.headers}
body: {self.body}"""


content_type_map = {
    "html": "text/html",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "svg": "image/svg+xml",
    "json": "application/json",
    "png": "image/png",
    "css": "text/css",
    "js": "text/javascript",
    "csv": "text/csv",
}


class FileResponse(Response):
    def __init__(self, file, status=200, headers={}):
        self.status = 404
        self.headers = headers
        self.file = file

        try:
            if (os.stat(self.file)[0] & 0x4000) == 0:
                self.status = 200

                # auto set content type
                extension = self.file.split(".")[-1].lower()
                if extension in content_type_map:
                    headers["Content-Type"] = content_type_map[extension]

                headers["Content-Length"] = os.stat(self.file)[6]
                # tell browser to cache files, served via serve_file() for 7 days
                headers["Cache-Control"] = "public, max-age=604800, stale-while-revalidate=604800"
        except OSError:  # type: ignore comment;
            return False


class Route:
    def __init__(self, path, handler, methods=["GET"]):
        self.path = path
        self.methods = methods
        self.handler = handler
        self.path_parts = path.split("/")

    # returns True if the supplied request matches this route
    def matches(self, request):
        if request.method not in self.methods:
            return False
        compare_parts = request.path.split("/")
        if len(compare_parts) != len(self.path_parts):
            return False
        for part, compare in zip(self.path_parts, compare_parts):
            if not part.startswith("<") and part != compare:
                return False
        return True

    # call the route handler passing any named parameters in the path
    def call_handler(self, request):
        parameters = {}
        for part, compare in zip(self.path_parts, request.path.split("/")):
            if part.startswith("<"):
                name = part[1:-1]
                parameters[name] = compare

        return self.handler(request, **parameters)
                
    def __str__(self):
        return f"""\
path: {self.path}
methods: {self.methods}
"""

    def __repr__(self):
        return f"<Route object {self.path} ({', '.join(self.methods)})>"


# parses the headers for a http request (or the headers attached to
# each field in a multipart/form-data)
async def _parse_headers(reader):
    headers = {}
    while True:
        header_line = await reader.readline()
        if header_line == b"\r\n": # crlf denotes body start
            break
        name, value = header_line.decode().strip().split(": ", 1)
        headers[name.lower()] = value
    return headers


# returns the route matching the supplied path or None
def _match_route(request):
    for route in _routes:
        if route.matches(request):
            return route
    return None


# if the content type is multipart/form-data then parse the fields
async def _parse_form_data(reader, headers):
    boundary = headers["content-type"].split("boundary=")[1]
    # discard first boundary line
    # dummy = await reader.readline()
    await reader.readline()

    form = {}
    while True:
        # get the field name
        field_headers = await _parse_headers(reader)
        if len(field_headers) == 0:
            break
        name = field_headers["content-disposition"].split("name=\"")[1][:-1]

        while True:
            # get the field value
            line = await reader.readline()
            line = line.decode().rstrip()
            # if we hit a boundary then save the value and move to next field
            if line == "--" + boundary:
                break
            # if we hit end of form data boundary then save value and return
            elif line == "--" + boundary + "--":
                return form
            # its normal content line
            else:
                # if list used for checkboxes - form array
                if name.endswith("[]"):
                    form[name] = [line] if name not in form.keys() else form[name] + [line]
                else:
                    form[name] = line if name not in form.keys() else form[name] + "\n" + line
    return None


# if the content type is application/json then parse the body
async def _parse_json_body(reader, headers):
    import json
    content_length_bytes = int(headers["content-length"])
    body = await reader.readexactly(content_length_bytes)
    return json.loads(body.decode())


status_message_map = {
    200: "OK",
    201: "Created",
    202: "Accepted",
    203: "Non-Authoritative Information",
    204: "No Content",
    205: "Reset Content",
    206: "Partial Content",

    300: "Multiple Choices",
    301: "Moved Permanently",
    302: "Found",
    303: "See Other",
    304: "Not Modified",
    305: "Use Proxy",
    306: "Switch Proxy",
    307: "Temporary Redirect",
    308: "Permanent Redirect",

    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    405: "Method Not Allowed",
    406: "Not Acceptable",
    408: "Request Timeout",
    409: "Conflict",
    410: "Gone",
    414: "URI Too Long",
    415: "Unsupported Media Type", 
    416: "Range Not Satisfiable",
    418: "I'm a teapot",

    500: "Internal Server Error",
    501: "Not Implemented"
}


# handle an incoming request to the web server
async def _handle_request(reader, writer):
    global _error_handler, _total_bytes_sent, _total_requests

    response = None
    request_start_time = time.ticks_ms()

    request_line = await reader.readline()
    try:
        method, uri, protocol = request_line.decode().split()
    except Exception as e:  # type: ignore comment;
        logging.error(e)
        return

    request = Request(method, uri, protocol)
    request.headers = await _parse_headers(reader)

    # try to extract IP of the client connected
    request.peer["ip"] = request.headers.get('x-forwarded-for', writer.get_extra_info('peername')[0] )

    if "content-length" in request.headers and "content-type" in request.headers:
        if request.headers["content-type"].startswith("multipart/form-data"):
            request.form = await _parse_form_data(reader, request.headers)
        if request.headers["content-type"].startswith("application/json"):
            request.data = await _parse_json_body(reader, request.headers)
        if request.headers["content-type"].startswith("application/x-www-form-urlencoded"):
            form_data = await reader.read(int(request.headers["content-length"]))
            request.form = _parse_query_string(form_data.decode())

    route = _match_route(request)
    
    try:
        if route:
            response = route.call_handler(request)
        elif catchall_handler:
            response = catchall_handler(request)

    except Exception as e:                # type: ignore comment;
        error_msg = convert_exc2str(e)
        try:
            if _error_handler is not None:
                print("_error_handler", _error_handler, error_msg)
                response = _error_handler(e, error_msg)

        except Exception as ee:           # type: ignore comment;
        # replacing error message with new one
            error_msg = convert_exc2str(ee)

        finally:
            if response is None:
                response = Response(_default_error_message, status = 500)

        logging.error(error_msg)

    # if shorthand body generator only notation used then convert to tuple
    if type(response).__name__ == "generator":
        response = (response, )

    # if shorthand body text only notation used then convert to tuple
    if isinstance(response, str):
        response = (response,)

    # if shorthand tuple notation used then build full response object
    if isinstance(response, tuple):
        body = response[0]
        status = response[1] if len(response) >= 2 else 200
        content_type = response[2] if len(response) >= 3 else "text/html"

        additional_headers = response[3] if len(response) >= 4 else False

        response = Response(body, status=status)
        response.add_header("Content-Type", content_type)
        if additional_headers:
            for k, v in additional_headers.items():
                response.add_header(k, v)

        if hasattr(body, '__len__'):
            response.add_header("Content-Length", len(body))

    # write status line
    # print("response.status", response.status)
    status_message = status_message_map.get(response.status, "Unknown")
    status_line = "HTTP/1.1 {0} {1}\r\n".format(response.status, status_message).encode("ascii")
    writer.write(status_line)
    _total_bytes_sent += len(status_line)

    # write headers
    for key, value in response.headers.items():
        header = f"{key}: {value}\r\n".encode("ascii")
        writer.write(header)
        _total_bytes_sent += len(header)

    # blank line to denote end of headers
    writer.write("\r\n".encode("ascii"))
    _total_bytes_sent += 4

    if isinstance(response, FileResponse):
        # file
        with open(response.file, "rb") as f:
            while True:
                chunk = f.read(1024)
                if not chunk:
                    break
                _total_bytes_sent += len(chunk)
                writer.write(chunk)
                await writer.drain()
    elif type(response.body).__name__ == "generator":
        # generator
        # print("response.body", response.body)
        for chunk in response.body:
            _total_bytes_sent += len(chunk)

            for i in range(0, len(chunk), 1024):
                writer.write(chunk[i:i+1024])
                await writer.drain()
    else:
        # string/bytes
        _total_bytes_sent += len(response.body)
        writer.write(response.body)
        await writer.drain()

    writer.close()
    await writer.wait_closed()
    logging.info( "{0}> {1} {2} ({3} {4}) [{5}ms]".format(
            request.peer["ip"],
            request.method,
            request.path,
            response.status,
            status_message,
            time.ticks_ms() - request_start_time
        )
    )
    _total_requests["Method"][request.method] = _total_requests["Method"].get(request.method, 0) + 1
    _total_requests["Status"][response.status] = _total_requests["Status"].get(response.status, 0) + 1


# adds a new route to the routing table
def add_route(path, handler, methods=["GET"]):
    global _routes
    _routes.append(Route(path, handler, methods))
    # descending complexity order so most complex routes matched first
    _routes = sorted(_routes, key=lambda route: len(route.path_parts),
                     reverse=True)


def set_callback(handler):
    global catchall_handler
    catchall_handler = handler


# decorator shorthand for adding a route
def route(path, methods=["GET"]):
    def _route(f):
        add_route(path, f, methods=methods)
        return f
    return _route


# decorator for adding catchall route
def catchall():
    def _catchall(f):
        set_callback(f)
        return f
    return _catchall


def errorhandler(e, emsg):
    def _wrap(f):
        global _error_handler
        _error_handler = f
        return f
    return _wrap


def redirect(url, status = 301):
    return Response("", status, {"Location": url})


def serve_file(file, head={}):
    return FileResponse(file, headers= head)

def get_stats():
    global _total_bytes_sent, _total_requests
    return (_total_bytes_sent, _total_requests)

def run(host = "0.0.0.0", port = 80):
    logging.info("> starting web server on port {}".format(port))

    loop = uasyncio.get_event_loop()
    loop.create_task(uasyncio.start_server(_handle_request, host, port))
    loop.run_forever()


catchall_handler = None
_error_handler = errorhandler