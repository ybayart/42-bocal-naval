# coding=utf-8

""" api42.py : Connect, use and scrap 42 API """
__author__ = "Jérémy 'Jpeg' Peguet"
__version__ = "1.0"
__email__ = "jpeg@42.fr"
__status__ = "Prod"

# IMPORTS  #####################################################################
from api42config import LOGIN, TOKEN_URL, ENDPOINT, PROGRESS_BAR, PER_PAGE, PARAMS, VERBOSE, RAISE
import sys, os, requests, json, re, errno, math, time, logging
from multiprocessing import cpu_count
from pathos.multiprocessing import ProcessingPool as Pool
from tqdm import tqdm
from pprint import pprint

from pygments import highlight
from pygments.lexers import JsonLexer
from pygments.style import Style
from pygments.formatters import Terminal256Formatter
from pygments.token import Keyword, Name, Comment, String, Error, Number, Operator, Generic

LOG = logging.getLogger(__name__)
logging.basicConfig(filename="api.log", level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

requests.packages.urllib3.disable_warnings()

# COLORS
def red(str): return "\033[91m{}\033[0m".format(str)
def green(str): return "\033[92m{}\033[0m".format(str)
def yellow(str): return "\033[93m{}\033[0m".format(str)
def blue(str): return "\033[94m{}\033[0m".format(str)
def pink(str): return "\033[95m{}\033[0m".format(str)

class MyStyle(Style):
    default_style = ""
    styles = {
                Comment:        'italic #888',
                Keyword:        'bold #00b2ba',
                Name:           '#cc6666',
                Name.Function:  '#0f0',
                Name.Class:     'bold #0f0',
                String:         '#f0c674',
                Number:         '#00b2ba',
    }

# EXCEPTIONS ###################################################################
class IntraUserError(Exception):
    pass

class IntraServerError(Exception):
    pass

def error(str):
    LOG.error(str)
    if VERBOSE:
        print(str)

def warn(str):
    LOG.warning(str)
    if VERBOSE:
        print(str)

def info(str):
    LOG.info(str)
    if VERBOSE:
        print(str)


# TOOLS #########################################################################
def get_token():
    ret = requests.post(TOKEN_URL, PARAMS)
    if ret.status_code == 200:
        return json.loads(ret.content.decode("utf-8"))["access_token"]
    if ret.status_code >= 400 and ret.status_code < 500:
        error(
            red(
                "Error token 🎟 is None, check your env API_CLIENT and API_SECRET keys 🔑 or specify a token= in parameter"
            )
        )
        raise IntraUserError(ret, ret.text)
    elif ret.status_code >= 500:
        warn(red("INTRA DOWN ✂"))
        raise IntraServerError(ret, ret.text)


# API CLASS ####################################################################
class api:
    def __init__(self, token=None):
        self.token = token if token else get_token()
        self.endpoint = ENDPOINT
        self.methods = {
            "get": self.rget,
            "put": self.rput,
            "patch": self.rpatch,
            "post": self.rpost,
            "delete": self.rdelete,
        }
        if self.token is not None:
            self.header = {
                "Authorization": "Bearer {}".format(self.token),
            }
        else:
            error(
                "Error token 🎟 is None, check your env API_CLIENT and API_SECRET keys 🔑 or specify a token= in parameter"
            )

    def rget(self, params, **kwargs):
        return requests.get(
            "{}/{}".format(self.endpoint, params), headers=self.header, **kwargs
        )

    def rpost(self, params, **kwargs):
        return requests.post(
            "{}/{}".format(self.endpoint, params), headers=self.header, **kwargs
        )

    def rpatch(self, params, **kwargs):
        return requests.patch(
            "{}/{}".format(self.endpoint, params), headers=self.header, **kwargs
        )

    def rdelete(self, params, **kwargs):
        return requests.delete(
            "{}/{}".format(self.endpoint, params), headers=self.header, **kwargs
        )

    def rput(self, params, **kwargs):
        return requests.put(
            "{}/{}".format(self.endpoint, params), headers=self.header, **kwargs
        )

    def get(self, params, **kwargs):
        return self.manage_err("get", params, **kwargs)

    def post(self, params, **kwargs):
        return self.manage_err("post", params, **kwargs)

    def patch(self, params, **kwargs):
        return self.manage_err("patch", params, **kwargs)

    def delete(self, params, **kwargs):
        return self.manage_err("delete", params, **kwargs)

    def put(self, params, **kwargs):
        return self.manage_err("put", params, **kwargs)

    # ERRORS MANAGEMENT ########################################################

    def manage_err(self, mode, params, **kwargs):
        while True:
            if mode in self.methods:
                cmd = self.methods[mode]
                res = cmd(params, **kwargs)
            rc = res.status_code
            rs = res.headers["Status"]
            if rc == 429:
                LOG.info(
                    "[{}] 🏃  {}:{}/{}".format(
                        red(rs), mode.upper(), blue(ENDPOINT), yellow(params)
                    )
                )
                time.sleep(float(res.headers["Retry-After"]))
                continue
            if rc >= 400 and rc < 500:
                if (
                    rc == 401
                    and json.loads(res.content)["message"] == "The access token expired"
                ):
                    LOG.info(
                        "[{}] 🔑  {}:{}/{}".format(
                            yellow(rs), mode.upper(), blue(ENDPOINT), yellow(params)
                        )
                    )
                    LOG.info(
                        "{} >>> {}".format(
                            red("The Access Token expired.."), green("Renewing !")
                        )
                    )
                    self.__init__()
                    return self.manage_err(mode, params, **kwargs)
                error(
                    "[{}] ⚙️   {}:{}/{}".format(
                        red(rs), mode.upper(), blue(ENDPOINT), yellow(params)
                    )
                )
                if RAISE:
                    raise IntraUserError(rc, rs, res.content, res.headers)
            elif rc >= 500:
                warn(
                    "[{}] 📡  {}:{}/{}".format(
                        yellow(rs), mode.upper(), blue(ENDPOINT), yellow(params)
                    )
                )
                return self.manage_err(mode, params, **kwargs)
                if RAISE:
                    raise IntraServerError(rc, rs, res.content, res.headers)
            elif 400 > rc > 0:
                LOG.info(
                    "[{}]  {}:{}/{}".format(
                        green(rs), mode.upper(), blue(ENDPOINT), yellow(params)
                    )
                )
            return res

    # REQUESTS MANAGEMENT ######################################################

    def roket(self, qr):
        req = self.get(qr)
        try:
            return json.loads(req.content.decode("utf-8"))
        except ValueError:
            warn(yellow("Empty"))
            return {}

    def proket(self, qr):
        return json.dumps(self.roket(qr), indent=4)

    def pproket(self, json):
        print(highlight(json, JsonLexer(), Terminal256Formatter(style=MyStyle)))

    def ppheader(self, qr):
        pprint(dict(self.get(qr).headers))

    def ppreq(self, req):
        print(req.headers["Status"])
        try:
            self.pproket(
                str(json.dumps(json.loads(req.content.decode("utf-8")), indent=4))
            )
        except json.decoder.JSONDecodeError:
            print("Empty JSON returned !")

    def get_pmax(self, qr):
        try:
            return int(
                re.search(
                    r"page=\b[^&]*(.*?)", str(self.get(qr).headers["Link"])
                ).group(0)[5:]
            )
        except KeyError:
            return 1

    def get_qsep(self, qr):
        return "?" if qr.find("?") < 0 else "&"

    # TOOLS ###############################################################

    def jload(self, path, perms):
        with open(path, perms) as f:
            data = json.load(f)
            f.close()
            return data

    def join_json_pages(self, name, pages, element=False):
        with open(name, "w") as outfile:
            if element:
                outfile.write("[")
            for page in pages:
                outfile.write(page)
        try:
            with open(name, "r") as infile:
                fdata = infile.read()
                fdata = fdata.replace("][", ",")
                fdata = fdata.replace("][{", ",{")
                if element:
                    fdata = fdata.replace("}{", "},{")
            with open(name, "w") as infile:
                infile.write(fdata)
                if element:
                    infile.write("]")
            return self.jload(name, "r")
        except ValueError:
            return 0

    # FUNCS ####################################################################

    def who_am_i(self, opt=None):
        print(yellow("🔐  Loading in progress.. 🌍\n"))
        self.me = LOGIN
        self.me_r = self.get("users/{}".format(self.me))
        self.user = json.loads(self.me_r.content.decode("utf-8"))
        me = self.me_r.headers
        self.my_id = str(self.user["id"])
        self.roles = me["X-Application-Roles"].split(";")
        scopes = PARAMS["scope"].split(" ")
        if opt is not None and "v" in opt:
            print(
                ">>> {} {}\n".format(
                    green(me["X-Application-Name"]), yellow(me["X-Application-Id"])
                )
            )
            print("Roles :")
            for role in self.roles:
                print("- {}".format(red(role)))
            print("")
            print("Scopes :")
            for scope in scopes:
                print("* {}".format(yellow(scope)))
            print("")

    def reqlaunch(self, req):
        LOG.info("[ 🚀  ] {}/{}".format(blue(ENDPOINT), yellow(req)))
        json = self.proket(req)
        return str(json)

    def prepare_reqs(self, qr):
        sep = self.get_qsep(qr)
        page_max = self.get_pmax("{}{}per_page={}".format(qr, sep, PER_PAGE)) + 1
        LOG.info(
            "[ 📄  ] {} page(s) for {}/{}".format(
                yellow(page_max - 1), blue(ENDPOINT), yellow(qr)
            )
        )
        reqs = []
        for page in range(1, page_max):
            req = qr + self.get_qsep(qr) + "page={}&per_page={}".format(page, PER_PAGE)
            reqs.append(req)
        return reqs, page_max

    def scrapper(self, qr, opt=None):
        """
        Prepare requests for all pages and multiprocess simultaneous GETs with error management.
        ~ return data of all pages of a qr as one json data ~
        options: - 'v' : progress_bar
                 - 'vv' : colored json pages
                 - 'json' : output a file.json named as qr
        """

        opt = "" if opt is None else opt
        self.opt = opt
        pool = Pool(processes=cpu_count())
        reqs, page_max = self.prepare_reqs(qr)
 
        pages = []
        if "v" in opt:
            start_time = time.time()
            with tqdm(total=page_max - 1) as pbar:
                for i, res in tqdm(enumerate(pool.imap(self.reqlaunch, reqs))):
                    pages.append(res)
                    pbar.update()
                    if "vv" in self.opt:
                        self.pproket(res)
            elapsed_time = time.time() - start_time
        else:
            pages = pool.map(self.reqlaunch, reqs)

        pool.close()
        pool.clear()

        name = qr.replace("/", "_") + ".json"
        data = self.join_json_pages(name, pages)
        if "v" in opt and data:
            print(green("⏱ Time elapsed : {}".format(yellow(elapsed_time))))
            print(
                green(
                    "📂 Scrolled {} pages for a total amount of {} datas".format(
                        blue(page_max - 1), yellow(len(data))
                    )
                )
            )
        if "json" not in opt:
            os.remove(name)
        return data
