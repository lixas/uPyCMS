import json  # type: ignore comment;
import libs.PyDB as mdb  # type: ignore comment;
from libs.phew import server
from libs.phew.template import render_template, render_template_noreplace  # type: ignore comment;
import conf as c
from modules.common import admin_required, active_modules

database_links=[
        "Manage data tables", [
        ["List Tables",     "/admin/database",                   "fa-solid fa-list-ul"],
        ["Create table",    "/admin/new/table",                  "fa-solid fa-table-list"],
        ["Show schema",     "/admin/database/table?act=schema",  "fa-solid fa-sitemap"],
        ["Query data",      "/admin/database/table?act=query",   "fa-solid fa-clipboard-question"],
        ["Insert data",     "/admin/database/table?act=insert",  "fa-solid fa-plus"],
    ]]

@server.route("/admin/database")
async def a_database(request):
    @admin_required
    async def f(request):
        data=[]
        for table_name in mdb.Database.open("database").list_tables():
            stats = mdb.Database.open("database").open_table(table_name).stats()
            data.append([
                table_name,                 # 0
                len(stats["Columns"]),      # 1
                stats["Data_Size"],         # 2
                stats["Pages_Count"],       # 3
                stats["Current_row"]        # 4
            ])
        await render_template(c.adm_head, leftmenu=database_links, enabled_modules=active_modules)
        await render_template("{}/database.html".format(__path__), tlist = data )
        return await render_template(c.adm_foot)
    return await f(request)


@server.route("/admin/database/table")
async def a_database_tbl(request):
    @admin_required
    async def f(request):
        action = request.query.get("act", None)
        tables = mdb.Database.open("database").list_tables()

        await render_template(c.adm_head, leftmenu=database_links, enabled_modules=active_modules)
        await render_template("{}/db-tbl-choose.html".format(__path__), tbl = tables, action=action)
        return await render_template(c.adm_foot)
    return await f(request)


@server.route("/admin/database/schema/<table>")
async def a_db_schema(request, table):
    @admin_required
    async def f(request, table):
        if table not in mdb.Database.open("database").list_tables():
            return await render_template_noreplace("{}generic.html".format(c.adm),
                leftmenu=database_links,
                content="Table '{}' was not found".format(table),
                enabled_modules=active_modules
            )
        data=[]
        cur_tbl = mdb.Database.open("database").open_table(str(table))
        for name, prop in cur_tbl.columns.items():
            length = prop["max_length"] if prop["data_type"] == "str" else ""
            data.append({
                "Name": name,
                "Type": prop["data_type"],
                "Length": length
            })
        tdef = {}
        tdef["per-page"]= cur_tbl.rows_per_page
        tdef["max"]= cur_tbl.max_rows
        del(cur_tbl)        # clear some RAM ~6kb

        await render_template(c.adm_head, leftmenu=database_links, enabled_modules=active_modules)
        await render_template("{}/db-schema.html".format(__path__),
            table = str(table),
            tdef = tdef,
            clist = data
        )
        return await render_template(c.adm_foot)
    return await f(request, table)


@server.route("/admin/database/query/<table>", methods=["GET", "POST"])
async def a_db_query(request, table, **kwargs):
    @admin_required
    async def f(request, table, **kwargs):
        jump_to_table = []
        current_table_found = False
        for tb in mdb.Database.open("database").list_tables():
            if tb == table:
                jump_to_table.append([tb, 1])
                current_table_found = True
            else:
                jump_to_table.append([tb, 0])

        if not current_table_found:
            return await render_template_noreplace("{}generic.html".format(c.adm),
                leftmenu=database_links,
                content="Table '{}' was not found".format(table),
                enabled_modules=active_modules
            )
        cur_tbl = mdb.Database.open("database").open_table(str(table))

        columns=[]
        try:
            # maybe we come here from other function and kwargs for  colums order is set 
            columns = json.loads(request.form.get("sorted", None)) if "columnsOrder" not in kwargs.keys() else json.loads(kwargs["columnsOrder"])
        except:
            columns = []
            for col in cur_tbl.columns.keys():
                columns.append({"n": col, "v": 1})

        columns_enabled =  [item['n'] for item in columns if item['v'] == 1]
        # maybe we come here from other function and kwargs for query string is set 
        query_string = request.form.get("query", None) if "returnQuery" not in kwargs.keys() else kwargs["returnQuery"]
        
        error = ""
        query = ""
        if query_string:
            try:
                t="true"
                f="false"
                query = json.loads(query_string.replace("True", t).replace("True", t).replace("False", f).replace("FALSE", f))
            except ValueError:    # type: ignore comment;    # malformed JSON query
                error = "Malformed query: {}".format(query_string)
        
        result=[]
        do = request.form.get("do", None) if "do" not in kwargs.keys() else kwargs["do"]
        if not error and do:
            from ucollections import OrderedDict
            for data_row in cur_tbl.scan(query, True):
                ordered_data = OrderedDict(data_row)
                row = [ordered_data[field] for field in ['_row'] + columns_enabled]
                result.append(row)

        del(cur_tbl)        # clear some RAM ~6kb

        await render_template(c.adm_head, leftmenu=database_links, enabled_modules=active_modules)
        await render_template_noreplace("{}/db-query.html".format(__path__),
            table_jump = jump_to_table,
            table = str(table),
            error_msg=error,
            columns= columns,
            last_query = query_string)
        await render_template_noreplace("{}/db-query-result.html".format(__path__),
            table = str(table),
            columns= columns,
            dlist = result)
        return await render_template(c.adm_foot)
    return await f(request, table, **kwargs)

