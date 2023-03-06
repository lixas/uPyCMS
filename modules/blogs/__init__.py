import os, time  # type: ignore comment;
import libs.PyDB as mdb  # type: ignore comment;
from libs.phew import server
from libs.phew.template import render_template, render_template_noreplace  # type: ignore comment;
import conf as c
from modules.common import admin_required, file_exists, dir_exists, active_modules

blog_links= [
        "Manage your blogs", [
        ["List blogs",  "/admin/blog",              "fa-solid fa-list-ol"],
        ["Write blog",  "/admin/new/blog",          "fa-solid fa-file-circle-plus"],
        ["Settings",    "/admin/blog/settings",     "fa-solid fa-gear"],
    ]]

@server.route("/admin/blog")
async def a_blog(request):
    @admin_required
    async def f(request):
        result = []

        blogs_table = mdb.Database.open("database").open_table("blogs")
        for itm in blogs_table.scan({}, True):
            path = "/blogs/{}/{}.md".format(itm["path"], itm["_row"])
            result.append([
                itm["_row"],           # 0
                itm["title"],          # 1
                itm["authorid"],       # 2
                itm["published"],      # 3
                path,                  # 4
                itm["size"],           # 5
                itm["readtime"]        # 6
            ])

        if len(result)>0:
            await render_template(c.adm_head, leftmenu=blog_links, enabled_modules=active_modules)
            await render_template("{}/blog.html".format(__path__), blist=result,)
            return await render_template(c.adm_foot)
            
        else:
            return await render_template_noreplace("{}generic.html".format(c.adm), 
                content="No blogs available. <a href=\"/admin/new/blog\">Create new</a>",
                leftmenu=blog_links, enabled_modules=active_modules
            )
    return await f(request)


@server.route("/admin/blog/save", methods=["POST"])
async def a_b_save(request):
    @admin_required
    async def f(request):
        try:
            blog_id = int(request.form.get("blog_id", 0))
        except ValueError:  # type: ignore comment;
            return await render_template("{}generic.html".format(c.adm), 
                content="Blog ID error. ID should be integer",
                leftmenu=blog_links, enabled_modules=active_modules
            )

        # create new record
        blogs_table = mdb.Database.open("database").open_table("blogs")
        if blog_id == 0:
            now = time.localtime()
            blog_path = "{0}-{1:02d}".format(now[0], now[1])

            path = "/blogs/{0}".format(blog_path)
            if not dir_exists(path):
                os.mkdir(path)

            if blogs_table.insert({
                "title": request.form.get("title", None), 
                "authorid": 999, 
                "published": "{0}-{1:02d}-{2:02d} {3:02d}:{4:02d}".format(now[0], now[1], now[2], now[3], now[4]), 
                "path": blog_path, 
                "readtime": request.form.get("readtime", "0:00"),
                "size": len(request.form.get("blog", None))
            }):
                with open("/blogs/{0}/{1}.md".format(blog_path, blogs_table.current_row), 'w') as f:
                    f.write(request.form.get("blog", None))
        # Update existing record
        else:
            data = blogs_table.find_row(blog_id)
            data["d"]["title"] = request.form.get("title", None)
            data["d"]["readtime"] = request.form.get("readtime", "0:00")
            data["d"]["size"] = len(request.form.get("blog", None))

            with open("/blogs/{0}/{1}.md".format(data["d"]["path"], blog_id), 'w') as f:
                f.write(request.form.get("blog", None))
                blogs_table.update_row(blog_id, data["d"])
        return await a_blog(request)
    return await f(request)


@server.route("/admin/blog/edit/<blog_id>")
async def a_b_edit(request, blog_id):
    @admin_required
    async def f(request, blog_id):
        try:
            blog_id = int(blog_id)
        except ValueError:  # type: ignore comment;
            return await render_template("{}generic.html".format(c.adm), 
                content="Blog ID error", leftmenu=blog_links, enabled_modules=active_modules)
        data = mdb.Database.open("database").open_table("blogs").find_row(blog_id)

        blog = []
        blog.append(data["r"])              # 0
        blog.append(data["d"]["title"])     # 1
        data_file_path = "/blogs/{0}/{1}.md".format(data["d"]["path"], data["r"])
        if file_exists(data_file_path):
            with open(data_file_path, "r") as f:
                blog.append(f.read())       # 2
        else:
            blog.append("WARNING: data file at path {} not found".format(data_file_path))
        await render_template(c.adm_head, leftmenu=blog_links, enabled_modules=active_modules)
        await render_template("{}/blog-edit.html".format(__path__), 
                blog_data=blog,
        )
        return await render_template(c.adm_foot)
    return await f(request, blog_id)


@server.route("/admin/blog/delete/<blog_id>")
async def a_b_delete(request, blog_id):
    @admin_required
    async def f(request, blog_id):
        try:
            blog_id = int(blog_id)
        except ValueError:  # type: ignore comment;
            return await render_template("{}generic.html".format(c.adm), 
                content="Blog ID error", leftmenu=blog_links, enabled_modules=active_modules )

        blogs_table = mdb.Database.open("database").open_table("blogs")
        data = blogs_table.find_row(blog_id)
        data_file_path = "/blogs/{0}/{1}.md".format(data["d"]["path"], data["r"])
        if file_exists(data_file_path):
            os.remove(data_file_path)
        blogs_table.delete_row(blog_id)
        return await a_blog(request)
    return await f(request, blog_id)        


@server.route("/admin/blog/settings", methods=["GET", "POST"])
async def a_b_settings(request):
    @admin_required
    async def f(request):
        if request.form.get("action", 0) == "update":
            # update database with new values
            pass
        # read database
        # show on page
        return await "ok"
    return await f(request)
