import time  # type: ignore comment;
from libs import session as ses
from libs.phew import server
from libs.phew.template import render_template  # type: ignore comment;
import conf as c
from modules.common import admin_required, active_modules

nav_links= [
        "Be on time", [
        ["Sync now",    "/admin/servertime/sync",   "fa-solid fa-rotate"],
    ]]

@server.route("/admin/servertime")
async def a_time(request):
    @admin_required
    async def f(request):
        now = time.localtime()
        return await render_template("{}generic.html".format(c.adm), 
                content="Time zone: {5} and server time: {0}-{1:02d}-{2:02d} {3:02d}:{4:02d}".format(now[0], now[1], now[2], now[3], now[4], c.timezone),
                leftmenu=nav_links,
                enabled_modules=active_modules )
    return await f(request) 

@server.route("/admin/servertime/sync")
async def a_t_sync(request):
    @admin_required
    async def f(request, ses):
        now = time.localtime()
        before = "{0}-{1:02d}-{2:02d} {3:02d}:{4:02d}".format(now[0], now[1], now[2], now[3], now[4])
        import libs.ntptime2    # type: ignore comment;
        libs.ntptime2.settime(c.timezone)
        del(libs.ntptime2)
        now = time.localtime()
        after = "{0}-{1:02d}-{2:02d} {3:02d}:{4:02d}".format(now[0], now[1], now[2], now[3], now[4])
        ses.refresh_session(ses.extractFromCookie(request), True)
        return await render_template("{}generic.html".format(c.adm), 
                content="Before sync: {0} and After sync: {1}".format(before, after),
                leftmenu=nav_links, enabled_modules=active_modules )
    return await f(request, ses) 
