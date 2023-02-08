from . import PyDB as mdb

class D(mdb.Database):
    pass

class T(mdb.Table):

    # def insert(self, data: any) -> bool:
    #     super().insert(data)
    #     self.index(True)
    
    # def delete(self, query_conditions: dict) -> bool:
    #     super().delete(query_conditions)
    #     self.index(True)
    
    # def delete_row(self, row_id: int):
    #     super().delete_row(row_id)
    #     self.index(True)
    
    # def truncate(self):
    #     super().truncate()
    #     self.index(True)

    def index_get(self, regenerate=False):
        if regenerate:
            with open("{}/rows.index".format(self.path), 'w') as f:
                for rec in self.scan(None, True):
                    f.write(" {}".format(rec['_row']))
        with open("{}/rows.index".format(self.path), 'r') as f:
            return f.read().strip().split(" ")


    def index_add(self, id):
        if id:
            with open("{}/rows.index".format(self.path), 'w') as f:
                for rec in self.scan(None, True):
                    f.write(" {}".format(rec['_row']))
        with open("{}/rows.index".format(self.path), 'r') as f:
            return f.read().strip().split(" ")

    def index_del(self, id):
        pass