@server.route("/admin/database/row/save", methods=["POST"])
async def a_db_row_save(request):
    @admin_required
    async def f(request):
        tbl_name = request.form.get("tablename", None)
        if not tbl_name:
            return "error, table not known"
        if tbl_name not in mdb.Database.open("database").list_tables():
            return await render_template_noreplace("{}generic.html".format(c.adm),
                leftmenu=database_links,
                content="Table '{}' was not found".format(tbl_name),
                enabled_modules=active_modules
            )
        
        table_obj = mdb.Database.open("database").open_table(tbl_name)
        tbl_data = {}
        tbl_cols = table_obj.columns.items()

        for col, prop in tbl_cols:
            if prop["data_type"] == "bool":
                tbl_data[col] = bool(request.form.get("f-{}".format(col), None))
            elif prop["data_type"] == "float":
                tbl_data[col] = float(request.form.get("f-{}".format(col), None))
            elif prop["data_type"] == "int":
                tbl_data[col] = int(request.form.get("f-{}".format(col), None))
            else:
                tbl_data[col] = request.form.get("f-{}".format(col), None)

        if not table_obj.insert(tbl_data):
            # report unsuccessful insert
            print("report unsuccessful insert")
            pass

        # if request.form.get("continue-insert", None) == "1":
        #     print("Vyksta redirektas, pilnas")
        #     return render_template("{}redirect.html".format(c.adm), location="/admin/new/row?t={}".format(tbl_name)), 200, "text/html", {}

        return await a_database(request)
    return await f(request)


@server.route("/admin/database/del-rows/<table>", methods=["POST"])
async def a_db_del_row(request, table):
    @admin_required
    async def f(request, table):
        if table not in mdb.Database.open("database").list_tables():
            return await render_template_noreplace("{}generic.html".format(c.adm),
                leftmenu=database_links,
                content="Table '{}' was not found".format(table),
                enabled_modules=active_modules
            )

        cur_tbl = mdb.Database.open("database").open_table(str(table))
        ids = request.form.get("_rid[]", None)
        if ids is not None:
            for rid in ids:
                cur_tbl.delete_row(int(rid))

        columnsOrderDelete = request.form.get("columnsOrderDelete", None)
        returnQueryDelete = request.form.get("returnQueryDelete", None)

        return await a_db_query(request, table, columnsOrder=columnsOrderDelete, returnQuery=returnQueryDelete, do=1)
    return await f(request, table)


@server.route("/admin/database/new_tbl/save", methods=["POST"])
async def a_db_tbl_save(request):
    @admin_required
    async def f(request):
        tbl_def_dict = {}
        tbl_name = request.form.get("tbl_name", None)
        for def_row in request.form.get("tbl_def", "").split("\n"):
            col, type = def_row.strip().split(" ")

            if type=="str":
                tbl_def_dict[col] = str
            elif type=="int":
                tbl_def_dict[col] = int
            elif type=="bool":
                tbl_def_dict[col] = bool
            elif type=="float":
                tbl_def_dict[col] = float

        mdb.Database.open("database").create_table(tbl_name, tbl_def_dict)    
        return await a_database(request)
    return await f(request)


@server.route("/admin/database/drop/<table>")
async def a_db_drop(request, table):
    @admin_required
    async def f(request, table):
        if table not in mdb.Database.open("database").list_tables():
            return await render_template_noreplace("{}generic.html".format(c.adm),
                leftmenu=database_links,
                content="Table '{}' was not found".format(table),
                enabled_modules=active_modules
            )
        cur_tbl = mdb.Database.open("database").open_table(str(table))
        cur_tbl.drop()
        del(cur_tbl)        # clear some RAM ~6kb
        return await a_database(request)
    return await f(request, table)
