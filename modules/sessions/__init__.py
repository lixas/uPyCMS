import time  # type: ignore comment;
import libs.PyDB as mdb  # type: ignore comment;
from libs.phew import server
from libs import session as ses
from libs.phew.template import render_template, render_template_noreplace  # type: ignore comment;
import conf as c
from modules.common import admin_required, active_modules

@server.route("/admin/sessions")
async def a_sessions(request):
    @admin_required
    async def f(request, seslib):
        if len(seslib.SERVER_SESSIONS) > 0:
            sl=[]
            for s in seslib.SERVER_SESSIONS:
                r = time.localtime(s[1])      # for readable time
                sl.append([
                    s[0],     # session key
                    "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(r[0], r[1], r[2], r[3], r[4], r[5]),
                    s[2],     # ip
                    s[3],     # data
                    True if s[0] == seslib.extractFromCookie(request) else False     # mark own session
                ])
            await render_template(c.adm_head, leftmenu=[], enabled_modules=active_modules)
            await render_template("{}/sessions.html".format(__path__), slist=sl)
            return await render_template(c.adm_foot)
        else:
            return await render_template_noreplace("{}generic.html".format(c.adm), 
                content="No sessions. Strange! How the hell you are here?",
                leftmenu=[], enabled_modules=active_modules )
    return await f(request, ses)
