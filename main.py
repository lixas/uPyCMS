import gc, uasyncio, os, sys, time, machine, network  # type: ignore comment;
import libs.PyDB as mdb  # type: ignore comment;
from libs import session as ses
from libs.phew import server
from libs.phew.template import render_template  # type: ignore comment;
import libs.phew.logging as logging  # type: ignore comment;
import conf as c
from modules.common import admin_required, file_exists, error_page, active_modules
gc.collect()

sys.path.append("/pages/codes") # users modules
blog_rows_index = []

sta_if = network.WLAN(network.STA_IF)
if not sta_if.isconnected():
    sta_if.active(True)
    available_wifi = False
    for net in sta_if.scan():
        net = net[0].decode("utf-8") 
        if net in c.wifi:
            available_wifi = net
            break
    if available_wifi:
        sta_if.connect(available_wifi, c.wifi[available_wifi])
        while not sta_if.isconnected():
            pass
        ip = sta_if.ifconfig()[0]
        logging.debug("> Server IP: {}".format(ip))
    else:
        ap = network.WLAN(network.AP_IF)
        ap.active(True)
        ap.config(essid='uPyCMS')

        while ap.active() == False:
            pass
        ip = ap.ifconfig()[0]
        logging.warn("> Started on Access point mode.")
        logging.info("> Loading captive portal")
        from libs.phew import captive_portal
        captive_portal.dns.run_catchall(ip)
        logging.info("> Connect to wifi 'uPyCMS' and open IP {}".format(ip))

gc.collect()

SDCard_available=False
try:
    os.mount(machine.SDCard(slot=2, width=1, sck=machine.Pin(14), miso=machine.Pin(2), mosi=machine.Pin(15), cs=machine.Pin(13), freq=20000000), "/sd")
    SDCard_available=True
except:
    pass


@server.route("/static/<resource>")
def serve(_, resource):
    resource = resource.replace("../", "")
    staticlist = os.listdir("/themes/static/")
    # gzipped exist? If found- send them first
    if "{}.gz".format(resource) in staticlist:
        return server.serve_file("themes/static/{}.gz".format(resource), {"Content-encoding": "gzip"})
    # non-gzipped exists ?
    elif resource in staticlist:
        return server.serve_file("themes/static/{}".format(resource))
    else:
        return "HTTP-404 Resource Not found", 404

@server.route("/favicon.ico")
def favicon(request):
    return serve(request, "favicon.ico")


