import gc, uasyncio, os, time  # type: ignore comment;
gc.enable()
import libs.PyDB as mdb  # type: ignore comment;
from libs.phew import server
from libs import session as ses
from libs.phew.template import render_template, render_template_noreplace  # type: ignore comment;
import conf as c
from .common import admin_required, file_exists

code_links=[
        "Management of Code Pages", [
        ["List Codes",          "/admin/code",          "fa-solid fa-list-ul"],
        ["Create new",          "/admin/new/code",      "fa-solid fa-file-circle-plus"],
        ["TODO: About Code Pages",    "/admin/code/about",    "fa-solid fa-file-circle-question"],
    ]]

@server.route("/admin/code")
async def a_code(request):
    @admin_required
    async def f(request):
        code_list = []
        code_table = mdb.Database.open("database").open_table("codepages")
        for i in code_table.scan({}, True):
            code_list.append([
                i["_row"],            # 0
                i["hyperlink"],       # 1
                i["enabled"],         # 2
                i["methods"],         # 3
                i["title"],           # 4
                i["exec_path"],       # 5
                i["created"],         # 6
                i["modified"]         # 7
            ])

        if len(code_list)== 0:
            return await render_template_noreplace("{}generic.html".format(c.adm), 
                content="No code pages available. <a href=\"/admin/new/code\">Create new</a>",
                leftmenu=code_links, enabled_modules=c.modules)
        await render_template(c.adm_head, leftmenu=code_links, enabled_modules=c.modules)
        await render_template("{}code.html".format(c.adm), code_list=code_list)
        return await render_template(c.adm_foot)
    # gc.collect()
    return await f(request)


@server.route("/admin/code/save", methods=["POST"])
async def a_c_save(request):
    @admin_required
    async def f(request):
        try:
            code_id = int(request.form.get("code_id", 0))
        except ValueError:  # type: ignore comment;
            return await render_template("{}generic.html".format(c.adm), 
                content="Code ID error- should be integer",
                leftmenu=code_links, enabled_modules=c.modules
            )
        # create new record
        codes_table = mdb.Database.open("database").open_table("codepages")
        location = "/pages/codes/"
        now = time.localtime()
        created = "{0}-{1:02d}-{2:02d} {3:02d}:{4:02d}".format(now[0], now[1], now[2], now[3], now[4])
        modified = created
        # Create new rcord
        methods = " ".join(request.form.get("methods[]", ""))
        enabled = True if request.form.get("enabled", 0) == "1" else False
        if code_id == 0:

            # avoid generation of file name, that already exists
            alphabet = "ABCDEFGHIJKLMNOPQRSTUXWYZ1234567890"
            code_path = "Code{0}".format( ses.generate_random_string(8, alphabet))
            path_content = os.listdir(location)
            while True:
                if code_path in path_content:
                    code_path = "{0}".format( ses.generate_random_string(8, alphabet))
                else:
                    break
            # new record inserted successfuly
            if codes_table.insert({
                "hyperlink": request.form.get("hyperlink", code_path),
                "exec_path": code_path,
                "title": request.form.get("title", "No title was provided"),
                "methods": methods,
                "enabled": enabled,
                "created": created,
                "modified": modified
            }):
                with open("{0}{1}.py".format(location, code_path), 'w') as f:
                    f.write(request.form.get("code", None))
        # Update existing record
        else:
            data = codes_table.find_row(code_id)
            data["d"]["title"] = request.form.get("title", None)
            data["d"]["hyperlink"] = request.form.get("hyperlink", None)
            data["d"]["methods"] = methods
            data["d"]["enabled"] = enabled
            data["d"]["modified"] = modified

            data_file_path = "/pages/codes/{0}.py".format(data["d"]["exec_path"])
            with open(data_file_path, 'w') as f:
                f.write(request.form.get("code", None))
                codes_table.update_row(code_id, data["d"])

        return await a_code(request)
    # gc.collect()
    return await f(request)


@server.route("/admin/code/edit/<code_id>")
async def a_c_edit(request, code_id):
    @admin_required
    async def f(request, code_id):
        # check if blog is is numeric
        try:
            code_id = int(code_id)
        except ValueError:  # type: ignore comment;
            return await render_template("{}generic.html".format(c.adm), 
                content="Code ID error",
                leftmenu=code_links, enabled_modules=c.modules
            )

        data = mdb.Database.open("database").open_table("codepages").find_row(code_id)
        code=[
            data["r"],
            data["d"]["hyperlink"],
            data["d"]["title"],
            data["d"]["methods"],
            data["d"]["enabled"],
        ]
        data_file_path = "/pages/codes/{0}.py".format(data["d"]["exec_path"])
        if file_exists(data_file_path):
            with open(data_file_path, "r") as f:
                code.append(f.read())
        else:
            code.append("WARNING: data file at path {} not found".format(data_file_path))
        await render_template(c.adm_head, leftmenu=code_links, enabled_modules=c.modules)
        await render_template("{}code-edit.html".format(c.adm), code_data=code)
        return await render_template(c.adm_foot)
    # gc.collect()
    return await f(request, code_id)

@server.route("/admin/code/delete/<code_id>")
async def a_c_delete(request, code_id):
    @admin_required
    async def f(request, code_id):
        # check if code id is numeric
        try:
            code_id = int(code_id)
        except ValueError:  # type: ignore comment;
            return await render_template("{}generic.html".format(c.adm), 
                content="Code ID error",
                leftmenu=code_links, enabled_modules=c.modules
            )

        codes_table = mdb.Database.open("database").open_table("codepages")
        data = codes_table.find_row(code_id)

        data_file_path = "/pages/codes/{0}.py".format(data["d"]["exec_path"])
        if file_exists(data_file_path):
            os.remove(data_file_path)
        codes_table.delete_row(code_id)
        return await a_code(request)
    # gc.collect()
    return await f(request, code_id)   
