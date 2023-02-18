import os  # type: ignore comment;
from libs import session as ses
from libs.phew import server
from libs.phew.template import render_template, render_template_noreplace  # type: ignore comment;
import conf as c
from modules.common import admin_required, file_exists, active_modules


page_links= [
        "Static pages management", [
        ["List pages",      "/admin/page", "fa-solid fa-list-ol"],
        ["Create new page", "/admin/new/page", "fa-solid fa-file-circle-plus"],
    ]]


@server.route("/admin/page")
async def a_page(request):
    @admin_required
    async def f(request):
        pages_list = []
        root = "/pages/"
        for entry in os.ilistdir(root):
            if entry[0] != "codes":
                file_without_ext = entry[0][:entry[0].rindex(".")]
                pages_list.append([file_without_ext, entry[3]])
        if len(pages_list)>0:
            await render_template(c.adm_head, leftmenu=page_links, enabled_modules=active_modules)
            await render_template("{}page.html".format(c.adm), plist=pages_list)
            return await render_template(c.adm_foot)
        else:
            return await render_template_noreplace("{}generic.html".format(c.adm), 
                content="No pages available. <a href=\"/admin/new/page\">Create new</a>",
                leftmenu=page_links, enabled_modules=active_modules)
    return await f(request)


@server.route("/admin/page/edit/<pagename>")
async def a_p_edit(request, pagename):
    @admin_required
    async def f(request, pagename):
        page = [str(pagename)]
        data_file_path = "/pages/{0}.md".format(pagename)
        if file_exists(data_file_path):
            with open(data_file_path, "r") as f:
                page.append(f.read())
        else:
            page.append("WARNING: data file at path {} not found".format(data_file_path))

        await render_template(c.adm_head, leftmenu=page_links, enabled_modules=active_modules)
        await render_template("{}page-edit.html".format(c.adm), page_data= page)
        return await render_template(c.adm_foot)
    return await f(request, pagename)


@server.route("/admin/page/save", methods=["POST"])
async def a_p_save(request):
    @admin_required
    async def f(request):
        filename = request.form.get("filename", None)
        #clear unwanted symbols
        for symbol in "./\\~`!@#$%^&*()-=_+":
            filename = filename.replace(symbol, "")
        if filename:
            with open("/pages/{0}.md".format(filename), 'w') as f:
                f.write(request.form.get("pagetext", None))
            return await a_page(request)

        return await render_template_noreplace("{}generic.html".format(c.adm), 
                content="Filename was left blank. <a href='#' onclick='history.back()'>Go back</a> and try again",
                leftmenu=page_links, enabled_modules=active_modules)
    return await f(request)