class Front():
    @server.route("/")
    async def index(request):
        async def f(request):
            index_file = "/pages/index.md"
            if not file_exists(index_file):
                with open(index_file, "w") as f:
                    f.write("# Your index file\nFill it with your data [here](/admin/page/edit/index)")

            with open(index_file, "r") as f:
                await render_template(c.frn_head)
                await render_template("{}page.html".format(c.frn), content=f.read(), title="Index")
                return await render_template(c.frn_foot)
        return await f(request)

    # render blog list
    @server.route("/blog")
    async def blog(request):
        async def f(request):
            global blog_rows_index
            tbl = mdb.Database.open("database").open_table("blogs")

            if len(blog_rows_index) < 1:
                for rec in tbl.scan(None, True):
                    blog_rows_index.append(rec['_row'])
                blog_rows_index.reverse()
            #paging logic
            page = int(request.query.get("page", 1))
            begin = (page-1)*c.blogs_per_page
            end = page*c.blogs_per_page

            next_enabled=True
            if end > len(blog_rows_index):
                next_enabled=False

            await render_template(c.frn_head)
            for blog_row in blog_rows_index[begin:end]:
                dt = tbl.find_row(blog_row)
                path = "/blogs/{0}/{1}.md".format(dt["d"]["path"], dt["r"])
                if(file_exists(path)):
                    with open(path) as f:
                        if(int(dt["d"]["size"])) > c.blog_list_content_size:
                            await render_template("{}blog-list-chunk.html".format(c.frn), 
                                    data=[blog_row, dt["d"]["title"],
                                    "{}&#8230;".format(f.read(c.blog_list_content_size)), 
                                    dt["d"]["published"], dt["d"]["readtime"]])
                        else:
                            await render_template("{}blog-list-chunk.html".format(c.frn), 
                                    data=[blog_row, dt["d"]["title"], 
                                    f.read(),
                                    dt["d"]["published"], dt["d"]["readtime"]])
            
            await render_template("{}blog-list-page.html".format(c.frn), page = page, next_enabled = next_enabled)
            return await render_template(c.frn_foot)
        return await f(request)

    # render blog post into template
    @server.route("/blog/<post_id>")
    def blog_post(request, post_id):
        global blog_rows_index

        tbl = mdb.Database.open("database").open_table("blogs")

        if len(blog_rows_index) < 1:
            for rec in tbl.scan(None, True):
                blog_rows_index.append(rec['_row'])
            blog_rows_index.reverse()

        if int(post_id) not in blog_rows_index:
            return error_page(404), 404
        data = tbl.find_row(int(post_id))
        path = "/blogs/{0}/{1}.md".format(data["d"]["path"], data["r"])
        if(file_exists(path)):
            with open(path) as f:
                return render_template("{}blog-f.html".format(c.frn), content=f.read(), title=data["d"]["title"], readtime=data["d"]["readtime"], published=data["d"]["published"])
        else:
            return error_page(404), 404

    # render requested codepage
    @server.route("/code/<codepage>", methods=["GET", "POST"])
    def code_page(request, codepage):
        # content handler
        def ch(code_data, method):
            if not code_data:
                return "Error", "Module not found"
            if not code_data["enabled"]:
                return "Error", "Module is disabled"
            if code_data["methods"].find(method) < 0:
                return "Error", "Module is not accessible via '{}' method".format(method)
            # all good, handle user module
            title = code_data["title"]
            user_mod_name = "{0}".format(code_data["exec_path"])
            user_mod = __import__(user_mod_name)         # type: ignore comment;
            content = str(user_mod.HTML) or "User module did not return anything in <b>HTML</b> variable"
            del(sys.modules[user_mod_name])
            return title, content

        code_data = mdb.Database.open("database").open_table("codepages").find({"hyperlink": codepage})
        if not code_data:
            return error_page(404), 404
        else:
            title, content = ch(code_data, request.method)
            return render_template("{}page-f.html".format(c.frn), content=content, title=title)

    @server.route("/page/<staticpage>")
    def static_page(request, staticpage):
        if file_exists("/pages/{0}.md".format(staticpage)):
            with open("/pages/{0}.md".format(staticpage)) as f:
                return render_template("{}page-f.html".format(c.frn), content=f.read()),
        else:
            return error_page(404), 404

