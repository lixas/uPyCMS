import os  # type: ignore comment;
from io import StringIO
from libs.phew import server
from libs.phew.template import render_template  # type: ignore comment;
import conf as c
from modules.common import admin_required, isAdmin, active_modules

@server.route("/admin/console")
async def a_console(request):
    @admin_required
    async def f(request):
        await render_template(c.adm_head, leftmenu=[], enabled_modules=active_modules)
        await render_template("{}console.html".format(c.adm))
        return await render_template(c.adm_foot)
    return await f(request)


@server.route("/admin/console/ajax", methods=["POST"])
async def a_c_ajax(request):
    async def f(request):
        if not isAdmin(request):
            return await "Err: not authorized"

        # return await "Sorry, console feature is disabled for public demo use"
        code = str(request.form.get("code", None))
        print("--------- Console command ---------")
        print(code)
        print("-"*35)

        for codeline in code.split("\n"):
            await ">>> {0}\n".format(codeline)

        # Capture the output of the script
        output = StringIO()
        os.dupterm(output)
        # Execute the script
        try:
            exec(code)
        except BaseException as err:        # type: ignore comment;
            await str(err)
        finally:
            # Reset the stdout stream
            os.dupterm(None)
        
        return await output.getvalue()
    return await f(request)
