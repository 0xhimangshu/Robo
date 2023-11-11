from http.server import SimpleHTTPRequestHandler
import http.server

server_address = ("0.0.0.0", 80)
PUBLIC_RESOURCE_PREFIX = './'
PUBLIC_DIRECTORY = '/transcripts/'

class MyRequestHandler(SimpleHTTPRequestHandler):

    def translate_path(self, path):
        if self.path.startswith(PUBLIC_RESOURCE_PREFIX):
            if self.path == PUBLIC_RESOURCE_PREFIX or self.path == PUBLIC_RESOURCE_PREFIX + '/':
                return PUBLIC_DIRECTORY + path[len(PUBLIC_RESOURCE_PREFIX):]
        else:
            return SimpleHTTPRequestHandler.translate_path(self, path)

with http.server.HTTPServer(server_address, MyRequestHandler) as httpd:
    print(f"Address: {server_address}")
    httpd.serve_forever()