class Admin():

    # TODO do not forget to remove
    @server.route("/admin/make")
    def _make(request):
        follow = request.query.get("follow", "/admin")
        return render_template("{}redirect.html".format(c.adm), location=follow), 200, "text/html", {"set-cookie": "PhewSession={}; Path=/".format(ses.create(request.peer["ip"], {"isAdmin":1, "user":1}))}

    # render admin dashboard
    @server.route("/admin")
    async def a_index(request):
        def fs(path = "/") -> dict:
            def color(used, available):
                percent = (used / available) * 100
                if percent < 50:
                    blue = 255 * (1 - (2 * (percent / 100)))
                    green = 255 * (2 * (percent / 100))
                    return '#00{:02x}{:02x}'.format(int(green), int(blue))
                elif percent < 75:
                    red = 255 * ((percent - 50) / 25)
                    green = 255
                    return '#{:02x}{:02x}00'.format(int(red), int(green))
                else:
                    red = 255
                    green = 255 * (1 - ((percent - 75) / 25))
                    return '#{:02x}{:02x}00'.format(int(red), int(green))
            if path is not None:        # real path
                stat = os.statvfs(path)
                size = stat[0] * stat[2]
                used = size - stat[0] * stat[3]
            else:                       # RAM
                used, free = gc.mem_alloc(), gc.mem_free()
                size = used+free
            return {"used": used, "total": size, "color": color(used, size)}

        @admin_required
        async def f(request):
            global server
            bytes_sent, req_stat = server.get_stats()
            now = time.localtime()
            await render_template(c.adm_head, leftmenu=[], enabled_modules=active_modules)
            await render_template("{}admin.html".format(c.adm),
                ram=fs(None),
                fs=fs("/"),
                sd=fs("/sd") if SDCard_available else {"used":0, "total":0, "color": "000000"},
                servertime = "{0}-{1:02d}-{2:02d} {3:02d}:{4:02d}".format(now[0], now[1], now[2], now[3], now[4]),
                bytes_sent = str(bytes_sent),
                req_stats = req_stat
            )
            return await render_template(c.adm_foot)

        return await f(request)

    @server.route("/admin/login", methods=["POST"])
    def a_login(request):
        username = request.form.get("username", None)
        password = request.form.get("password", None)
        result = mdb.Database.open("database").open_table("users").find({"login": username, "pass": password})
        if result:
            return render_template("{}redirect.html".format(c.adm), location="/admin"), 200, "text/html", {"set-cookie": "PhewSession={0}; Path=/".format(ses.create(request.peer.ip, {"isAdmin":result["isadmin"], "user":1}))}
        else:
            return render_template(c.adm_login)

    @server.route("/admin/logout")
    def a_logout(request):
        return render_template("{}redirect.html".format(c.adm), location="/"), 200, "text/html", {"set-cookie": f"PhewSession=None; Path=/"}

    @server.route("/admin/new/<obj>")
    async def a_new(request, obj):
        @admin_required
        async def f(request, obj):
            if obj == "blog":
                from modules.blogs import blog_links
                await render_template(c.adm_head, leftmenu=blog_links, enabled_modules=active_modules)
                await render_template("/modules/blogs/blog-edit.html", blog_data=[0, "", ""])

            elif obj == "code":
                from modules.codes import code_links
                await render_template(c.adm_head, leftmenu=code_links, enabled_modules=active_modules)
                await render_template("/modules/codes/code-edit.html", code_data=[ 0, "", "", "", False, "def myAdder(x):\n  result = x**x + x**x\n  return result\n\n# HTML variable is used by caller to show final code\nHTML = 'Answer is {}'.format(myAdder(4))"])

            elif obj == "page":
                from modules.pages import page_links
                await render_template(c.adm_head, leftmenu=page_links, enabled_modules=active_modules)
                await render_template("{}page-edit.html".format(c.adm), page_data=["", ""])

            elif obj == "table":
                from modules.database import database_links
                await render_template(c.adm_head, leftmenu=database_links, enabled_modules=active_modules)
                await render_template("/modules/database/db-tbl-create.html",
                    new_tbl_name = request.query.get("t", "") )
            elif obj == "row":
                from modules.database import database_links
                await render_template(c.adm_head, leftmenu=database_links, enabled_modules=active_modules)
                tbl = request.query.get("t", None)
                if tbl:
                    await render_template("/modules/database/db-row-begin.html", table=tbl)  # new row begin
                    #each field
                    for name, prop in mdb.Database.open("database").open_table(tbl).columns.items():
                        length = prop["max_length"] if prop["data_type"] == "str" else ""
                        # await render_template("/modules/database/db-row-{}.html".format(prop["data_type"]), name=name, maxlength=length)
                        await render_template("/modules/database/db-row.html", data_type=prop["data_type"], name=name, maxlength=length)
                    # buttons
                    await render_template("/modules/database/db-row-end.html")
            else:
                await render_template(c.adm_head, leftmenu=[], enabled_modules=active_modules)

            return await render_template(c.adm_foot)
        return await f(request, obj)


# always import modules management
from modules import mods

for mod in active_modules:
    __import__("modules.{}".format(mod))      # type: ignore comment;

# ----------------------------------------------------------------
@server.catchall()
def catchall(request):
    return error_page(404), 404

loop = uasyncio.get_event_loop()
loop.create_task(ses.clear_ended())
server.run()                            # Run the server. Nothing executed below this line
