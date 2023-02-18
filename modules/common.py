import os
from libs import session as ses
from libs.phew.template import render_template  # type: ignore comment;
import libs.PyDB as mdb  # type: ignore comment;

active_modules = []

def error_page(code):
    with open("/themes/basic/{}.html".format(str(code).replace("..", "")))as f:
        return f.read()

def isAdmin(req):
    sesKey = ses.extractFromCookie(req)
    if ses.is_valid(sesKey):
        if ses.get_data(sesKey).get("isAdmin") == 1:
            ses.refresh_session(sesKey)
            return True
    return False

# decorator
def admin_required(f):
    def d(request, *args, **kwargs):
        if not isAdmin(request):
            return render_template("/themes/admin/login.html", follow=request.path)
        return f(request, *args, **kwargs)
    return d

def file_exists(path):
    try:
        f = open(path, 'r') 
        f.close()
        return True
    except OSError:  # type: ignore comment;
        return False

def dir_exists(path):
    try:
        return os.stat(path)[0] & 0o170000 == 0o040000
    except OSError:  # type: ignore comment;
        return False

def breadcrumb(s):
    parts = s.split(":")
    objects = []
    path = ""
    for _, part in enumerate(parts):
        path += part
        objects.append({"P": path, "T": part})
        path += ":"
    return objects

def get_file_size(path):
    path_array = path.split("/")
    name = path_array.pop()
    location = "/".join(path_array)
    if(dir_exists(location)):
        for loc in os.ilistdir(location):
            if loc[0] == name:
                return loc[3]
    else:
        return False

tbl = mdb.Database.open("database").open_table("modules")
for mod in tbl.query({"active": True}):
    active_modules.append(mod['name'])