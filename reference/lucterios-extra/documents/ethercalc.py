# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import requests
import json
import re
import datetime
from logging import getLogger

basedate = datetime.date(1899, 12, 30)
basedatetime = datetime.datetime(1899, 12, 30)


def ss_to_xy(coordinate):
    """convert spreadsheet coordinates to zero-index xy coordinates.
    return None if input is invalid"""
    result = re.match(r'\$*([A-Z]+)\$*([0-9]+)', coordinate, re.RegexFlag.IGNORECASE)
    if result is None:
        return None
    xstring = result.group(1).upper()
    multiplier = 1
    posx = 0
    for i in xstring:
        posx = posx * multiplier + (ord(i) - 64)
        multiplier = multiplier * 26
    posx = posx - 1
    posy = int(result.group(2)) - 1
    return (posx, posy)


def _grid_size(cells):
    maxx = -1
    maxy = -1
    for coordinate, _value in cells.items():
        (posx, posy) = ss_to_xy(coordinate)
        maxx = max(posx, maxx)
        maxy = max(posy, maxy)
    return (maxx + 1, maxy + 1)


class EtherCalc(object):
    def __init__(self, url_root):
        self.root = url_root

    def get(self, cmd):
        r = requests.get(self.root + "/" + cmd, verify=False)
        r.raise_for_status()
        getLogger('ethercalc').debug('GET %s -> %s', r.url, r.content)
        return r

    def post(self, calc_id, data, content_type):
        r = requests.post(self.root + "/_" + calc_id, data=data, headers={"Content-Type": content_type}, verify=False)
        r.raise_for_status()
        getLogger('ethercalc').debug('POST %s (%s) -> %s', r.url, content_type, r.content)
        return r

    def put(self, calc_id, data, content_type):
        r = requests.put(self.root + "/_" + calc_id, data=data,
                         headers={"Content-Type": content_type}, verify=False)
        r.raise_for_status()
        getLogger('ethercalc').debug('PUT %s (%s) -> %s', r.url, content_type, r.content)
        return r

    def delete(self, calc_id):
        r = requests.delete(self.root + "/_/" + calc_id, verify=False)
        r.raise_for_status()
        getLogger('ethercalc').debug('DELETE %s -> %s', r.url, r.content)
        return r

    def cells(self, page, coord=None):
        api = ("_/%s/cells" % page)
        if coord is not None:
            api = api + "/" + coord
        return self.get(api).json()

    def command(self, page, command):
        r = requests.post(self.root + "/_/%s" % page, json={"command": command})
        r.raise_for_status()
        return r.json()

    def is_exist(self, calc_id):
        try:
            res = self.get('_exists/%s' % calc_id)
            return (res.content == b'true')
        except requests.exceptions.HTTPError:
            return False

    def new(self, calc_id):
        if calc_id is None:
            calc_id = ""
        else:
            calc_id = "/" + calc_id
        return self.put(calc_id, None, "text/x-socialcalc")

    def create(self, data, calc_format="python", calc_id=None):
        if calc_id is None:
            calc_id = ""
        else:
            calc_id = "/" + calc_id
        if calc_format == "python":
            return self.post(calc_id, json.dumps({"snapshot": data}), "application/json")
        elif calc_format == "json":
            return self.post(calc_id, data, "application/json")
        elif calc_format == "csv":
            return self.post(calc_id, data, "text/csv")
        elif calc_format == "socialcalc":
            return self.post(calc_id, data, "text/x-socialcalc")
        elif calc_format == "xlsx":
            return self.post(calc_id, data, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        elif calc_format == "ods":
            return self.post(calc_id, data, "application/vnd.oasis.opendocument.spreadsheet")

    def update(self, data, calc_format="python", calc_id=None):
        if calc_id is None:
            sid = ""
        else:
            sid = "/" + calc_id
        if calc_format == "python":
            return self.put(sid, json.dumps({"snapshot": data}), "application/json")
        elif calc_format == "json":
            return self.put(sid, data, "application/json")
        elif calc_format == "csv":
            return self.put(sid, data, "text/csv")
        elif calc_format == "socialcalc":
            if calc_id is None:
                upload = {"snapshot": data}
            else:
                upload = {"room": calc_id, "snapshot": data}
            return self.post(calc_id, json.dumps(upload), "application/json")
        elif calc_format == "xlsx":
            return self.put(sid, data, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        elif calc_format == "ods":
            return self.put(sid, data, "application/vnd.oasis.opendocument.spreadsheet")

    def _export_python(self, page):
        cells = self.cells(page)
        sizex, sizey = _grid_size(cells)
        grid = [[None for _ in range(sizex)] for _ in range(sizey)]
        for coordinate, value in cells.items():
            posx, posy = ss_to_xy(coordinate)
            if value['valuetype'] == 'n':
                grid[posy][posx] = float(value['datavalue'])
            elif value['valuetype'] == 'b':
                grid[posy][posx] = None
            elif value['valuetype'] == 'nd':
                grid[posy][posx] = basedate + datetime.timedelta(days=int(value['datavalue']))
            elif value['valuetype'] == 'ndt':
                grid[posy][posx] = basedatetime + datetime.timedelta(days=float((value['datavalue'])))
            else:
                grid[posy][posx] = str(value['datavalue'])
        return grid

    def export(self, page, calc_format="python"):
        if calc_format == "python":
            return self._export_python(page)
        elif calc_format == "json":
            return self.get("_/" + page + "/csv.json").content
        elif calc_format == "socialcalc":
            return self.get("_/" + page).content
        elif calc_format == "csv":
            return self.get(page + ".csv").content
        elif calc_format == "xlsx":
            return self.get(page + ".xlsx").content
        elif calc_format == "ods":
            return self.get(page + ".ods").content
        else:
            raise ValueError


if __name__ == "__main__":
    import pprint
    pp = pprint.PrettyPrinter(indent=4)
    e = EtherCalc("http://localhost:8000")
    pp.pprint(e.cells("test"))
    pp.pprint(e.cells("test", "A1"))
    pp.pprint(e.export("test"))
