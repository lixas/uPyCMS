import os  # type: ignore comment;
from libs.phew import server
from libs.phew.template import render_template, render_template_noreplace  # type: ignore comment;
import conf as c
from .common import admin_required, dir_exists, file_exists, breadcrumb, active_modules

filesys= [
        "Browse folders", [
        ["Root",        "/admin/files/browse/",         "fa-solid fa-folder-tree"],
        ["Blogs",       "/admin/files/browse/blogs",    "fa-solid fa-blog"],
        ["Pages",       "/admin/files/browse/pages",    "fa-regular fa-file-lines"],
        ["Database",    "/admin/files/browse/database", "fa-solid fa-database"],
        ["Themes",      "/admin/files/browse/themes",   "fa-solid fa-palette"],
        ["SD Card",     "/admin/files/browse/sd",       "fa-solid fa-sd-card"],
    ]]

@server.route("/admin/files")
async def a_files(request):
    @admin_required
    async def f(request):
        await render_template(c.adm_head, leftmenu=filesys, enabled_modules=active_modules)
        await render_template("{}file-chunk-begin.html".format(c.adm), breadcrumb=[], parent=None, msg=None)
        for loc in filesys[1]:
            await render_template("{}file-chunk-browse.html".format(c.adm), d=[loc[0], loc[1].split("/")[-1], ""])
        await render_template("{}file-chunk-end.html".format(c.adm))
        return await render_template(c.adm_foot)
    return await f(request)


@server.route("/admin/files/browse/<location>")
async def a_f_browse(request, location):
    @admin_required
    async def f(request, location):
        current = location.replace("..", "").strip(":")
        location_path = "/{}".format(current.replace(":", "/"))
        dlist = []
        flist = []


        if not dir_exists(location_path):
            msg = "Location {} does not exist or inaccesible".format(location_path)
            parent = ""
        else:
            msg =  ""
            for loc in os.ilistdir(location_path):
                name = "{0}".format(loc[0])
                if loc[1] == 0x8000:        #file
                    size = loc[3]
                    path = "{0}:{1}".format(current, loc[0]) if current else "{}".format(loc[0])
                    flist.append([name, path, size])
                elif loc[1] == 0x4000:        #folder
                    size = ""
                    path = "{0}:{1}".format(current, loc[0]) if current else "{}".format(loc[0])
                    dlist.append([name, path, size])
                else:
                    pass

                parent = ":".join(current.split(":")[:-1]) if len(current.split(":"))> 1 else " "
        await render_template(c.adm_head, leftmenu=filesys, enabled_modules=active_modules)
        await render_template("{}file-chunk-begin.html".format(c.adm), breadcrumb=breadcrumb(current), parent=parent, msg=msg)
        for d in dlist:
            await render_template("{}file-chunk-browse.html".format(c.adm), d=d)
        for fl in flist:
            await render_template("{}file-chunk-view.html".format(c.adm), f=fl)
        await render_template("{}file-chunk-end.html".format(c.adm))
        return await render_template(c.adm_foot)
    return await f(request, location)


@server.route("/admin/files/view/<location>")
async def a_f_view(request, location):
    @admin_required
    async def f(request, location):
        current = location.replace("..", "").strip(":")
        with open("/{}".format(current.replace(":", "/")), "r") as f:
            await render_template(c.adm_head, leftmenu=filesys, enabled_modules=active_modules)
            await render_template_noreplace("{}file-view-begin.html".format(c.adm), 
                file_title="/{}".format(current.replace(":", "/")),
            )
            while True:
                data = f.read(256)
                if not data:
                    break
                await render_template("{}string.html".format(c.adm), s=data.replace(">", "&gt;").replace("<", "&lt;"))
            
            await render_template_noreplace("{}file-view-end.html".format(c.adm), 
                back_location = ":".join(current.split(":")[:-1]),
            )
            return await render_template(c.adm_foot)
    return await f(request, location)        


@server.route("/admin/files/del/<location>", methods=["GET", "POST"])
async def a_f_del(request, location):
    @admin_required
    async def f(request, location):
        return_location = request.query.get("return", None)
        current = location.replace("..", "").replace(":", "/").split("/")
        cleaned_path = "/{}".format('/'.join([part for part in current if part]))

        for safe_location in c.safe_locations:
            if cleaned_path.startswith(safe_location.rstrip("*")):
                return await render_template("{}string.html".format(c.adm), s="{} is a safe location and cannot be deleted".format(cleaned_path))
        if file_exists(cleaned_path):
            os.remove(cleaned_path)
        else:
            return await render_template("{}string.html".format(c.adm), s="Error: Provided location {} does not exist".format(cleaned_path))

        if return_location == "page":
            from .pages import a_page
            return await a_page(request)
        
        if return_location == "file":
            return_path = ":".join(current[:-1])
            return await a_f_browse(request, return_path)
        
        return await render_template("{}string.html".format(c.adm), s="File '{0}' deleted. Need to return to '{1}'".format(location, return_location))
    return await f(request, location)
