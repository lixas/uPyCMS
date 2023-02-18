import gc  # type: ignore comment;
from machine import Timer, deepsleep
import libs.PyDB as mdb  # type: ignore comment;
from libs.phew import server
from libs.phew.template import render_template  # type: ignore comment;
import conf as c
from modules.common import admin_required, active_modules

modules_links= [
        "Modules management", [
        ["List modules",                "/admin/mods",          "fa-solid fa-list-ol"],
        ["Import and load modules",     "/admin/mods/import",   "fa-solid fa-file-import"],
    ]]


@server.route("/admin/mods")
async def mods_list(request):
    @admin_required
    async def f(request):
        result = []
        mods_table = mdb.Database.open("database").open_table("modules")
        for itm in mods_table.scan({}):
            result.append([
                itm["active"],
                itm["name"],
                itm["description"]
            ])
        await render_template(c.adm_head, leftmenu=modules_links, enabled_modules=active_modules)
        await render_template("{}mods.html".format(c.adm), mlist=result,)
        return await render_template(c.adm_foot)
    return await f(request)


@server.route("/admin/mods/<mod>/<act>")
async def mods_activate(request, mod, act):
    @admin_required
    async def f(request, mod, act):
        global active_modules
        if mod == "mod":
            return await "400"
        
        tbl = mdb.Database.open("database").open_table("modules")
        data = tbl.find({"name": mod}, True)

        if not data:
            return await "404"
        active = True if act=="1" else False
        tbl.update_row( data["_row"], {"active": active} )
        if active:
            active_modules.append(mod)
            __import__("modules.{}".format(mod))      # type: ignore comment;
        else:
            active_modules.remove(mod)
            gc.collect()
        return await "200"
    return await f(request, mod, act)

@server.route("/admin/mods/restart", methods=["POST"])
@admin_required
async def mods_reset(request):
    def restart(_):
        deepsleep(1)
    tim = Timer(-1)
    tim.init(mode=Timer.ONE_SHOT, period=5000, callback=restart)
    return await render_template("{}redirect.html".format(c.adm), location="/admin")